# DocuRoute Edge: Intelligent Document Classification & Routing System

Edge-based application that reads uploaded images, scans, PDFs or text **locally** (offline OCR), classifies them into 8 document categories with **TF-IDF + Linear SVM / Logistic Regression**, and **routes** each file to the right department folder, with full history, confidence, alerts and a live dashboard.

> 📘 **Full documentation (problem statement, design, ML, testing, demo script, viva Q&A): [EVERYTHING.md](EVERYTHING.md)**

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
Rebuild data/model from scratch: `python generate_dataset.py && python train_model.py`

## Results
| Metric | Value |
|---|---|
| Test accuracy (400 unseen docs) | **98.0%** |
| 5-fold cross-validation | **98.35% ± 0.54%** |
| End-to-end OCR + model on 32 scanned images | **32/32** |
| Functional tests (normal + abnormal) | **42/42 passed** |
| Classification time | ~8 ms / document (CPU) |

## Categories → departments
Invoice → Finance (Accounts Payable) · Receipt → Finance (Expense Claims) · Identity Document → HR (KYC) · Application Form → Applications Desk · Bank Statement → Finance (Audit) · Medical Report → Health & Insurance Claims · Resume → HR (Recruitment) · Legal Contract → Legal & Compliance · uncertain → Manual Review Desk

## Optional AI
`backend/.env` holds `OPENAI_API_KEY` and `OPENAI_MODEL=gpt-4o-mini`, used only when the user clicks *AI summary* on a document (sensitive numbers are masked first). Leave the key empty to run fully offline.
