# import os
# import shutil
# from pathlib import Path
# from typing import Optional

# from app.core.logger import logger


# from app.core.logger import (
#     get_logger,
#     log_stage_started,
#     log_stage_success,
#     log_stage_failure,
# )


# # ------------------------------------------------------------
# # Local storage configuration
# # ------------------------------------------------------------
# # This file is the LOCAL replacement for app.services.s3_service_bucket.
# # Put this file inside:
# # backend_code/app/local/local_s3_service_bucket.py
# #
# # It saves files into backend_code/static/... instead of S3.
# # ------------------------------------------------------------

# APP_DIR = Path(__file__).resolve().parents[1]          # backend_code/app
# BACKEND_DIR = APP_DIR.parent                           # backend_code
# STATIC_DIR = BACKEND_DIR / "static"

# UPLOAD_DIR = STATIC_DIR / "uploads"       # PDFs uploaded from API
# JSON_DIR = STATIC_DIR / "json"            # JSON generated from PDF extraction
# DOWNLOAD_DIR = STATIC_DIR / "downloades"  # keeping your folder spelling as requested


# def _ensure_required_dirs() -> None:
#     """Create local folders if they do not exist."""
#     for folder in (UPLOAD_DIR, JSON_DIR, DOWNLOAD_DIR):
#         folder.mkdir(parents=True, exist_ok=True)


# def _normalize_key(key: str) -> str:
#     """
#     Converts S3-style keys into safe local relative paths.

#     Examples:
#         upload_file/2026.pdf -> upload_file/2026.pdf
#         /json_file/a.json    -> json_file/a.json
#     """
#     key = str(key or "").replace("\\", "/").strip().lstrip("/")
#     if ".." in Path(key).parts:
#         raise ValueError(f"Unsafe key path is not allowed: {key}")
#     return key


# def resolve_local_path_from_key(key: str) -> Path:
#     """
#     Maps old S3 folder names to the new local folders.

#     Old S3 path              New local path
#     --------------------------------------------------
#     upload_file/file.pdf  -> static/uploads/file.pdf
#     json_file/file.json   -> static/json/file.json
#     ai_updated_file/x.pdf -> static/downloades/x.pdf
#     """
#     _ensure_required_dirs()
#     normalized_key = _normalize_key(key)
#     parts = normalized_key.split("/", 1)

#     if len(parts) == 1:
#         # Fallback: store unknown files by extension
#         filename = parts[0]
#         if filename.lower().endswith(".json"):
#             return JSON_DIR / filename
#         if filename.lower().endswith(".pdf"):
#             return UPLOAD_DIR / filename
#         return STATIC_DIR / filename

#     folder, filename = parts[0], parts[1]
#     filename = Path(filename).name

#     if folder == "upload_file":
#         return UPLOAD_DIR / filename
#     if folder == "json_file":
#         return JSON_DIR / filename
#     if folder == "ai_updated_file":
#         return DOWNLOAD_DIR / filename

#     return STATIC_DIR / folder / filename


# def upload_file_to_s3(
#     file_path: str,
#     bucket: Optional[str],
#     key: str,
#     content_type: Optional[str] = None,
# ) -> str:
#     """
#     Local replacement for S3 upload.

#     Kept the same function name/signature so existing service code can call it
#     without changing business logic.

#     Returns a local URI-like string instead of s3://bucket/key.
#     """
#     _ensure_required_dirs()

#     source_path = Path(file_path)
#     if not source_path.exists():
#         raise FileNotFoundError(f"Source file does not exist: {file_path}")

#     destination_path = resolve_local_path_from_key(key)
#     destination_path.parent.mkdir(parents=True, exist_ok=True)

#     shutil.copy2(source_path, destination_path)

#     logger.info("Local file saved: %s", destination_path)
#     return f"local://{destination_path.as_posix()}"


# def download_file_from_local(key: str, local_path: str) -> str:
#     """
#     Optional helper for later replacement/download flow.
#     Copies a file from static folders to a requested local path.
#     """
#     source_path = resolve_local_path_from_key(key)
#     if not source_path.exists():
#         raise FileNotFoundError(f"Local source file does not exist: {source_path}")

#     destination_path = Path(local_path)
#     destination_path.parent.mkdir(parents=True, exist_ok=True)
#     shutil.copy2(source_path, destination_path)

#     logger.info("Local file copied from %s to %s", source_path, destination_path)
#     return str(destination_path)

import os
import shutil
from pathlib import Path
from typing import Optional

from app.core.logger import (
    get_logger,
    log_stage_started,
    log_stage_success,
    log_stage_failure,
)

logger = get_logger(__name__)

# ------------------------------------------------------------
# Local storage configuration
# ------------------------------------------------------------
# This file is the LOCAL replacement for app.services.s3_service_bucket.
# Put this file inside:
# backend_code/app/local/local_s3_service_bucket.py
#
# It saves files into backend_code/static/... instead of S3.
# ------------------------------------------------------------

APP_DIR = Path(__file__).resolve().parents[1]          # backend_code/app
BACKEND_DIR = APP_DIR.parent                           # backend_code
STATIC_DIR = BACKEND_DIR / "static"

UPLOAD_DIR = STATIC_DIR / "uploads"       # PDFs uploaded from API
JSON_DIR = STATIC_DIR / "json"            # JSON generated from PDF extraction
DOWNLOAD_DIR = STATIC_DIR / "downloades"  # keeping your folder spelling as requested


def _ensure_required_dirs() -> None:
    """Create local folders if they do not exist."""
    stage = "LOCAL STORAGE SERVICE"
    log_stage_started(logger, stage, "Ensuring required local storage directories exist")
    try:
        for folder in (UPLOAD_DIR, JSON_DIR, DOWNLOAD_DIR):
            folder.mkdir(parents=True, exist_ok=True)

        log_stage_success(logger, stage, "Required local storage directories are ready")
    except Exception as e:
        log_stage_failure(logger, stage, "Failed to create required local storage directories", e)
        raise


def _normalize_key(key: str) -> str:
    """
    Converts S3-style keys into safe local relative paths.

    Examples:
        upload_file/2026.pdf -> upload_file/2026.pdf
        /json_file/a.json    -> json_file/a.json
    """
    stage = "LOCAL STORAGE SERVICE"
    log_stage_started(logger, stage, f"Normalizing storage key: {key}")
    try:
        key = str(key or "").replace("\\", "/").strip().lstrip("/")
        if ".." in Path(key).parts:
            raise ValueError(f"Unsafe key path is not allowed: {key}")

        log_stage_success(logger, stage, f"Storage key normalized successfully: {key}")
        return key
    except Exception as e:
        log_stage_failure(logger, stage, f"Failed to normalize storage key: {key}", e)
        raise


def resolve_local_path_from_key(key: str) -> Path:
    """
    Maps old S3 folder names to the new local folders.

    Old S3 path              New local path
    --------------------------------------------------
    upload_file/file.pdf  -> static/uploads/file.pdf
    json_file/file.json   -> static/json/file.json
    ai_updated_file/x.pdf -> static/downloades/x.pdf
    """
    stage = "LOCAL STORAGE SERVICE"
    log_stage_started(logger, stage, f"Resolving local path from key: {key}")
    try:
        _ensure_required_dirs()
        normalized_key = _normalize_key(key)
        parts = normalized_key.split("/", 1)

        if len(parts) == 1:
            # Fallback: store unknown files by extension
            filename = parts[0]
            if filename.lower().endswith(".json"):
                resolved_path = JSON_DIR / filename
                log_stage_success(logger, stage, f"Resolved local JSON path: {resolved_path}")
                return resolved_path
            if filename.lower().endswith(".pdf"):
                resolved_path = UPLOAD_DIR / filename
                log_stage_success(logger, stage, f"Resolved local PDF upload path: {resolved_path}")
                return resolved_path

            resolved_path = STATIC_DIR / filename
            log_stage_success(logger, stage, f"Resolved fallback static path: {resolved_path}")
            return resolved_path

        folder, filename = parts[0], parts[1]
        filename = Path(filename).name

        if folder == "upload_file":
            resolved_path = UPLOAD_DIR / filename
            log_stage_success(logger, stage, f"Resolved upload file path: {resolved_path}")
            return resolved_path

        if folder == "json_file":
            resolved_path = JSON_DIR / filename
            log_stage_success(logger, stage, f"Resolved JSON file path: {resolved_path}")
            return resolved_path

        if folder == "ai_updated_file":
            resolved_path = DOWNLOAD_DIR / filename
            log_stage_success(logger, stage, f"Resolved output PDF path: {resolved_path}")
            return resolved_path

        resolved_path = STATIC_DIR / folder / filename
        log_stage_success(logger, stage, f"Resolved generic static path: {resolved_path}")
        return resolved_path

    except Exception as e:
        log_stage_failure(logger, stage, f"Failed to resolve local path from key: {key}", e)
        raise


def upload_file_to_s3(
    file_path: str,
    bucket: Optional[str],
    key: str,
    content_type: Optional[str] = None,
) -> str:
    """
    Local replacement for S3 upload.

    Kept the same function name/signature so existing service code can call it
    without changing business logic.

    Returns a local URI-like string instead of s3://bucket/key.
    """
    stage = "LOCAL STORAGE SERVICE"
    log_stage_started(logger, stage, f"Uploading local file. Source: {file_path}, Key: {key}")

    try:
        _ensure_required_dirs()

        source_path = Path(file_path)
        if not source_path.exists():
            raise FileNotFoundError(f"Source file does not exist: {file_path}")

        destination_path = resolve_local_path_from_key(key)
        destination_path.parent.mkdir(parents=True, exist_ok=True)

        shutil.copy2(source_path, destination_path)

        logger.info(
            f"Local file saved: {destination_path}",
            extra={"stage": stage, "status": "SUCCESS", "error": "None"}
        )
        log_stage_success(logger, stage, f"Local upload completed successfully: {destination_path}")
        return f"local://{destination_path.as_posix()}"

    except Exception as e:
        log_stage_failure(logger, stage, f"Local upload failed for source: {file_path}, key: {key}", e)
        raise


def download_file_from_local(key: str, local_path: str) -> str:
    """
    Optional helper for later replacement/download flow.
    Copies a file from static folders to a requested local path.
    """
    stage = "LOCAL STORAGE SERVICE"
    log_stage_started(logger, stage, f"Downloading local file. Key: {key}, Destination: {local_path}")

    try:
        source_path = resolve_local_path_from_key(key)
        if not source_path.exists():
            raise FileNotFoundError(f"Local source file does not exist: {source_path}")

        destination_path = Path(local_path)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination_path)

        logger.info(
            f"Local file copied from {source_path} to {destination_path}",
            extra={"stage": stage, "status": "SUCCESS", "error": "None"}
        )
        log_stage_success(logger, stage, f"Local file download completed successfully: {destination_path}")
        return str(destination_path)

    except Exception as e:
        log_stage_failure(logger, stage, f"Local file download failed for key: {key}", e)
        raise