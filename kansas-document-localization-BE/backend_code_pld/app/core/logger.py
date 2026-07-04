# import logging

# logging.basicConfig(level=logging.INFO)

# logger = logging.getLogger("doctranslate-ai-agent")
import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional


# Create logs directory if not exists
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "..", "static", "logs")
os.makedirs(LOG_DIR, exist_ok=True)


# Log file format: dd_mm_yyyy_hh_mm
timestamp = datetime.now().strftime("%d_%m_%Y_%H_%M")
LOG_FILE = os.path.join(LOG_DIR, f"app_{timestamp}.log")


class StageFormatter(logging.Formatter):
    """
    Formatter used for both console and file logs.

    Required output format:
        STAGE: <stage>
        STATUS: <status>
        ERROR: <error>
    """

    def format(self, record):
        stage = getattr(record, "stage", "GENERAL")
        status = getattr(record, "status", record.levelname)
        error = getattr(record, "error", None)
        message = record.getMessage()

        if error is None:
            error = "None"

        return (    
            "================================================="
            f"STAGE: {stage}"
            f"STATUS: {status}"
            f"MESSAGE: {message}"
            f"ERROR: {error}"
            "=================================================="
        )


def get_logger(name: str) -> logging.Logger:
    """
    Create and return a configured logger.
    Logs are printed to console and saved to timestamp-based file.
    """

    logger = logging.getLogger(name)

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    formatter = StageFormatter()

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)

    # File handler
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


def log_stage_started(logger: logging.Logger, stage: str, message: str):
    logger.info(
        message,
        extra={
            "stage": stage,
            "status": "STARTED",
            "error": "None"
        }
    )


def log_stage_success(logger: logging.Logger, stage: str, message: str):
    logger.info(
        message,
        extra={
            "stage": stage,
            "status": "SUCCESS",
            "error": "None"
        }
    )


def log_stage_failure(
    logger: logging.Logger,
    stage: str,
    message: str,
    error: Optional[Exception] = None
):
    logger.error(
        message,
        extra={
            "stage": stage,
            "status": "FAILURE",
            "error": str(error) if error else "Unknown error"
        }
    ) 