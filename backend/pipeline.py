"""
pipeline.py - The complete edge processing flow for ONE document:

    file ──► extract text (OCR) ──► classify (TF-IDF + ML) ──► decision rules ──► route to folder ──► save history

Decision rules (abnormal input handling):
  * no / too little text          -> "unknown", Manual Review   (blank page, photo, unreadable scan)
  * unfamiliar vocabulary         -> "unknown", Manual Review   (out-of-domain text, e.g. a recipe)
  * confidence < threshold        -> "unknown", Manual Review   (model is not sure)
  * otherwise                     -> auto-routed to the predicted department
"""
import hashlib
import os
import time
import uuid

from werkzeug.utils import secure_filename

import config
import database
import extractor
import ocr
import router


def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def save_upload(file_storage):
    """Save an uploaded file (Flask FileStorage) to data/uploads with a unique name."""
    original = secure_filename(file_storage.filename) or "document"
    stored = f"{uuid.uuid4().hex[:12]}_{original}"
    path = os.path.join(config.UPLOAD_DIR, stored)
    file_storage.save(path)
    return path, original


def save_text(text):
    stored = f"{uuid.uuid4().hex[:12]}_pasted_text.txt"
    path = os.path.join(config.UPLOAD_DIR, stored)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path, "pasted_text.txt"


def decide(pred, text_len, extraction):
    """Apply business rules on top of the ML prediction. Returns (final_category, status, alerts)."""
    alerts = []
    if pred is None:
        alerts.append({"level": "danger", "message": "No readable text found (blank page, photo or unreadable scan). Sent to Manual Review."})
        return config.UNKNOWN_CATEGORY, "needs_review", alerts

    label = config.category_info(pred["category"])["label"]
    pct = round(pred["confidence"] * 100, 1)
    if pred["known_word_ratio"] < config.MIN_KNOWN_WORD_RATIO:
        alerts.append({"level": "danger", "message": f"Content does not look like any supported document type "
                       f"(only {round(pred['known_word_ratio'] * 100)}% familiar words). Sent to Manual Review."})
        final, status = config.UNKNOWN_CATEGORY, "needs_review"
    elif pred["confidence"] < config.CONFIDENCE_THRESHOLD:
        alerts.append({"level": "warning", "message": f"Low confidence: model suggests {label} at {pct}% "
                       f"(threshold {int(config.CONFIDENCE_THRESHOLD * 100)}%). Sent to Manual Review."})
        final, status = config.UNKNOWN_CATEGORY, "needs_review"
    else:
        final, status = pred["category"], "auto_routed"
        p = pred["probabilities"]
        if len(p) > 1 and p[0]["probability"] - p[1]["probability"] < 0.25:
            alerts.append({"level": "info", "message": f"Close call between {label} and "
                           f"{config.category_info(p[1]['category'])['label']}."})

    ocr_conf = extraction.get("ocr_confidence")
    if ocr_conf is not None and ocr_conf < config.LOW_OCR_QUALITY:
        alerts.append({"level": "warning", "message": f"Poor scan quality (OCR confidence {round(ocr_conf * 100)}%). Consider re-scanning."})
    if final == "identity_document":
        alerts.append({"level": "info", "message": "Contains personal identity data - routed to restricted KYC folder."})
    return final, status, alerts


def process_document(path, original_name, source, classifier):
    start = time.time()
    digest = file_hash(path)
    duplicate = database.find_by_hash(digest)

    extraction = ocr.extract_text(path)            # may raise ocr.ExtractionError
    text = extraction["text"]

    pred, classify_ms = None, 0.0
    if len(text) >= config.MIN_TEXT_CHARS:
        t0 = time.time()
        pred = classifier.predict(text)
        classify_ms = (time.time() - t0) * 1000

    final, status, alerts = decide(pred, len(text), extraction)
    if duplicate:
        alerts.insert(0, {"level": "warning", "message": f"Duplicate: identical file already processed as document #{duplicate['id']} ({duplicate['filename']})."})

    record = {
        "filename": original_name,
        "stored_name": os.path.basename(path),
        "file_ext": os.path.splitext(original_name)[1].lower().lstrip("."),
        "file_size": os.path.getsize(path),
        "file_hash": digest,
        "source": source,
        "extraction_method": extraction["method"],
        "ocr_confidence": extraction["ocr_confidence"],
        "pages": extraction["pages"],
        "text": text,
        "predicted_category": pred["category"] if pred else config.UNKNOWN_CATEGORY,
        "confidence": pred["confidence"] if pred else 0.0,
        "probabilities": pred["probabilities"] if pred else [],
        "top_terms": pred["top_terms"] if pred else [],
        "known_word_ratio": pred["known_word_ratio"] if pred else 0.0,
        "final_category": final,
        "department": config.category_info(final)["department"],
        "status": status,
        "alerts": alerts,
        "key_fields": extractor.extract_fields(text) if text else {},
        "extraction_ms": extraction["extraction_ms"],
        "classify_ms": round(classify_ms, 2),
        "model_version": classifier.version,
    }
    doc_id = database.insert_document(record)
    routed = router.route_file(path, final, doc_id, original_name)
    database.update_document(doc_id, routed_path=routed, total_ms=round((time.time() - start) * 1000, 1))
    return database.get_document(doc_id)


def review_document(doc_id, category):
    """Human-in-the-loop: confirm or correct a category and move the file to the right department."""
    doc = database.get_document(doc_id)
    if doc is None:
        return None
    status = "reviewed" if category == doc["predicted_category"] else "corrected"
    routed = router.reroute_file(doc["routed_path"], category, doc_id, doc["filename"])
    alerts = [a for a in (doc["alerts"] or []) if a["level"] == "info"]
    alerts.append({"level": "info", "message": f"Human {'confirmed' if status == 'reviewed' else 'corrected'} category as "
                   f"{config.category_info(category)['label']}."})
    database.update_document(doc_id, final_category=category, status=status, routed_path=routed,
                             department=config.category_info(category)["department"], alerts=alerts)
    return database.get_document(doc_id)
