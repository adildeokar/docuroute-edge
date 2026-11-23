# Test Report - Edge Document Classification & Routing

Run at 2026-11-23 23:01 · model v1 (Linear SVM (calibrated))

**Functional tests: 43/43 passed**  
**End-to-end OCR + model accuracy: 32/32 = 100.0%** (avg OCR 2957.8 ms, avg ML 8.95 ms per document)

| Group | Test case | Result | Details |
|---|---|---|---|
| Normal | application_form_clean.png | PASS | HTTP 200 -> application_form (99.9%) [auto_routed] 3694 ms |
| Normal | application_form_scanned.jpg | PASS | HTTP 200 -> application_form (99.7%) [auto_routed] 2576 ms |
| Normal | bank_statement_clean.png | PASS | HTTP 200 -> bank_statement (99.6%) [auto_routed] 3043 ms |
| Normal | bank_statement_digital.pdf | PASS | HTTP 200 -> bank_statement (99.9%) [auto_routed] 90 ms |
| Normal | bank_statement_scanned.jpg | PASS | HTTP 200 -> bank_statement (99.4%) [auto_routed] 4089 ms |
| Normal | identity_document_clean.png | PASS | HTTP 200 -> identity_document (99.9%) [auto_routed] 1268 ms |
| Normal | identity_document_scanned.jpg | PASS | HTTP 200 -> identity_document (99.9%) [auto_routed] 1642 ms |
| Normal | invoice_clean.png | PASS | HTTP 200 -> invoice (99.4%) [auto_routed] 3658 ms |
| Normal | invoice_digital.pdf | PASS | HTTP 200 -> invoice (99.5%) [auto_routed] 28 ms |
| Normal | invoice_scanned.jpg | PASS | HTTP 200 -> invoice (99.1%) [auto_routed] 3014 ms |
| Normal | legal_contract_clean.png | PASS | HTTP 200 -> legal_contract (99.3%) [auto_routed] 5504 ms |
| Normal | legal_contract_digital.pdf | PASS | HTTP 200 -> legal_contract (98.9%) [auto_routed] 40 ms |
| Normal | legal_contract_scanned.jpg | PASS | HTTP 200 -> legal_contract (97.8%) [auto_routed] 6797 ms |
| Normal | medical_report_clean.png | PASS | HTTP 200 -> medical_report (99.4%) [auto_routed] 2624 ms |
| Normal | medical_report_scanned.jpg | PASS | HTTP 200 -> medical_report (99.2%) [auto_routed] 1938 ms |
| Normal | receipt_clean.png | PASS | HTTP 200 -> receipt (99.3%) [auto_routed] 565 ms |
| Normal | receipt_scanned.jpg | PASS | HTTP 200 -> receipt (98.7%) [auto_routed] 915 ms |
| Normal | resume_clean.png | PASS | HTTP 200 -> resume (99.2%) [auto_routed] 3653 ms |
| Normal | resume_plain.txt | PASS | HTTP 200 -> resume (99.4%) [auto_routed] 18 ms |
| Normal | resume_scanned.jpg | PASS | HTTP 200 -> resume (99.2%) [auto_routed] 3012 ms |
| Normal | pasted invoice text | PASS | HTTP 200 -> invoice (86.3%) [auto_routed] 29 ms |
| Abnormal | blank_page.png (blank) | PASS | HTTP 200 -> unknown (0.0%) [needs_review] 1179 ms |
| Abnormal | landscape_photo.jpg (not a document) | PASS | HTTP 200 -> unknown (0.0%) [needs_review] 514 ms |
| Abnormal | very_little_text.png (too little text) | PASS | HTTP 200 -> unknown (0.0%) [needs_review] 899 ms |
| Abnormal | unrelated_recipe.txt (out-of-domain) | PASS | HTTP 200 -> unknown (62.4%) [needs_review] 20 ms |
| Abnormal | ambiguous_invoice_receipt.png (mixed) | PASS | HTTP 200 -> unknown (66.9%) [needs_review] 1168 ms |
| Abnormal | short invoice/receipt snippet (ambiguous) | PASS | HTTP 200 -> unknown (54.1%) [needs_review] 23 ms |
| Abnormal | very_blurry_scan.jpg (poor quality) | PASS | HTTP 200 -> medical_report (98.9%) [auto_routed] 2476 ms |
| Abnormal | corrupted_file.png (random bytes) | PASS | HTTP 422: File is corrupted or unreadable (UnidentifiedImageError) |
| Abnormal | virus.exe (unsupported type) | PASS | HTTP 415: Unsupported file type '.exe'. Allowed: bmp, docx, jpeg, jpg, pdf, png, tif, tiff, txt, webp |
| Abnormal | empty.png (0 bytes) | PASS | HTTP 422: The file is empty (0 bytes) |
| Abnormal | request without file or text | PASS | HTTP 400: Send a document in the 'file' field or text in the 'text' field. |
| Abnormal | huge.pdf (> 15 MB) | PASS | HTTP 413 |
| Abnormal | duplicate upload detected | PASS | Duplicate: identical file already processed as document #8 (invoice_cl |
| Review | correct category -> file moved | PASS | Manual_Review/000030_unrelated_recipe.txt  ->  Applications_Desk/000030_unrelated_recipe.txt |
| Review | invalid category rejected | PASS | HTTP 400 |
| API | GET /api/health | PASS | HTTP 200 |
| API | GET /api/stats | PASS | HTTP 200 |
| API | GET /api/documents | PASS | HTTP 200 |
| API | GET /api/departments | PASS | HTTP 200 |
| API | GET /api/model | PASS | HTTP 200 |
| API | GET /api/export.csv | PASS | HTTP 200 |
| API | GET /api/samples | PASS | HTTP 200 |

## End-to-end image results

| Image | Expected | Predicted | Confidence | OCR conf. | OCR time |
|---|---|---|---|---|---|
| application_form__1.png | application_form | application_form | 99.9% | 0.979 | 3832 ms |
| application_form__2.png | application_form | application_form | 99.9% | 0.986 | 3430 ms |
| application_form__3.png | application_form | application_form | 99.8% | 0.981 | 2628 ms |
| application_form__4.png | application_form | application_form | 99.9% | 0.989 | 1977 ms |
| bank_statement__1.png | bank_statement | bank_statement | 99.7% | 0.97 | 3979 ms |
| bank_statement__2.png | bank_statement | bank_statement | 99.9% | 0.981 | 4195 ms |
| bank_statement__3.png | bank_statement | bank_statement | 99.6% | 0.971 | 5465 ms |
| bank_statement__4.png | bank_statement | bank_statement | 99.9% | 0.975 | 6079 ms |
| identity_document__1.png | identity_document | identity_document | 99.9% | 0.982 | 1583 ms |
| identity_document__2.png | identity_document | identity_document | 99.7% | 0.993 | 1648 ms |
| identity_document__3.png | identity_document | identity_document | 99.8% | 0.98 | 1534 ms |
| identity_document__4.png | identity_document | identity_document | 99.9% | 0.991 | 1871 ms |
| invoice__1.png | invoice | invoice | 99.5% | 0.975 | 3094 ms |
| invoice__2.png | invoice | invoice | 99.5% | 0.986 | 2113 ms |
| invoice__3.png | invoice | invoice | 99.2% | 0.977 | 3220 ms |
| invoice__4.png | invoice | invoice | 99.6% | 0.985 | 3118 ms |
| legal_contract__1.png | legal_contract | legal_contract | 99.2% | 0.982 | 4833 ms |
| legal_contract__2.png | legal_contract | legal_contract | 99.4% | 0.988 | 4842 ms |
| legal_contract__3.png | legal_contract | legal_contract | 99.5% | 0.981 | 6540 ms |
| legal_contract__4.png | legal_contract | legal_contract | 99.5% | 0.992 | 4822 ms |
| medical_report__1.png | medical_report | medical_report | 99.5% | 0.988 | 1453 ms |
| medical_report__2.png | medical_report | medical_report | 99.1% | 0.989 | 1723 ms |
| medical_report__3.png | medical_report | medical_report | 99.6% | 0.983 | 2226 ms |
| medical_report__4.png | medical_report | medical_report | 99.3% | 0.986 | 845 ms |
| receipt__1.png | receipt | receipt | 99.4% | 0.987 | 1417 ms |
| receipt__2.png | receipt | receipt | 99.6% | 0.992 | 862 ms |
| receipt__3.png | receipt | receipt | 99.0% | 0.985 | 1435 ms |
| receipt__4.png | receipt | receipt | 99.6% | 0.991 | 564 ms |
| resume__1.png | resume | resume | 99.3% | 0.988 | 2989 ms |
| resume__2.png | resume | resume | 99.2% | 0.985 | 2922 ms |
| resume__3.png | resume | resume | 99.5% | 0.984 | 4284 ms |
| resume__4.png | resume | resume | 99.1% | 0.987 | 3125 ms |
