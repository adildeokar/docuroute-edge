# EVERYTHING.md: DocuRoute Edge

### Intelligent Document Classification and Routing System
*Applied Edge Analytics: Final Jury Project (Problem Statement 11)*

This file explains **everything** about the project: the original question and instructions, how each requirement is met, how the system works internally, how to run it, how to demo it, and how to answer the jury's questions.

---

## Table of Contents

1. [The Original Question (verbatim)](#1-the-original-question-verbatim)
2. [Requirement → Implementation Checklist](#2-requirement--implementation-checklist)
3. [Problem Understanding](#3-problem-understanding)
4. [Solution Overview & Architecture](#4-solution-overview--architecture)
5. [Folder Structure (what every file does)](#5-folder-structure-what-every-file-does)
6. [Dataset & Input Preparation](#6-dataset--input-preparation)
7. [Feature Extraction (OCR + TF-IDF)](#7-feature-extraction-ocr--tf-idf)
8. [Machine Learning Model](#8-machine-learning-model)
9. [Decision Rules & Abnormal Input Handling](#9-decision-rules--abnormal-input-handling)
10. [Routing to Departments](#10-routing-to-departments)
11. [Classification History (Database)](#11-classification-history-database)
12. [Edge Implementation (Flask Microservice)](#12-edge-implementation-flask-microservice)
13. [Communication (HTTP)](#13-communication-http)
14. [Dashboard (Frontend)](#14-dashboard-frontend)
15. [Optional AI Assistant (OpenAI gpt-4o-mini)](#15-optional-ai-assistant-openai-gpt-4o-mini)
16. [Human-in-the-Loop & Retraining](#16-human-in-the-loop--retraining)
17. [Testing (Normal & Abnormal Cases)](#17-testing-normal--abnormal-cases)
18. [Performance](#18-performance)
19. [Role of Edge Computing](#19-role-of-edge-computing)
20. [Limitations & Future Scope](#20-limitations--future-scope)
21. [How to Run](#21-how-to-run)
22. [Live Demo Script for the Jury](#22-live-demo-script-for-the-jury)
23. [Code Walkthrough: Life of One Document](#23-code-walkthrough-life-of-one-document)
24. [Likely Jury Questions & Answers](#24-likely-jury-questions--answers)
25. [Glossary](#25-glossary)

---

## 1. The Original Question (verbatim)

### Problem Statement

> **11. Intelligent Document Classification and Routing System**
>
> **Problem Statement:** Develop an edge-based document classification application that identifies document categories from uploaded images or scanned documents and routes them to the appropriate department.
>
> **Student Implementation Guide**
> 70. Collect sample documents such as invoices, receipts, identity documents and application forms.
> 71. Extract text or visual features from the documents.
> 72. Train a classification model to identify document categories.
> 73. Deploy the trained model as a local edge service.
> 74. Upload a new document and predict its category.
> 75. Assign the document to a corresponding department or folder based on the predicted category.
> 76. Maintain classification history and prediction confidence.
>
> **Suggested ML / Technical Approach:** TF-IDF with Logistic Regression or SVM; alternatively, lightweight image classification.
>
> **Expected Output:** A document classification and routing application that performs local document analysis.

### Jury Instructions

> **1. About the Jury Projects**
> The following problem statements are designed for the Applied Edge Analytics Jury Examination. Each project combines a practical application with machine learning and edge computing. Students should build a working prototype that accepts new input data, runs a trained model locally through an edge application or microservice, and presents the result. The projects are intended to be of medium difficulty and suitable for groups of 3–4 students. Students may use public datasets, sample images, simulated device data or software-based test inputs. Physical sensors and boards are not compulsory.
>
> **2. General Project Requirements**
> - **Problem understanding:** Explain the real-world problem, intended users and why edge processing is useful for the selected application.
> - **Dataset and input preparation:** Identify a suitable dataset or create realistic sample inputs. Explain data collection, labelling, preprocessing and train/test splitting, as applicable.
> - **Machine learning:** Train or configure a suitable ML model. Explain the selected algorithm, input features, output classes or prediction target, and model evaluation.
> - **Edge implementation:** Deploy the model locally as a Python application or microservice. Flask and Docker may be used; Azure IoT Edge/EFLOW may be used where feasible.
> - **Communication:** Demonstrate HTTP or MQTT communication between the edge service and another application, device simulator or dashboard.
> - **Live prediction:** Submit new test inputs during the demonstration and show the model's actual prediction. Do not rely only on screenshots or pre-recorded outputs.
> - **Dashboard and records:** Display useful predictions, status information, alerts or history through a basic dashboard or interface.
> - **Testing and explanation:** Test normal and abnormal or varied input cases. Explain limitations, performance and the role of edge computing.

### Additional instructions given for this build
- Complete project with a **frontend and backend**, very good UI, final-semester quality.
- **No hardware required**: a purely software project.
- Keep the codebase **simple enough to explain** to the jury.
- AI features may use the **cheapest OpenAI mini model** (we use `gpt-4o-mini`).
- Produce this `EVERYTHING.md`.

---

## 2. Requirement → Implementation Checklist

| # | Requirement | Where / how it is met |
|---|---|---|
| 70 | Collect sample documents (invoices, receipts, IDs, application forms) | **3,200 labelled documents in 8 categories** (the 4 required + bank statements, medical reports, resumes, legal contracts). **1,500 are real documents from 5 public Kaggle datasets** (`backend/kaggle_dataset.py`) and 1,700 are realistic synthetic documents (`backend/generate_dataset.py`) for the private types (ID cards, bank statements, application forms). Plus 32 rendered scan images for testing and 27 demo files in `sample_documents/` |
| 71 | Extract text or visual features | `backend/ocr.py`: offline OCR (RapidOCR/ONNX) for images, text layer or OCR for PDFs, DOCX/TXT readers. `backend/train_model.py`: **word + character TF-IDF** features |
| 72 | Train a classification model | `backend/train_model.py` trains and compares **Logistic Regression, Linear SVM, Naive Bayes**; best = Linear SVM (calibrated), 99.38% test accuracy, 99.44% 5-fold CV, 100% on unseen real Kaggle documents |
| 73 | Deploy the model as a local edge service | `backend/app.py`: **Flask REST microservice** on port 5000; also `Dockerfile` + `docker-compose.yml` |
| 74 | Upload a new document and predict its category | Dashboard → *Classify Document* (drag & drop, paste text, sample gallery) → `POST /api/classify` |
| 75 | Assign to department / folder | `backend/router.py` copies the file into `data/routed/<Department>/`; routing table in `backend/config.py` |
| 76 | Maintain history and confidence | `backend/database.py`: SQLite `data/history.db` stores prediction, confidence, all class probabilities, department, status, alerts and timings. *History* page + CSV export |
| Approach | TF-IDF + LR/SVM | Exactly this: TF-IDF + Logistic Regression **and** SVM, compared side by side |
| Jury: problem understanding | Section 3 of this file + dashboard hero text |
| Jury: dataset prep | Section 6 (public Kaggle datasets + synthetic data, labelling, preprocessing, 80/20 stratified split) |
| Jury: ML explained & evaluated | Section 8 + *Model & Analytics* page (accuracy, F1, confusion matrix, CV, keywords) |
| Jury: edge implementation | Flask microservice, all inference local, works offline, Docker image |
| Jury: communication | HTTP REST API used by (a) the dashboard, (b) `scanner_simulator.py` device simulator, (c) curl/any client, (d) *Live API console* on the Edge System page |
| Jury: live prediction | Upload any new file during the demo; real OCR + model output is shown in seconds |
| Jury: dashboard & records | 7-page dashboard: KPIs, charts, alerts, history, review queue, departments, model analytics, system health |
| Jury: testing | `backend/test_system.py`: **43/43 functional tests pass** (normal + 13 abnormal cases), **32/32 held-out scanned images correct**; report in `reports/test_report.md` |
| Jury: limitations, performance, edge role | Sections 18–20 |

---

## 3. Problem Understanding

### The real-world problem
Every organisation (banks, hospitals, universities, insurance companies, government offices) receives a constant stream of mixed paperwork: invoices, receipts, ID proofs, application forms, bank statements, lab reports, CVs and contracts. They arrive by scanner, e-mail or phone photos. Today a person usually has to **open each file, decide what it is, and forward it** to the right team. This is:
- **slow**: documents wait in a shared inbox for hours or days;
- **error-prone**: a misplaced invoice means a late payment fine; a misplaced ID breaks KYC compliance;
- **expensive**: skilled staff spend time sorting instead of processing.

### Intended users
| User | What they get |
|---|---|
| Front-office / mail-room staff | Drop documents in; the system sorts them automatically |
| Department teams (Finance, HR, Legal, Claims, Admissions) | Receive only their documents in their folder |
| Supervisors / auditors | Dashboard with volumes, confidence, alerts and a full audit history |
| IT / administrators | A small self-contained service that runs on a local PC or edge box |

### Why edge processing?
| Reason | Explanation |
|---|---|
| **Privacy & compliance** | ID cards, bank statements and medical reports are highly sensitive. Processing them **on the premises** means they never travel to a third-party cloud (important under data-protection rules such as India's DPDP Act and GDPR). |
| **Low latency** | Classification takes ~8 ms; OCR ~1–4 s on an ordinary CPU. No upload / queue / network round-trip. |
| **Works offline** | A branch office with poor internet still sorts documents. Everything, including the chart library, is bundled locally. |
| **Lower cost** | No per-document cloud API fees; runs on existing hardware. |
| **Bandwidth** | Scanned pages are large (100 KB–5 MB). Sending only metadata (category, confidence) upstream instead of images saves bandwidth. |

---

## 4. Solution Overview & Architecture

```
 ┌───────────────────────┐   HTTP (REST/JSON)   ┌──────────────────────────────────────────────────────────┐
 │  INPUT DEVICES        │ ───────────────────► │            EDGE SERVICE  (Flask, port 5000)              │
 │ • Web dashboard       │                      │                                                          │
 │ • Scanner simulator   │ ◄─────────────────── │  1. Save upload ─► 2. Extract text (OCR / PDF / DOCX)    │
 │ • curl / any app      │   JSON prediction    │                         │                                │
 └───────────────────────┘                      │                         ▼                                │
                                                │  3. TF-IDF features ─► ML model (Linear SVM)             │
                                                │                         │  category + probabilities      │
                                                │                         ▼                                │
                                                │  4. Decision rules (confidence, out-of-domain, blank,    │
                                                │     duplicates, scan quality)                            │
                                                │                         │                                │
                                                │                         ▼                                │
                                                │  5. Router ─► data/routed/<Department>/file              │
                                                │  6. SQLite history (data/history.db)                     │
                                                │  7. Local key-field extraction (regex)                   │
                                                └───────────────┬──────────────────────────────────────────┘
                                                                │ optional, on user click only
                                                                ▼
                                                   OpenAI gpt-4o-mini (summary / second opinion,
                                                   personal numbers masked before sending)
```

### Technology stack (and why)

| Layer | Technology | Why this choice |
|---|---|---|
| Backend | **Python 3.12 + Flask** | Suggested by the jury instructions; tiny, easy to explain |
| OCR | **RapidOCR** (PaddleOCR models on **ONNX Runtime**) | Pure `pip install`, no system install like Tesseract, runs on CPU offline: ideal for edge |
| PDF | **PyMuPDF** | Reads the PDF text layer instantly; renders scanned PDFs for OCR |
| ML | **scikit-learn**: TF-IDF + Linear SVM / Logistic Regression | Exactly the suggested approach; trains in seconds, predicts in milliseconds, tiny model |
| Storage | **SQLite** + normal folders | Single local file, zero setup, perfect for an edge device |
| Frontend | **HTML + CSS + vanilla JavaScript**, **Chart.js** (bundled locally) | No build step, no framework to explain; works offline |
| Optional AI | **OpenAI gpt-4o-mini** | Cheapest capable mini model; used only on demand |
| Packaging | **Docker** (optional) | One-command deployment on any edge box |

---

## 5. Folder Structure (what every file does)

```
AEA Final JURY/
├── EVERYTHING.md               ← this file
├── README.md                   ← short quick-start
├── requirements.txt            ← Python libraries (pinned, tested versions)
├── setup.bat / run.bat         ← Windows: install once / start the system
├── Dockerfile, docker-compose.yml, .dockerignore, .gitignore
│
├── backend/                    ← THE EDGE SERVICE (Python)
│   ├── config.py               ← all settings: paths, thresholds, category → department table
│   ├── generate_dataset.py     ← STEP 70: synthetic documents (all 8 types) + demo/test images
│   ├── kaggle_dataset.py       ← STEP 70: downloads REAL documents from public Kaggle datasets, mixes them in
│   ├── train_model.py          ← STEPS 71-72: TF-IDF features, trains & compares 3 models, saves best
│   ├── classifier.py           ← loads the model; predict() returns category, probabilities, explanation
│   ├── ocr.py                  ← text extraction from images / PDF / DOCX / TXT (offline OCR)
│   ├── pipeline.py             ← the full flow for one document + decision rules + human review
│   ├── router.py               ← STEP 75: copies/moves files into department folders
│   ├── database.py             ← STEP 76: SQLite history + dashboard statistics
│   ├── extractor.py            ← local regex extraction of key fields (invoice no, total, dates…)
│   ├── ai_assistant.py         ← optional OpenAI summary (with personal-data masking)
│   ├── app.py                  ← STEP 73: Flask REST API + serves the dashboard
│   ├── scanner_simulator.py    ← separate "device" that sends documents over HTTP
│   ├── test_system.py          ← automated normal/abnormal tests + end-to-end OCR accuracy
│   ├── .env                    ← OpenAI key (private, not committed)
│   └── .env.example            ← template without the key
│
├── frontend/                   ← THE DASHBOARD (served by Flask at http://localhost:5000)
│   ├── index.html              ← page layout: sidebar, top bar, page sections, modal
│   ├── css/styles.css          ← all styling, light + dark theme, responsive
│   ├── vendor/chart.umd.min.js ← Chart.js stored locally (offline)
│   └── js/
│       ├── api.js              ← fetch() wrapper for the REST API
│       ├── ui.js               ← shared helpers + the document detail view
│       ├── main.js             ← navigation, health polling, theme toggle, live refresh
│       └── pages/              ← one file per page: dashboard, classify, review, history,
│                                  departments, model, system
│
├── data/
│   ├── dataset/documents.csv       ← 3,200 labelled training documents (label, text, source = kaggle/synthetic)
│   ├── dataset/synthetic_documents.csv ← output of generate_dataset.py (input of kaggle_dataset.py)
│   ├── kaggle_raw/                 ← downloaded Kaggle files (cache, not committed)
│   ├── dataset/ocr_test_images/    ← 32 held-out rendered scans for end-to-end testing
│   ├── history.db                  ← created at runtime: classification history
│   ├── uploads/                    ← created at runtime: original uploads
│   └── routed/<Department>/        ← created at runtime: THE DEPARTMENT FOLDERS
├── models/
│   ├── document_classifier.joblib  ← trained model (pipeline: TF-IDF + classifier)
│   └── metrics.json                ← evaluation results shown on the Model page
├── sample_documents/
│   ├── normal/                     ← 20 demo docs: clean PNG, phone-style scanned JPG, PDF, TXT
│   └── abnormal/                   ← 7 edge cases: blank, photo, recipe, corrupted, blurry…
└── reports/
    ├── test_report.md              ← output of test_system.py
    └── end_to_end.json             ← OCR + model accuracy on scanned images
```

---

## 6. Dataset & Input Preparation

### 6.1 Where the data comes from: real (Kaggle) + synthetic
The training corpus `data/dataset/documents.csv` has **3,200 labelled documents, 400 per category**, from two sources:

| Category | Real documents (public Kaggle dataset) | Synthetic | Total |
|---|---|---|---|
| Invoice | 300: *Company Documents Dataset* (`ayoubcherguelaine/company-documents-dataset`, Apache 2.0) | 100 | 400 |
| Receipt | 300: *SROIE 2019* scanned receipts, ICDAR competition (`ryanznie/sroie-datasetv2-with-labels`, MIT) | 100 | 400 |
| Resume | 300: *Resume Dataset* from livecareer.com (`snehaanbhawal/resume-dataset`, CC0) | 100 | 400 |
| Medical Report | 300: *Medical Transcriptions* from mtsamples.com (`tboyle10/medicaltranscriptions`, CC0) | 100 | 400 |
| Legal Contract | 300: *CUAD v1* commercial contracts, The Atticus Project (`konradb/atticus-open-contract-dataset-aok-beta`, CC BY 4.0) | 100 | 400 |
| Identity Document | none: no public dataset exists (private data) | 400 | 400 |
| Bank Statement | none: no public dataset exists (private data) | 400 | 400 |
| Application Form | none: no public dataset exists (private data) | 400 | 400 |
| **Total** | **1,500 real** | **1,700** | **3,200** |

**Why not 100% real data?** ID cards, bank statements and filled application forms contain **personal data**; publishing them is neither legal nor ethical, so no public dataset of them exists. The jury instructions explicitly allow *"public datasets, sample images, simulated device data"*, so we use **public datasets where they exist and a realistic generator where they cannot exist**. We also keep 100 synthetic documents in the real categories so the model still knows the Indian-style layouts of our demo documents (GSTIN, Rs., Aadhaar…).

### 6.2 Real documents: `kaggle_dataset.py`
- Public Kaggle datasets can be downloaded **without an account** from `https://www.kaggle.com/api/v1/datasets/download/<owner>/<dataset>/<file>`. The script downloads only the files it needs (a CSV, a JSON, or the OCR text files of the receipts), about 110 MB in total, and caches them in `data/kaggle_raw/` (not committed to Git).
- **Receipts (SROIE)** already come with OCR output (one line per detected text box, `x1,y1,…,x4,y4,TEXT`); we keep only the text.
- **Contracts (CUAD)** are 510 long commercial agreements; **medical transcriptions** are real anonymised reports (operative notes, consultations, discharge summaries); **resumes** are 2,400+ real CVs in 24 job categories.
- **Cleaning:** collapse whitespace, drop texts shorter than 80 characters, **remove exact duplicates** (mtsamples has some), randomly sample 300 per class (fixed seed 7), and **cut every document to its first 3,000 characters** (about 1–2 pages: what a scanner usually captures and enough to recognise the type; it also stops 50-page contracts from dominating the TF-IDF statistics).
- Each row gets a `source` column (`kaggle` or `synthetic`) so we can measure accuracy on real and synthetic documents separately (Section 8.4).

### 6.3 Synthetic documents: `generate_dataset.py`
For each of the 8 categories there is a **template function** (`make_invoice()`, `make_receipt()`, …) that writes a realistic document with randomised:
- names, companies, stores, banks, hospitals, cities, addresses, phone numbers, e-mails;
- dates in 5 different formats, amounts in different currencies (Rs., INR, $, ₹, EUR…);
- IDs: invoice numbers, GSTIN, IFSC, passport/DL/Aadhaar/PAN numbers, MRZ lines;
- document sub-types: e.g. *Tax Invoice / Proforma Invoice / Bill of Supply*, *Passport / Driving Licence / Aadhaar / PAN / Voter ID*, *Admission / Loan / Job / Scholarship application*, *NDA / Rental / Employment contract*;
- optional sections (each optional line kept with ~60% probability) so layouts differ.

| Category (label) | Examples of sub-types | Department |
|---|---|---|
| `invoice` | tax invoice, proforma, bill of supply, commercial invoice | Finance - Accounts Payable |
| `receipt` | cash memo, payment receipt, fuel/café/pharmacy receipt | Finance - Expense Claims |
| `identity_document` | passport, driving licence, Aadhaar, PAN, voter ID | HR - KYC & Verification |
| `application_form` | admission, loan, job, scholarship, account opening | Admissions & Applications Desk |
| `bank_statement` | savings/current statements with transaction tables | Finance - Accounts & Audit |
| `medical_report` | lab report, prescription, discharge summary, radiology | Health & Insurance Claims |
| `resume` | CV, résumé with experience/education/skills | HR - Recruitment |
| `legal_contract` | NDA, rental, employment, service agreement, MoU | Legal & Compliance |

### 6.4 Making the synthetic data realistic (and hard)
A first version gave 100% accuracy, which is unrealistic. So we added the kinds of mess real documents have:
1. **OCR noise**: characters swapped the way OCR confuses them (`o→0`, `l→1`, `rn→m`, `S→5`…) and dropped characters, at 0–12% intensity.
2. **Partial scans**: 35% of documents are cut off (only 20–70% of lines kept), and random lines are dropped.
3. **Missing title**: 25% of documents lose their heading (so the model cannot just read "INVOICE").
4. **Cross-category mixing**: 40% of documents have 2–6 lines borrowed from another category (a receipt that says "invoice", a loan form with bank details, a contract mentioning salary).
5. **Case changes**: some documents are all-UPPER or all-lower case.

### 6.5 Labelling
- **Real documents:** the label comes from the dataset itself (a receipt dataset contains only receipts, CUAD only contracts, etc.), so no manual labelling is needed.
- **Synthetic documents:** the template that generated a document *is* its label.
Both are stored in the `label` column of `documents.csv`.

### 6.6 Preprocessing (`classifier.preprocess`)
The same function is used in training and prediction:
1. lower-case everything;
2. replace every digit with `0` (amounts and ID numbers are random; their *shape* matters, not the value);
3. collapse whitespace.

### 6.7 Train / test split
- **3,200 documents**, **400 per class** (balanced); 1,500 real + 1,700 synthetic.
- **80/20 stratified split** → 2,560 train / 640 test (80 per class), `random_state=7` for reproducibility. The test set contains 285 real and 355 synthetic documents.
- **5-fold stratified cross-validation** on all data as a second, more robust estimate.
- **Separate held-out image set**: 32 newly generated documents rendered as images (half "scanned" with rotation, noise, blur, yellow paper tint) that the model **never saw**; used to test the *whole* pipeline including OCR.

### 6.8 Demo inputs (`sample_documents/`)
- `normal/`: for every category a **clean PNG** and a **phone-style scanned JPG**; plus **digital PDFs** (invoice, contract, bank statement) and a **TXT** resume.
- `abnormal/`: blank page, landscape photo, image with only "Hello", unrelated recipe text, ambiguous invoice/receipt mix, very blurry scan, corrupted file (random bytes with a .png name).

---

## 7. Feature Extraction (OCR + TF-IDF)

### 7.1 From file to text: `ocr.py`
| Input | Method |
|---|---|
| PNG, JPG, BMP, TIFF, WEBP | **RapidOCR**: text detection (DBNet) + text recognition (CRNN) models from PaddleOCR, run with ONNX Runtime on CPU. Image is auto-rotated using EXIF and downscaled to max 1800 px for speed. Detected boxes are sorted top-to-bottom, left-to-right and joined into lines. The mean box confidence = **OCR confidence**. |
| PDF | Reads the embedded text layer (instant). If there is almost no text (a scanned PDF), the first 3 pages are rendered at 150 DPI and OCR'd. |
| DOCX | Paragraph text via `python-docx` |
| TXT | Read directly |
| Anything else / corrupted | Raises `ExtractionError` → HTTP 415/422 with a clear message |

### 7.2 From text to numbers: TF-IDF (`train_model.build_pipeline`)
A computer cannot read words, so each document becomes a long vector of numbers. **TF-IDF** = *Term Frequency × Inverse Document Frequency*:
- **TF**: how often a term appears in *this* document (we use `sublinear_tf`, i.e. 1 + log(tf), so repeating a word 50 times doesn't dominate).
- **IDF**: how rare the term is across *all* documents. "the" appears everywhere → weight ≈ 0. "IFSC" appears mostly in bank documents → high weight.

We combine **two TF-IDF vectorizers** (a `FeatureUnion`):

| Vectorizer | What it looks at | Why |
|---|---|---|
| **Word TF-IDF** | single words and word pairs (1–2 grams), English stop-words removed, max 40,000 features (39,002 used) | Captures meaning: "invoice no", "date of birth", "closing balance", "hereinafter referred" |
| **Character TF-IDF** | 3–5 character pieces inside words (`char_wb`), max 30,000 features | **Robust to OCR errors**: "inv0ice" still shares "inv", "ice", "voice" with "invoice". Also handles words OCR glued together ("PAYMENTRECEIPT") |

**Total: 69,002 features per document.** (The word limit was raised from 20,000 to 40,000 when the real Kaggle text was added: its larger vocabulary was pushing common words of our scanned demo documents out of the vocabulary.) Example: the text *"Invoice No: INV-20931"* becomes non-zero values for features like `invoice`, `invoice inv`, ` inv`, `nvoi`, `voice`, `ice `, `no` …

---

## 8. Machine Learning Model

### 8.1 Problem type
**Supervised multi-class text classification.**
- **Input:** TF-IDF vector (69,002 numbers) of the document text.
- **Output classes (8):** invoice, receipt, identity_document, application_form, bank_statement, medical_report, resume, legal_contract.
- Plus a 9th *decision* outcome, **"unknown / Manual Review"**, produced by rules (Section 9), not by the model.

### 8.2 Algorithms compared (same 80/20 split)

| Model | Test accuracy | Macro F1 | Train time | Predict / doc |
|---|---|---|---|---|
| Logistic Regression (C=10) | 99.22% | 99.22% | 7.5 s | 1.2 ms |
| **Linear SVM, calibrated (C=0.5)** ✅ | **99.38%** | **99.37%** | 5.1 s | 1.0 ms |
| Multinomial Naive Bayes (α=0.05) | 97.19% | 97.18% | 3.6 s | 1.1 ms |

The script automatically **selects the best macro-F1** model, re-trains it on **100% of the data**, and saves it.

**How each algorithm works (simple explanation):**
- **Logistic Regression**: learns a weight for every feature per class; adds up `weight × feature value` and turns the scores into probabilities with the softmax function.
- **Linear SVM (Support Vector Machine)**: also learns weights, but chooses them to put the **widest possible margin** between classes. Excellent for high-dimensional sparse text. SVMs don't output probabilities, so we wrap it in `CalibratedClassifierCV` (3-fold), which learns how to convert SVM scores into **reliable probabilities**; we need these for the confidence threshold.
- **Naive Bayes**: counts how likely each word is in each class and multiplies the probabilities, assuming words are independent. Very fast, slightly less accurate.

### 8.3 Evaluation of the selected model (Linear SVM, calibrated)

- **Test accuracy: 99.38%** (636 / 640 correct)
- **Macro F1: 99.37%**
- **5-fold cross-validation accuracy: 99.44% ± 0.25%** (stable, not a lucky split)
- **Accuracy on the 285 unseen real Kaggle documents: 100%**; on the 355 unseen synthetic documents: 98.9%
- **End-to-end on 32 held-out scanned images (OCR + model): 32/32 = 100%**

| Class | Precision | Recall | F1 |
|---|---|---|---|
| Application Form | 100% | 100% | 100% |
| Bank Statement | 97.6% | 100% | 98.8% |
| Identity Document | 100% | 97.5% | 98.7% |
| Invoice | 100% | 100% | 100% |
| Legal Contract | 98.8% | 100% | 99.4% |
| Medical Report | 100% | 100% | 100% |
| Receipt | 100% | 97.5% | 98.7% |
| Resume / CV | 98.8% | 100% | 99.4% |

**Confusion matrix** (rows = true, columns = predicted; order: Application, Bank, ID, Invoice, Contract, Medical, Receipt, Resume):
```
Application  80  0  0  0  0  0  0  0
Bank          0 80  0  0  0  0  0  0
Identity      0  1 78  0  1  0  0  0
Invoice       0  0  0 80  0  0  0  0
Contract      0  0  0  0 80  0  0  0
Medical       0  0  0  0  0 80  0  0
Receipt       0  1  0  0  0  0 78  1
Resume        0  0  0  0  0  0  0 80
```
All 4 mistakes are **synthetic** documents that were heavily truncated and noisy and had lines borrowed from another category (e.g. a café receipt containing bank IFSC lines). They are listed on the Model page as *"Examples the model got wrong"*, with their source.

### 8.4 Real-world validation (why the Kaggle data matters)
Two checks are computed automatically by `train_model.py` and shown on the Model page (*Real-world validation* card):

| Check | Result | Meaning |
|---|---|---|
| Final model on **unseen real** test documents | **100%** (285/285) | the model works on real receipts, invoices, resumes, medical reports and contracts, not only on our templates |
| Model trained **only on synthetic** documents, tested on **all 1,500 real** ones | **93.7%** | our generator alone already produced a model that mostly generalises to real documents it never saw; adding real data closes the remaining gap |

**Honest caveat:** each real category comes from *one* dataset with its own style (SROIE receipts are Malaysian, with "RM" for ringgit; Kaggle resumes contain the placeholder "Company Name City, State"). The model partly learns these source-specific words (see 8.5), so 100% on the real test split is optimistic: real test documents come from the same datasets as the real training documents. Documents from a completely new source (e.g. your own office's receipts) would score lower. The Review Queue + Retrain loop exists exactly for that.

**Metric definitions** (for the viva):
- *Precision* = of the documents predicted as X, how many really were X.
- *Recall* = of the real X documents, how many we found.
- *F1* = harmonic mean of precision and recall.
- *Macro F1* = average F1 over classes (treats every class equally).

### 8.5 What the model learned (strongest words per class)
| Class | Top words |
|---|---|
| Application Form | form, app, personal, gender, applicant, guardian |
| Bank Statement | main, account, branch, bank, micr, holder |
| Identity Document | birth, india, sex, card, date birth, indian |
| Invoice | gstin, invoice, po, inv, order, product |
| Legal Contract | agreement, exhibit, term, agree, parties, shall |
| Medical Report | patient, age, dr, age sex, left, normal |
| Receipt | gst, receipt, total, rm, cash, tax |
| Resume | city state, state, experience, company city, skills, city |

Most words are exactly what a human would use. Two are **dataset artefacts** worth mentioning in the viva: `rm` (Malaysian ringgit, from the SROIE receipts) and `city state` / `company city` (anonymisation placeholders in the Kaggle resumes). This is a real-world lesson: a model learns *whatever* separates the classes, including quirks of where the data came from.

### 8.6 Explainability for every prediction
`classifier.predict()` multiplies each word's TF-IDF value by the predicted class's weight. The highest positive contributions are shown in the UI under **"Why this prediction?"**, e.g. a receipt shows `cash +0.07, counter +0.05, paid +0.04…`.

### 8.7 Model file
`models/document_classifier.joblib` (~21 MB, mostly the TF-IDF vocabularies) contains the full scikit-learn **Pipeline** (both vectorizers + classifier), so prediction is one call. `models/metrics.json` stores all evaluation numbers.

---

## 9. Decision Rules & Abnormal Input Handling

The ML model *always* returns one of 8 classes, even for a photo of a mountain. A real system must know **when not to trust it**. `pipeline.decide()` adds these rules:

| Situation | Detection | Result |
|---|---|---|
| Blank page / photo / unreadable | fewer than **25** characters of text | `unknown` → **Manual Review**, red alert |
| Not a supported document (e.g. a recipe) | less than **35%** of its words exist in the model's vocabulary ("familiar words") | `unknown` → **Manual Review**, red alert |
| Model unsure | top probability below **70%** | `unknown` → **Manual Review**, amber alert with the model's suggestion |
| Close call | top-2 probabilities differ by < 25% | routed, but blue info alert |
| Poor scan | OCR confidence < 75% | amber "re-scan" warning |
| Identity document | category = identity_document | info alert: restricted KYC folder |
| Duplicate | same **SHA-256 hash** as an earlier file | amber alert pointing to the original document |
| Corrupted file | image library cannot decode it | **HTTP 422**, nothing routed |
| Unsupported type (.exe…) | extension not allowed | **HTTP 415** |
| Empty file / no input | 0 bytes / missing fields | **HTTP 422 / 400** |
| Too large | > 15 MB | **HTTP 413** |

All thresholds live in `backend/config.py` and can be tuned.

---

## 10. Routing to Departments

`router.route_file()` copies the original file to:
```
data/routed/<Department folder>/<6-digit document id>_<original filename>
e.g. data/routed/Finance_Accounts_Payable/000012_invoice_march.pdf
```

| Category | Department | Folder |
|---|---|---|
| Invoice | Finance - Accounts Payable | `Finance_Accounts_Payable` |
| Receipt | Finance - Expense Claims | `Finance_Expense_Claims` |
| Identity Document | HR - KYC & Verification | `HR_KYC_Verification` |
| Application Form | Admissions & Applications Desk | `Applications_Desk` |
| Bank Statement | Finance - Accounts & Audit | `Finance_Accounts_Audit` |
| Medical Report | Health & Insurance Claims | `Health_Insurance_Claims` |
| Resume / CV | HR - Recruitment | `HR_Recruitment` |
| Legal Contract | Legal & Compliance | `Legal_Compliance` |
| *(unknown)* | Manual Review Desk | `Manual_Review` |

When a human corrects a category, `router.reroute_file()` **moves** the file to the new folder. In a real deployment these folders could be network shares, e-mail queues or ERP inboxes; only `router.py` would change.

---

## 11. Classification History (Database)

A single SQLite table `documents` in `data/history.db`:

| Column | Meaning |
|---|---|
| id, created_at, updated_at | record id and timestamps |
| filename, stored_name, file_ext, file_size, file_hash, source | file info; `source` = dashboard / scanner-sim-01 / text-input / curl… |
| extraction_method, ocr_confidence, pages, text | how text was obtained and the text itself |
| predicted_category, **confidence**, **probabilities** (JSON) | model output for **all 8 classes** |
| top_terms (JSON), known_word_ratio | explanation + out-of-domain score |
| final_category, department, routed_path | where it actually went |
| status | `auto_routed`, `needs_review`, `reviewed` (human confirmed), `corrected` (human changed) |
| alerts, key_fields, ai_insights (JSON) | warnings, extracted fields, optional AI output |
| extraction_ms, classify_ms, total_ms, model_version | performance + which model version decided |

The History page can search, filter by category/status/department and **export CSV**.

---

## 12. Edge Implementation (Flask Microservice)

`backend/app.py` starts one Python process that:
- loads the ML model **once** into memory (`DocumentClassifier`);
- warms up the OCR engine in a background thread;
- serves the REST API **and** the dashboard on `http://<device-ip>:5000`;
- is multi-threaded (`threaded=True`) so the scanner and the dashboard can work at the same time.

### REST API

| Method & path | Purpose |
|---|---|
| `GET /api/health` | service status, model name/version, OCR ready, AI enabled, uptime |
| `GET /api/categories` | categories, departments, thresholds |
| `POST /api/classify` | **upload a file** (`file`) or **text** (`text`) + optional `source` → full prediction JSON |
| `GET /api/documents` | history (query: `search`, `category`, `status`, `department`, `limit`) |
| `GET /api/documents/<id>` | one record incl. full text |
| `GET /api/documents/<id>/file` | original file (preview / `?download=1`) |
| `POST /api/documents/<id>/review` | human confirms/corrects `{ "category": "invoice" }` |
| `POST /api/documents/<id>/ai` | optional AI insights |
| `DELETE /api/documents/<id>` | delete record and routed file |
| `GET /api/stats` | KPIs and chart data for the dashboard |
| `GET /api/departments` | department folders, counts, recent docs |
| `GET /api/model` | training metrics + end-to-end test results |
| `POST /api/model/retrain` | retrain with human-verified docs and hot-swap the model |
| `GET /api/samples`, `POST /api/samples/classify` | demo documents |
| `GET /api/export.csv` | history as CSV |

Example response of `POST /api/classify` (shortened):
```json
{
  "id": 8, "filename": "invoice_clean.png", "source": "scanner-sim-01",
  "extraction_method": "OCR (RapidOCR / ONNX)", "ocr_confidence": 0.978,
  "predicted_category": "invoice", "confidence": 0.9942,
  "probabilities": [{"category": "invoice", "probability": 0.9942}, {"category": "identity_document", "probability": 0.0021}, "..."],
  "top_terms": [{"term": "invoice", "weight": 0.1}, {"term": "po", "weight": 0.09}],
  "final_category": "invoice", "department": "Finance - Accounts Payable",
  "routed_path": "Finance_Accounts_Payable/000008_invoice_clean.png",
  "status": "auto_routed", "alerts": [],
  "key_fields": {"document_number": "INV-64431", "total_amount": "188,776.78"},
  "extraction_ms": 2930, "classify_ms": 6.2, "total_ms": 2950, "model_version": 1
}
```

### Docker (optional)
```bash
docker compose up --build        # builds the image and starts the service on port 5000
```
The image installs the same pinned libraries; the `.env` key is **not** baked into the image (excluded by `.dockerignore`) and is passed at runtime. The model can also be deployed to Azure IoT Edge as this container image.

---

## 13. Communication (HTTP)

We demonstrate HTTP communication between the edge service and **three** different clients:

1. **Web dashboard** (browser) calls the REST API with `fetch()` (`frontend/js/api.js`). It polls `/api/health` and `/api/stats` every 5 s, so new documents appear **live**.
2. **Scanner / device simulator**: `backend/scanner_simulator.py` is a **separate program** acting like a network scanner in an office. It reads files from a folder and POSTs them one by one, printing the edge service's reply:
   ```
   python scanner_simulator.py                                        # send all demo documents
   python scanner_simulator.py --folder ../sample_documents/abnormal  # send edge cases
   python scanner_simulator.py --loop --interval 3                    # continuous scanning
   python scanner_simulator.py --url http://192.168.1.20:5000         # edge device on another PC
   ```
   Output:
   ```
   FILE                          HTTP  CATEGORY            CONF  DEPARTMENT                     TIME
   invoice_scanned.jpg            200  invoice            98.6%  Finance - Accounts Payable   5543ms
   blank_page.png                 200  unknown             0.0%  Manual Review Desk           3075ms  [REVIEW]
   corrupted_file.png             422  REJECTED: File is corrupted or unreadable
   ```
3. **Any HTTP client**, e.g. `curl -F "file=@invoice.png" -F "source=curl" http://localhost:5000/api/classify`.

The *Edge System* page also has a **Live API console** that sends GET requests and shows the raw JSON, HTTP status and latency, which makes the communication visible to the jury.

*(MQTT was not needed since HTTP is explicitly allowed; it would be a small add-on, see Future Scope.)*

---

## 14. Dashboard (Frontend)

Open `http://localhost:5000`. Light/dark theme toggle (top right), responsive for phones, works offline.

| Page | What it shows / does |
|---|---|
| **Dashboard** | Hero with the pipeline; 6 KPI tiles (documents processed, auto-routed %, needs review, avg confidence, avg processing time split into OCR/ML, live human-verified accuracy); charts: documents by category, daily volume (14 days), confidence distribution, routing outcome; recent documents table; alerts feed. **Auto-refreshes every 5 s** (LIVE). |
| **Classify Document** | 3 input modes: **drag & drop upload** (multiple files, processed one after another in a queue), **paste text** (with examples incl. random text), **sample gallery** (normal and abnormal demo files with thumbnails). Shows the full result (below). |
| **Result view** (also opens from any table) | 4-step pipeline tracker with timings (Received → Text extracted → Classified → Routed/Manual review); confidence ring; predicted category & status; department + folder path; alerts; **probability bars for all 8 classes**; **"Why this prediction?"** influential words; locally extracted key fields; **human review** (confirm/reassign); **AI insights** button; original document preview (image/PDF); extracted text; processing details (OCR confidence, familiar words, timings, SHA-256). |
| **Review Queue** | All documents with status *needs_review*, with thumbnail, alerts, the model's top-3 guesses, and a one-click "Assign" to a department. Sidebar badge shows the count. |
| **History** | Searchable, filterable table of every record; click a row for details; **Export CSV**. |
| **Departments** | Routing table + one card per department with file count, folder size and recent documents. |
| **Model & Analytics** | Algorithm, version, test accuracy, macro F1, cross-validation, dataset size, feature count; end-to-end OCR test results; algorithm comparison (error-rate chart + table); per-class precision/recall/F1; confusion-matrix heat map; top keywords per class; dataset distribution; **Retrain** button; misclassified examples. |
| **Edge System** | Service status, uptime, host, model, OCR engine, AI status; architecture diagram; privacy/latency/offline notes; **Live API console**; traffic per input source; commands for the simulator and curl. |

Deep link: `http://localhost:5000/#history/12` opens document #12 directly.

---

## 15. Optional AI Assistant (OpenAI gpt-4o-mini)

- **What:** on a document's detail view, *Generate AI summary & key fields* sends the OCR text to **gpt-4o-mini** (the cheapest capable OpenAI model; ~700 tokens ≈ a fraction of a cent per document). It returns JSON: a 2–3 sentence **summary**, up to 8 **key fields**, its own **category opinion** (agrees / disagrees with the local model), **next actions** for the department, and a **priority**.
- **Why optional:** the project is about **edge** analytics. The classification and routing **never** depend on the internet. The AI is a convenience "second opinion" that only runs when a human clicks the button.
- **Privacy:** before sending, `ai_assistant.mask_sensitive()` replaces e-mails with `[email]` and any long number (account, Aadhaar, card, phone) with `XXXX` + last 4 digits.
- **Configuration:** `backend/.env` → `OPENAI_API_KEY=...`, `OPENAI_MODEL=gpt-4o-mini`. Remove the key and the button is disabled; everything else works the same.
- **Local alternative always shown:** `extractor.py` extracts invoice/receipt numbers, total amount, dates, e-mail, phone, GSTIN, IFSC and names with regular expressions, fully offline.

---

## 16. Human-in-the-Loop & Retraining

1. Uncertain documents go to the **Review Queue** instead of the wrong department.
2. A staff member picks the right category → the file is **moved** to that department, status becomes `reviewed` or `corrected`.
3. These human-verified documents are **new labelled training data**.
4. *Model & Analytics → Retrain model now* calls `POST /api/model/retrain`: the original 3,200 docs + all verified docs are used to retrain all 3 algorithms, the best is saved as **version N+1** and **hot-swapped** into the running service (no restart; ~1 minute on a laptop).
5. The dashboard's **"Live accuracy"** KPI shows how often the model's suggestion matched the human decision.

This is called **active learning / continuous learning**, and it is how the system adapts to a real organisation's own documents over time.

---

## 17. Testing (Normal & Abnormal Cases)

Run: `cd backend && python test_system.py` (uses a temporary data folder; your real history is untouched). Latest result: **43/43 passed**, full table in `reports/test_report.md`.

### Normal cases (21 tests)
All 8 categories as clean PNG, phone-style scanned JPG, digital PDF (3), plain TXT and pasted text → **every one classified correctly and auto-routed** with 86–99.9% confidence, and the routed file verified on disk.

### Abnormal / varied cases (13 tests)
| Input | Expected | Result |
|---|---|---|
| `blank_page.png` | Manual Review (no text) | ✅ unknown, needs_review |
| `landscape_photo.jpg` | Manual Review (not a document) | ✅ |
| `very_little_text.png` ("Hello") | Manual Review | ✅ |
| `unrelated_recipe.txt` | Manual Review (out-of-domain) | ✅ best guess only 62% → Manual Review |
| `ambiguous_invoice_receipt.png` | review or finance category | ✅ 66.9% → Manual Review |
| 5-line snippet "INVOICE / Subtotal / GST / Total" | review or invoice, never a wrong department | ✅ 54% → Manual Review (real SROIE receipts are also titled "TAX INVOICE" and list GST, so this is genuinely ambiguous) |
| `very_blurry_scan.jpg` | medical report or review | ✅ medical_report 98.9% |
| `corrupted_file.png` | HTTP 422 | ✅ |
| `virus.exe` | HTTP 415 | ✅ |
| `empty.png` (0 bytes) | HTTP 422 | ✅ |
| request with no file/text | HTTP 400 | ✅ |
| 16 MB file | HTTP 413 | ✅ |
| same file uploaded twice | duplicate alert | ✅ |

### Workflow & API (9 tests)
Human correction moves the file (`Manual_Review/… → Applications_Desk/…`), invalid category rejected, and all GET endpoints return 200.

### End-to-end accuracy on scanned images
32 held-out rendered documents (16 clean, 16 noisy/rotated/blurred) → OCR → model: **32/32 correct (100%)**, average OCR ≈ 3.0 s, average ML ≈ 9 ms.

---

## 18. Performance

Measured on the development laptop (Windows 11, Python 3.12, CPU only, no GPU):

| Step | Typical time |
|---|---|
| ML classification (TF-IDF + SVM) | **~6–16 ms** per document |
| PDF / TXT / DOCX text extraction | **~10–30 ms** |
| OCR, receipt / ID card image | ~0.8–2 s |
| OCR, full A4 page image | ~2–5 s (more text lines = longer) |
| Training 3 models + 5-fold CV + real-data check | ~60 s |
| Model size on disk | ~21 MB |
| First OCR call after start-up | +1 s (model loading; we warm it up in the background) |

OCR dominates the time; the ML part is effectively instant. On a Raspberry Pi-class device OCR would take longer (≈5–15 s per page), still acceptable for a mail-room workflow.

---

## 19. Role of Edge Computing

- **Where the computation happens:** OCR, feature extraction, classification, decision rules, routing and storage all run **on the local device** (laptop, office PC, mini-PC or edge gateway). Proven by unplugging the internet: everything except the optional AI button continues to work.
- **Edge vs cloud trade-off:** cloud OCR/AI services are more accurate on very messy documents but cost money per page, need connectivity, add latency and send sensitive documents off-site. Our design keeps the **critical path at the edge** and uses the cloud only as an **opt-in assistant**, with masking.
- **Edge-friendly choices:** ONNX Runtime (optimised CPU inference), an ~21 MB linear model, SQLite (no database server), no frontend build step, Chart.js bundled locally, Docker image for deployment to edge runtimes (e.g. Azure IoT Edge).
- **Upstream summarisation:** the `/api/stats` endpoint shows how an edge node could send only *aggregated* metadata (counts, confidence, alerts) to a central office instead of raw documents.

---

## 20. Limitations & Future Scope

### Limitations (be honest with the jury)
1. **Partly synthetic, single-source data.** 1,500 of the 3,200 training documents are real (Kaggle), but ID documents, bank statements and application forms are synthetic because no public dataset of them can exist. Each real category also comes from only one dataset, so the model partly learns source quirks (e.g. "RM" in Malaysian receipts). Accuracy on documents from a brand-new source would be lower than the reported 99%; the Review Queue + Retrain loop is designed to add those organisation-specific examples.
2. **Text only.** The model uses text, not visual layout (logos, tables, photos). Documents with almost no text (e.g. a photo-only ID back side) go to Manual Review.
3. **OCR quality.** Very blurry, handwritten, or rotated-90° images reduce OCR quality. The bundled OCR model sometimes merges words ("PAYMENTRECEIPT"); character n-grams make the classifier tolerant of this.
4. **Languages.** Trained on English documents only; Hindi/regional text is not classified reliably.
5. **One category per file.** A PDF containing an invoice *and* an ID card gets one label for the whole file.
6. **OCR speed on CPU** (2–5 s per A4 page) limits throughput to roughly 1,000–1,500 pages per hour per device.
7. **No user authentication**: fine for a prototype on a trusted LAN, not for production.

### Future scope
- Add real anonymised ID cards, bank statements and forms from a partner organisation, and more than one source per category; add layout-aware models (e.g. LayoutLM) or a lightweight image CNN as a second opinion.
- Page splitting for multi-document PDFs.
- Multilingual OCR + training data (Hindi, Marathi…).
- MQTT publishing of routing events (`docs/routed/<department>`) for other systems.
- E-mail / Teams notification to departments; integration with ERP / HRMS.
- Login and role-based access (e.g. only HR sees identity documents), encryption at rest.
- Watch-folder ingestion from a real network scanner.

---

## 21. How to Run

### Requirements
- Windows/Linux/macOS with **Python 3.10–3.12** (tested on 3.12.10)
- ~500 MB disk for libraries; no GPU, no hardware, no Tesseract install needed.

### Option A: Windows quick start
1. Double-click **`setup.bat`** (installs libraries, only once).
2. Double-click **`run.bat`**: starts the service and opens **http://localhost:5000**.

### Option B: Manual (any OS)
```bash
pip install -r requirements.txt
cd backend
python generate_dataset.py     # (already done) synthetic documents + demo samples + test images
python kaggle_dataset.py       # (already done) downloads real Kaggle documents (no account needed), builds documents.csv
python train_model.py          # (already done) trains & saves the model, prints metrics
python app.py                  # starts the edge service → open http://localhost:5000
```
In a **second terminal** (to demo device communication):
```bash
cd backend
python scanner_simulator.py
```
Run the tests:
```bash
cd backend
python test_system.py
```

### Option C: Docker
```bash
docker compose up --build      # → http://localhost:5000
```

### Optional AI
`backend/.env` already contains the OpenAI key and `OPENAI_MODEL=gpt-4o-mini`. To run 100% offline, empty `OPENAI_API_KEY`.

### Reset the demo
Stop the service and delete `data/history.db`, `data/uploads/` and `data/routed/`; they are recreated automatically.

### Troubleshooting
| Problem | Fix |
|---|---|
| Python crashes on start (Windows) when importing OCR | Make sure `onnxruntime==1.20.1` is installed (newer versions conflict with scikit-learn's DLLs on some Windows machines) |
| `Model not found` | run `python generate_dataset.py`, `python kaggle_dataset.py`, then `python train_model.py` |
| `kaggle_dataset.py` cannot download | needs internet once; files are then cached in `data/kaggle_raw/`. The committed `documents.csv` and model already contain the result, so this is only needed to rebuild |
| Port 5000 busy | set `EDGE_PORT=5050` before `python app.py` |
| Simulator is slow to connect | use `--url http://127.0.0.1:5000` (Windows resolves `localhost` to IPv6 first) |
| AI button disabled | add `OPENAI_API_KEY` to `backend/.env` and restart |

---

## 22. Live Demo Script for the Jury

A suggested 8–10 minute flow (each step uses **live** predictions):

1. **Problem (30 s)**: Dashboard hero: "offices receive mixed documents; we sort and route them automatically, on-device."
2. **Live upload (2 min)**: *Classify Document* → drag in a scanned invoice JPG and a PDF. Point out the pipeline tracker with timings, the confidence ring, the probability bars, *"Why this prediction?"* words, key fields, and the **department folder path**. Open the folder `data/routed/Finance_Accounts_Payable` in Explorer to prove the file was routed.
3. **A document they bring**: ask a juror for any document or take a phone photo of a printed page and upload it.
4. **Abnormal inputs (1.5 min)**: *Sample gallery → Abnormal*: blank page, landscape photo, recipe text, corrupted file. Show how each is handled (Manual Review / clear rejection) and that the service keeps running. Paste "Example: random text".
5. **Device communication (1.5 min)**: second terminal: `python scanner_simulator.py`. Switch to the Dashboard and watch documents appear **live** (LIVE badge, charts update). Show the *Edge System → Live API console* and the traffic-by-source table.
6. **Human-in-the-loop (1 min)**: *Review Queue* → assign a document → it moves folder; *Model → Retrain model now* → version increases.
7. **Model explanation (1.5 min)**: *Model & Analytics*: the **Real-world validation** card (1,500 real Kaggle documents, 100% on unseen real docs, 93.7% for the synthetic-only model), the dataset chart (real vs synthetic per category), algorithm comparison, confusion matrix, cross-validation, end-to-end OCR test, keywords (point out the `rm` artefact as an honest limitation).
8. **Optional AI (30 s)**: open an invoice → *Generate AI summary*; mention masking and that it's optional.
9. **Edge argument (30 s)**: turn Wi-Fi off and upload again: still works.
10. **Testing**: show `reports/test_report.md` (43/43 + 32/32).

---

## 23. Code Walkthrough: Life of One Document

What happens when you drop `invoice.jpg` on the dashboard:

1. **Browser**: `classify.js → API.classifyFile(file)` sends `POST /api/classify` (multipart form, field `file`).
2. **`app.py → classify()`**: checks the extension is allowed (else 415), calls `pipeline.save_upload()` which stores it as `data/uploads/<random>_invoice.jpg`.
3. **`app.py → run_pipeline()`**: rejects empty files, then calls `pipeline.process_document(path, name, source, classifier)`.
4. **`pipeline.process_document()`**:
   1. `file_hash()` → SHA-256; `database.find_by_hash()` checks for duplicates.
   2. `ocr.extract_text(path)` → `ocr_image()` runs RapidOCR, rebuilds lines, returns text + OCR confidence + time.
   3. If text ≥ 25 chars: `classifier.predict(text)`:
      - `preprocess()` (lower-case, digits → 0),
      - pipeline `features.transform()` → 69,002-dim TF-IDF vector,
      - `clf.predict_proba()` → 8 probabilities,
      - explanation: TF-IDF × class weights → top words,
      - `known_word_ratio()` → out-of-domain score.
   4. `decide()` applies the rules (Section 9) → final category, status, alerts.
   5. `extractor.extract_fields()` → invoice no, total, dates…
   6. `database.insert_document()` → new row, gets an `id`.
   7. `router.route_file()` → copies to `data/routed/Finance_Accounts_Payable/000042_invoice.jpg`.
   8. `database.update_document()` saves the routed path and total time; the full record is returned.
5. **`app.py`** returns it as JSON (HTTP 200).
6. **Browser**: `ui.js → docDetailHtml(doc)` renders the result; `refreshBadges()` updates the review count; the dashboard picks it up on its next 5-second refresh.

**Training flow:** `generate_dataset.py` → `synthetic_documents.csv` → `kaggle_dataset.py` (+ real Kaggle documents) → `data/dataset/documents.csv` → `train_model.py: load_dataset() → train_test_split → build_pipeline() for 3 models → evaluate → cross_val_score → refit best on all data → joblib.dump + metrics.json` → `classifier.py` loads it.

---

## 24. Likely Jury Questions & Answers

**Q: Why TF-IDF and not deep learning?**
A: It's the suggested approach, it's very accurate for text-heavy documents (99.4%), trains in about a minute, predicts in ~9 ms on a CPU, the model is only ~21 MB, and it's explainable (we can show which words drove the decision). Deep models need GPUs, much more data and are harder to explain: a poor fit for an edge device.

**Q: Why did you choose SVM over Logistic Regression?**
A: We trained both (plus Naive Bayes) on the same split and selected automatically by macro F1. SVM scored 99.38% vs 99.22%. The difference is small (1 document out of 640); both are linear models over the same features. We calibrate the SVM so it still gives probabilities.

**Q: What is calibration?**
A: An SVM outputs distances from its decision boundary, not probabilities. `CalibratedClassifierCV` learns (with internal 3-fold CV) a mapping from those scores to probabilities, so "90% confidence" really means right about 90% of the time. We need that for the 70% threshold.

**Q: Why character n-grams?**
A: OCR makes spelling mistakes ("inv0ice") and merges words. Character pieces like "nvoi", "voice" still match, so the model is robust to OCR noise.

**Q: Which dataset did you use?**
A: A mix. 1,500 real documents from five public Kaggle datasets (SROIE receipts, a company invoice dataset, a resume dataset, mtsamples medical transcriptions, CUAD legal contracts) plus 1,700 synthetic documents. ID cards, bank statements and application forms are synthetic because they are private and no public dataset of them can legally exist. Every row has a `source` column, and we report accuracy on real and synthetic documents separately.

**Q: Isn't 99% accuracy too good to be true?**
A: Partly, and we say so. On *unseen real* documents the model scores 100%, but those come from the same five datasets as the training documents, and each dataset has its own style (e.g. Malaysian "RM" receipts), which the model partly learns. A model trained *only* on our synthetic data scored 93.7% on all 1,500 real documents, which is a fairer estimate of performance on documents from a brand-new source. On the synthetic part we deliberately added OCR noise, truncation, missing titles and borrowed lines; that is where the remaining 4 errors are. In deployment, the Review Queue + Retrain loop adds the organisation's own labelled documents.

**Q: Did adding real data make the model better?**
A: It made it more *trustworthy*. Before, we could only claim accuracy on our own templates. Now we can show it on real receipts, contracts, resumes, medical reports and invoices. It also exposed a real-world ambiguity the synthetic data hid: real receipts are often titled "TAX INVOICE", so a tiny invoice snippet now (correctly) goes to Manual Review instead of being auto-routed.

**Q: What happens with a document type the model has never seen?**
A: Three safety nets: (1) if fewer than 35% of its words are known to the model, it's flagged out-of-domain; (2) if confidence < 70%, it goes to Manual Review; (3) a human can assign it and retrain.

**Q: How is this "edge"?**
A: All inference (OCR + ML) runs on the local machine in a Flask microservice; it works with no internet. Data never leaves the premises. It can be containerised with Docker and deployed on an edge gateway / Azure IoT Edge.

**Q: Where is the communication requirement?**
A: HTTP REST. The dashboard, a separate scanner simulator program and curl all talk to the edge service over HTTP. We show it live, including the raw JSON in the API console.

**Q: How do you handle duplicate documents?**
A: SHA-256 hash of the file bytes; an identical file triggers a duplicate alert pointing to the first record.

**Q: Why is OCR slow compared to classification?**
A: OCR runs two neural networks (text detection + recognition) over the whole image on a CPU; classification is a single sparse dot product. On a GPU or with smaller images OCR would be faster.

**Q: Is the OpenAI part required? Isn't it against edge?**
A: Not required. It is opt-in per document, sensitive numbers are masked, and the system is fully functional with no key. It demonstrates a hybrid edge–cloud design where the cloud adds value without being on the critical path.

**Q: How would you scale this?**
A: Run several edge nodes (one per office) each with its own model; send only aggregated statistics to a central server; periodically retrain a central model with verified data and push the new version to all nodes.

**Q: What are precision and recall for bank statements?**
A: Precision 100% (when we say bank statement, it is one), recall 94% (3 of 50 were predicted as something else, mostly heavily truncated ones).

---

## 25. Glossary

| Term | Meaning |
|---|---|
| **Edge computing** | Processing data on/near the device where it's created instead of in a distant cloud |
| **OCR** | Optical Character Recognition: converting an image of text into text |
| **ONNX Runtime** | Fast engine to run neural network models on CPU |
| **TF-IDF** | Term Frequency × Inverse Document Frequency: word importance score |
| **n-gram** | sequence of n words (word n-gram) or n characters (char n-gram) |
| **Logistic Regression / SVM / Naive Bayes** | Classic machine-learning classifiers |
| **Calibration** | Converting model scores into trustworthy probabilities |
| **Stratified split** | Train/test split keeping the same class proportions |
| **Cross-validation** | Training/testing k times on different splits to get a stable accuracy estimate |
| **Confusion matrix** | Table of true vs predicted classes |
| **Precision / Recall / F1** | Correctness of positive predictions / coverage of real positives / their balance |
| **Out-of-domain** | Input unlike anything in the training data |
| **Human-in-the-loop** | People review uncertain predictions; their decisions improve the model |
| **REST API** | Web interface where clients send HTTP requests and get JSON back |
| **Microservice** | Small independent service doing one job, reachable over the network |
| **SHA-256** | Cryptographic fingerprint of a file, used for duplicate detection |
| **Hot-swap** | Replacing the model in a running service without restarting it |
