# import fitz
# import os


# from app.core.logger import (
#     get_logger,
#     log_stage_started,
#     log_stage_success,
#     log_stage_failure,
# )


# # ================= BASE PATH ================= #
# BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# # ================= LOCAL FOLDERS ================= #
# STATIC_PDF_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
# STATIC_OUTPUT_FOLDER = os.path.join(BASE_DIR, "static", "downloads")

# # ================= UTIL ================= #
# def ensure_output_dir():
#     os.makedirs(STATIC_OUTPUT_FOLDER, exist_ok=True)

# def get_base_name(request_id):
#     return request_id.replace(".json", "")

# def build_output_file_name(request_id):
#     return f"translated_{get_base_name(request_id)}.pdf"

# def build_output_path(request_id):
#     return os.path.join(STATIC_OUTPUT_FOLDER, build_output_file_name(request_id))

# def get_local_pdf_path(request_id):
#     return os.path.join(STATIC_PDF_FOLDER, f"{get_base_name(request_id)}.pdf")

# # ================= LOCAL LOAD ================= #
# def load_local_pdf(request_id):
#     ensure_output_dir()
#     pdf_path = get_local_pdf_path(request_id)
    
#     if not os.path.exists(pdf_path):
#         raise FileNotFoundError(f"Input PDF not found: {pdf_path}")
    
#     return pdf_path

# # ================= MAIN LOGIC ================= #
# def replace_text(request_id: str, payload: dict):

#     pdf_path = load_local_pdf(request_id)
#     output_name = build_output_file_name(request_id)
#     output_path = build_output_path(request_id)

#     doc = fitz.open(pdf_path)

#     replaced_count = 0
#     logs = []

#     for item in payload.get("results", []):
#         old_text = item.get("old_text")
#         new_text = item.get("new_text")
#         page_no = item.get("matched_page_number", 1) - 1

#         if not old_text or not new_text:
#             continue

#         page = doc[page_no]
#         blocks = page.get_text("blocks")

#         for block in blocks:
#             x0, y0, x1, y1, text, *_ = block

#             if old_text in text:
#                 try:
#                     updated_line = text.replace(old_text, new_text)

#                     # ✅ Expand rect (CRITICAL)
#                     rect = fitz.Rect(
#                         x0 - 2,
#                         y0 - 1,
#                         x1 + 10,
#                         y1 + 3
#                     )

#                     # ✅ Remove old text
#                     page.add_redact_annot(rect, fill=(1, 1, 1))
#                     page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

#                     # ✅ Insert new text
#                     result = page.insert_textbox(
#                         rect,
#                         updated_line,
#                         fontsize=9.3,
#                         color=(0, 0, 0),
#                         align=0
#                     )

#                     # ✅ Fallback
#                     if result < 0:
#                         page.insert_text(
#                             (rect.x0, rect.y1 - 2),
#                             updated_line,
#                             fontsize=9.3,
#                             color=(0, 0, 0)
#                         )

#                     replaced_count += 1

#                     logs.append({
#                         "status": "REPLACED",
#                         "old_text": old_text,
#                         "new_text": new_text,
#                         "page": page_no + 1
#                     })

#                     break

#                 except Exception as e:
#                     logs.append({
#                         "status": "ERROR",
#                         "error": str(e),
#                         "page": page_no + 1
#                     })

#     ensure_output_dir()

#     doc.save(output_path)
#     doc.close()

#     return replaced_count, logs, output_name, output_path

import fitz
import os

from app.core.logger import (
    get_logger,
    log_stage_started,
    log_stage_success,
    log_stage_failure,
)

logger = get_logger(__name__)

# ================= BASE PATH ================= #
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# ================= LOCAL FOLDERS ================= #
STATIC_PDF_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
STATIC_OUTPUT_FOLDER = os.path.join(BASE_DIR, "static", "downloads")

# ================= UTIL ================= #
def ensure_output_dir():
    stage = "PDF REPLACE SERVICE"
    log_stage_started(logger, stage, "Ensuring output directory exists")
    try:
        os.makedirs(STATIC_OUTPUT_FOLDER, exist_ok=True)
        log_stage_success(logger, stage, f"Output directory is ready: {STATIC_OUTPUT_FOLDER}")
    except Exception as e:
        log_stage_failure(logger, stage, "Failed to ensure output directory", e)
        raise

def get_base_name(request_id):
    stage = "PDF REPLACE SERVICE"
    log_stage_started(logger, stage, f"Extracting base name from request_id: {request_id}")
    try:
        result = request_id.replace(".json", "")
        log_stage_success(logger, stage, f"Base name extracted successfully: {result}")
        return result
    except Exception as e:
        log_stage_failure(logger, stage, f"Failed to extract base name from request_id: {request_id}", e)
        raise

def build_output_file_name(request_id):
    stage = "PDF REPLACE SERVICE"
    log_stage_started(logger, stage, f"Building output file name for request_id: {request_id}")
    try:
        result = f"translated_{get_base_name(request_id)}.pdf"
        log_stage_success(logger, stage, f"Output file name built successfully: {result}")
        return result
    except Exception as e:
        log_stage_failure(logger, stage, f"Failed to build output file name for request_id: {request_id}", e)
        raise

def build_output_path(request_id):
    stage = "PDF REPLACE SERVICE"
    log_stage_started(logger, stage, f"Building output path for request_id: {request_id}")
    try:
        result = os.path.join(STATIC_OUTPUT_FOLDER, build_output_file_name(request_id))
        log_stage_success(logger, stage, f"Output path built successfully: {result}")
        return result
    except Exception as e:
        log_stage_failure(logger, stage, f"Failed to build output path for request_id: {request_id}", e)
        raise

def get_local_pdf_path(request_id):
    stage = "PDF REPLACE SERVICE"
    log_stage_started(logger, stage, f"Building local PDF path for request_id: {request_id}")
    try:
        result = os.path.join(STATIC_PDF_FOLDER, f"{get_base_name(request_id)}.pdf")
        log_stage_success(logger, stage, f"Local PDF path built successfully: {result}")
        return result
    except Exception as e:
        log_stage_failure(logger, stage, f"Failed to build local PDF path for request_id: {request_id}", e)
        raise

# ================= LOCAL LOAD ================= #
def load_local_pdf(request_id):
    stage = "PDF REPLACE SERVICE"
    log_stage_started(logger, stage, f"Loading local PDF for request_id: {request_id}")

    try:
        ensure_output_dir()
        pdf_path = get_local_pdf_path(request_id)

        logger.info(
            f"Resolved input PDF path: {pdf_path}",
            extra={"stage": stage, "status": "STARTED", "error": "None"}
        )

        if not os.path.exists(pdf_path):
            log_stage_failure(logger, stage, f"Input PDF not found: {pdf_path}", FileNotFoundError(f"Input PDF not found: {pdf_path}"))
            raise FileNotFoundError(f"Input PDF not found: {pdf_path}")

        log_stage_success(logger, stage, f"Input PDF found successfully: {pdf_path}")
        return pdf_path

    except Exception as e:
        log_stage_failure(logger, stage, f"Failed to load local PDF for request_id: {request_id}", e)
        raise

# ================= MAIN LOGIC ================= #
def replace_text(request_id: str, payload: dict):
    stage = "PDF REPLACE SERVICE"
    log_stage_started(logger, stage, f"PDF text replacement started for request_id: {request_id}")

    try:
        pdf_path = load_local_pdf(request_id)
        output_name = build_output_file_name(request_id)
        output_path = build_output_path(request_id)

        logger.info(
            f"Opening PDF for replacement. Input: {pdf_path}, Output: {output_path}",
            extra={"stage": stage, "status": "STARTED", "error": "None"}
        )

        doc = fitz.open(pdf_path)

        replaced_count = 0
        logs = []

        logger.info(
            f"Processing {len(payload.get('results', []))} replacement result item(s)",
            extra={"stage": stage, "status": "STARTED", "error": "None"}
        )

        for item in payload.get("results", []):
            old_text = item.get("old_text")
            new_text = item.get("new_text")
            page_no = item.get("matched_page_number", 1) - 1

            logger.info(
                f"Processing replacement item for page={page_no + 1}, old_text={old_text}, new_text={new_text}",
                extra={"stage": stage, "status": "STARTED", "error": "None"}
            )

            if not old_text or not new_text:
                logger.info(
                    f"Skipping replacement item because old_text or new_text is missing on page={page_no + 1}",
                    extra={"stage": stage, "status": "FAILURE", "error": "old_text or new_text missing"}
                )
                continue

            page = doc[page_no]
            blocks = page.get_text("blocks")

            logger.info(
                f"Fetched {len(blocks)} text block(s) from page={page_no + 1}",
                extra={"stage": stage, "status": "SUCCESS", "error": "None"}
            )

            for block in blocks:
                x0, y0, x1, y1, text, *_ = block

                if old_text in text:
                    try:
                        logger.info(
                            f"Matched old_text on page={page_no + 1}. Starting replacement",
                            extra={"stage": stage, "status": "STARTED", "error": "None"}
                        )

                        updated_line = text.replace(old_text, new_text)

                        # ✅ Expand rect (CRITICAL)
                        rect = fitz.Rect(
                            x0 - 2,
                            y0 - 1,
                            x1 + 10,
                            y1 + 3
                        )

                        # ✅ Remove old text
                        page.add_redact_annot(rect, fill=(1, 1, 1))
                        page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE)

                        # ✅ Insert new text
                        result = page.insert_textbox(
                            rect,
                            updated_line,
                            fontsize=9.3,
                            color=(0, 0, 0),
                            align=0
                        )

                        # ✅ Fallback
                        if result < 0:
                            logger.info(
                                f"Textbox insertion returned negative result on page={page_no + 1}. Using fallback insert_text",
                                extra={"stage": stage, "status": "STARTED", "error": "None"}
                            )
                            page.insert_text(
                                (rect.x0, rect.y1 - 2),
                                updated_line,
                                fontsize=9.3,
                                color=(0, 0, 0)
                            )

                        replaced_count += 1

                        logs.append({
                            "status": "REPLACED",
                            "old_text": old_text,
                            "new_text": new_text,
                            "page": page_no + 1
                        })

                        logger.info(
                            f"Replacement completed successfully on page={page_no + 1}",
                            extra={"stage": stage, "status": "SUCCESS", "error": "None"}
                        )

                        break

                    except Exception as e:
                        logs.append({
                            "status": "ERROR",
                            "error": str(e),
                            "page": page_no + 1
                        })

                        log_stage_failure(
                            logger,
                            stage,
                            f"Replacement failed on page={page_no + 1}",
                            e
                        )

        ensure_output_dir()

        logger.info(
            f"Saving updated PDF to output path: {output_path}",
            extra={"stage": stage, "status": "STARTED", "error": "None"}
        )

        doc.save(output_path)
        doc.close()

        log_stage_success(
            logger,
            stage,
            f"PDF replacement completed successfully. replaced_count={replaced_count}, output_path={output_path}"
        )

        return replaced_count, logs, output_name, output_path

    except Exception as e:
        log_stage_failure(logger, stage, f"PDF replacement failed for request_id: {request_id}", e)
        raise