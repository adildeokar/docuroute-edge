"""
kaggle_dataset.py - Build the training corpus from REAL public Kaggle datasets + our synthetic data.

Public datasets exist for 5 of our 8 categories. Identity documents, bank statements and
application forms are private by nature (no public dataset can share them), so those 3 stay synthetic.

  category         Kaggle dataset (owner/name)                                   licence
  receipt          ryanznie/sroie-datasetv2-with-labels   (ICDAR-2019 SROIE scanned receipts, OCR text)   MIT
  invoice          ayoubcherguelaine/company-documents-dataset  (business invoices, extracted text)       Apache 2.0
  resume           snehaanbhawal/resume-dataset           (resumes from livecareer.com)                  CC0
  medical_report   tboyle10/medicaltranscriptions         (medical reports from mtsamples.com)           CC0
  legal_contract   konradb/atticus-open-contract-dataset-aok-beta (CUAD v1 commercial contracts)         CC BY 4.0

Each of these 5 classes = 300 real documents + 100 synthetic ones (so our own demo layouts are still known).
The other 3 classes = 400 synthetic documents.  Total 3,200 documents, 1,500 of them real.

Public Kaggle files download WITHOUT an account from
    https://www.kaggle.com/api/v1/datasets/download/<owner>/<dataset>/<file path>
Raw files are cached in data/kaggle_raw/ (git-ignored), so the download happens only once.

Run order:  python generate_dataset.py  ->  python kaggle_dataset.py  ->  python train_model.py
"""
import csv
import io
import json
import os
import random
import re
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor

import config

KAGGLE = "https://www.kaggle.com/api/v1/datasets"
RAW_DIR = os.path.join(config.PROJECT_DIR, "data", "kaggle_raw")
REAL_PER_CLASS = 300      # real documents per category that has a public dataset
SYNTHETIC_MIX = 100       # synthetic documents kept in those categories
MAX_CHARS = 3000          # ~ first 1-2 pages: enough to recognise the document type
rng = random.Random(7)

SOURCES = {
    "receipt": "Kaggle: SROIE 2019 scanned receipts (ryanznie/sroie-datasetv2-with-labels, MIT)",
    "invoice": "Kaggle: Company Documents Dataset (ayoubcherguelaine/company-documents-dataset, Apache 2.0)",
    "resume": "Kaggle: Resume Dataset (snehaanbhawal/resume-dataset, CC0)",
    "medical_report": "Kaggle: Medical Transcriptions (tboyle10/medicaltranscriptions, CC0)",
    "legal_contract": "Kaggle: CUAD v1 contracts (konradb/atticus-open-contract-dataset-aok-beta, CC BY 4.0)",
}


# ---------------------------------------------------------------------------
# Download helpers
# ---------------------------------------------------------------------------
def kaggle_file(ref, path):
    """Download one file of a public Kaggle dataset (cached). Returns its bytes."""
    local = os.path.join(RAW_DIR, ref.replace("/", "__"), *path.split("/"))
    if not os.path.exists(local):
        url = f"{KAGGLE}/download/{ref}/{urllib.parse.quote(path, safe='')}"
        data = urllib.request.urlopen(url, timeout=300).read()
        if data[:2] == b"PK":                         # Kaggle zips the bigger files
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                data = z.read(z.namelist()[0])
        if data.lstrip()[:15].lower().startswith(b"<!doctype html"):
            raise RuntimeError(f"Kaggle returned a web page instead of {ref}/{path}")
        os.makedirs(os.path.dirname(local), exist_ok=True)
        with open(local, "wb") as f:
            f.write(data)
    with open(local, "rb") as f:
        return f.read()


def kaggle_file_list(ref, prefix):
    """Names of the files in a dataset that start with `prefix` (the listing API is paginated)."""
    cache = os.path.join(RAW_DIR, ref.replace("/", "__"), "_file_list.json")
    if os.path.exists(cache):
        names = json.load(open(cache, encoding="utf-8"))
    else:
        names, token = [], ""
        while True:
            url = f"{KAGGLE}/list/{ref}?pageSize=200&pageToken={urllib.parse.quote(token)}"
            page = json.load(urllib.request.urlopen(url, timeout=60))
            names += [f["name"] for f in page.get("datasetFiles") or []]
            token = page.get("nextPageToken") or ""
            if not token:
                break
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        json.dump(names, open(cache, "w", encoding="utf-8"))
    return sorted(n for n in names if n.startswith(prefix))


def read_csv(data):
    csv.field_size_limit(10 ** 8)
    return list(csv.DictReader(io.StringIO(data.decode("utf-8", errors="replace"))))


def clean(text):
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text).strip()
    return text[:MAX_CHARS]


def pick(texts, n):
    """Clean, drop empty/short/duplicate texts, then take a random sample of n."""
    unique = list(dict.fromkeys(t for t in map(clean, texts) if len(t) >= 80))
    rng.shuffle(unique)
    return unique[:n]


# ---------------------------------------------------------------------------
# One loader per category
# ---------------------------------------------------------------------------
def load_receipts(n):
    ref = "ryanznie/sroie-datasetv2-with-labels"
    files = kaggle_file_list(ref, "SROIE2019/train/box/")
    files = rng.sample(files, min(len(files), n + 40))          # a few spare in case of duplicates
    with ThreadPoolExecutor(8) as pool:
        raw = list(pool.map(lambda p: kaggle_file(ref, p), files))
    texts = []
    for data in raw:                                             # each line: x1,y1,...,x4,y4,TEXT
        lines = [ln.split(",", 8)[-1] for ln in data.decode("utf-8", errors="replace").splitlines() if ln.count(",") >= 8]
        texts.append("\n".join(lines))
    return pick(texts, n)


def load_invoices(n):
    rows = read_csv(kaggle_file("ayoubcherguelaine/company-documents-dataset", "company-document-text.csv"))
    return pick([r["text"] for r in rows if r["label"].strip().lower() == "invoice"], n)


def load_resumes(n):
    rows = read_csv(kaggle_file("snehaanbhawal/resume-dataset", "Resume/Resume.csv"))
    return pick([r["Resume_str"] for r in rows], n)


def load_medical(n):
    rows = read_csv(kaggle_file("tboyle10/medicaltranscriptions", "mtsamples.csv"))
    return pick([r["transcription"] for r in rows], n)


def load_contracts(n):
    data = json.loads(kaggle_file("konradb/atticus-open-contract-dataset-aok-beta", "CUAD_v1/CUAD_v1.json"))
    return pick([p["context"] for doc in data["data"] for p in doc["paragraphs"]], n)


LOADERS = {"receipt": load_receipts, "invoice": load_invoices, "resume": load_resumes,
           "medical_report": load_medical, "legal_contract": load_contracts}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def build():
    with open(config.SYNTHETIC_CSV, encoding="utf-8") as f:
        synthetic = list(csv.DictReader(f))

    rows = []
    for label in config.CATEGORIES:
        own = [r["text"] for r in synthetic if r["label"] == label]
        if label in LOADERS:
            real = LOADERS[label](REAL_PER_CLASS)
            print(f"  {label:18s} {len(real):4d} real  + {SYNTHETIC_MIX} synthetic   <- {SOURCES[label]}")
            rows += [(label, t, "kaggle") for t in real]
            rows += [(label, t, "synthetic") for t in own[:SYNTHETIC_MIX]]
        else:
            print(f"  {label:18s}    0 real  + {len(own)} synthetic   (no public dataset: private documents)")
            rows += [(label, t, "synthetic") for t in own]

    rng.shuffle(rows)
    with open(config.DATASET_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["label", "text", "source"])
        w.writerows(rows)
    real = sum(r[2] == "kaggle" for r in rows)
    print(f"[dataset] {len(rows)} documents ({real} real from Kaggle, {len(rows) - real} synthetic) -> {config.DATASET_CSV}")


if __name__ == "__main__":
    print("Downloading public Kaggle datasets (cached in data/kaggle_raw/) ...")
    build()
    print("Done. Next step:  python train_model.py")
