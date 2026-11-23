"""
ocr.py - STEP 2 at prediction time: turn any uploaded file into plain text, fully offline.

  * Images (png/jpg/bmp/tiff/webp) -> RapidOCR (PaddleOCR models running on ONNX Runtime, CPU only)
  * PDF                            -> embedded text layer; if it is a scanned PDF, pages are rendered and OCR'd
  * TXT / DOCX                     -> read directly

Returns text + which method was used + OCR confidence + time taken.
"""
import os
import threading
import time

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

import config

_engine = None
_engine_lock = threading.Lock()


def get_engine():
    """Load the OCR model once (lazy) - takes ~1s, then every call is fast."""
    global _engine
    with _engine_lock:
        if _engine is None:
            from rapidocr_onnxruntime import RapidOCR
            _engine = RapidOCR()
    return _engine


class ExtractionError(Exception):
    """Raised when a file cannot be read (corrupted / unsupported)."""


def _prepare_image(img):
    img = ImageOps.exif_transpose(img).convert("RGB")      # respect phone camera rotation
    max_side = 1800                                          # downscale huge photos -> faster on edge CPU
    if max(img.size) > max_side:
        scale = max_side / max(img.size)
        img = img.resize((int(img.width * scale), int(img.height * scale)))
    return img


def ocr_image(img):
    """Run OCR on a PIL image. Returns (text, mean_confidence)."""
    # use_cls=False skips the 180-degree text-angle model (scanned pages are upright; EXIF rotation handled above)
    result, _ = get_engine()(np.array(_prepare_image(img)), use_cls=False)
    if not result:
        return "", 0.0
    # result = [[box, text, score], ...]; sort top-to-bottom, then left-to-right to rebuild lines
    items = sorted(result, key=lambda r: (round(r[0][0][1] / 15), r[0][0][0]))
    lines, last_y = [], None
    for box, text, score in items:
        y = round(box[0][1] / 15)
        if last_y is not None and y == last_y:
            lines[-1] += " " + text
        else:
            lines.append(text)
        last_y = y
    confidence = float(np.mean([float(r[2]) for r in result]))
    return "\n".join(lines), confidence


def extract_text(path):
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    start = time.time()
    pages, confidence = 1, None

    try:
        if ext in config.IMAGE_EXTENSIONS:
            with Image.open(path) as img:
                text, confidence = ocr_image(img)
            method = "OCR (RapidOCR / ONNX)"

        elif ext == "pdf":
            import pymupdf
            with pymupdf.open(path) as doc:
                pages = doc.page_count
                text = "\n".join(page.get_text() for page in doc)
                method = "PDF text layer"
                if len(text.strip()) < config.MIN_TEXT_CHARS:      # scanned PDF -> OCR first 3 pages
                    texts, confs = [], []
                    for page in list(doc)[:3]:
                        pix = page.get_pixmap(dpi=150)
                        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                        t, c = ocr_image(img)
                        texts.append(t)
                        confs.append(c)
                    text, confidence = "\n".join(texts), float(np.mean(confs)) if confs else 0.0
                    method = "OCR on scanned PDF"

        elif ext == "txt":
            with open(path, encoding="utf-8", errors="ignore") as f:
                text = f.read()
            method = "Plain text"

        elif ext == "docx":
            import docx
            text = "\n".join(p.text for p in docx.Document(path).paragraphs)
            method = "Word document"

        else:
            raise ExtractionError(f"Unsupported file type '.{ext}'")

    except ExtractionError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, RuntimeError) as e:
        raise ExtractionError(f"File is corrupted or unreadable ({type(e).__name__})") from e
    except Exception as e:  # pymupdf / docx raise their own error types
        raise ExtractionError(f"Could not read file: {e}") from e

    return {
        "text": text.strip(),
        "method": method,
        "ocr_confidence": round(confidence, 3) if confidence is not None else None,
        "pages": pages,
        "extraction_ms": round((time.time() - start) * 1000, 1),
    }
