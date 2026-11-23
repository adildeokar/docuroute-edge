"""
test_system.py - "Testing and explanation: test normal and abnormal or varied input cases."

Runs the REAL edge service code (Flask test client, real OCR, real model) against:
  1. Normal documents of every category (clean images, phone-style scans, PDFs, TXT)
  2. Abnormal inputs (blank page, photo, recipe text, corrupted file, wrong type, empty, duplicate, too large...)
  3. Human review flow (correction moves the file to another department)
  4. End-to-end accuracy on 32 held-out scanned images (OCR + model), with timings

It uses a temporary data folder, so your real history is not touched.
Results are written to  reports/test_report.md  and  reports/end_to_end.json

Run:  python test_system.py
"""
import glob
import io
import json
import os
import statistics
import sys
import tempfile
import time
from datetime import datetime

os.environ["EDGE_DATA_DIR"] = tempfile.mkdtemp(prefix="edge_test_")   # must be set before importing config

import config  # noqa: E402
from app import app, classifier  # noqa: E402
import ocr  # noqa: E402

client = app.test_client()
results = []


def record(group, name, passed, detail):
    results.append((group, name, passed, detail))
    print(f"  [{'PASS' if passed else 'FAIL'}] {name:42s} {detail}")


def upload(path, filename=None):
    with open(path, "rb") as f:
        data = f.read()
    return client.post("/api/classify", data={"file": (io.BytesIO(data), filename or os.path.basename(path)), "source": "test"},
                       content_type="multipart/form-data")


def sample(rel):
    return os.path.join(config.SAMPLES_DIR, rel)


def summary(r):
    j = r.get_json()
    if r.status_code != 200:
        return f"HTTP {r.status_code}: {j.get('error')}"
    return f"HTTP 200 -> {j['final_category']} ({j['confidence'] * 100:.1f}%) [{j['status']}] {j['total_ms']:.0f} ms"


def test_normal():
    print("\n1) NORMAL DOCUMENTS")
    for path in sorted(glob.glob(sample("normal/*"))):
        name = os.path.basename(path)
        expected = next(k for k in config.CATEGORIES if name.startswith(k))
        r = upload(path)
        j = r.get_json()
        ok = r.status_code == 200 and j["final_category"] == expected and j["status"] == "auto_routed" \
            and os.path.exists(os.path.join(config.ROUTED_DIR, j["routed_path"]))
        record("Normal", name, ok, summary(r))
    r = client.post("/api/classify", data={"text": "TAX INVOICE\nNova Supplies Co.\nInvoice No: INV-1001\nInvoice Date: 12/03/2026\n"
                                                   "Bill To: Apex Ltd\nDescription | Qty | Unit Price | Amount\nPrinter Toner | 4 | 250.00 | 1000.00\n"
                                                   "Subtotal 1000.00\nGST 180.00\nTotal Amount Due: 1180.00\nPayment Terms: Net 30"})
    record("Normal", "pasted invoice text", r.status_code == 200 and r.get_json()["final_category"] == "invoice", summary(r))


def test_abnormal():
    print("\n2) ABNORMAL / EDGE CASES")

    def expect_review(rel, why):
        r = upload(sample(rel))
        j = r.get_json()
        ok = r.status_code == 200 and j["status"] == "needs_review" and j["final_category"] == "unknown"
        record("Abnormal", f"{os.path.basename(rel)} ({why})", ok, summary(r))

    expect_review("abnormal/blank_page.png", "blank")
    expect_review("abnormal/landscape_photo.jpg", "not a document")
    expect_review("abnormal/very_little_text.png", "too little text")
    expect_review("abnormal/unrelated_recipe.txt", "out-of-domain")

    r = upload(sample("abnormal/ambiguous_invoice_receipt.png"))
    j = r.get_json()
    record("Abnormal", "ambiguous_invoice_receipt.png (mixed)", r.status_code == 200 and
           (j["status"] == "needs_review" or j["final_category"] in ("invoice", "receipt")), summary(r))
    # real receipts (SROIE) are titled "TAX INVOICE" and list GST, so a tiny snippet is genuinely ambiguous:
    # it must go to review or to the invoice desk, never be auto-routed to a wrong department
    r = client.post("/api/classify", data={"text": "INVOICE\nInvoice No: INV-1001\nSubtotal 1000.00\nGST 180.00\nTotal Amount Due: 1180.00"})
    j = r.get_json()
    record("Abnormal", "short invoice/receipt snippet (ambiguous)", r.status_code == 200 and
           (j["status"] == "needs_review" or j["final_category"] == "invoice"), summary(r))
    r = upload(sample("abnormal/very_blurry_scan.jpg"))
    j = r.get_json()
    record("Abnormal", "very_blurry_scan.jpg (poor quality)", r.status_code == 200 and
           j["final_category"] in ("medical_report", "unknown"), summary(r))

    r = upload(sample("abnormal/corrupted_file.png"))
    record("Abnormal", "corrupted_file.png (random bytes)", r.status_code == 422, summary(r))
    r = client.post("/api/classify", data={"file": (io.BytesIO(b"MZ\x90\x00binary"), "virus.exe")}, content_type="multipart/form-data")
    record("Abnormal", "virus.exe (unsupported type)", r.status_code == 415, summary(r))
    r = client.post("/api/classify", data={"file": (io.BytesIO(b""), "empty.png")}, content_type="multipart/form-data")
    record("Abnormal", "empty.png (0 bytes)", r.status_code == 422, summary(r))
    r = client.post("/api/classify", data={})
    record("Abnormal", "request without file or text", r.status_code == 400, summary(r))
    r = client.post("/api/classify", data={"file": (io.BytesIO(b"0" * (config.MAX_UPLOAD_MB + 1) * 1024 * 1024), "huge.pdf")},
                    content_type="multipart/form-data")
    record("Abnormal", f"huge.pdf (> {config.MAX_UPLOAD_MB} MB)", r.status_code == 413, f"HTTP {r.status_code}")

    r = upload(sample("normal/invoice_clean.png"))
    alerts = " ".join(a["message"] for a in r.get_json()["alerts"])
    record("Abnormal", "duplicate upload detected", "Duplicate" in alerts, alerts[:70])


def test_review_flow():
    print("\n3) HUMAN REVIEW / RE-ROUTING")
    j = upload(sample("abnormal/unrelated_recipe.txt")).get_json()
    r = client.post(f"/api/documents/{j['id']}/review", json={"category": "application_form"})
    d = r.get_json()
    ok = r.status_code == 200 and d["status"] == "corrected" and d["routed_path"].startswith("Applications_Desk") \
        and os.path.exists(os.path.join(config.ROUTED_DIR, d["routed_path"]))
    record("Review", "correct category -> file moved", ok, f"{j['routed_path']}  ->  {d['routed_path']}")
    r = client.post(f"/api/documents/{j['id']}/review", json={"category": "not_a_category"})
    record("Review", "invalid category rejected", r.status_code == 400, f"HTTP {r.status_code}")

    for ep in ["/api/health", "/api/stats", "/api/documents", "/api/departments", "/api/model", "/api/export.csv", "/api/samples"]:
        r = client.get(ep)
        record("API", f"GET {ep}", r.status_code == 200, f"HTTP {r.status_code}")


def test_end_to_end():
    print("\n4) END-TO-END ACCURACY ON HELD-OUT SCANNED IMAGES (OCR + MODEL)")
    images = sorted(glob.glob(os.path.join(config.OCR_TEST_DIR, "*.png")))
    correct, ocr_ms, cls_ms, rows = 0, [], [], []
    for path in images:
        expected = os.path.basename(path).split("__")[0]
        ext = ocr.extract_text(path)
        t0 = time.time()
        pred = classifier.predict(ext["text"])
        cls_ms.append((time.time() - t0) * 1000)
        ocr_ms.append(ext["extraction_ms"])
        hit = pred["category"] == expected
        correct += hit
        rows.append({"image": os.path.basename(path), "expected": expected, "predicted": pred["category"],
                     "confidence": pred["confidence"], "ocr_confidence": ext["ocr_confidence"], "ocr_ms": ext["extraction_ms"]})
        print(f"  {'OK ' if hit else 'XX '} {os.path.basename(path):32s} -> {pred['category']:18s} {pred['confidence'] * 100:5.1f}%  OCR {ext['extraction_ms']:.0f} ms")
    report = {
        "tested_at": datetime.now().isoformat(timespec="seconds"),
        "images": len(images),
        "correct": correct,
        "accuracy": round(correct / len(images), 4) if images else 0,
        "avg_ocr_ms": round(statistics.mean(ocr_ms), 1) if ocr_ms else 0,
        "avg_classify_ms": round(statistics.mean(cls_ms), 2) if cls_ms else 0,
        "results": rows,
    }
    with open(os.path.join(config.REPORTS_DIR, "end_to_end.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"  => {correct}/{len(images)} correct ({report['accuracy'] * 100:.1f}%), avg OCR {report['avg_ocr_ms']} ms, avg ML {report['avg_classify_ms']} ms")
    return report


def write_report(e2e):
    passed = sum(1 for r in results if r[2])
    lines = [f"# Test Report - Edge Document Classification & Routing", "",
             f"Run at {datetime.now():%Y-%m-%d %H:%M} · model v{classifier.version} ({classifier.model_name})", "",
             f"**Functional tests: {passed}/{len(results)} passed**  ",
             f"**End-to-end OCR + model accuracy: {e2e['correct']}/{e2e['images']} = {e2e['accuracy'] * 100:.1f}%** "
             f"(avg OCR {e2e['avg_ocr_ms']} ms, avg ML {e2e['avg_classify_ms']} ms per document)", "",
             "| Group | Test case | Result | Details |", "|---|---|---|---|"]
    lines += [f"| {g} | {n} | {'PASS' if p else 'FAIL'} | {d.replace('|', '/')} |" for g, n, p, d in results]
    lines += ["", "## End-to-end image results", "", "| Image | Expected | Predicted | Confidence | OCR conf. | OCR time |", "|---|---|---|---|---|---|"]
    lines += [f"| {r['image']} | {r['expected']} | {r['predicted']} | {r['confidence'] * 100:.1f}% | {r['ocr_confidence']} | {r['ocr_ms']:.0f} ms |" for r in e2e["results"]]
    with open(os.path.join(config.REPORTS_DIR, "test_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nFunctional tests: {passed}/{len(results)} passed. Report -> reports/test_report.md")
    return passed == len(results)


if __name__ == "__main__":
    print(f"Temporary data folder: {config.DATA_DIR}")
    test_normal()
    test_abnormal()
    test_review_flow()
    e2e = test_end_to_end()
    sys.exit(0 if write_report(e2e) else 1)
