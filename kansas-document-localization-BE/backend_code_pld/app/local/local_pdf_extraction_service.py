# import os
# import tempfile
# from datetime import datetime
# from pathlib import Path
# from typing import List

# from fastapi import UploadFile, HTTPException

# from app.processors.pdf_processor import process_pdf
# from app.local.local_s3_service_bucket import upload_file_to_s3
# from app.local.local_bedrock_agent_service import send_payload_to_bedrock_agent



# from app.core.logger import (
#     get_logger,
#     log_stage_started,
#     log_stage_success,
#     log_stage_failure,
# )

# # ------------------------------------------------------------
# # Local PDF extraction flow
# # ------------------------------------------------------------
# # Put this file inside:
# # backend_code/app/local/local_pdf_extraction_service.py
# #
# # This keeps the same API-level behavior as pdf_extraction_service.py,
# # but saves PDF and JSON locally:
# #   static/uploads    -> PDF files
# #   static/json       -> extracted layout JSON files
# #   static/downloades -> downloaded/updated PDFs later
# # ------------------------------------------------------------

# LOCAL_BUCKET_NAME = "local-file-system"  # dummy value; kept for signature compatibility

# APP_DIR = Path(__file__).resolve().parents[1]          # backend_code/app
# BACKEND_DIR = APP_DIR.parent                           # backend_code
# STATIC_DIR = BACKEND_DIR / "static"
# UPLOAD_DIR = STATIC_DIR / "uploads"
# JSON_DIR = STATIC_DIR / "json"
# DOWNLOAD_DIR = STATIC_DIR / "downloades"  # keeping your requested spelling


# def ensure_local_dirs() -> None:
#     for folder in (UPLOAD_DIR, JSON_DIR, DOWNLOAD_DIR):
#         folder.mkdir(parents=True, exist_ok=True)


# async def process_pdf_request(file: UploadFile, payload: List[dict]):
#     """
#     Local version of process_pdf_request.

#     Flow:
#     1. Validate PDF and payload.
#     2. Read uploaded PDF from API.
#     3. Save renamed PDF into static/uploads.
#     4. Generate layout JSON using process_pdf().
#     5. Save generated JSON into static/json.
#     6. Build same downstream payload.
#     7. Call existing downstream backend agent API.
#     8. Return local file paths/URIs to frontend.
#     """
#     ensure_local_dirs()

#     if not file.filename or not file.filename.lower().endswith(".pdf"):
#         raise HTTPException(status_code=400, detail="Only PDF files are allowed")

#     if not isinstance(payload, list) or len(payload) == 0:
#         raise HTTPException(status_code=400, detail="Payload must be a non-empty list")

#     timestamp = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
#     pdf_file_name = f"{timestamp}.pdf"
#     json_file_name = f"{timestamp}.json"

#     # Keep old S3-style keys because local_s3_service_bucket maps them to local folders.
#     pdf_local_key = f"upload_file/{pdf_file_name}"
#     json_local_key = f"json_file/{json_file_name}"

#     temp_pdf_path = None
#     temp_json_path = None

#     try:
#         # 1. Save uploaded PDF temporarily first
#         with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
#             content = await file.read()
#             if not content:
#                 raise HTTPException(status_code=400, detail="Uploaded file is empty")
#             temp_pdf.write(content)
#             temp_pdf_path = temp_pdf.name

#         # 2. Save renamed PDF locally into static/uploads
#         pdf_local_uri = upload_file_to_s3(
#             file_path=temp_pdf_path,
#             bucket=LOCAL_BUCKET_NAME,
#             key=pdf_local_key,
#             content_type="application/pdf",
#         )

#         # 3. Generate JSON into temp file first
#         temp_json_path = os.path.join(tempfile.gettempdir(), json_file_name)
#         process_pdf(
#             input_pdf_path=temp_pdf_path,
#             output_json_path=temp_json_path,
#         )

#         if not os.path.exists(temp_json_path):
#             raise HTTPException(status_code=500, detail="JSON file was not created")

#         # 4. Save generated JSON locally into static/json
#         json_local_uri = upload_file_to_s3(
#             file_path=temp_json_path,
#             bucket=LOCAL_BUCKET_NAME,
#             key=json_local_key,
#             content_type="application/json",
#         )

#         # 5. Build downstream payload exactly like existing flow
#         instructions = []
#         for item in payload:
#             instructions.append(
#                 {
#                     "language": item.get("language", ""),
#                     "page_number": item.get("page_number"),
#                     "section_name": item.get("section_name", ""),
#                     "old_text": item.get("old_text", ""),
#                     "new_text": item.get("new_text", ""),
#                     "json_file": json_file_name,
#                     "user_instructions": item.get("user_instructions", ""),
#                 }
#             )

#         downstream_payload = {
#             "request_id": json_file_name,
#             "instructions": instructions,
#         }

#         # 6. Call your backend agent API as before
#         bedrock_agent_response = await send_payload_to_bedrock_agent(downstream_payload)

#         # 7. Return response to frontend
#         return {
#             "message": "Success",
#             "storage_mode": "local",
#             "pdf_local": pdf_local_uri,
#             "json_local": json_local_uri,
#             "pdf_name": pdf_file_name,
#             "json_name": json_file_name,
#             "pdf_path": str((UPLOAD_DIR / pdf_file_name).resolve()),
#             "json_path": str((JSON_DIR / json_file_name).resolve()),
#             "download_dir": str(DOWNLOAD_DIR.resolve()),
#             "downstream_payload": downstream_payload,
#             "bedrock_agent_response": bedrock_agent_response,
#         }

#     finally:
#         if temp_pdf_path and os.path.exists(temp_pdf_path):
#             os.remove(temp_pdf_path)
#         if temp_json_path and os.path.exists(temp_json_path):
#             os.remove(temp_json_path)


import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import UploadFile, HTTPException

from app.processors.pdf_processor import process_pdf
from app.local.local_s3_service_bucket import upload_file_to_s3
from app.local.local_bedrock_agent_service import send_payload_to_bedrock_agent

from app.core.logger import (
    get_logger,
    log_stage_started,
    log_stage_success,
    log_stage_failure,
)

logger = get_logger(__name__)

# ------------------------------------------------------------
# Local PDF extraction flow
# ------------------------------------------------------------
# Put this file inside:
# backend_code/app/local/local_pdf_extraction_service.py
#
# This keeps the same API-level behavior as pdf_extraction_service.py,
# but saves PDF and JSON locally:
#   static/uploads    -> PDF files
#   static/json       -> extracted layout JSON files
#   static/downloades -> downloaded/updated PDFs later
# ------------------------------------------------------------

LOCAL_BUCKET_NAME = "local-file-system"  # dummy value; kept for signature compatibility

APP_DIR = Path(__file__).resolve().parents[1]          # backend_code/app
BACKEND_DIR = APP_DIR.parent                           # backend_code
STATIC_DIR = BACKEND_DIR / "static"
UPLOAD_DIR = STATIC_DIR / "uploads"
JSON_DIR = STATIC_DIR / "json"
DOWNLOAD_DIR = STATIC_DIR / "downloades"  # keeping your requested spelling


def ensure_local_dirs() -> None:
    stage = "PDF EXTRACTION SERVICE"
    log_stage_started(logger, stage, "Ensuring local directories exist")
    try:
        for folder in (UPLOAD_DIR, JSON_DIR, DOWNLOAD_DIR):
            folder.mkdir(parents=True, exist_ok=True)
        log_stage_success(logger, stage, "Local directories are ready")
    except Exception as e:
        log_stage_failure(logger, stage, "Failed to ensure local directories", e)
        raise


async def process_pdf_request(file: UploadFile, payload: List[dict]):
    """
    Local version of process_pdf_request.

    Flow:
    1. Validate PDF and payload.
    2. Read uploaded PDF from API.
    3. Save renamed PDF into static/uploads.
    4. Generate layout JSON using process_pdf().
    5. Save generated JSON into static/json.
    6. Build same downstream payload.
    7. Call existing downstream backend agent API.
    8. Return local file paths/URIs to frontend.
    """
    stage = "PDF EXTRACTION SERVICE"
    log_stage_started(logger, stage, "PDF extraction request started")

    ensure_local_dirs()

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        log_stage_failure(logger, stage, "Invalid uploaded file type", ValueError("Only PDF files are allowed"))
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    if not isinstance(payload, list) or len(payload) == 0:
        log_stage_failure(logger, stage, "Invalid payload received", ValueError("Payload must be a non-empty list"))
        raise HTTPException(status_code=400, detail="Payload must be a non-empty list")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
    pdf_file_name = f"{timestamp}.pdf"
    json_file_name = f"{timestamp}.json"

    logger.info(
        f"Generated file names. PDF: {pdf_file_name}, JSON: {json_file_name}",
        extra={"stage": stage, "status": "STARTED", "error": "None"}
    )

    # Keep old S3-style keys because local_s3_service_bucket maps them to local folders.
    pdf_local_key = f"upload_file/{pdf_file_name}"
    json_local_key = f"json_file/{json_file_name}"

    temp_pdf_path = None
    temp_json_path = None

    try:
        # 1. Save uploaded PDF temporarily first
        logger.info(
            "Reading uploaded PDF and saving to temporary path",
            extra={"stage": stage, "status": "STARTED", "error": "None"}
        )
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            content = await file.read()
            if not content:
                log_stage_failure(logger, stage, "Uploaded file is empty", ValueError("Uploaded file is empty"))
                raise HTTPException(status_code=400, detail="Uploaded file is empty")
            temp_pdf.write(content)
            temp_pdf_path = temp_pdf.name

        logger.info(
            f"Temporary PDF created successfully: {temp_pdf_path}",
            extra={"stage": stage, "status": "SUCCESS", "error": "None"}
        )

        # 2. Save renamed PDF locally into static/uploads
        logger.info(
            f"Uploading PDF to local storage with key: {pdf_local_key}",
            extra={"stage": stage, "status": "STARTED", "error": "None"}
        )
        pdf_local_uri = upload_file_to_s3(
            file_path=temp_pdf_path,
            bucket=LOCAL_BUCKET_NAME,
            key=pdf_local_key,
            content_type="application/pdf",
        )

        logger.info(
            f"PDF saved successfully to local storage: {pdf_local_uri}",
            extra={"stage": stage, "status": "SUCCESS", "error": "None"}
        )

        # 3. Generate JSON into temp file first
        temp_json_path = os.path.join(tempfile.gettempdir(), json_file_name)
        logger.info(
            f"Starting PDF processing to generate JSON: {temp_json_path}",
            extra={"stage": stage, "status": "STARTED", "error": "None"}
        )
        process_pdf(
            input_pdf_path=temp_pdf_path,
            output_json_path=temp_json_path,
        )

        if not os.path.exists(temp_json_path):
            log_stage_failure(logger, stage, "JSON file was not created after PDF processing", FileNotFoundError("JSON file was not created"))
            raise HTTPException(status_code=500, detail="JSON file was not created")

        logger.info(
            f"JSON generated successfully at temp location: {temp_json_path}",
            extra={"stage": stage, "status": "SUCCESS", "error": "None"}
        )

        # 4. Save generated JSON locally into static/json
        logger.info(
            f"Uploading JSON to local storage with key: {json_local_key}",
            extra={"stage": stage, "status": "STARTED", "error": "None"}
        )
        json_local_uri = upload_file_to_s3(
            file_path=temp_json_path,
            bucket=LOCAL_BUCKET_NAME,
            key=json_local_key,
            content_type="application/json",
        )

        logger.info(
            f"JSON saved successfully to local storage: {json_local_uri}",
            extra={"stage": stage, "status": "SUCCESS", "error": "None"}
        )

        # 5. Build downstream payload exactly like existing flow
        instructions = []
        logger.info(
            "Building downstream payload instructions",
            extra={"stage": stage, "status": "STARTED", "error": "None"}
        )
        for item in payload:
            instructions.append(
                {
                    "language": item.get("language", ""),
                    "page_number": item.get("page_number"),
                    "section_name": item.get("section_name", ""),
                    "old_text": item.get("old_text", ""),
                    "new_text": item.get("new_text", ""),
                    "json_file": json_file_name,
                    "user_instructions": item.get("user_instructions", ""),
                }
            )

        downstream_payload = {
            "request_id": json_file_name,
            "instructions": instructions,
        }

        logger.info(
            f"Downstream payload built successfully with {len(instructions)} instruction(s)",
            extra={"stage": stage, "status": "SUCCESS", "error": "None"}
        )

        # 6. Call your backend agent API as before
        logger.info(
            "Sending payload to local bedrock agent service",
            extra={"stage": stage, "status": "STARTED", "error": "None"}
        )
        bedrock_agent_response = await send_payload_to_bedrock_agent(downstream_payload)

        logger.info(
            "Received response from local bedrock agent service",
            extra={"stage": stage, "status": "SUCCESS", "error": "None"}
        )

        # 7. Return response to frontend
        log_stage_success(logger, stage, "PDF extraction request completed successfully")
        return {
            "message": "Success",
            "storage_mode": "local",
            "pdf_local": pdf_local_uri,
            "json_local": json_local_uri,
            "pdf_name": pdf_file_name,
            "json_name": json_file_name,
            "pdf_path": str((UPLOAD_DIR / pdf_file_name).resolve()),
            "json_path": str((JSON_DIR / json_file_name).resolve()),
            "download_dir": str(DOWNLOAD_DIR.resolve()),
            "downstream_payload": downstream_payload,
            "bedrock_agent_response": bedrock_agent_response,
        }

    except Exception as e:
        log_stage_failure(logger, stage, "PDF extraction request failed", e)
        raise

    finally:
        logger.info(
            "Cleaning up temporary files if they exist",
            extra={"stage": stage, "status": "STARTED", "error": "None"}
        )
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
            logger.info(
                f"Temporary PDF removed: {temp_pdf_path}",
                extra={"stage": stage, "status": "SUCCESS", "error": "None"}
            )
        if temp_json_path and os.path.exists(temp_json_path):
            os.remove(temp_json_path)
            logger.info(
                f"Temporary JSON removed: {temp_json_path}",
                extra={"stage": stage, "status": "SUCCESS", "error": "None"}
            )