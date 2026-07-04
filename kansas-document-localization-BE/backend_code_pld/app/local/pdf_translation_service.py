import os
import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple, Any

from fastapi import UploadFile, HTTPException

from app.processors.pdf_processor import process_pdf
from app.local.local_s3_service_bucket import upload_file_to_s3
from app.local.pdf_translation_agent import PdfTranslationAgent
from app.local.pdf_translate_reconstruct import reconstruct_translated_pdf
from app.core.logger import (
    get_logger,
    log_stage_started,
    log_stage_success,
    log_stage_failure,
)

logger = get_logger(__name__)

LOCAL_BUCKET_NAME = "local-file-system"

APP_DIR = Path(__file__).resolve().parents[1]          # backend_code/app
BACKEND_DIR = APP_DIR.parent                           # backend_code
STATIC_DIR = BACKEND_DIR / "static"
UPLOAD_DIR = STATIC_DIR / "uploads"
JSON_DIR = STATIC_DIR / "json"
DOWNLOAD_DIR = STATIC_DIR / "downloads"


def ensure_local_dirs() -> None:
    for folder in (UPLOAD_DIR, JSON_DIR, DOWNLOAD_DIR):
        folder.mkdir(parents=True, exist_ok=True)


async def process_pdf_translation_request(
    file: UploadFile,
    source_language: str = "English",
    target_language: str = "Spanish",
) -> dict:
    """
    Full PDF language conversion flow with layout preservation.

    Flow:
    1. Validate uploaded PDF.
    2. Save PDF locally under static/uploads.
    3. Extract layout JSON using existing process_pdf().
    4. Save JSON locally under static/json.
    5. Extract {block_id: text} from JSON.
    6. Translate block dictionary using existing Ollama/BedrockService wrapper.
    7. Build replacement payload old_text -> translated_text.
    8. Reuse existing pdf_replace.replace_text() to generate final PDF.
    """
    stage = "PDF TRANSLATION SERVICE"
    log_stage_started(logger, stage, "PDF translation request started")

    ensure_local_dirs()

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    temp_pdf_path = None
    temp_json_path = None

    try:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
        safe_original_name = Path(file.filename).stem.replace(" ", "_")
        pdf_file_name = f"{timestamp}_{safe_original_name}.pdf"
        json_file_name = f"{timestamp}_{safe_original_name}.json"

        pdf_local_key = f"upload_file/{pdf_file_name}"
        json_local_key = f"json_file/{json_file_name}"

        # 1. Read uploaded PDF into temp file.
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            content = await file.read()
            if not content:
                raise HTTPException(status_code=400, detail="Uploaded file is empty")
            temp_pdf.write(content)
            temp_pdf_path = temp_pdf.name

        # 2. Save PDF locally using existing local S3-compatible wrapper.
        pdf_local_uri = upload_file_to_s3(
            file_path=temp_pdf_path,
            bucket=LOCAL_BUCKET_NAME,
            key=pdf_local_key,
            content_type="application/pdf",
        )

        # 3. Generate JSON using existing extraction processor.
        temp_json_path = os.path.join(tempfile.gettempdir(), json_file_name)
        process_pdf(
            input_pdf_path=temp_pdf_path,
            output_json_path=temp_json_path,
        )

        if not os.path.exists(temp_json_path):
            raise HTTPException(status_code=500, detail="JSON file was not created")

        # 4. Save generated JSON locally.
        json_local_uri = upload_file_to_s3(
            file_path=temp_json_path,
            bucket=LOCAL_BUCKET_NAME,
            key=json_local_key,
            content_type="application/json",
        )

        json_path = JSON_DIR / json_file_name
        with open(json_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        # 5. Extract block_id -> text from JSON.
        text_by_block_id, block_meta = extract_text_dictionary_from_json(json_data)

        if not text_by_block_id:
            raise HTTPException(status_code=422, detail="No translatable text blocks found in extracted JSON")

        # 6. Translate all text blocks.
        translation_agent = PdfTranslationAgent()
        translated_text_by_block_id = translation_agent.translate_blocks(
            text_by_block_id=text_by_block_id,
            source_language=source_language,
            target_language=target_language,
        )

        # 7. Update JSON in memory and save translated JSON copy.
        updated_json = apply_translations_to_json(json_data, translated_text_by_block_id)
        translated_json_file_name = f"translated_{json_file_name}"
        translated_json_path = JSON_DIR / translated_json_file_name
        with open(translated_json_path, "w", encoding="utf-8") as f:
            json.dump(updated_json, f, ensure_ascii=False, indent=2)

        # 8. Build replacement payload and reuse existing PDF replacement code.
        reconstruct_result = reconstruct_translated_pdf(
            request_id=json_file_name,
            json_data=json_data,
            translated_text_by_block_id=translated_text_by_block_id,
        )

        output_file_name = reconstruct_result["output_file_name"]
        output_path = reconstruct_result["output_path"]
        output_url = reconstruct_result["output_url"]
        logs = reconstruct_result["logs"]

        output_url = f"/static/downloads/{output_file_name}"

        result = {
            "source_language": source_language,
            "target_language": target_language,
            "storage_mode": "local",
            "pdf_name": pdf_file_name,
            "json_name": json_file_name,
            "translated_json_name": translated_json_file_name,
            "pdf_local": pdf_local_uri,
            "json_local": json_local_uri,
            "translated_block_count": len(translated_text_by_block_id),
            "replaced_count": len(translated_text_by_block_id),
            "replacement_logs": logs,
            "output_file_name": output_file_name,
            "output_path": output_path,
            "output_url": output_url,
        }

        log_stage_success(logger, stage, "PDF translation completed successfully")
        return result

    except HTTPException:
        raise
    except Exception as e:
        log_stage_failure(logger, stage, "PDF translation failed", e)
        raise
    finally:
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
        if temp_json_path and os.path.exists(temp_json_path):
            os.remove(temp_json_path)


def extract_text_dictionary_from_json(json_data: dict) -> Tuple[Dict[str, str], Dict[str, dict]]:
    """
    Creates:
    - text_by_block_id: {block_id: text}
    - block_meta: {block_id: {page_number, type, bbox}}

    Handles the JSON structure used by your extraction flow:
    documents -> pages -> blocks -> properties -> lines.
    """
    text_by_block_id = {}
    block_meta = {}

    documents = json_data.get("documents", [])
    for document in documents:
        for page in document.get("pages", []):
            page_number = page.get("page_number", 1)
            for block in page.get("blocks", []):
                block_type = block.get("type")
                if block_type != "text":
                    continue

                block_id = block.get("block_id")
                if not block_id:
                    continue

                text = extract_text_from_block(block)
                if not text:
                    continue

                text_by_block_id[block_id] = text
                block_meta[block_id] = {
                    "page_number": page_number,
                    "type": block_type,
                    "bbox": block.get("bbox"),
                }

    return text_by_block_id, block_meta


def extract_text_from_block(block: dict) -> str:
    properties = block.get("properties", {})

    print("\n" + "=" * 80)
    print("BLOCK ID:", block.get("block_id"))
    print("BLOCK TYPE:", block.get("type"))
    print("PROPERTY KEYS:", list(properties.keys()) if isinstance(properties, dict) else "NOT_DICT")
    print("RAW BLOCK SAMPLE:")
    print(str(block)[:2000])
    print("=" * 80)

    lines = properties.get("lines", []) if isinstance(properties, dict) else []

    line_texts = []

    for line in lines:
        if isinstance(line, dict):
            text = str(line.get("text", "")).strip()

            if text:
                line_texts.append(text)

    extracted_text = " ".join(line_texts).strip()

    if extracted_text:
        print("EXTRACTED TEXT:", extracted_text[:300])

    return extracted_text

def apply_translations_to_json(json_data: dict, translated_text_by_block_id: Dict[str, str]) -> dict:
    """
    Replaces text inside the exact same block_id positions in the extracted JSON.
    Keeps bbox, font, color, image, table and layout metadata untouched.
    """
    documents = json_data.get("documents", [])
    for document in documents:
        for page in document.get("pages", []):
            for block in page.get("blocks", []):
                block_id = block.get("block_id")
                if not block_id or block_id not in translated_text_by_block_id:
                    continue

                properties = block.get("properties", {})
                lines = properties.get("lines", []) if isinstance(properties, dict) else []
                if not lines:
                    continue

                # Put the translated text into the first line, clear remaining line text.
                # This preserves the same block_id and layout metadata.
                translated_text = translated_text_by_block_id[block_id]
                first_line_done = False
                for line in lines:
                    if not isinstance(line, dict):
                        continue
                    if not first_line_done:
                        line["text"] = translated_text
                        first_line_done = True
                    else:
                        line["text"] = ""

    return json_data


def build_replacement_payload(
    text_by_block_id: Dict[str, str],
    translated_text_by_block_id: Dict[str, str],
    block_meta: Dict[str, dict],
) -> dict:
    """
    Converts block translations into the same result shape expected by pdf_replace.replace_text().
    """
    results = []

    for block_id, old_text in text_by_block_id.items():
        new_text = translated_text_by_block_id.get(block_id)
        if not new_text or new_text.strip() == old_text.strip():
            continue

        meta = block_meta.get(block_id, {})
        results.append({
            "matched_segment_id": block_id,
            "matched_page_number": meta.get("page_number", 1),
            "confidence": 1.0,
            "layout_risk": "MEDIUM",
            "old_text": old_text,
            "new_text": new_text,
        })

    return {
        "status": "SUCCESS",
        "results": results,
        "errors": [],
    }
