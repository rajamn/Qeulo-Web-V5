from django.conf import settings
import os
from PIL import Image
import base64
import json
from openai import OpenAI
from pdf2image import convert_from_path


# -------------------------------
# Utility
# -------------------------------
def get_openai_client():
    return OpenAI(api_key=settings.OPENAI_API_KEY)


def image_to_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# -------------------------------
# OCR EXTRACTOR
# -------------------------------
def extract_text_from_file(filepath: str) -> str:
    client = get_openai_client()
    ext = os.path.splitext(filepath)[1].lower()

    # PDF → Images → OCR
    if ext == ".pdf":
        images = convert_from_path(filepath)
        full_text = ""

        for i, img in enumerate(images):
            img_path = f"/tmp/page_{i}.jpg"
            img.save(img_path, "JPEG")
            b64 = image_to_base64(img_path)

            result = client.responses.create(
                model="gpt-4o-mini",
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_image",
                             "image_url": f"data:image/jpeg;base64,{b64}"},
                            {"type": "text",
                             "text": "Extract all text from this page accurately."}
                        ],
                    }
                ]
            )

            text = result.output_text
            full_text += "\n" + text

        return full_text.strip()

    # Image → OCR
    elif ext in [".jpg", ".jpeg", ".png"]:
        b64 = image_to_base64(filepath)

        result = client.responses.create(
            model="gpt-4o-mini",
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_image",
                         "image_url": f"data:image/jpeg;base64,{b64}"},
                        {"type": "text",
                         "text": "Extract all text from this image accurately."}
                    ],
                }
            ]
        )
        return result.output_text.strip()

    return "[UNSUPPORTED FILE TYPE]"


# -------------------------------
# SUMMARY GENERATOR
# -------------------------------
def generate_ai_summary(ocr_text: str):
    """
    Returns: (summary_dict, is_ai, error_message)
    summary_dict matches template requirements.
    """

    client = get_openai_client()

    prompt = f"""
You are an Indian outpatient clinical assistant.
Summarise the following OCR text into STRICT JSON + bullet points + clinical notes.

REQUIRED JSON SCHEMA:
{{
  "key_findings": "",
  "impression": "",
  "recommendations": "",
  "structured_values": [],
  "abnormal_values": []
}}

THEN WRITE:
### Bullet Summary:
- point 1
- point 2

### Clinical Notes:
Free text paragraph.

OCR Input:
{ocr_text}
    """

    try:
        response = client.responses.create(
            model="gpt-4o-mini",
            input=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )

        full_output = response.output_text.strip()

        # ------------ JSON extraction -------------
        try:
            start = full_output.index("{")
            end = full_output.rindex("}") + 1
            json_block = full_output[start:end]
            summary_json = json.loads(json_block)
        except Exception:
            summary_json = {}

        # ------------ remaining text --------------
        remaining = full_output[end:].strip()

        # Bullet summary
        bullet_summary = ""
        clinical_notes = ""

        if "### Clinical Notes:" in remaining:
            parts = remaining.split("### Clinical Notes:")
            bullet_summary = parts[0].replace("### Bullet Summary:", "").strip()
            clinical_notes = parts[1].strip()
        else:
            bullet_summary = remaining

        # ------------ Final structured return ------
        final_summary = {
            "key_findings": summary_json.get("key_findings", ""),
            "impression": summary_json.get("impression", ""),
            "recommendations": summary_json.get("recommendations", ""),
            "structured_values": summary_json.get("structured_values", []),
            "abnormal_values": summary_json.get("abnormal_values", []),
            "bullet_summary": bullet_summary,
            "clinical_notes": clinical_notes,
        }

        return final_summary, True, None

    except Exception as e:
        print("AI Summary Error =>", e)

        fallback = {
            "key_findings": "",
            "impression": "",
            "recommendations": "",
            "structured_values": [],
            "abnormal_values": [],
            "bullet_summary": "",
            "clinical_notes": ocr_text,
        }

        return fallback, False, "AI Summary unavailable"
