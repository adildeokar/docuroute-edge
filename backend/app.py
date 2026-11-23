"""
app.py - The EDGE MICROSERVICE (Flask REST API) + serves the web dashboard.

Start:   python app.py      ->  open http://localhost:5000

HTTP API (used by the dashboard AND by the scanner simulator / any other app):
  GET    /api/health                      service + model status
  GET    /api/categories                  categories, departments, thresholds
  POST   /api/classify                    upload a file (field "file") or text (field "text") -> prediction + routing
  GET    /api/documents                   history (filters: search, category, status, department)
  GET    /api/documents/<id>              one document with full text
  GET    /api/documents/<id>/file         original file (preview / download)
  POST   /api/documents/<id>/review       human confirms / corrects category  {"category": "..."}
  POST   /api/documents/<id>/ai           optional OpenAI insights
  DELETE /api/documents/<id>              delete record + routed file
  GET    /api/stats                       dashboard numbers & charts
  GET    /api/departments                 department folders and their documents
  GET    /api/model                       training metrics, confusion matrix, model comparison
  POST   /api/model/retrain               retrain with human-verified documents (active learning)
  GET    /api/samples                     demo documents shipped with the project
  POST   /api/samples/classify            classify one demo document {"path": "normal/invoice_clean.png"}
  GET    /api/export.csv                  history as CSV
"""
import csv
import io
import json
import os
import platform
import shutil
import socket
import threading
import time
import uuid

from flask import Flask, Response, jsonify, request, send_file, send_from_directory
from flask_cors import CORS

import ai_assistant
import config
import database
import ocr
import pipeline
import router
from classifier import DocumentClassifier

config.ensure_dirs()
database.init_db()

app = Flask(__name__, static_folder=None)
app.json.sort_keys = False                 # keep our ordering (e.g. confidence buckets)
app.config["MAX_CONTENT_LENGTH"] = config.MAX_UPLOAD_MB * 1024 * 1024
CORS(app)                                  # allow other apps / devices to call the API

classifier = DocumentClassifier()
STARTED = time.time()
retrain_lock = threading.Lock()


def error(message, code=400):
    return jsonify({"error": message}), code


def run_pipeline(path, original, source):
    """Shared by upload, text and sample endpoints."""
    try:
        if os.path.getsize(path) == 0:
            raise ocr.ExtractionError("The file is empty (0 bytes)")
        return jsonify(pipeline.process_document(path, original, source, classifier))
    except ocr.ExtractionError as e:
        os.remove(path)
        return error(str(e), 422)


# ---------------------------------------------------------------------------
# Frontend (dashboard)
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return send_from_directory(config.FRONTEND_DIR, "index.html")


@app.route("/<path:path>")
def frontend_files(path):
    if path.startswith("api/"):
        return error("Unknown API endpoint", 404)
    return send_from_directory(config.FRONTEND_DIR, path)


# ---------------------------------------------------------------------------
# Status & configuration
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return jsonify({
        "status": "online",
        "service": "Edge Document Classification & Routing Service",
        "host": socket.gethostname(),
        "platform": f"{platform.system()} {platform.release()} / Python {platform.python_version()}",
        "uptime_s": round(time.time() - STARTED),
        "model_loaded": classifier.pipeline is not None,
        "model_name": classifier.model_name,
        "model_version": classifier.version,
        "ocr_engine": "RapidOCR (PaddleOCR models on ONNX Runtime, CPU)",
        "ocr_ready": ocr._engine is not None,
        "ai_enabled": config.AI_ENABLED,
        "ai_model": config.OPENAI_MODEL if config.AI_ENABLED else None,
        "retraining": retrain_lock.locked(),
        "inference": "100% local - works without internet",
    })


@app.get("/api/categories")
def categories():
    cats = [{"key": k, **v} for k, v in config.CATEGORIES.items()]
    return jsonify({
        "categories": cats,
        "unknown": {"key": config.UNKNOWN_CATEGORY, **config.MANUAL_REVIEW},
        "confidence_threshold": config.CONFIDENCE_THRESHOLD,
        "min_known_word_ratio": config.MIN_KNOWN_WORD_RATIO,
        "allowed_extensions": sorted(config.ALLOWED_EXTENSIONS),
        "max_upload_mb": config.MAX_UPLOAD_MB,
    })


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------
@app.post("/api/classify")
def classify():
    source = request.form.get("source", "dashboard")[:40]
    if "file" in request.files and request.files["file"].filename:
        f = request.files["file"]
        ext = os.path.splitext(f.filename)[1].lower().lstrip(".")
        if ext not in config.ALLOWED_EXTENSIONS:
            return error(f"Unsupported file type '.{ext}'. Allowed: {', '.join(sorted(config.ALLOWED_EXTENSIONS))}", 415)
        path, original = pipeline.save_upload(f)
        return run_pipeline(path, original, source)

    text = (request.form.get("text") or (request.get_json(silent=True) or {}).get("text") or "").strip()
    if text:
        path, original = pipeline.save_text(text)
        return run_pipeline(path, original, source if source != "dashboard" else "text-input")
    return error("Send a document in the 'file' field or text in the 'text' field.")


@app.get("/api/samples")
def samples():
    out = []
    for group in ["normal", "abnormal"]:
        folder = os.path.join(config.SAMPLES_DIR, group)
        for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
            out.append({"path": f"{group}/{name}", "name": name, "group": group,
                        "ext": os.path.splitext(name)[1].lstrip(".").lower(),
                        "size_kb": round(os.path.getsize(os.path.join(folder, name)) / 1024, 1)})
    return jsonify(out)


def _sample_path(rel):
    path = os.path.abspath(os.path.join(config.SAMPLES_DIR, rel or ""))
    if not path.startswith(os.path.abspath(config.SAMPLES_DIR)) or not os.path.isfile(path):
        return None
    return path


@app.get("/api/samples/file")
def sample_file():
    path = _sample_path(request.args.get("path"))
    return send_file(path) if path else error("Sample not found", 404)


@app.post("/api/samples/classify")
def classify_sample():
    src = _sample_path((request.get_json(silent=True) or {}).get("path"))
    if not src:
        return error("Sample not found", 404)
    name = os.path.basename(src)
    dest = os.path.join(config.UPLOAD_DIR, f"{uuid.uuid4().hex[:12]}_{name}")
    shutil.copy2(src, dest)
    return run_pipeline(dest, name, "sample-gallery")


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------
@app.get("/api/documents")
def documents():
    a = request.args
    return jsonify(database.list_documents(a.get("search", ""), a.get("category", ""), a.get("status", ""),
                                           a.get("department", ""), int(a.get("limit", 200)), int(a.get("offset", 0))))


@app.get("/api/documents/<int:doc_id>")
def document(doc_id):
    doc = database.get_document(doc_id)
    return jsonify(doc) if doc else error("Document not found", 404)


@app.get("/api/documents/<int:doc_id>/file")
def document_file(doc_id):
    doc = database.get_document(doc_id)
    if not doc:
        return error("Document not found", 404)
    for path in [os.path.join(config.ROUTED_DIR, doc["routed_path"] or ""), os.path.join(config.UPLOAD_DIR, doc["stored_name"])]:
        if os.path.isfile(path):
            return send_file(path, as_attachment=request.args.get("download") == "1", download_name=doc["filename"])
    return error("File no longer exists on disk", 404)


@app.post("/api/documents/<int:doc_id>/review")
def review(doc_id):
    category = (request.get_json(silent=True) or {}).get("category")
    if category not in config.CATEGORIES:
        return error("Choose a valid category")
    doc = pipeline.review_document(doc_id, category)
    return jsonify(doc) if doc else error("Document not found", 404)


@app.post("/api/documents/<int:doc_id>/ai")
def ai_insights(doc_id):
    doc = database.get_document(doc_id)
    if not doc:
        return error("Document not found", 404)
    if len(doc["text"] or "") < config.MIN_TEXT_CHARS:
        return error("Not enough text in this document for AI analysis", 422)
    try:
        insights = ai_assistant.analyze(doc["text"], doc["predicted_category"])
    except Exception as e:
        return error(f"AI assistant unavailable: {e}", 503)
    database.update_document(doc_id, ai_insights=insights)
    return jsonify(insights)


@app.delete("/api/documents/<int:doc_id>")
def delete(doc_id):
    doc = database.get_document(doc_id)
    if not doc:
        return error("Document not found", 404)
    router.remove_file(doc["routed_path"])
    upload = os.path.join(config.UPLOAD_DIR, doc["stored_name"])
    if os.path.isfile(upload):
        os.remove(upload)
    database.delete_document(doc_id)
    return jsonify({"deleted": doc_id})


@app.get("/api/export.csv")
def export_csv():
    rows = database.list_documents(limit=100000)
    buf = io.StringIO()
    cols = ["id", "created_at", "filename", "source", "predicted_category", "confidence", "final_category",
            "department", "status", "routed_path", "extraction_method", "ocr_confidence", "total_ms", "model_version"]
    w = csv.writer(buf)
    w.writerow(cols)
    for r in rows:
        w.writerow([r.get(c) for c in cols])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=classification_history.csv"})


# ---------------------------------------------------------------------------
# Dashboard, departments, model
# ---------------------------------------------------------------------------
@app.get("/api/stats")
def stats():
    return jsonify(database.stats())


@app.get("/api/departments")
def departments():
    folders = router.folder_summary()
    out = []
    for key, info in list(config.CATEGORIES.items()) + [(config.UNKNOWN_CATEGORY, config.MANUAL_REVIEW)]:
        docs = database.list_documents(department=info["department"], limit=6)
        out.append({"key": key, **info, **folders.get(info["folder"], {}),
                    "path": f"data/routed/{info['folder']}",
                    "recent": [{k: d[k] for k in ("id", "filename", "confidence", "status", "created_at")} for d in docs]})
    return jsonify(out)


@app.get("/api/model")
def model_info():
    with open(config.METRICS_PATH, encoding="utf-8") as f:
        metrics = json.load(f)
    e2e = os.path.join(config.REPORTS_DIR, "end_to_end.json")
    if os.path.exists(e2e):
        with open(e2e, encoding="utf-8") as f:
            metrics["end_to_end"] = json.load(f)
    metrics["available_feedback"] = len(database.feedback_rows())
    return jsonify(metrics)


@app.post("/api/model/retrain")
def retrain():
    if not retrain_lock.acquire(blocking=False):
        return error("Retraining already in progress", 409)
    try:
        import train_model
        feedback = database.feedback_rows()
        metrics = train_model.train(extra_rows=feedback, verbose=False)
        classifier.load()                       # hot-swap the new model, no restart needed
        return jsonify({"message": f"Model v{metrics['version']} trained with {len(feedback)} human-verified documents",
                        "metrics": metrics})
    finally:
        retrain_lock.release()


# ---------------------------------------------------------------------------
@app.errorhandler(413)
def too_large(_):
    return error(f"File too large. Maximum size is {config.MAX_UPLOAD_MB} MB", 413)


@app.errorhandler(500)
def server_error(e):
    return error(f"Internal error: {e}", 500)


if __name__ == "__main__":
    threading.Thread(target=ocr.get_engine, daemon=True).start()   # warm up OCR model in background
    print(f"\n  Edge Document Router running ->  http://localhost:{config.PORT}\n")
    app.run(host=config.HOST, port=config.PORT, debug=False, threaded=True)
