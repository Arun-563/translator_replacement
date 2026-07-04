import fitz
import boto3
import os
import json


S3_BUCKET = "kansas-document-files"
S3_REGION = "us-east-1"

UPLOAD_FOLDER = "upload_file"
JSON_FOLDER = "json_file"
UPDATED_FOLDER = "ai_updated_file"

OUTPUT_DIR = "output"
INPUT_PATH = f"{OUTPUT_DIR}/input.pdf"
LAYOUT_JSON_PATH = f"{OUTPUT_DIR}/layout.json"


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_s3_client():
    return boto3.client("s3", region_name=S3_REGION)


def get_request_base_name(request_id: str):
    return request_id.replace(".json", "")


def derive_original_pdf_key(request_id: str):
    base_name = get_request_base_name(request_id)
    return f"{UPLOAD_FOLDER}/{base_name}.pdf"


def derive_layout_json_key(request_id: str):
    return f"{JSON_FOLDER}/{request_id}"


def build_output_file_name(request_id: str):
    base_name = get_request_base_name(request_id)
    return f"translated_{base_name}.pdf"


def build_local_output_path(request_id: str):
    output_file_name = build_output_file_name(request_id)
    return f"{OUTPUT_DIR}/{output_file_name}"


def download_pdf_from_s3(request_id: str):
    ensure_output_dir()

    s3 = get_s3_client()
    s3_key = derive_original_pdf_key(request_id)

    s3.download_file(S3_BUCKET, s3_key, INPUT_PATH)

    return INPUT_PATH


def download_layout_json_from_s3(request_id: str):
    ensure_output_dir()

    s3 = get_s3_client()
    s3_key = derive_layout_json_key(request_id)

    s3.download_file(S3_BUCKET, s3_key, LAYOUT_JSON_PATH)

    with open(LAYOUT_JSON_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def upload_pdf_to_s3(local_output_path: str, output_file_name: str):
    s3 = get_s3_client()

    s3_key = f"{UPDATED_FOLDER}/{output_file_name}"

    s3.upload_file(local_output_path, S3_BUCKET, s3_key)

    return s3_key


def find_block_by_id(data, target_block_id):
    if isinstance(data, dict):
        current_id = (
            data.get("block_id")
            or data.get("id")
            or data.get("segment_id")
        )

        if current_id == target_block_id:
            return data

        for value in data.values():
            found = find_block_by_id(value, target_block_id)
            if found:
                return found

    elif isinstance(data, list):
        for item in data:
            found = find_block_by_id(item, target_block_id)
            if found:
                return found

    return None


def get_block_text(block):
    if block.get("text"):
        return block["text"]

    properties = block.get("properties", {})
    lines = properties.get("lines", [])

    line_texts = []

    for line in lines:
        if line.get("text"):
            line_texts.append(line["text"])

    return "\n".join(line_texts)


def get_block_bbox(block):
    if block.get("bbox"):
        return block["bbox"]

    properties = block.get("properties", {})
    lines = properties.get("lines", [])

    if lines and lines[0].get("bbox"):
        return lines[0]["bbox"]

    return None


def get_original_font_size(block):
    properties = block.get("properties", {})
    lines = properties.get("lines", [])

    for line in lines:
        spans = line.get("spans", [])
        for span in spans:
            font_size = span.get("font_size")
            if font_size:
                return float(font_size)

    return 9.5


def get_original_font_color(block):
    properties = block.get("properties", {})
    lines = properties.get("lines", [])

    for line in lines:
        spans = line.get("spans", [])
        for span in spans:
            color = span.get("color")
            if color == "#000000":
                return (0, 0, 0)

    return (0, 0, 0)


def should_skip_bbox(bbox, confidence, layout_risk, page):
    if confidence < 0.85:
        return True, "Low confidence"

    if str(layout_risk).upper() == "HIGH":
        return True, "High layout risk"

    x0, y0, x1, y1 = bbox

    if y0 < 60:
        return True, "Header protected"

    if y1 > page.rect.height - 60:
        return True, "Footer protected"

    return False, ""


def expand_rect_slightly(rect):
    """
    Small safe expansion to reduce text clipping while preserving layout.
    This does not shift the text to another section.
    """
    return fitz.Rect(
        rect.x0,
        rect.y0 - 1,
        rect.x1 + 4,
        rect.y1 + 2
    )


def replace_text(request_id: str, payload: dict):
    """
    Main replacement flow:
    1. Download original PDF from S3 upload_file/
    2. Download layout JSON from S3 json_file/
    3. Find backend block by matched_segment_id
    4. Use backend bbox directly
    5. Replace only old_text inside full block text
    6. Save unique local PDF
    7. Upload unique PDF to S3 ai_updated_file/
    """

    input_pdf = download_pdf_from_s3(request_id)
    layout_json = download_layout_json_from_s3(request_id)

    output_file_name = build_output_file_name(request_id)
    local_output_path = build_local_output_path(request_id)

    doc = fitz.open(input_pdf)

    replaced_count = 0
    logs = []

    for item in payload.get("results", []):
        matched_segment_id = item.get("matched_segment_id")
        matched_page_number = item.get("matched_page_number")
        confidence = item.get("confidence", 0)
        layout_risk = item.get("layout_risk", "LOW")
        old_text = item.get("old_text")
        new_text = item.get("new_text")

        if not matched_segment_id:
            logs.append({
                "status": "SKIPPED",
                "reason": "matched_segment_id missing"
            })
            continue

        if not old_text or not new_text:
            logs.append({
                "segment_id": matched_segment_id,
                "status": "SKIPPED",
                "reason": "old_text or new_text missing"
            })
            continue

        block = find_block_by_id(layout_json, matched_segment_id)

        if not block:
            logs.append({
                "segment_id": matched_segment_id,
                "status": "SKIPPED",
                "reason": "block_id not found in layout JSON"
            })
            continue

        bbox = get_block_bbox(block)
        block_text = get_block_text(block)
        original_font_size = get_original_font_size(block)
        original_color = get_original_font_color(block)

        if not bbox:
            logs.append({
                "segment_id": matched_segment_id,
                "status": "SKIPPED",
                "reason": "bbox missing in layout JSON"
            })
            continue

        if not matched_page_number:
            logs.append({
                "segment_id": matched_segment_id,
                "status": "SKIPPED",
                "reason": "matched_page_number missing"
            })
            continue

        page = doc[matched_page_number - 1]

        skip, reason = should_skip_bbox(
            bbox=bbox,
            confidence=confidence,
            layout_risk=layout_risk,
            page=page
        )

        if skip:
            logs.append({
                "segment_id": matched_segment_id,
                "status": "SKIPPED",
                "reason": reason,
                "bbox": bbox
            })
            continue

        if block_text and old_text in block_text:
            final_text = block_text.replace(old_text, new_text)
        else:
            final_text = new_text

        rect = fitz.Rect(bbox)
        rect = expand_rect_slightly(rect)

        try:
            page.add_redact_annot(rect, fill=(1, 1, 1))
            page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

            page.insert_textbox(
                rect,
                final_text,
                fontsize=original_font_size,
                color=original_color
            )

            replaced_count += 1

            logs.append({
                "segment_id": matched_segment_id,
                "status": "REPLACED",
                "page": matched_page_number,
                "bbox": bbox,
                "old_text": old_text,
                "new_text": new_text,
                "block_text": block_text,
                "final_text": final_text,
                "font_size": original_font_size
            })

        except Exception as error:
            logs.append({
                "segment_id": matched_segment_id,
                "status": "ERROR",
                "reason": str(error)
            })

    ensure_output_dir()
    doc.save(local_output_path)
    doc.close()

    s3_key = upload_pdf_to_s3(local_output_path, output_file_name)

    return replaced_count, logs, output_file_name, local_output_path, s3_key