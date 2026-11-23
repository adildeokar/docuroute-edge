# Test Report - Edge Document Classification & Routing

Run at 2026-11-23 20:53 · model v1 (Linear SVM (calibrated))

**Functional tests: 42/42 passed**  
**End-to-end OCR + model accuracy: 32/32 = 100.0%** (avg OCR 3119.6 ms, avg ML 7.99 ms per document)

| Group | Test case | Result | Details |
|---|---|---|---|
| Normal | application_form_clean.png | PASS | HTTP 200 -> application_form (99.4%) [auto_routed] 4482 ms |
| Normal | application_form_scanned.jpg | PASS | HTTP 200 -> application_form (99.0%) [auto_routed] 3280 ms |
| Normal | bank_statement_clean.png | PASS | HTTP 200 -> bank_statement (98.4%) [auto_routed] 4184 ms |
| Normal | bank_statement_digital.pdf | PASS | HTTP 200 -> bank_statement (99.7%) [auto_routed] 246 ms |
| Normal | bank_statement_scanned.jpg | PASS | HTTP 200 -> bank_statement (98.4%) [auto_routed] 4728 ms |
| Normal | identity_document_clean.png | PASS | HTTP 200 -> identity_document (99.3%) [auto_routed] 1462 ms |
| Normal | identity_document_scanned.jpg | PASS | HTTP 200 -> identity_document (98.8%) [auto_routed] 1875 ms |
| Normal | invoice_clean.png | PASS | HTTP 200 -> invoice (99.4%) [auto_routed] 4118 ms |
| Normal | invoice_digital.pdf | PASS | HTTP 200 -> invoice (99.6%) [auto_routed] 22 ms |
| Normal | invoice_scanned.jpg | PASS | HTTP 200 -> invoice (98.6%) [auto_routed] 3561 ms |
| Normal | legal_contract_clean.png | PASS | HTTP 200 -> legal_contract (99.0%) [auto_routed] 5374 ms |
| Normal | legal_contract_digital.pdf | PASS | HTTP 200 -> legal_contract (98.9%) [auto_routed] 21 ms |
| Normal | legal_contract_scanned.jpg | PASS | HTTP 200 -> legal_contract (96.3%) [auto_routed] 6556 ms |
| Normal | medical_report_clean.png | PASS | HTTP 200 -> medical_report (99.2%) [auto_routed] 2801 ms |
| Normal | medical_report_scanned.jpg | PASS | HTTP 200 -> medical_report (98.6%) [auto_routed] 1977 ms |
| Normal | receipt_clean.png | PASS | HTTP 200 -> receipt (99.2%) [auto_routed] 596 ms |
| Normal | receipt_scanned.jpg | PASS | HTTP 200 -> receipt (98.6%) [auto_routed] 911 ms |
| Normal | resume_clean.png | PASS | HTTP 200 -> resume (99.5%) [auto_routed] 3797 ms |
| Normal | resume_plain.txt | PASS | HTTP 200 -> resume (99.4%) [auto_routed] 18 ms |
| Normal | resume_scanned.jpg | PASS | HTTP 200 -> resume (98.8%) [auto_routed] 2901 ms |
| Normal | pasted invoice text | PASS | HTTP 200 -> invoice (95.6%) [auto_routed] 20 ms |
| Abnormal | blank_page.png (blank) | PASS | HTTP 200 -> unknown (0.0%) [needs_review] 1309 ms |
| Abnormal | landscape_photo.jpg (not a document) | PASS | HTTP 200 -> unknown (0.0%) [needs_review] 597 ms |
| Abnormal | very_little_text.png (too little text) | PASS | HTTP 200 -> unknown (0.0%) [needs_review] 867 ms |
| Abnormal | unrelated_recipe.txt (out-of-domain) | PASS | HTTP 200 -> unknown (63.1%) [needs_review] 20 ms |
| Abnormal | ambiguous_invoice_receipt.png (mixed) | PASS | HTTP 200 -> unknown (64.9%) [needs_review] 1275 ms |
| Abnormal | very_blurry_scan.jpg (poor quality) | PASS | HTTP 200 -> medical_report (98.9%) [auto_routed] 2592 ms |
| Abnormal | corrupted_file.png (random bytes) | PASS | HTTP 422: File is corrupted or unreadable (UnidentifiedImageError) |
| Abnormal | virus.exe (unsupported type) | PASS | HTTP 415: Unsupported file type '.exe'. Allowed: bmp, docx, jpeg, jpg, pdf, png, tif, tiff, txt, webp |
| Abnormal | empty.png (0 bytes) | PASS | HTTP 422: The file is empty (0 bytes) |
| Abnormal | request without file or text | PASS | HTTP 400: Send a document in the 'file' field or text in the 'text' field. |
| Abnormal | huge.pdf (> 15 MB) | PASS | HTTP 413 |
| Abnormal | duplicate upload detected | PASS | Duplicate: identical file already processed as document #8 (invoice_cl |
| Review | correct category -> file moved | PASS | Manual_Review/000029_unrelated_recipe.txt  ->  Applications_Desk/000029_unrelated_recipe.txt |
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
| application_form__1.png | application_form | application_form | 99.6% | 0.979 | 4110 ms |
| application_form__2.png | application_form | application_form | 99.8% | 0.986 | 3829 ms |
| application_form__3.png | application_form | application_form | 99.6% | 0.981 | 2958 ms |
| application_form__4.png | application_form | application_form | 99.7% | 0.989 | 2159 ms |
| bank_statement__1.png | bank_statement | bank_statement | 98.7% | 0.97 | 4428 ms |
| bank_statement__2.png | bank_statement | bank_statement | 99.7% | 0.981 | 4176 ms |
| bank_statement__3.png | bank_statement | bank_statement | 98.8% | 0.971 | 5480 ms |
| bank_statement__4.png | bank_statement | bank_statement | 99.5% | 0.975 | 6386 ms |
| identity_document__1.png | identity_document | identity_document | 99.3% | 0.982 | 1639 ms |
| identity_document__2.png | identity_document | identity_document | 99.2% | 0.993 | 1701 ms |
| identity_document__3.png | identity_document | identity_document | 99.1% | 0.98 | 1655 ms |
| identity_document__4.png | identity_document | identity_document | 99.6% | 0.991 | 1982 ms |
| invoice__1.png | invoice | invoice | 99.3% | 0.975 | 3317 ms |
| invoice__2.png | invoice | invoice | 99.7% | 0.986 | 2383 ms |
| invoice__3.png | invoice | invoice | 99.1% | 0.977 | 3430 ms |
| invoice__4.png | invoice | invoice | 99.7% | 0.985 | 3605 ms |
| legal_contract__1.png | legal_contract | legal_contract | 99.1% | 0.982 | 5094 ms |
| legal_contract__2.png | legal_contract | legal_contract | 99.4% | 0.988 | 5021 ms |
| legal_contract__3.png | legal_contract | legal_contract | 99.3% | 0.981 | 6503 ms |
| legal_contract__4.png | legal_contract | legal_contract | 99.3% | 0.992 | 5292 ms |
| medical_report__1.png | medical_report | medical_report | 98.8% | 0.988 | 1447 ms |
| medical_report__2.png | medical_report | medical_report | 99.3% | 0.989 | 1838 ms |
| medical_report__3.png | medical_report | medical_report | 98.9% | 0.983 | 2212 ms |
| medical_report__4.png | medical_report | medical_report | 99.4% | 0.986 | 871 ms |
| receipt__1.png | receipt | receipt | 99.5% | 0.987 | 1474 ms |
| receipt__2.png | receipt | receipt | 99.7% | 0.992 | 917 ms |
| receipt__3.png | receipt | receipt | 99.4% | 0.985 | 1550 ms |
| receipt__4.png | receipt | receipt | 99.7% | 0.991 | 658 ms |
| resume__1.png | resume | resume | 99.2% | 0.988 | 3224 ms |
| resume__2.png | resume | resume | 99.2% | 0.985 | 3011 ms |
| resume__3.png | resume | resume | 99.5% | 0.984 | 4298 ms |
| resume__4.png | resume | resume | 99.1% | 0.987 | 3181 ms |
