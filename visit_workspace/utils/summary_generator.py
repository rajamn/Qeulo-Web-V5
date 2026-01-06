import re

def extract_lab_values(text):
    """
    Extract structured lab rows as:
    { "test": "...", "value": "...", "range": "..." }
    """
    rows = []
    for line in text.splitlines():
        if not re.search(r"\d", line):
            continue

        parts = re.split(r"\s{2,}|\t", line.strip())
        if len(parts) < 2:
            continue

        test = parts[0]
        value = parts[1]

        ref = parts[2] if len(parts) >= 3 else ""

        rows.append({
            "test": test,
            "value": value,
            "range": ref,
        })

    return rows


def extract_impression(text):
    patterns = [
        r"impression[:\- ]+(.*)",
        r"conclusion[:\- ]+(.*)",
        r"overall[:\- ]+(.*)",
        r"summary[:\- ]+(.*)",
        r"diagnosis[:\- ]+(.*)",
    ]
    for p in patterns:
        m = re.search(p, text, flags=re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return ""


def extract_abnormal(rows):
    abnormal = []
    
    abnormal_markers = ["high", "low", "H", "L", "↑", "↓", "*"]

    for row in rows:
        joined = f"{row['test']} {row['value']} {row['range']}".lower()
        if any(x.lower() in joined for x in abnormal_markers):
            abnormal.append(row)

    return abnormal


def summarize_free_text(text, limit=300):
    words = text.split()
    small = " ".join(words[:limit])
    return small + ("..." if len(words) > limit else "")


def generate_summary(text, doc_type):
    text = text.strip()

    summary = {
        "doc_type": doc_type,
        "key_findings": "",
        "impression": "",
        "recommendations": "",
        "structured_values": [],
        "abnormal_values": [],
        "free_summary": "",
    }

    # ---------------------------
    # LAB REPORTS
    # ---------------------------
    if doc_type == "LAB":
        rows = extract_lab_values(text)
        summary["structured_values"] = rows
        summary["abnormal_values"] = extract_abnormal(rows)
        summary["impression"] = extract_impression(text) or "No impression found"
        summary["key_findings"] = "Lab values extracted"
        summary["recommendations"] = "Correlate clinically"

        return summary

    # ---------------------------
    # RADIOLOGY REPORTS
    # ---------------------------
    elif doc_type == "RAD":
        summary["impression"] = extract_impression(text) or "Impression missing"
        summary["key_findings"] = "Radiology report extracted"
        summary["recommendations"] = "Review imaging findings"
        summary["free_summary"] = summarize_free_text(text)

        return summary

    # ---------------------------
    # OLD PRESCRIPTIONS
    # ---------------------------
    elif doc_type == "RX_OLD":
        summary["key_findings"] = "Medication list extracted"
        summary["impression"] = "Historical prescription document"
        summary["free_summary"] = summarize_free_text(text)

        return summary

    # ---------------------------
    # DISCHARGE SUMMARY
    # ---------------------------
    elif doc_type == "DISCH":
        summary["key_findings"] = "Discharge summary extracted"
        summary["impression"] = extract_impression(text) or "Impression not found"
        summary["free_summary"] = summarize_free_text(text)

        return summary

    # ---------------------------
    # EVERYTHING ELSE
    # ---------------------------
    else:
        summary["free_summary"] = summarize_free_text(text)
        summary["impression"] = extract_impression(text) or "Not available"
        summary["key_findings"] = "General document summary"
        summary["recommendations"] = "Review content"

        return summary
