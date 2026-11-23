"""
router.py - STEP 6: "Assign the document to a corresponding department or folder".

Every department is a folder under data/routed/. After classification the original file
is copied into the department's folder, e.g.

    data/routed/Finance_Accounts_Payable/000012_invoice_march.pdf

If a human later corrects the category, the file is moved to the new department folder.
"""
import os
import shutil

import config


def _destination(category, doc_id, filename):
    folder = config.category_info(category)["folder"]
    return os.path.join(folder, f"{doc_id:06d}_{filename}")


def route_file(src_path, category, doc_id, filename):
    """Copy the uploaded file into the department folder. Returns path relative to data/routed."""
    rel = _destination(category, doc_id, filename)
    dest = os.path.join(config.ROUTED_DIR, rel)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copy2(src_path, dest)
    return rel.replace("\\", "/")


def reroute_file(old_rel, new_category, doc_id, filename):
    """Move an already-routed file to another department (after human correction)."""
    new_rel = _destination(new_category, doc_id, filename)
    old_abs = os.path.join(config.ROUTED_DIR, old_rel or "")
    new_abs = os.path.join(config.ROUTED_DIR, new_rel)
    os.makedirs(os.path.dirname(new_abs), exist_ok=True)
    if old_rel and os.path.exists(old_abs) and old_abs != new_abs:
        shutil.move(old_abs, new_abs)
    return new_rel.replace("\\", "/")


def remove_file(rel):
    path = os.path.join(config.ROUTED_DIR, rel or "")
    if rel and os.path.isfile(path):
        os.remove(path)


def folder_summary():
    """File count + size for each department folder (shown on the Departments page)."""
    out = {}
    for info in list(config.CATEGORIES.values()) + [config.MANUAL_REVIEW]:
        path = os.path.join(config.ROUTED_DIR, info["folder"])
        files = [f for f in os.listdir(path)] if os.path.isdir(path) else []
        out[info["folder"]] = {
            "files": len(files),
            "size_kb": round(sum(os.path.getsize(os.path.join(path, f)) for f in files) / 1024, 1),
        }
    return out
