# Tech.md: Technical Reference for DocuRoute Edge

This file covers every technical detail of the project: which models are used, which datasets, how each model was trained, the exact settings, and the results. Everything here matches the code and the numbers in `models/metrics.json` and `reports/test_report.md`.

For the problem statement, demo script and viva Q&A, see [EVERYTHING.md](EVERYTHING.md).

---

## Contents
1. [One-paragraph summary](#1-one-paragraph-summary)
2. [All the models in the system](#2-all-the-models-in-the-system)
3. [Technology stack (exact versions)](#3-technology-stack-exact-versions)
4. [Dataset](#4-dataset)
5. [Text extraction (OCR models)](#5-text-extraction-ocr-models)
6. [Preprocessing](#6-preprocessing)
7. [Feature extraction (TF-IDF)](#7-feature-extraction-tf-idf)
8. [The ML models and how each one works](#8-the-ml-models-and-how-each-one-works)
9. [How the model was trained (step by step)](#9-how-the-model-was-trained-step-by-step)
10. [Evaluation results](#10-evaluation-results)
11. [How a prediction is made at run time](#11-how-a-prediction-is-made-at-run-time)
12. [Decision rules and thresholds](#12-decision-rules-and-thresholds)
13. [Routing, storage and history](#13-routing-storage-and-history)
14. [Key-field extraction](#14-key-field-extraction)
15. [Optional AI assistant (OpenAI)](#15-optional-ai-assistant-openai)
16. [Retraining (human in the loop)](#16-retraining-human-in-the-loop)
17. [Edge service and REST API](#17-edge-service-and-rest-api)
18. [Frontend](#18-frontend)
19. [Deployment](#19-deployment)
20. [Testing](#20-testing)
21. [Performance](#21-performance)
22. [Limitations](#22-limitations)
23. [Numbers to remember](#23-numbers-to-remember)

---

## 1. One-paragraph summary

A document (image, scan, PDF, Word file or text) is uploaded to a **Flask microservice running on the local machine**. **RapidOCR** (PaddleOCR PP-OCRv4 models on ONNX Runtime, CPU) turns it into text. The text is cleaned and converted into a **69,002-number TF-IDF vector** (word and character n-grams). A **calibrated Linear SVM** (scikit-learn) predicts one of **8 categories** with a probability for each. **Decision rules** send uncertain or unfamiliar documents to Manual Review. Otherwise the file is **copied into the department's folder**, and everything is stored in **SQLite**. The model was trained on **3,200 documents: 1,500 real ones from 5 public Kaggle datasets and 1,700 synthetic ones**. It reaches **99.38% test accuracy** and **100% on unseen real documents**. Everything runs offline; the only cloud part is an **optional gpt-4o-mini summary** button.

---

## 2. All the models in the system

| # | Model | Type | What it does | Where it runs | Trained by us? |
|---|---|---|---|---|---|
| 1 | **PP-OCRv4 text detector** (`ch_PP-OCRv4_det_infer.onnx`, 4.7 MB) | Deep learning, DBNet (Differentiable Binarization) segmentation network | Finds the boxes in an image that contain text | Local CPU, ONNX Runtime | No, pre-trained by Baidu PaddleOCR |
| 2 | **PP-OCRv4 text recogniser** (`ch_PP-OCRv4_rec_infer.onnx`, 10.9 MB) | Deep learning, SVTR-LCNet (CNN + transformer blocks) with CTC decoding | Reads the characters inside each text box | Local CPU, ONNX Runtime | No, pre-trained |
| 3 | Text-angle classifier (`ch_ppocr_mobile_v2.0_cls_infer.onnx`) | Small CNN | Detects upside-down text lines | **Disabled** (`use_cls=False`) to save time; phone rotation is fixed from EXIF instead | No |
| 4 | **TF-IDF vectorizers** (word + character) | Statistical feature extractor | Turns text into 69,002 numeric features | Local CPU, scikit-learn | **Yes**, vocabulary and IDF weights learnt from our dataset |
| 5 | **Linear SVM, calibrated** ✅ selected | Classical ML, linear classifier | Predicts the document category + probabilities | Local CPU, scikit-learn | **Yes** |
| 6 | Logistic Regression | Classical ML, linear classifier | Candidate, compared during training | Training only | **Yes** |
| 7 | Multinomial Naive Bayes | Classical ML, probabilistic classifier | Candidate, compared during training | Training only | **Yes** |
| 8 | **gpt-4o-mini** (OpenAI) | Large language model | Optional summary, key fields, second opinion | Cloud, **only on button click** | No |

Models 4 and 5 are saved together as one scikit-learn `Pipeline` in `models/document_classifier.joblib` (~21 MB). Models 1–3 ship inside the `rapidocr_onnxruntime` Python package.

**Why this split?** OCR is a hard vision problem, so we use proven pre-trained deep models for it. Choosing a document type from text is a simpler problem, where a small, fast, explainable linear model trained on our own data works best on an edge CPU.

---

## 3. Technology stack (exact versions)

From `requirements.txt`, tested on Windows 11 with Python 3.12.10.

| Area | Library | Version | Used for |
|---|---|---|---|
| Web service | Flask | 3.0.3 | REST API + serving the dashboard |
| | flask-cors | 6.0.5 | Allow other devices/clients to call the API |
| | python-dotenv | 1.0.0 | Load `backend/.env` (OpenAI key) |
| Machine learning | scikit-learn | 1.3.2 | TF-IDF, SVM, LR, NB, metrics, cross-validation |
| | numpy | 1.26.2 | Arrays |
| | joblib | 1.3.2 | Save / load the trained model |
| OCR / reading files | rapidocr_onnxruntime | 1.4.4 | OCR (PaddleOCR models) |
| | onnxruntime | 1.20.1 | Runs the OCR neural networks on CPU (pinned: newer versions crash with scikit-learn's DLLs on some Windows PCs) |
| | Pillow | 12.1.1 | Image loading, EXIF rotation, resizing |
| | PyMuPDF | 2.1 | PDF text layer + rendering scanned PDF pages |
| | python-docx | 1.2.0 | Word documents |
| AI + simulator | openai | 2.36.0 | Optional gpt-4o-mini call |
| | requests | 2.33.1 | Scanner simulator HTTP client |
| Database | SQLite | built into Python | Classification history |
| Frontend | HTML + CSS + vanilla JavaScript | no build step | Dashboard |
| | Chart.js | 4.4.1 (stored locally in `frontend/vendor/`) | Charts, works offline |
| Deployment | Docker + docker-compose | Python 3.12-slim image | Container for edge devices |

---

## 4. Dataset

### 4.1 Overview

| | Value |
|---|---|
| File | `data/dataset/documents.csv`, columns `label, text, source` |
| Total documents | **3,200** |
| Per category | **400** (perfectly balanced) |
| Real documents (Kaggle) | **1,500** (`source = kaggle`) |
| Synthetic documents | **1,700** (`source = synthetic`) |
| Categories | 8 |
| Train / test split | 2,560 / 640 (80/20, stratified) |

### 4.2 Composition per category

| Category | Real (Kaggle) | Synthetic | Kaggle dataset used | Licence |
|---|---|---|---|---|
| Invoice | 300 | 100 | `ayoubcherguelaine/company-documents-dataset` (Company Documents Dataset: 830 invoices with extracted text) | Apache 2.0 |
| Receipt | 300 | 100 | `ryanznie/sroie-datasetv2-with-labels` (SROIE 2019, ICDAR competition: 973 scanned receipts with OCR text) | MIT |
| Resume | 300 | 100 | `snehaanbhawal/resume-dataset` (2,400+ resumes from livecareer.com, 24 job categories) | CC0 |
| Medical Report | 300 | 100 | `tboyle10/medicaltranscriptions` (~5,000 medical transcriptions from mtsamples.com) | CC0 |
| Legal Contract | 300 | 100 | `konradb/atticus-open-contract-dataset-aok-beta` (CUAD v1: 510 commercial contracts, The Atticus Project) | CC BY 4.0 |
| Identity Document | 0 | 400 | none (private data, no public dataset exists) | n/a |
| Bank Statement | 0 | 400 | none (private data) | n/a |
| Application Form | 0 | 400 | none (private data) | n/a |

### 4.3 How the real data was collected: `backend/kaggle_dataset.py`
1. **Download without an account.** Public Kaggle files download from `https://www.kaggle.com/api/v1/datasets/download/<owner>/<dataset>/<file>`, with the file path URL-encoded. Only the needed files are downloaded (about 110 MB) and cached in `data/kaggle_raw/`, which is not committed.
   - Invoices: `company-document-text.csv` → rows with `label = invoice` → `text` column.
   - Receipts: the SROIE `train/box/*.txt` files. Each line is `x1,y1,x2,y2,x3,y3,x4,y4,TEXT`, and only `TEXT` is kept. 340 files are downloaded in parallel (8 threads), leaving spares in case of duplicates.
   - Resumes: `Resume/Resume.csv` → `Resume_str` column.
   - Medical: `mtsamples.csv` → `transcription` column.
   - Contracts: `CUAD_v1/CUAD_v1.json` (SQuAD format) → each contract's `context` (full text).
2. **Clean:** collapse spaces and tabs, remove blank lines.
3. **Filter:** drop texts shorter than 80 characters, then **remove exact duplicates** (mtsamples contains repeats).
4. **Sample:** shuffle with a fixed seed (`random.Random(7)`) and take **300 per category**.
5. **Truncate:** keep the **first 3,000 characters** of each document. That is about 1–2 pages, which is what a scanner typically captures and enough to recognise the type. It also stops 50-page contracts from dominating the TF-IDF statistics.
6. **Mix:** add 100 synthetic documents to each real category, so the model still knows the Indian-style layouts of the demo files (GSTIN, Rs., Aadhaar). Add 400 synthetic documents to each private category. Shuffle and write `documents.csv` with a `source` column.

### 4.4 How the synthetic data was made: `backend/generate_dataset.py`
- **Templates:** one function per category (`make_invoice()`, `make_receipt()`, …) builds a realistic document from random names, companies, cities, addresses, phone numbers, e-mails, dates (5 formats), amounts (Rs., INR, ₹, $, EUR) and IDs (GSTIN, IFSC, PAN, Aadhaar, passport, MRZ lines).
- **Sub-types:**
  - invoices: tax, proforma, bill of supply
  - identity documents: passport, driving licence, Aadhaar, PAN, voter ID
  - application forms: admission, loan, job, scholarship
  - contracts: NDA, rental, employment, service, MoU
  - and so on for the other categories
- **400 per category**, random seed 42, written to `data/dataset/synthetic_documents.csv` (3,200 rows; `kaggle_dataset.py` takes what it needs from it).
- **Realism and difficulty.** Without these steps the first version scored an unrealistic 100%.

| Effect | Probability / amount |
|---|---|
| Partial scan (page cut to 20–70% of its lines) | 35% of documents |
| Each individual line dropped | 12% |
| Title removed | 25% of documents |
| Lines borrowed from another category (2–6 lines, sometimes its title) | 40% of documents |
| OCR character noise (o↔0, l↔1, rn↔m, S↔5, e→c …) + dropped characters | level randomly chosen from 0, 0, 1, 3, 5, 8, 12% |
| Whole document UPPER or lower case | 20% of documents |

- **Labels:** the template that generated a document *is* its label, so there are no labelling errors. Real documents are labelled by their source dataset (a receipt dataset contains only receipts).

### 4.5 Separate test material (never used for training)
- `data/dataset/ocr_test_images/`: **32 images** (4 per category), rendered from fresh synthetic documents. Half are "scanned": rotated ±2.5°, Gaussian noise, yellow paper tint and blur. Used to test **OCR + model end to end**.
- `sample_documents/normal/`: 20 demo files (a clean PNG and a scanned JPG per category, 3 digital PDFs, 1 TXT).
- `sample_documents/abnormal/`: 7 edge cases (blank page, landscape photo, "Hello" only, unrelated recipe, ambiguous invoice/receipt mix, very blurry scan, corrupted file).

---

## 5. Text extraction (OCR models)

File: `backend/ocr.py`

| Input | Method |
|---|---|
| PNG, JPG, JPEG, BMP, TIF, TIFF, WEBP | **RapidOCR** (details below) |
| PDF | PyMuPDF reads the embedded text layer (instant). If it gives fewer than 25 characters (a scanned PDF), the **first 3 pages are rendered at 150 DPI** and OCR'd. |
| DOCX | python-docx, paragraph text |
| TXT | read directly (UTF-8) |
| anything else | rejected: HTTP 415 |
| corrupted / empty | `ExtractionError` → HTTP 422 |

**RapidOCR image pipeline:**
1. Fix phone rotation from EXIF (`ImageOps.exif_transpose`), convert to RGB.
2. Downscale so the longest side is at most **1800 px** (speed on edge CPUs).
3. **Detection** (PP-OCRv4 det, DBNet): predicts a "text probability" map and turns it into text boxes. Settings: threshold 0.3, box threshold 0.5, unclip ratio 1.6.
4. **Recognition** (PP-OCRv4 rec, SVTR-LCNet + CTC): each box is resized to 48 px height and the characters are decoded. Boxes with a score below 0.5 are dropped.
5. The angle classifier is skipped (`use_cls=False`).
6. **Rebuild lines:** boxes are sorted top-to-bottom (in 15 px bands), then left-to-right. Boxes in the same band are joined into one line.
7. **OCR confidence** = mean recognition score of all boxes, used for the "poor scan" warning.

The OCR engine is loaded once (lazily, thread-safe) and **warmed up in a background thread** when the service starts.

---

## 6. Preprocessing

File: `backend/classifier.py → preprocess()`. **The same function is used in training and prediction**, so the model always sees text in the same form.

1. **Lower-case** everything.
2. **Replace every digit with `0`.** Amounts, dates and ID numbers are different in every document. Their *shape* matters (`0000-0000-0000` looks like an Aadhaar number), not the value.
3. **Collapse whitespace** to single spaces.

Example: `"Invoice No: INV-20931\nTotal Rs. 11,800.00"` → `"invoice no: inv-00000 total rs. 00,000.00"`

---

## 7. Feature extraction (TF-IDF)

File: `backend/train_model.py → build_pipeline()`

**TF-IDF** (Term Frequency × Inverse Document Frequency) gives each term a weight. The weight is high if the term is frequent in *this* document but rare across *all* documents.

- `tf` uses **sublinear scaling**: 1 + log(count), so a word repeated 50 times does not dominate.
- `idf = ln((1 + N) / (1 + df)) + 1` (smoothed), where N = number of documents and df = documents containing the term.
- Each document vector is **L2-normalised** (length 1).

Two vectorizers are combined side by side with a `FeatureUnion`:

| | Word TF-IDF | Character TF-IDF |
|---|---|---|
| `analyzer` | word | `char_wb` (characters inside word boundaries) |
| `ngram_range` | (1, 2): single words and word pairs | (3, 5): 3-, 4- and 5-character pieces |
| `token_pattern` | `\b[a-z][a-z]+\b` (letters only, 2+ letters) | n/a |
| `stop_words` | English (removes "the", "and", "of" …) | none |
| `min_df` | 2 (a term must appear in at least 2 documents) | 2 |
| `max_features` | 40,000 → **39,002 used** | 30,000 → **30,000 used** |
| `sublinear_tf` | True | True |
| Why | captures meaning: "invoice no", "date birth", "closing balance", "hereinafter referred" | **robust to OCR errors**: "inv0ice" still shares "inv", "voi", "ice" with "invoice"; also handles words OCR glued together |

**Total: 69,002 features per document.** The vector is very sparse: a typical document has only a few hundred non-zero values.

The word limit was raised from 20,000 to 40,000 when the Kaggle data was added. The larger real vocabulary had pushed common words of our scanned demo documents out of the vocabulary, which broke the out-of-domain check (Section 12).

---

## 8. The ML models and how each one works

Problem type: **supervised multi-class text classification**, with 8 classes and one label per document.

### 8.1 Linear SVM, calibrated ✅ (selected)
```python
CalibratedClassifierCV(LinearSVC(C=0.5, dual="auto"), cv=3)
```
- **LinearSVC** learns one weight per feature for each class (one-vs-rest: 8 binary classifiers). The score for a class is the sum of `weight × feature value`. Training chooses the weights so the **margin** between classes is as wide as possible (squared hinge loss + L2 regularisation).
- **C = 0.5** controls regularisation strength. Smaller C means simpler weights and less overfitting.
- An SVM outputs distances from its decision boundary, not probabilities. **`CalibratedClassifierCV`** (sigmoid / Platt scaling, 3-fold) fixes this:
  1. It trains 3 SVMs, each on 2/3 of the training data.
  2. On the remaining 1/3, it fits a sigmoid that maps scores to probabilities.
  3. At prediction time it averages the 3 calibrated outputs.

  We need real probabilities for the 70% confidence threshold.

### 8.2 Logistic Regression
```python
LogisticRegression(C=10, max_iter=3000)
```
- Also linear, with one weight per feature per class, but trained to maximise the likelihood of the correct class. The **softmax** function turns scores into probabilities directly.
- C = 10 means weak regularisation. The lbfgs solver is used, with multinomial loss.

### 8.3 Multinomial Naive Bayes
```python
MultinomialNB(alpha=0.05)
```
- Learns how likely each term is in each class and multiplies these probabilities, assuming terms are independent (the "naive" assumption).
- `alpha = 0.05` is additive (Lidstone) smoothing, so unseen terms don't give zero probability.
- Very fast, usually slightly less accurate on text with correlated words.

### 8.4 Selection rule
All three are trained on the **same 80% split** and scored on the **same 20% test set**. The model with the **highest macro F1** is chosen automatically. The calibrated SVM and Logistic Regression are within 1 document of each other (636 vs 635 correct out of 640).

---

## 9. How the model was trained (step by step)

Command: `cd backend && python train_model.py` (≈ 60 seconds on a laptop CPU)

1. **Load** `documents.csv` → 3,200 texts, labels and sources (plus any human-verified feedback rows from the database, marked `source = feedback`).
2. **Preprocess** every text (Section 6).
3. **Split** 80/20, **stratified by label**, `random_state=7`: 2,560 train / 640 test (80 per class; 285 real + 355 synthetic test documents).
4. For each of the 3 candidate models:
   1. Build the pipeline `FeatureUnion(word TF-IDF, char TF-IDF) → classifier`.
   2. **Fit on the 2,560 training documents only.** The TF-IDF vocabulary and IDF values are also learnt from the training part, so there is no test leakage.
   3. Predict the 640 test documents and record accuracy, macro F1, training time and prediction time per document.
5. **Select** the model with the best macro F1 → **Linear SVM (calibrated)**.
6. For the selected model, compute the **classification report** (precision, recall and F1 per class), the **confusion matrix**, the **misclassified examples** and the **accuracy per source** (real vs synthetic).
7. **5-fold stratified cross-validation** (shuffled, seed 7) on all 3,200 documents, as a second and more robust estimate.
8. **Generalisation check:** train the same model **only on the 1,700 synthetic documents** and test it on **all 1,500 real documents**.
9. **Final fit** of the selected model on **100% of the data** (more data gives a better final model; the evaluation was already done on held-out data).
10. Also compute the **top keywords per class** (largest word weights).
11. **Save:**
    - `models/document_classifier.joblib` = `{pipeline, classes, version, model_name}`
    - `models/metrics.json` = every number shown on the Model & Analytics page (version is incremented on each retrain)

End-to-end testing on scanned images is a separate step: `python test_system.py` → `reports/end_to_end.json`.

---

## 10. Evaluation results

### 10.1 Model comparison (same 640-document test set)
| Model | Accuracy | Macro F1 | Train time | Predict / doc |
|---|---|---|---|---|
| Logistic Regression | 99.22% | 99.22% | 7.5 s | 1.2 ms |
| **Linear SVM (calibrated)** ✅ | **99.38%** | **99.37%** | 5.1 s | 1.0 ms |
| Multinomial Naive Bayes | 97.19% | 97.18% | 3.6 s | 1.1 ms |

### 10.2 Selected model
| Metric | Value |
|---|---|
| Test accuracy | **99.38%** (636 / 640) |
| Macro F1 | **99.37%** |
| 5-fold cross-validation | **99.44% ± 0.25%** |
| Accuracy on unseen **real** (Kaggle) test docs | **100%** (285 / 285) |
| Accuracy on unseen **synthetic** test docs | 98.87% (351 / 355) |
| Synthetic-only model → all 1,500 real docs | **93.73%** |
| End-to-end on 32 scanned images (OCR + model) | **32 / 32 = 100%** |

### 10.3 Per class (test set, 80 documents each)
| Class | Precision | Recall | F1 |
|---|---|---|---|
| Application Form | 100% | 100% | 100% |
| Bank Statement | 97.6% | 100% | 98.8% |
| Identity Document | 100% | 97.5% | 98.7% |
| Invoice | 100% | 100% | 100% |
| Legal Contract | 98.8% | 100% | 99.4% |
| Medical Report | 100% | 100% | 100% |
| Receipt | 100% | 97.5% | 98.7% |
| Resume | 98.8% | 100% | 99.4% |

### 10.4 Confusion matrix (rows = true, columns = predicted)
```
              App  Bank  ID  Inv  Con  Med  Rec  Res
Application    80    0    0    0    0    0    0    0
Bank            0   80    0    0    0    0    0    0
Identity        0    1   78    0    1    0    0    0
Invoice         0    0    0   80    0    0    0    0
Contract        0    0    0    0   80    0    0    0
Medical         0    0    0    0    0   80    0    0
Receipt         0    1    0    0    0    0   78    1
Resume          0    0    0    0    0    0    0   80
```
All 4 errors are **synthetic** documents that were heavily cut, noisy and mixed with lines from another category.

### 10.5 What the model learned (strongest words per class)
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

Two of these words are **dataset artefacts**, and it's honest to mention them:
- `rm` is Malaysian ringgit, from the SROIE receipts.
- `city state` and `company city` are anonymisation placeholders in the Kaggle resumes.

### 10.6 How to read these numbers honestly
- **100% on real documents is optimistic.** The real test documents come from the same 5 datasets as the real training documents, and each dataset has its own style.
- **93.7% (synthetic-only model → real documents)** is the fairer estimate of how the approach performs on documents from a source the model has never seen.
- Metric definitions:
  - **Precision:** of the documents predicted as X, the share that really were X.
  - **Recall:** of the real X documents, the share found.
  - **F1:** the harmonic mean of precision and recall.
  - **Macro F1:** the average of the per-class F1 scores, which treats all classes equally.

---

## 11. How a prediction is made at run time

File: `backend/pipeline.py → process_document()`

```
upload ─► save file ─► SHA-256 hash (duplicate check)
       ─► extract text (Section 5)
       ─► if ≥ 25 characters: classifier.predict(text)
              preprocess ─► TF-IDF (69,002 features) ─► calibrated SVM ─► 8 probabilities
              + explanation (top words) + known-word ratio
       ─► decision rules (Section 12) ─► final category, status, alerts
       ─► key-field extraction (Section 14)
       ─► insert into SQLite ─► copy file to department folder ─► save timings
       ─► JSON response to the client
```

**Explanation ("Why this prediction?"):** for the predicted class, each word's contribution = its TF-IDF value × the class weight (for the calibrated SVM, the weights of its 3 internal SVMs are averaged). The 8 largest positive word contributions are shown.

**Known-word ratio:** the share of the document's words (2+ letters) that are in the model's word vocabulary. It is used to detect out-of-domain text.

**Thread safety:** a lock protects the model, so a retrain can **hot-swap** it while requests are being served.

---

## 12. Decision rules and thresholds

All thresholds are in `backend/config.py`.

| Rule (checked in this order) | Threshold | Result |
|---|---|---|
| Too little text (blank page, photo, unreadable) | < **25** characters | `unknown` → Manual Review |
| Out-of-domain (vocabulary unfamiliar) | known-word ratio < **0.35** | `unknown` → Manual Review |
| Low confidence | top probability < **0.70** | `unknown` → Manual Review (model's suggestion kept) |
| Otherwise | | **auto-routed** to the predicted department |
| Close call (warning only) | top-1 − top-2 probability < **0.25** | info alert |
| Poor scan (warning only) | OCR confidence < **0.75** | warning alert |
| Identity document (info only) | | "restricted KYC folder" alert |
| Duplicate (warning only) | same SHA-256 already in history | warning alert |
| Unsupported file type | not in allowed list | HTTP **415** |
| Empty / corrupted file | | HTTP **422** |
| No file and no text | | HTTP **400** |
| File too large | > **15 MB** | HTTP **413** |

---

## 13. Routing, storage and history

**Routing table** (`config.CATEGORIES`):

| Category | Department | Folder (`data/routed/…`) |
|---|---|---|
| invoice | Finance - Accounts Payable | `Finance_Accounts_Payable` |
| receipt | Finance - Expense Claims | `Finance_Expense_Claims` |
| identity_document | HR - KYC & Verification | `HR_KYC_Verification` |
| application_form | Admissions & Applications Desk | `Applications_Desk` |
| bank_statement | Finance - Accounts & Audit | `Finance_Accounts_Audit` |
| medical_report | Health & Insurance Claims | `Health_Insurance_Claims` |
| resume | HR - Recruitment | `HR_Recruitment` |
| legal_contract | Legal & Compliance | `Legal_Compliance` |
| unknown | Manual Review Desk | `Manual_Review` |

- `router.route_file()` **copies** the original upload to `data/routed/<Folder>/<id:06d>_<filename>`, e.g. `Finance_Accounts_Payable/000042_invoice.jpg`.
- A human correction **moves** the file to the new folder (`reroute_file`). Deleting a record removes the routed copy.

**SQLite database** (`data/history.db`, table `documents`, one row per document): id, filename, stored name, extension, size, SHA-256 hash, source (dashboard / text-input / scanner device / sample), extraction method, OCR confidence, pages, full text, predicted category, confidence, all probabilities (JSON), top terms (JSON), known-word ratio, final category, department, routed path, status (`auto_routed | needs_review | reviewed | corrected`), alerts (JSON), key fields (JSON), AI insights (JSON), extraction ms, classify ms, total ms, model version, created / updated timestamps.

`database.stats()` powers the dashboard. It returns totals, counts by status, category, department and source, average confidence, average times, a 14-day volume chart, confidence buckets (<50, 50–70, 70–90, 90–100%) and **live accuracy** (how often the model's suggestion matched the human's decision on reviewed documents).

---

## 14. Key-field extraction

File: `backend/extractor.py`. Offline regular expressions, no ML:

| Field | How |
|---|---|
| document_number | label (invoice/receipt/policy/passport/account/patient/form/txn…) + "no / number / # / id" + code |
| total_amount | first match, in priority order: grand total → total amount due → amount due → balance due → invoice total → closing balance → amount paid → `\btotal` (word boundary, so "Subtotal" doesn't match) |
| email, phone | standard patterns (Indian 10-digit and +country formats) |
| gstin | 15-character GST number pattern |
| ifsc | 4 letters + `0` + 6 characters |
| person_name | after "name / patient name / account holder / name of applicant" |
| dates_found | up to 3 unique dates in 4 common formats |
| word_count | number of words |

---

## 15. Optional AI assistant (OpenAI)

File: `backend/ai_assistant.py`. Called **only** when a user clicks *Generate AI summary* (`POST /api/documents/<id>/ai`). Classification never depends on it.

| Setting | Value |
|---|---|
| Model | **gpt-4o-mini** (cheapest capable mini model; `OPENAI_MODEL` in `.env`) |
| Temperature | 0.2 (consistent, factual) |
| Max output tokens | 500 |
| Output format | JSON mode (`response_format = json_object`) |
| Input | the local model's predicted category + the document text, **masked** and cut to 3,500 characters |
| Privacy masking | e-mail addresses → `[email]`; any run of 6+ digits → `XXXX` + last 4 digits |
| Returns | summary, up to 8 key fields, suggested category, whether it agrees with the local model, reason, 1–3 action items, priority |
| Key storage | `backend/.env` (git-ignored); without a key the button is disabled and everything else works offline |

---

## 16. Retraining (human in the loop)

1. Documents in the **Review Queue** (status `needs_review`) are assigned a category by a person. The status becomes `reviewed` (model was right) or `corrected` (model was wrong), and the file is moved.
2. `database.feedback_rows()` returns `(final_category, text)` for every human-verified document.
3. **Model & Analytics → Retrain model now** → `POST /api/model/retrain` → `train_model.train(extra_rows=feedback)`. This repeats the whole procedure of Section 9 on the 3,200 documents plus the feedback rows (feedback is marked `source = feedback`).
4. The new model is saved as **version N+1**, and `classifier.load()` **hot-swaps** it into the running service with no restart. A lock prevents two retrains at once (HTTP 409).

---

## 17. Edge service and REST API

File: `backend/app.py`. Flask on `0.0.0.0:5000` (override with `EDGE_HOST` / `EDGE_PORT`). It also serves the dashboard, so there is a single process and a single port.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | service status, model version, OCR engine, host/platform, uptime |
| GET | `/api/categories` | categories, departments, colours |
| POST | `/api/classify` | **main endpoint**: multipart `file` or form/JSON `text`, optional `source` |
| GET | `/api/samples` | list demo documents |
| GET | `/api/samples/file` | download a demo document |
| POST | `/api/samples/classify` | classify a demo document by path |
| GET | `/api/documents` | history, with filters (category, status, search, …) |
| GET | `/api/documents/<id>` | one record |
| GET | `/api/documents/<id>/file` | original file (preview) |
| POST | `/api/documents/<id>/review` | human decision → re-route |
| POST | `/api/documents/<id>/ai` | optional gpt-4o-mini insights |
| DELETE | `/api/documents/<id>` | delete record + routed file |
| GET | `/api/export.csv` | history as CSV |
| GET | `/api/stats` | dashboard statistics |
| GET | `/api/departments` | folders and their files |
| GET | `/api/model` | metrics.json + end-to-end results + available feedback |
| POST | `/api/model/retrain` | retrain + hot-swap |

**Communication:** HTTP/REST with JSON. The clients are:
1. the dashboard (browser `fetch`);
2. `scanner_simulator.py`, a separate program acting as an office scanner (`--url`, `--folder`, `--interval 1.5`, `--loop`, `--device scanner-sim-01`);
3. curl or any HTTP client;
4. the Live API console on the Edge System page.

---

## 18. Frontend

- **Plain HTML, CSS and vanilla JavaScript.** There is no framework and no build step, which makes it easy to explain and works offline.
- `index.html` (layout), `css/styles.css` (light + dark theme via CSS variables, responsive), `js/api.js` (fetch wrapper), `js/ui.js` (shared helpers + document detail view), `js/main.js` (hash router with `#page/<id>` deep links, health polling, theme toggle).
- `js/pages/` has one file per page:

  | Page | Contents |
  |---|---|
  | Dashboard | KPIs, charts, recent documents, alerts; live refresh every 5 s |
  | Classify | drag & drop, paste text, sample gallery, processing queue |
  | Review Queue | documents waiting for a human decision |
  | History | filters + CSV export |
  | Departments | the routed folders and their files |
  | Model & Analytics | real-world validation, comparison, confusion matrix, keywords, dataset chart, retrain |
  | Edge System | architecture, Live API console, traffic by source |

- **Charts:** Chart.js 4.4.1 stored locally. Category colours are fixed per category and were checked for colour-blind safety.

---

## 19. Deployment

| Option | How |
|---|---|
| Windows | `setup.bat` (pip install) → `run.bat` (starts service, opens browser) |
| Any OS | `pip install -r requirements.txt` → `cd backend` → `python app.py` |
| Docker | `docker compose up --build`: `python:3.12-slim` + libgl/glib (OpenCV inside RapidOCR); volume `docuroute-data` keeps history and folders across restarts |
| Rebuild data + model | `python generate_dataset.py && python kaggle_dataset.py && python train_model.py` |

No GPU, no Tesseract install and no hardware are needed. The trained model, dataset and samples are committed, so a fresh clone runs immediately.

---

## 20. Testing

Command: `cd backend && python test_system.py`. It uses a **temporary data folder**, so real history is untouched, and writes `reports/test_report.md` and `reports/end_to_end.json`.

| Group | Tests | Result |
|---|---|---|
| Normal: 20 sample files (PNG, scanned JPG, PDF, TXT) + pasted invoice text | 21 | all correct + auto-routed, file verified on disk |
| Abnormal: blank, photo, too little text, recipe, ambiguous mix, ambiguous 5-line snippet, very blurry scan, corrupted, .exe, empty file, no input, > 15 MB, duplicate | 13 | all handled (Manual Review or correct HTTP error) |
| Review flow + API endpoints | 9 | correction moves the file, invalid category rejected, all GET endpoints 200 |
| **Total** | **43** | **43 / 43 passed** |
| End-to-end OCR + model on 32 held-out scanned images | 32 | **32 / 32 correct** |

---

## 21. Performance

Measured on the development laptop (Windows 11, Python 3.12, CPU only).

| Step | Time |
|---|---|
| ML classification (TF-IDF + calibrated SVM) | ~9 ms per document (1 ms in batch) |
| PDF / TXT / DOCX text extraction | ~10–30 ms |
| OCR, receipt / ID card image | ~0.6–2 s |
| OCR, full A4 page image | ~2–6 s (average on test images: 3.0 s) |
| First OCR after start | +~1 s (model load; warmed up in background) |
| Full training (3 models + 5-fold CV + real-data check + final fit) | ~60 s |
| Model file | ~21 MB |
| OCR models | ~16 MB (det 4.7 + rec 10.9 + cls 0.6) |

OCR dominates the processing time; the ML step is effectively instant.

---

## 22. Limitations

1. **Three categories are synthetic only** (ID, bank statement, application form): no public dataset can exist for them.
2. **One source per real category:** the model partly learns source quirks (`rm`, `city state`), so accuracy on documents from a new source will be lower than 99% (the synthetic → real check gave 93.7%).
3. **Text only:** visual layout, logos and photos are not used, so a document with almost no text goes to Manual Review.
4. **OCR limits:** very blurry, handwritten or 90°-rotated images reduce quality.
5. **English only.**
6. **One label per file:** a PDF containing several documents gets a single category.
7. **CPU OCR speed:** about 2–5 s per A4 page, so roughly 1,000–1,500 pages per hour per device.
8. **No login / authentication:** a prototype for a trusted local network.

---

## 23. Numbers to remember

| | |
|---|---|
| Categories | **8** (+ Manual Review) |
| Dataset | **3,200** docs = **1,500 real (Kaggle, 5 datasets)** + **1,700 synthetic** |
| Split | **80/20** stratified → 2,560 / 640 |
| Features | **69,002** (39,002 word + 30,000 char TF-IDF) |
| Selected model | **Linear SVM, C = 0.5, calibrated (sigmoid, 3-fold)** |
| Test accuracy | **99.38%** · macro F1 **99.37%** |
| Cross-validation | **99.44% ± 0.25%** (5-fold) |
| Unseen real docs | **100%** (285) · synthetic-only model on real: **93.7%** |
| End-to-end scans | **32 / 32** |
| Functional tests | **43 / 43** |
| Thresholds | confidence **0.70** · known words **0.35** · min text **25 chars** · OCR quality **0.75** · max file **15 MB** |
| OCR | **RapidOCR 1.4.4**: PaddleOCR **PP-OCRv4** det (DBNet) + rec (SVTR-LCNet/CTC) on **ONNX Runtime 1.20.1**, CPU |
| Speed | ML **~9 ms**/doc · OCR **~3 s**/page |
| AI | **gpt-4o-mini**, optional, masked input, JSON output |
| Stack | Python 3.12 · Flask 3.0.3 · scikit-learn 1.3.2 · SQLite · vanilla JS · Chart.js 4.4.1 · Docker |
