"""
extractor.py - Offline key-field extraction with simple regular expressions.

After a document is classified, the receiving department usually needs a few fields
(invoice number, total amount, dates, e-mail...). This runs 100% locally - no cloud.
"""
import re

PATTERNS = {
    "document_number": r"(?:invoice|receipt|application|policy|passport|account|dl|id|patient|uhid|mrn|form|txn)\s*(?:no|number|#|id)?\.?\s*[:#-]\s*([A-Z0-9][A-Z0-9\-/]{3,20})",
    "email": r"([\w.+-]+@[\w-]+\.[\w.]+)",
    "phone": r"(\+?\d{1,3}[\s-]?\d{5}[\s-]?\d{5}|\b\d{10}\b)",
    "gstin": r"\b(\d{2}[A-Z0-9]{10}\d?Z[A-Z0-9])\b",
    "ifsc": r"\b([A-Z]{4}0[A-Z0-9]{6})\b",
}
# labels for the final amount, most specific first (r"\btotal" avoids matching inside "Subtotal")
TOTAL_LABELS = ["grand total", "total amount due", "amount due", "balance due", "invoice total",
                "closing balance", "amount paid", r"\btotal"]
AMOUNT = r"\s*[:\-]?\s*(?:rs\.?|inr|usd|eur|\$|₹)?\s*([\d,]+\.\d{2})"
DATE_PATTERN = r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|\d{1,2} [A-Z][a-z]{2} \d{4}|[A-Z][a-z]+ \d{1,2}, \d{4})\b"
NAME_PATTERN = r"(?:name of applicant|full name of applicant|patient name|account holder|name)\s*[:\-]\s*([A-Za-z .]{3,40})"


def extract_fields(text):
    fields = {}
    for key, pattern in PATTERNS.items():
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            fields[key] = m.group(1).strip()
    for label in TOTAL_LABELS:
        m = re.search(label + AMOUNT, text, flags=re.IGNORECASE)
        if m:
            fields["total_amount"] = m.group(1)
            break
    m = re.search(NAME_PATTERN, text, flags=re.IGNORECASE)
    if m:
        fields["person_name"] = m.group(1).strip().title()
    dates = re.findall(DATE_PATTERN, text)
    if dates:
        fields["dates_found"] = ", ".join(dict.fromkeys(dates[:3]))   # unique, keep order
    fields["word_count"] = len(text.split())
    return fields
