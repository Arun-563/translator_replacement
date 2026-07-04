# LOADS all variables from .env into environment
import os
from dotenv import load_dotenv

load_dotenv(override=True)

class Settings:
    # AWS_PROFILE = os.getenv("AWS_PROFILE")
    # AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    # AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    # AWS_SESSION_TOKEN = os.getenv("AWS_SESSION_TOKEN")
    # AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    
    OLLAMA_BASE_URL = os.getenv( #changed
        "OLLAMA_BASE_URL",       ##
        "http://localhost:11434" ##
    )

    OLLAMA_MODEL_ID = os.getenv( ##
        "OLLAMA_MODEL_ID",       ##
        "qwen2.5:3b"            ##
        )

    OLLAMA_VALIDATION_MODEL_ID = os.getenv( ##
        "OLLAMA_VALIDATION_MODEL_ID",       ##
        "qwen2.5:14b"            ##
        )
    STATIC_JSON_DIR = "backend_code/static/json" ##

    OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", 1200)) ##


    # S3_BUCKET = os.getenv("S3_BUCKET")
    # S3_JSON_PREFIX = os.getenv("S3_JSON_PREFIX", "json_file")
    # LOCAL_DOWNLOAD_DIR = os.getenv("LOCAL_DOWNLOAD_DIR", "downloads")
    NEXT_TEAM_API_URL = os.getenv("NEXT_TEAM_API_URL", "")

    # BEDROCK_MODEL_ID = os.getenv(
    #     "BEDROCK_MODEL_ID",
    #     "anthropic.claude-3-sonnet-20240229-v1:0"
    # )
settings = Settings()