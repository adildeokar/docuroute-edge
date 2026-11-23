# DocuRoute Edge: Intelligent Document Classification & Routing System

Edge-based application that reads uploaded images, scans, PDFs or text **locally** (offline OCR), classifies them into 8 document categories with **TF-IDF + Linear SVM / Logistic Regression**, and **routes** each file to the right department folder, with full history, confidence, alerts and a live dashboard.

> 📘 **Full documentation (problem statement, design, ML, testing, demo script, viva Q&A): [EVERYTHING.md](EVERYTHING.md)**
> 🛠️ **Technical reference (all models, datasets, training procedure, hyperparameters, results): [Tech.md](Tech.md)**

## Quick start (Windows)
1. `setup.bat`: install Python libraries (once)
2. `run.bat`: start the edge service and open **http://localhost:5000**

## Manual start (any OS)
```bash
pip install -r requirements.txt
cd backend
python app.py                     # edge service + dashboard on http://localhost:5000
python scanner_simulator.py       # (2nd terminal) device simulator sending documents over HTTP
python test_system.py             # normal + abnormal tests, end-to-end OCR accuracy
```
Rebuild data/model from scratch: `python generate_dataset.py && python kaggle_dataset.py && python train_model.py`

## Dataset
3,200 labelled documents, 400 per category: **1,500 real documents from public Kaggle datasets** + 1,700 synthetic ones.

| Category | Real data (Kaggle) | Licence |
|---|---|---|
| Receipt | SROIE 2019 scanned receipts: `ryanznie/sroie-datasetv2-with-labels` | MIT |
| Invoice | Company Documents Dataset: `ayoubcherguelaine/company-documents-dataset` | Apache 2.0 |
| Resume | Resume Dataset: `snehaanbhawal/resume-dataset` | CC0 |
| Medical Report | Medical Transcriptions (mtsamples): `tboyle10/medicaltranscriptions` | CC0 |
| Legal Contract | CUAD v1 (The Atticus Project): `konradb/atticus-open-contract-dataset-aok-beta` | CC BY 4.0 |
| ID document, bank statement, application form | none exist publicly (private data), so synthetic only (`generate_dataset.py`) | n/a |

## Results
| Metric | Value |
|---|---|
| Test accuracy (640 unseen docs) | **99.4%** |
| Accuracy on unseen **real** Kaggle documents | **100%** (285 docs) |
| Synthetic-only model tested on all 1,500 real docs | **93.7%** |
| 5-fold cross-validation | **99.44% ± 0.25%** |
| End-to-end OCR + model on 32 scanned images | **32/32** |
| Functional tests (normal + abnormal) | **43/43 passed** |
| Classification time | ~9 ms / document (CPU) |

## Categories → departments
Invoice → Finance (Accounts Payable) · Receipt → Finance (Expense Claims) · Identity Document → HR (KYC) · Application Form → Applications Desk · Bank Statement → Finance (Audit) · Medical Report → Health & Insurance Claims · Resume → HR (Recruitment) · Legal Contract → Legal & Compliance · uncertain → Manual Review Desk

## Optional AI
`backend/.env` holds `OPENAI_API_KEY` and `OPENAI_MODEL=gpt-4o-mini`, used only when the user clicks *AI summary* on a document (sensitive numbers are masked first). Leave the key empty to run fully offline.
