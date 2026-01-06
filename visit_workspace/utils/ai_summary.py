# visit_workspace/utils/ai_summary.py

from openai import OpenAI, OpenAIError, RateLimitError
from django.conf import settings
import logging
import json

logger = logging.getLogger(__name__)


def get_openai_client():
    api_key = getattr(settings, "OPENAI_API_KEY", None)
    if not api_key:
        raise RuntimeError("OpenAI API key is missing in settings.")
    return OpenAI(api_key=api_key)


def generate_ai_summary(ocr_text: str):
    client = get_openai_client()

    prompt = f"""
You are an Indian outpatient (OPD) clinical assistant.
Summarise the following OCR text.

TASK 1 – Produce JSON:
{{
  "diagnosis": [],
  "drugs": [],
  "labs": [],
  "radiology": "",
  "notes": ""
}}

TASK 2 – Provide 5-7 bullet summary.

TASK 3 – Clinical notes paragraph.

OCR Input:
{ocr_text}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
    except Exception as e:
        print("🚨 OpenAI API ERROR:", type(e), str(e))
        # Return failure signal
        return None, False, f"OpenAI Error: {str(e)}"

    try:
        full_output = response.choices[0].message.content.strip()
    except Exception as e:
        print("🚨 ERROR reading OpenAI response:", e)
        return None, False, "Invalid AI response structure."

    # Parse JSON block
    try:
        start = full_output.index("{")
        end = full_output.rindex("}") + 1
        json_block = full_output[start:end]
        json_data = json.loads(json_block)
    except Exception as e:
        print("🚨 JSON PARSE ERROR:", e)
        print("AI Output was:\n", full_output)
        json_data = {}

    # Extract remaining text
    remaining = full_output[end:].strip()

    if "Clinical Notes:" in remaining:
        parts = remaining.split("Clinical Notes:", 1)
        summary = parts[0].strip()
        clinical_notes = parts[1].strip()
    else:
        summary = remaining
        clinical_notes = json_data.get("notes", "")

    return {
        "diagnosis": json_data.get("diagnosis", []),
        "drugs": json_data.get("drugs", []),
        "labs": json_data.get("labs", []),
        "radiology": json_data.get("radiology", ""),
        "notes": clinical_notes,
        "summary": summary,
    }, True, None
