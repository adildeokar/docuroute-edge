"""
generate_dataset.py - STEP 1 of the implementation guide: "Collect sample documents".

Real invoices, ID cards and medical reports contain private data, so we cannot
download thousands of them. Instead this script *synthesises* realistic documents
for 8 categories using randomised templates (names, amounts, dates, layouts,
optional sections) and then adds OCR-style noise (wrong characters, missing
lines, partial scans) so the model learns to cope with imperfect scans.

Outputs
  data/dataset/documents.csv           -> text corpus used for training (label, text)
  data/dataset/ocr_test_images/*.png   -> held-out rendered "scans" for end-to-end OCR testing
  sample_documents/                    -> demo files (images, PDFs, txt) + abnormal test inputs

Run:  python generate_dataset.py
"""
import csv
import os
import random
import string
from datetime import date, timedelta

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import config

SAMPLES_PER_CLASS = 250
rng = random.Random(42)

# ---------------------------------------------------------------------------
# Random value helpers
# ---------------------------------------------------------------------------
FIRST = ["Aarav", "Priya", "Rohan", "Ananya", "Vikram", "Sneha", "Arjun", "Kavya", "Rahul", "Meera",
         "Neha", "Karan", "Pooja", "Aditya", "Isha", "John", "Emily", "Michael", "Sarah",
         "David", "Olivia", "Daniel", "Sophia", "Ravi", "Divya", "Sanjay", "Fatima", "Imran", "Lakshmi"]
LAST = ["Sharma", "Patel", "Mehta", "Iyer", "Reddy", "Gupta", "Singh", "Nair", "Joshi", "Kapoor",
        "Desai", "Rao", "Shah", "Verma", "Smith", "Johnson", "Brown", "Williams", "Khan",
        "Fernandes", "Pillai", "Chopra", "Bose", "Malhotra"]
CITIES = ["Mumbai", "Pune", "Bengaluru", "Delhi", "Chennai", "Hyderabad", "Ahmedabad", "Kolkata",
          "Jaipur", "Nagpur", "Surat", "Indore", "London", "New York", "Singapore", "Dubai"]
STREETS = ["MG Road", "Park Street", "Link Road", "Station Road", "Ring Road", "Hill View Lane",
           "Lake Avenue", "Nehru Nagar", "Gandhi Marg", "Church Street", "Market Yard"]
COMPANIES = ["Apex Technologies Pvt Ltd", "BlueOcean Traders", "Sunrise Electronics", "Nova Supplies Co.",
             "Greenleaf Agro Industries", "Orbit Logistics LLP", "Vertex Solutions Inc.", "Prime Office Mart",
             "Zenith Pharma Ltd", "Metro Hardware Stores", "Silverline Textiles", "Quantum Systems Ltd"]
STORES = ["SuperMart", "FreshBasket", "City Pharmacy", "Cafe Mocha", "Fuel Express", "BookWorld",
          "Reliance Smart", "D-Mart", "Starbucks Coffee", "Hotel Grand Residency", "Uber Trip", "Croma Retail"]
BANKS = ["State Bank of India", "HDFC Bank", "ICICI Bank", "Axis Bank", "Kotak Mahindra Bank",
         "Bank of Baroda", "Punjab National Bank", "Yes Bank", "Canara Bank"]
HOSPITALS = ["City Care Hospital", "Apollo Diagnostics", "Sunshine Multispeciality Hospital",
             "LifeLine Pathology Lab", "Metro Heart Institute", "Green Valley Clinic", "Fortis Health Centre"]
PRODUCTS = ["Laptop Dell Inspiron", "Office Chair", "A4 Paper Ream", "Printer Toner", "LED Monitor 24in",
            "Wireless Mouse", "Network Switch", "Software License", "Consulting Services", "Annual Maintenance",
            "Steel Rods", "Cotton Fabric", "Packaging Boxes", "Web Hosting Plan", "Cloud Storage 1TB"]
GROCERY = ["Milk 1L", "Bread", "Eggs 12pc", "Rice 5kg", "Coffee Latte", "Sandwich", "Petrol", "Notebook",
           "Shampoo", "Paracetamol 500mg", "Bananas", "Chocolate", "Water Bottle", "Room Charges", "Cab Fare"]
SKILLS = ["Python", "Java", "SQL", "Machine Learning", "React", "Data Analysis", "Project Management",
          "Communication", "Excel", "Docker", "AWS", "Leadership", "Digital Marketing", "Accounting", "C++"]
TESTS = [("Hemoglobin", "g/dL", (11.0, 17.0), "13.0 - 17.0"), ("WBC Count", "/cumm", (4000, 11000), "4000 - 11000"),
         ("Platelet Count", "lakh/cumm", (1.5, 4.5), "1.5 - 4.5"), ("Blood Sugar Fasting", "mg/dL", (70, 160), "70 - 110"),
         ("Serum Creatinine", "mg/dL", (0.5, 1.6), "0.6 - 1.2"), ("Total Cholesterol", "mg/dL", (120, 260), "< 200"),
         ("TSH", "uIU/mL", (0.3, 6.0), "0.4 - 4.0"), ("Vitamin D", "ng/mL", (10, 60), "30 - 100")]
MEDICINES = ["Tab. Paracetamol 650mg", "Cap. Amoxicillin 500mg", "Tab. Metformin 500mg", "Syp. Cough Relief",
             "Tab. Pantoprazole 40mg", "Tab. Cetirizine 10mg", "Tab. Vitamin D3", "Tab. Atorvastatin 10mg"]


def pick(seq):
    return rng.choice(seq)


def name():
    return f"{pick(FIRST)} {pick(LAST)}"


def a_date(start_year=2018, end_year=2026):
    d = date(start_year, 1, 1) + timedelta(days=rng.randint(0, (end_year - start_year) * 365))
    fmt = pick(["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d %b %Y", "%B %d, %Y"])
    return d.strftime(fmt)


def money(lo=50, hi=50000):
    return f"{rng.uniform(lo, hi):,.2f}"


def cur():
    return pick(["Rs.", "INR", "$", "USD", "₹", "EUR"])


def digits(n):
    return "".join(rng.choice(string.digits) for _ in range(n))


def code(n):
    return "".join(rng.choice(string.ascii_uppercase + string.digits) for _ in range(n))


def address():
    return f"{rng.randint(1, 999)}, {pick(STREETS)}, {pick(CITIES)} - {digits(6)}"


def phone():
    return f"+91 {digits(5)} {digits(5)}"


def email(person):
    return person.lower().replace(" ", ".") + "@" + pick(["gmail.com", "yahoo.com", "outlook.com", "company.in"])


def some(lines, lo=0.6):
    """Keep a random subset of optional lines (keeps original order)."""
    return [l for l in lines if rng.random() < lo]


# ---------------------------------------------------------------------------
# Templates: each returns (title, list_of_lines)
# ---------------------------------------------------------------------------
def make_invoice():
    seller, buyer = pick(COMPANIES), pick(COMPANIES + [name()])
    c = cur()
    title = pick(["TAX INVOICE", "INVOICE", "COMMERCIAL INVOICE", "PROFORMA INVOICE", "BILL OF SUPPLY", "SALES INVOICE"])
    lines = [seller, address(), f"GSTIN: {digits(2)}{code(10)}1Z{code(1)}"]
    lines += [f"Invoice No: INV-{digits(5)}", f"Invoice Date: {a_date()}", f"Due Date: {a_date()}"]
    lines += some([f"PO Number: PO-{digits(6)}", f"Place of Supply: {pick(CITIES)}", f"Order Ref: {code(8)}"])
    lines += ["Bill To:", buyer, address()] + some(["Ship To:", address()], 0.4)
    lines.append("Description | Qty | Unit Price | Amount")
    subtotal = 0.0
    for _ in range(rng.randint(1, 6)):
        q, p = rng.randint(1, 20), rng.uniform(100, 9000)
        subtotal += q * p
        lines.append(f"{pick(PRODUCTS)} | {q} | {p:,.2f} | {q * p:,.2f}")
    tax = subtotal * pick([0.05, 0.12, 0.18])
    lines += [f"Subtotal: {c} {subtotal:,.2f}", f"{pick(['CGST + SGST', 'IGST', 'GST', 'VAT', 'Tax'])}: {c} {tax:,.2f}",
              f"{pick(['Total Amount Due', 'Grand Total', 'Invoice Total', 'Balance Due'])}: {c} {subtotal + tax:,.2f}"]
    lines += some([f"Amount in words: {pick(['Twelve', 'Forty', 'Seven', 'Ninety'])} Thousand Only",
                   f"Payment Terms: {pick(['Net 30', 'Net 15', 'Due on receipt', 'Net 45'])}",
                   f"Bank: {pick(BANKS)}  A/C No: {digits(12)}  IFSC: {code(4)}0{digits(6)}",
                   "Please make payment before the due date.", "Late payment will attract interest at 18% p.a.",
                   "Thank you for your business!", "Authorised Signatory", "This is a computer generated invoice.",
                   "Kindly send the payment receipt to accounts@vendor.com"], 0.55)
    return title, lines


def make_receipt():
    store, c = pick(STORES), cur()
    title = pick(["RECEIPT", "CASH RECEIPT", "PAYMENT RECEIPT", "SALES RECEIPT", "CASH MEMO", "TAX RECEIPT"])
    lines = [store, f"{pick(STREETS)}, {pick(CITIES)}"] + some([f"Tel: {phone()}", f"GST No: {code(15)}"], 0.5)
    lines += [f"Receipt No: {pick(['R', 'RC', 'TXN', '#'])}{digits(6)}", f"Date: {a_date()}  Time: {rng.randint(8, 22)}:{rng.randint(10, 59)}"]
    lines += some([f"Cashier: {pick(FIRST)}", f"Counter: {rng.randint(1, 9)}", f"Table: {rng.randint(1, 30)}"], 0.5)
    total = 0.0
    for _ in range(rng.randint(1, 7)):
        p = rng.uniform(10, 900)
        total += p
        lines.append(f"{pick(GROCERY)}  x{rng.randint(1, 3)}  {p:,.2f}")
    lines += [f"Subtotal {total:,.2f}", f"Tax {total * 0.05:,.2f}", f"TOTAL {c} {total * 1.05:,.2f}"]
    mode = pick(["CASH", "VISA CARD", "MASTERCARD", "UPI", "Google Pay", "Debit Card"])
    lines += [f"Paid by: {mode}", f"Amount Paid: {total * 1.05 + rng.choice([0, 0, 10, 50]):,.2f}"]
    lines += some([f"Card ending **** {digits(4)}", f"Change Due: {rng.uniform(0, 50):.2f}", f"Auth Code: {code(6)}",
                   "Thank you for shopping with us!", "Please visit again", "No returns or exchange without receipt",
                   "Customer Copy", "Items sold: " + str(rng.randint(1, 9)), "Received with thanks"], 0.55)
    return title, lines


def make_identity():
    person, kind = name(), pick(["PASSPORT", "DRIVING LICENCE", "NATIONAL IDENTITY CARD", "AADHAAR",
                                 "VOTER IDENTITY CARD", "PERMANENT ACCOUNT NUMBER CARD", "RESIDENCE PERMIT"])
    title = kind
    lines = [pick(["GOVERNMENT OF INDIA", "REPUBLIC OF INDIA", "Election Commission of India",
                   "Income Tax Department", "Transport Department", "Unique Identification Authority of India"])]
    lines += [f"Name: {person.upper()}", f"Date of Birth: {a_date(1960, 2006)}", f"Sex: {pick(['M', 'F', 'Male', 'Female'])}"]
    lines += some([f"Father's Name: {name().upper()}", f"Nationality: {pick(['INDIAN', 'Indian'])}",
                   f"Place of Birth: {pick(CITIES).upper()}", f"Blood Group: {pick(['A+', 'B+', 'O+', 'AB-'])}",
                   f"Address: {address()}"], 0.6)
    if kind == "PASSPORT":
        lines += [f"Passport No: {pick(string.ascii_uppercase)}{digits(7)}", "Type: P  Country Code: IND",
                  f"Date of Issue: {a_date()}", f"Date of Expiry: {a_date(2027, 2036)}",
                  f"P<IND{person.split()[1].upper()}<<{person.split()[0].upper()}<<<<<<<<<<<<<<<"]
    elif kind == "DRIVING LICENCE":
        lines += [f"DL No: MH{digits(2)} {digits(11)}", f"Valid Till: {a_date(2027, 2040)}",
                  f"Class of Vehicle: {pick(['LMV', 'MCWG', 'LMV-NT', 'TRANS'])}", f"Issuing Authority: RTO {pick(CITIES)}"]
    elif kind == "AADHAAR":
        lines += [f"{digits(4)} {digits(4)} {digits(4)}", "Aadhaar - Aam Aadmi ka Adhikar", "VID: " + digits(16)]
    elif kind == "PERMANENT ACCOUNT NUMBER CARD":
        lines += [f"Permanent Account Number: {code(5)}{digits(4)}{pick(string.ascii_uppercase)}"]
    else:
        lines += [f"ID No: {code(3)}{digits(7)}", f"Date of Issue: {a_date()}", f"Valid Upto: {a_date(2027, 2036)}"]
    lines += some(["Signature of Holder", "Holder's Signature", "Issuing Authority Signature",
                   "This card is property of the Government", "If found please return to nearest police station"], 0.5)
    return title, lines


def make_application():
    person = name()
    kind = pick(["ADMISSION APPLICATION FORM", "LOAN APPLICATION FORM", "JOB APPLICATION FORM",
                 "MEMBERSHIP APPLICATION FORM", "SCHOLARSHIP APPLICATION", "ACCOUNT OPENING FORM",
                 "PASSPORT APPLICATION FORM", "LEAVE APPLICATION FORM", "INSURANCE PROPOSAL FORM"])
    lines = [pick(["Please fill in BLOCK LETTERS", "All fields marked * are mandatory", "Form No. " + digits(4)])]
    lines += [f"Application No: APP-{digits(6)}", "Section A: Personal Details", f"Full Name of Applicant: {person}",
              f"Date of Birth: {a_date(1970, 2008)}", f"Gender: [ ] Male [ ] Female [ ] Other"]
    lines += some([f"Father's / Guardian's Name: {name()}", f"Correspondence Address: {address()}",
                   f"Mobile Number: {phone()}", f"Email ID: {email(person)}", "Marital Status: [ ] Single [ ] Married",
                   "Category: [ ] General [ ] OBC [ ] SC/ST"], 0.7)
    if "ADMISSION" in kind or "SCHOLARSHIP" in kind:
        lines += ["Section B: Academic Details", f"Course Applied For: {pick(['B.Tech Computer Engineering', 'MBA', 'B.Com', 'M.Sc Data Science'])}",
                  f"Previous Qualification: {pick(['HSC', 'Diploma', 'B.Sc'])}  Percentage: {rng.randint(55, 98)}%"]
    elif "LOAN" in kind or "ACCOUNT" in kind:
        lines += ["Section B: Financial Details", f"Loan Amount Requested: Rs. {money(50000, 5000000)}",
                  f"Monthly Income: Rs. {money(15000, 300000)}", f"Employment Type: [ ] Salaried [ ] Self-Employed",
                  f"Purpose of Loan: {pick(['Home', 'Education', 'Vehicle', 'Business'])}"]
    elif "JOB" in kind:
        lines += ["Section B: Position Details", f"Position Applied For: {pick(['Software Engineer', 'Accountant', 'Sales Executive'])}",
                  f"Expected Salary: {money(20000, 150000)}", "Notice Period: [ ] Immediate [ ] 30 days [ ] 60 days"]
    else:
        lines += ["Section B: Other Details", f"Reason for Application: {pick(['Personal', 'Medical', 'Travel', 'Membership'])}",
                  f"Number of days / years: {rng.randint(1, 10)}"]
    lines += some(["Paste recent passport size photograph here", "Documents enclosed: [ ] ID Proof [ ] Address Proof",
                   "Declaration: I hereby declare that the information furnished above is true to the best of my knowledge.",
                   "Signature of Applicant", f"Place: {pick(CITIES)}  Date: {a_date()}", "FOR OFFICE USE ONLY",
                   "Application received by: ________  Verified by: ________", "Applicant must submit the form before the last date"], 0.65)
    return kind, lines


def make_bank_statement():
    person, bank = name(), pick(BANKS)
    title = pick(["ACCOUNT STATEMENT", "STATEMENT OF ACCOUNT", "BANK STATEMENT", "SAVINGS ACCOUNT STATEMENT", "e-STATEMENT"])
    lines = [bank, f"Branch: {pick(CITIES)} Main", f"Account Holder: {person}", f"Account Number: XXXXXX{digits(4)}",
             f"IFSC Code: {code(4)}0{digits(6)}", f"Statement Period: {a_date()} to {a_date()}"]
    lines += some([f"Customer ID: {digits(9)}", f"Account Type: {pick(['Savings', 'Current', 'Salary'])}", f"MICR: {digits(9)}",
                   f"Address: {address()}"], 0.6)
    bal = rng.uniform(1000, 500000)
    lines += [f"Opening Balance: {bal:,.2f}", "Date | Narration | Chq/Ref No | Withdrawal | Deposit | Balance"]
    for _ in range(rng.randint(3, 10)):
        amt = rng.uniform(100, 60000)
        desc = pick(["NEFT CR SALARY", "UPI/DR/" + digits(6), "ATM WDL " + pick(CITIES).upper(), "IMPS TRANSFER",
                     "POS PURCHASE " + pick(STORES).upper(), "CHQ DEP " + digits(6), "INTEREST CREDIT", "EMI DEBIT LOAN",
                     "ACH DR INSURANCE", "SMS CHARGES"])
        if "CR" in desc or "DEP" in desc or "INTEREST" in desc:
            bal += amt
            lines.append(f"{a_date()} | {desc} | {digits(8)} | | {amt:,.2f} | {bal:,.2f}")
        else:
            bal -= amt
            lines.append(f"{a_date()} | {desc} | {digits(8)} | {amt:,.2f} | | {bal:,.2f}")
    lines += [f"Closing Balance: {bal:,.2f}"]
    lines += some([f"Total Debits: {money()}  Total Credits: {money()}", "This is a computer generated statement and does not require signature.",
                   "Please report discrepancies within 15 days.", "Never share your OTP, PIN or CVV with anyone.",
                   f"Customer Care: 1800 {digits(3)} {digits(4)}"], 0.6)
    return title, lines


def make_medical():
    patient, hosp = name(), pick(HOSPITALS)
    title = pick(["LABORATORY REPORT", "PATHOLOGY REPORT", "DISCHARGE SUMMARY", "PRESCRIPTION", "MEDICAL CERTIFICATE",
                  "RADIOLOGY REPORT", "DIAGNOSTIC REPORT"])
    lines = [hosp, address(), f"Patient Name: {patient}", f"Age / Sex: {rng.randint(1, 90)} Y / {pick(['M', 'F'])}",
             f"Patient ID: {pick(['UHID', 'MRN', 'PID'])}-{digits(7)}", f"Referred By: Dr. {name()}"]
    lines += some([f"Sample Collected: {a_date()}", f"Report Date: {a_date()}", f"Ward / Bed: {pick(['ICU', 'General'])}-{rng.randint(1, 40)}",
                   f"Admission Date: {a_date()}"], 0.6)
    if title in ("LABORATORY REPORT", "PATHOLOGY REPORT", "DIAGNOSTIC REPORT"):
        lines.append("Test Name | Result | Unit | Biological Reference Range")
        for t in rng.sample(TESTS, rng.randint(2, 6)):
            lines.append(f"{t[0]} | {rng.uniform(*t[2]):.1f} | {t[1]} | {t[3]}")
    elif title == "RADIOLOGY REPORT":
        lines += [f"Investigation: {pick(['X-Ray Chest PA View', 'MRI Brain', 'CT Abdomen', 'USG Whole Abdomen'])}",
                  "Findings: " + pick(["No abnormality detected.", "Mild degenerative changes noted.", "Lungs are clear."]),
                  "Impression: " + pick(["Normal study.", "Suggest clinical correlation.", "Follow up advised."])]
    else:
        lines += [f"Diagnosis: {pick(['Viral Fever', 'Type 2 Diabetes Mellitus', 'Hypertension', 'Acute Gastritis', 'Fracture of left radius'])}",
                  "Rx"] + [f"{m} - {pick(['1-0-1', '0-0-1', '1-1-1'])} x {rng.randint(3, 15)} days" for m in rng.sample(MEDICINES, rng.randint(1, 4))]
        lines += some(["Advice: Rest for 3 days, drink plenty of fluids.", "Follow up after one week.",
                       "Patient is advised medical leave from " + a_date() + " to " + a_date()], 0.6)
    lines += some([f"Dr. {name()}, MBBS, MD ({pick(['Pathology', 'Medicine', 'Radiology'])})", f"Reg. No: {digits(5)}",
                   "*** End of Report ***", "Results to be correlated clinically.", "Not valid for medico-legal purpose."], 0.6)
    return title, lines


def make_resume():
    person = name()
    title = pick(["RESUME", "CURRICULUM VITAE", "CV", person.upper(), "PROFESSIONAL RESUME"])
    lines = [person, f"{pick(['Software Engineer', 'Data Analyst', 'Accountant', 'Marketing Manager', 'Mechanical Engineer', 'HR Executive'])}",
             f"Email: {email(person)} | Phone: {phone()} | {pick(CITIES)}"]
    lines += some([f"LinkedIn: linkedin.com/in/{person.lower().replace(' ', '')}", f"GitHub: github.com/{person.split()[0].lower()}{digits(2)}"], 0.5)
    lines += [pick(["PROFESSIONAL SUMMARY", "CAREER OBJECTIVE", "PROFILE"]),
              pick(["Results-driven professional with " + str(rng.randint(1, 15)) + " years of experience in " + pick(SKILLS) + ".",
                    "Seeking a challenging position to utilise my skills and grow with the organisation.",
                    "Motivated graduate with strong analytical and problem-solving skills."])]
    lines.append(pick(["WORK EXPERIENCE", "PROFESSIONAL EXPERIENCE", "EMPLOYMENT HISTORY"]))
    for _ in range(rng.randint(1, 3)):
        lines += [f"{pick(['Senior', 'Junior', 'Lead', ''])} {pick(['Developer', 'Analyst', 'Consultant', 'Intern', 'Manager'])} - {pick(COMPANIES)} ({rng.randint(2012, 2022)} - {pick(['Present', str(rng.randint(2023, 2026))])})",
                  "- " + pick(["Developed and maintained", "Led a team that built", "Improved performance of", "Designed"]) + " " + pick(["web applications", "data pipelines", "financial reports", "marketing campaigns"]),
                  "- " + pick(["Reduced costs by ", "Increased sales by ", "Improved efficiency by "]) + str(rng.randint(5, 60)) + "%"]
    lines += ["EDUCATION", f"{pick(['B.Tech', 'B.E.', 'MBA', 'B.Com', 'M.Sc', 'BCA'])} - {pick(['Mumbai University', 'Pune University', 'IIT Bombay', 'VIT', 'Anna University'])} ({rng.randint(2010, 2025)})  CGPA: {rng.uniform(6, 9.9):.2f}"]
    lines += ["SKILLS", ", ".join(rng.sample(SKILLS, rng.randint(4, 8)))]
    lines += some(["PROJECTS", "- " + pick(["Smart Attendance System", "E-commerce Website", "Stock Price Predictor", "Chatbot"]),
                   "CERTIFICATIONS", "- " + pick(["AWS Certified Cloud Practitioner", "Google Data Analytics", "PMP"]),
                   "LANGUAGES: English, Hindi, Marathi", "HOBBIES: Reading, Cricket, Travelling", "References available upon request.",
                   "Declaration: I hereby declare that the above details are true."], 0.6)
    return title, lines


def make_contract():
    p1, p2 = pick(COMPANIES), pick(COMPANIES + [name()])
    title = pick(["NON-DISCLOSURE AGREEMENT", "SERVICE AGREEMENT", "RENTAL AGREEMENT", "EMPLOYMENT CONTRACT",
                  "LEASE DEED", "MEMORANDUM OF UNDERSTANDING", "SALE AGREEMENT", "CONSULTANCY AGREEMENT"])
    lines = [f"This Agreement is made and entered into on {a_date()} by and between {p1}, having its registered office at {address()} (hereinafter referred to as the \"First Party\")",
             f"AND {p2} (hereinafter referred to as the \"Second Party\")."]
    clauses = ["WHEREAS the First Party is engaged in the business of providing services;",
               "NOW THEREFORE, in consideration of the mutual covenants contained herein, the parties agree as follows:",
               f"1. TERM: This Agreement shall remain in force for a period of {rng.randint(11, 60)} months from the Effective Date.",
               "2. CONFIDENTIALITY: The Receiving Party shall not disclose any Confidential Information to any third party.",
               f"3. CONSIDERATION: The Second Party shall pay a sum of Rs. {money(10000, 900000)} as agreed.",
               "4. TERMINATION: Either party may terminate this Agreement by giving thirty (30) days written notice.",
               "5. INDEMNIFICATION: Each party shall indemnify and hold harmless the other party against all claims.",
               f"6. GOVERNING LAW: This Agreement shall be governed by the laws of India and courts at {pick(CITIES)} shall have jurisdiction.",
               "7. ARBITRATION: Any dispute shall be referred to arbitration under the Arbitration and Conciliation Act, 1996.",
               "8. FORCE MAJEURE: Neither party shall be liable for delay caused by events beyond reasonable control.",
               "9. ENTIRE AGREEMENT: This document constitutes the entire agreement between the parties.",
               f"The monthly rent of Rs. {money(5000, 90000)} shall be payable on or before the 5th day of each month.",
               "The Lessee shall pay a refundable security deposit to the Lessor."]
    lines += some(clauses, 0.65)
    lines += ["IN WITNESS WHEREOF the parties have executed this Agreement on the date first written above."]
    lines += some(["Signed by the First Party: ____________", "Signed by the Second Party: ____________",
                   f"Witness 1: {name()}", f"Witness 2: {name()}", "Stamp Duty Paid: Rs. 500", "Notarised"], 0.6)
    return title, lines


TEMPLATES = {
    "invoice": make_invoice,
    "receipt": make_receipt,
    "identity_document": make_identity,
    "application_form": make_application,
    "bank_statement": make_bank_statement,
    "medical_report": make_medical,
    "resume": make_resume,
    "legal_contract": make_contract,
}

# ---------------------------------------------------------------------------
# OCR-style noise so the model is robust to imperfect scans
# ---------------------------------------------------------------------------
OCR_CONFUSIONS = {"o": "0", "0": "o", "l": "1", "1": "l", "i": "l", "e": "c", "a": "o", "s": "5", "5": "s",
                  "b": "6", "g": "9", "B": "8", "O": "0", "I": "1", "S": "5", "rn": "m", "m": "rn"}


def add_ocr_noise(text, level):
    chars = list(text)
    for i, ch in enumerate(chars):
        r = rng.random()
        if r < level and ch in OCR_CONFUSIONS:
            chars[i] = OCR_CONFUSIONS[ch]
        elif r < level * 1.3:
            chars[i] = ""                       # dropped character
    return "".join(chars)


def to_text(title, lines, noisy=True, label=None):
    if noisy:
        # simulate partial scans: sometimes cut off the page, drop lines or lose the title
        if rng.random() < 0.35:
            lines = lines[: max(3, int(len(lines) * rng.uniform(0.2, 0.7)))]
        lines = [l for l in lines if rng.random() > 0.12]
        if rng.random() < 0.25:
            title = ""
        # real documents share vocabulary: a receipt may say "invoice", a loan form may
        # contain bank details... so sometimes mix in a few lines from another category
        if label and rng.random() < 0.4:
            other = pick([k for k in TEMPLATES if k != label])
            o_title, o_lines = TEMPLATES[other]()
            borrowed = rng.sample(o_lines, min(len(o_lines), rng.randint(2, 6)))
            if rng.random() < 0.3:
                borrowed.append(o_title)
            for b in borrowed:
                lines.insert(rng.randint(0, len(lines)), b)
    text = "\n".join([title] + lines).strip()
    if noisy:
        text = add_ocr_noise(text, rng.choice([0, 0, 0.01, 0.03, 0.05, 0.08, 0.12]))
        if rng.random() < 0.2:
            text = text.lower() if rng.random() < 0.5 else text.upper()
    return text


# ---------------------------------------------------------------------------
# Rendering documents as images (to test the real OCR pipeline)
# ---------------------------------------------------------------------------
def load_font(size, bold=False):
    candidates = (["arialbd.ttf", "DejaVuSans-Bold.ttf"] if bold else ["arial.ttf", "DejaVuSans.ttf"])
    for f in candidates + ["C:/Windows/Fonts/" + candidates[0], "/usr/share/fonts/truetype/dejavu/" + candidates[-1]]:
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def wrap(line, width):
    out, cur_line = [], ""
    for word in line.split(" "):
        if len(cur_line) + len(word) + 1 > width:
            out.append(cur_line)
            cur_line = word
        else:
            cur_line = (cur_line + " " + word).strip()
    out.append(cur_line)
    return out


def render(category, title, lines, scanned=False):
    color = config.CATEGORIES[category]["color"]
    if category == "identity_document":            # ID card layout
        W, size, wrap_w = 1100, 26, 50
        H = max(700, 200 + 36 * sum(len(wrap(l, 42)) for l in lines))
    elif category == "receipt":                    # narrow thermal receipt
        W, size, wrap_w = 640, 24, 40
        H = 200 + 36 * sum(len(wrap(l, wrap_w)) for l in lines)
    else:                                          # A4 page
        W, size, wrap_w = 1240, 24, 80
        H = max(1100, 260 + 36 * sum(len(wrap(l, wrap_w)) for l in lines))

    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 110], fill=color)
    d.text((40, 32), title[:40], font=load_font(42, bold=True), fill="white")
    font = load_font(size)
    y = 140
    x0 = 40
    if category == "identity_document":            # photo placeholder
        d.rectangle([40, 140, 300, 470], outline="#94a3b8", width=3, fill="#e2e8f0")
        d.text((110, 290), "PHOTO", font=load_font(30, bold=True), fill="#94a3b8")
        x0 = 330
    for line in lines:
        for part in wrap(line, wrap_w if x0 == 40 else 42):
            d.text((x0, y), part, font=font, fill="#111827")
            y += 36
        if " | " in line:
            d.line([x0, y - 4, W - 40, y - 4], fill="#cbd5e1", width=1)
    d.rectangle([4, 4, W - 5, H - 5], outline="#cbd5e1", width=3)

    if scanned:                                     # make it look like a phone photo / scan
        img = img.rotate(rng.uniform(-2.5, 2.5), expand=True, fillcolor="white", resample=Image.BICUBIC)
        arr = np.array(img).astype(np.int16)
        arr = arr + np.random.default_rng(rng.randint(0, 9999)).normal(0, 12, arr.shape).astype(np.int16)
        arr[..., 2] -= 12                           # slight yellow paper tint
        img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6))
    return img


def write_pdf(path, title, lines):
    import pymupdf
    doc = pymupdf.open()
    page = doc.new_page()
    y = 60
    page.insert_text((50, y), title, fontsize=18)
    y += 30
    for line in lines:
        for part in wrap(line, 90):
            if y > 800:
                page = doc.new_page()
                y = 60
            page.insert_text((50, y), part, fontsize=10)
            y += 15
    doc.save(path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def build_corpus():
    os.makedirs(config.DATASET_DIR, exist_ok=True)
    rows = []
    for label, make in TEMPLATES.items():
        for _ in range(SAMPLES_PER_CLASS):
            title, lines = make()
            rows.append((label, to_text(title, lines, label=label)))
    rng.shuffle(rows)
    with open(config.DATASET_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["label", "text"])
        w.writerows(rows)
    print(f"[dataset] {len(rows)} labelled documents -> {config.DATASET_CSV}")


def build_ocr_test_images(per_class=4):
    """Held-out rendered images (never used for training) to test OCR + model end-to-end."""
    os.makedirs(config.OCR_TEST_DIR, exist_ok=True)
    for label, make in TEMPLATES.items():
        for i in range(per_class):
            title, lines = make()
            render(label, title, lines, scanned=(i % 2 == 1)).save(os.path.join(config.OCR_TEST_DIR, f"{label}__{i + 1}.png"))
    print(f"[dataset] {per_class * len(TEMPLATES)} OCR test images -> {config.OCR_TEST_DIR}")


def build_samples():
    """Demo files the jury can upload live (normal + abnormal cases)."""
    normal = os.path.join(config.SAMPLES_DIR, "normal")
    abnormal = os.path.join(config.SAMPLES_DIR, "abnormal")
    os.makedirs(normal, exist_ok=True)
    os.makedirs(abnormal, exist_ok=True)

    for label, make in TEMPLATES.items():
        title, lines = make()
        render(label, title, lines).save(os.path.join(normal, f"{label}_clean.png"))
        title, lines = make()
        render(label, title, lines, scanned=True).convert("RGB").save(os.path.join(normal, f"{label}_scanned.jpg"), quality=70)
    for label in ["invoice", "legal_contract", "bank_statement"]:
        title, lines = TEMPLATES[label]()
        write_pdf(os.path.join(normal, f"{label}_digital.pdf"), title, lines)
    title, lines = make_resume()
    with open(os.path.join(normal, "resume_plain.txt"), "w", encoding="utf-8") as f:
        f.write(title + "\n" + "\n".join(lines))

    # ---- abnormal / edge cases ----
    Image.new("RGB", (1240, 1754), "white").save(os.path.join(abnormal, "blank_page.png"))
    # a "landscape photo" (sky, sun, hills) - not a document at all
    img = Image.new("RGB", (1200, 800), "#87ceeb")
    d = ImageDraw.Draw(img)
    d.ellipse([850, 80, 1000, 230], fill="#fde047")
    d.polygon([(0, 800), (300, 380), (650, 800)], fill="#16a34a")
    d.polygon([(400, 800), (800, 300), (1200, 800)], fill="#15803d")
    img.save(os.path.join(abnormal, "landscape_photo.jpg"), quality=85)
    # a tiny amount of text
    img = Image.new("RGB", (800, 300), "white")
    ImageDraw.Draw(img).text((60, 120), "Hello", font=load_font(48), fill="black")
    img.save(os.path.join(abnormal, "very_little_text.png"))
    # unrelated text (a recipe) - readable but not one of our document types
    with open(os.path.join(abnormal, "unrelated_recipe.txt"), "w", encoding="utf-8") as f:
        f.write("Grandma's Chocolate Chip Cookies\nPreheat the oven to 180 degrees. Cream the butter and sugar until fluffy. "
                "Beat in the eggs and vanilla essence. Fold in flour, baking soda and a pinch of salt. Stir in chocolate chips. "
                "Scoop spoonfuls onto a tray and bake for twelve minutes until golden. Let them cool and enjoy with a glass of milk.")
    # an ambiguous document: half receipt, half invoice
    title, inv = make_invoice()
    _, rec = make_receipt()
    render("invoice", "PAYMENT DOCUMENT", inv[:6] + rec[4:10]).save(os.path.join(abnormal, "ambiguous_invoice_receipt.png"))
    # very poor scan (heavy blur + noise)
    title, lines = make_medical()
    render("medical_report", title, lines, scanned=True).filter(ImageFilter.GaussianBlur(2.2)).save(os.path.join(abnormal, "very_blurry_scan.jpg"), quality=40)
    # corrupted file with an image extension
    with open(os.path.join(abnormal, "corrupted_file.png"), "wb") as f:
        f.write(os.urandom(2048))
    print(f"[samples] demo documents -> {config.SAMPLES_DIR}")


if __name__ == "__main__":
    build_corpus()
    build_ocr_test_images()
    build_samples()
    print("Done. Next step:  python train_model.py")
