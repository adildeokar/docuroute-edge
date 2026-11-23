"""
ai_assistant.py - OPTIONAL cloud "second opinion" using OpenAI's cheapest mini model (gpt-4o-mini).

Important design decision for an EDGE system:
  * Classification and routing ALWAYS run locally - this module is never required.
  * It runs only when a user clicks "AI Insights" on a document.
  * Before any text leaves the device, long numbers (account / ID / card numbers) and
    e-mail addresses are masked to protect personal data.
"""
import json
import re

import config

SYSTEM_PROMPT = """You are an assistant in a document management office. You receive OCR text of ONE document
and the category predicted by a local machine-learning model. Reply ONLY with JSON:
{
  "summary": "2-3 sentence plain-English summary of the document",
  "key_fields": {"field name": "value", ...},          // up to 8 most useful fields (dates, amounts, names, numbers)
  "suggested_category": "one of: %s",
  "agrees_with_model": true/false,
  "reason": "one sentence explaining your category opinion",
  "action_items": ["what the receiving department should do next", ...],   // 1-3 items
  "priority": "low" | "medium" | "high"
}"""


def mask_sensitive(text):
    """Hide personal identifiers before sending text to the cloud."""
    text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "[email]", text)
    # any run of 6+ digits (spaces allowed) -> keep only the last 4 digits
    return re.sub(r"\d[\d ]{4,}\d", lambda m: "X" * 4 + m.group(0).replace(" ", "")[-4:], text)


def analyze(text, predicted_category):
    if not config.AI_ENABLED:
        raise RuntimeError("AI assistant is disabled (no OPENAI_API_KEY in backend/.env)")
    from openai import OpenAI

    labels = ", ".join(info["label"] for info in config.CATEGORIES.values()) + ", Other"
    client = OpenAI(api_key=config.OPENAI_API_KEY, timeout=30)
    response = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        temperature=0.2,
        max_tokens=500,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT % labels},
            {"role": "user", "content": f"Model prediction: {config.category_info(predicted_category)['label']}\n\n"
                                        f"Document text:\n{mask_sensitive(text)[:3500]}"},
        ],
    )
    result = json.loads(response.choices[0].message.content)
    result["model"] = config.OPENAI_MODEL
    result["tokens_used"] = response.usage.total_tokens if response.usage else None
    return result
