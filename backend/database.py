"""
database.py - STEP 7: "Maintain classification history and prediction confidence".

A single SQLite table (file: data/history.db) stores every processed document:
prediction, confidence, all class probabilities, department, routing path, alerts,
human corrections and timings. SQLite is a single local file - perfect for an edge device.
"""
import json
import sqlite3
from datetime import datetime, timedelta

import config

JSON_FIELDS = ["probabilities", "top_terms", "alerts", "key_fields", "ai_insights"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    filename           TEXT,
    stored_name        TEXT,
    file_ext           TEXT,
    file_size          INTEGER,
    file_hash          TEXT,
    source             TEXT,
    extraction_method  TEXT,
    ocr_confidence     REAL,
    pages              INTEGER,
    text               TEXT,
    predicted_category TEXT,
    confidence         REAL,
    probabilities      TEXT,
    top_terms          TEXT,
    known_word_ratio   REAL,
    final_category     TEXT,
    department         TEXT,
    routed_path        TEXT,
    status             TEXT,      -- auto_routed | needs_review | reviewed | corrected
    alerts             TEXT,
    key_fields         TEXT,
    ai_insights        TEXT,
    extraction_ms      REAL,
    classify_ms        REAL,
    total_ms           REAL,
    model_version      INTEGER,
    created_at         TEXT,
    updated_at         TEXT
);
"""


def connect():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with connect() as conn:
        conn.executescript(SCHEMA)


def _to_dict(row):
    if row is None:
        return None
    d = dict(row)
    for f in JSON_FIELDS:
        d[f] = json.loads(d[f]) if d.get(f) else None
    return d


def now():
    return datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------
def insert_document(rec):
    rec = dict(rec)
    for f in JSON_FIELDS:
        if f in rec and rec[f] is not None:
            rec[f] = json.dumps(rec[f])
    rec["created_at"] = rec["updated_at"] = now()
    cols = ", ".join(rec.keys())
    marks = ", ".join("?" for _ in rec)
    with connect() as conn:
        cur = conn.execute(f"INSERT INTO documents ({cols}) VALUES ({marks})", list(rec.values()))
        return cur.lastrowid


def update_document(doc_id, **fields):
    for f in JSON_FIELDS:
        if f in fields and fields[f] is not None:
            fields[f] = json.dumps(fields[f])
    fields["updated_at"] = now()
    sets = ", ".join(f"{k} = ?" for k in fields)
    with connect() as conn:
        conn.execute(f"UPDATE documents SET {sets} WHERE id = ?", list(fields.values()) + [doc_id])


def get_document(doc_id):
    with connect() as conn:
        return _to_dict(conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone())


def delete_document(doc_id):
    with connect() as conn:
        conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))


def find_by_hash(file_hash):
    with connect() as conn:
        row = conn.execute("SELECT id, filename FROM documents WHERE file_hash = ? ORDER BY id LIMIT 1",
                           (file_hash,)).fetchone()
        return dict(row) if row else None


def list_documents(search="", category="", status="", department="", limit=200, offset=0):
    query, params = "SELECT * FROM documents WHERE 1=1", []
    if search:
        query += " AND (filename LIKE ? OR text LIKE ? OR department LIKE ?)"
        params += [f"%{search}%"] * 3
    if category:
        query += " AND final_category = ?"
        params.append(category)
    if status:
        query += " AND status = ?"
        params.append(status)
    if department:
        query += " AND department = ?"
        params.append(department)
    query += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params += [limit, offset]
    with connect() as conn:
        rows = [_to_dict(r) for r in conn.execute(query, params).fetchall()]
    for r in rows:                     # keep list responses light
        r["text_preview"] = (r.pop("text") or "")[:200]
    return rows


def feedback_rows():
    """Documents a human confirmed or corrected -> extra training data for retraining."""
    with connect() as conn:
        rows = conn.execute("SELECT final_category, text FROM documents WHERE status IN ('reviewed','corrected') "
                            "AND final_category != ? AND length(text) >= ?",
                            (config.UNKNOWN_CATEGORY, config.MIN_TEXT_CHARS)).fetchall()
    return [(r["final_category"], r["text"]) for r in rows]


# ---------------------------------------------------------------------------
# Dashboard statistics
# ---------------------------------------------------------------------------
def stats():
    with connect() as conn:
        one = lambda q, p=(): conn.execute(q, p).fetchone()[0]
        total = one("SELECT COUNT(*) FROM documents")
        by_status = {r[0]: r[1] for r in conn.execute("SELECT status, COUNT(*) FROM documents GROUP BY status")}
        by_category = {r[0]: r[1] for r in conn.execute("SELECT final_category, COUNT(*) FROM documents GROUP BY final_category")}
        by_department = {r[0]: r[1] for r in conn.execute("SELECT department, COUNT(*) FROM documents GROUP BY department")}
        by_source = {r[0]: r[1] for r in conn.execute("SELECT source, COUNT(*) FROM documents GROUP BY source")}
        avg_conf = one("SELECT AVG(confidence) FROM documents WHERE predicted_category != ?", (config.UNKNOWN_CATEGORY,))
        avg_ms = one("SELECT AVG(total_ms) FROM documents")
        avg_ocr_ms = one("SELECT AVG(extraction_ms) FROM documents")
        avg_cls_ms = one("SELECT AVG(classify_ms) FROM documents")

        since = (datetime.now() - timedelta(days=13)).date().isoformat()
        daily_rows = {r[0]: r[1] for r in conn.execute(
            "SELECT substr(created_at,1,10) d, COUNT(*) FROM documents WHERE created_at >= ? GROUP BY d", (since,))}
        daily = []
        for i in range(14):
            day = (datetime.now() - timedelta(days=13 - i)).date().isoformat()
            daily.append({"date": day, "count": daily_rows.get(day, 0)})

        buckets = {"< 50%": 0, "50-70%": 0, "70-90%": 0, "90-100%": 0}
        for (c,) in conn.execute("SELECT confidence FROM documents WHERE predicted_category != ?", (config.UNKNOWN_CATEGORY,)):
            c = c or 0
            key = "< 50%" if c < .5 else "50-70%" if c < .7 else "70-90%" if c < .9 else "90-100%"
            buckets[key] += 1

        verified = conn.execute("SELECT predicted_category, final_category FROM documents "
                                "WHERE status IN ('reviewed','corrected') AND predicted_category != ?",
                                (config.UNKNOWN_CATEGORY,)).fetchall()
        live_acc = (sum(1 for r in verified if r[0] == r[1]) / len(verified)) if verified else None

        recent = [_to_dict(r) for r in conn.execute(
            "SELECT id, filename, final_category, confidence, department, status, source, total_ms, created_at "
            "FROM documents ORDER BY id DESC LIMIT 8").fetchall()]
        alerts = []
        for r in conn.execute("SELECT id, filename, alerts, created_at FROM documents "
                              "WHERE alerts IS NOT NULL AND alerts != '[]' ORDER BY id DESC LIMIT 12"):
            for a in json.loads(r["alerts"]):
                alerts.append({"doc_id": r["id"], "filename": r["filename"], "created_at": r["created_at"], **a})

    return {
        "total": total,
        "by_status": by_status,
        "needs_review": by_status.get("needs_review", 0),
        "by_category": by_category,
        "by_department": by_department,
        "by_source": by_source,
        "avg_confidence": round(avg_conf, 4) if avg_conf else 0,
        "avg_processing_ms": round(avg_ms, 1) if avg_ms else 0,
        "avg_extraction_ms": round(avg_ocr_ms, 1) if avg_ocr_ms else 0,
        "avg_classify_ms": round(avg_cls_ms, 2) if avg_cls_ms else 0,
        "daily": daily,
        "confidence_buckets": buckets,
        "human_verified": len(verified),
        "live_accuracy": round(live_acc, 4) if live_acc is not None else None,
        "recent": recent,
        "alerts": alerts[:15],
    }
