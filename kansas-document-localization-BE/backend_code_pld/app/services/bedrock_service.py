import json
import boto3
from app.core.config import settings


class BedrockService:

    def __init__(self):
        if settings.AWS_PROFILE:
            session = boto3.Session(
                profile_name=settings.AWS_PROFILE,
                region_name=settings.AWS_REGION
            )
        else:
            session = boto3.Session(
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                aws_session_token=settings.AWS_SESSION_TOKEN,
                region_name=settings.AWS_REGION
            )

        self.client = session.client("bedrock-runtime")
        self.model_id = settings.BEDROCK_MODEL_ID

    def invoke_json_prompt(self, prompt: str) -> dict:
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1200,
            "temperature": 0,
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}]
                }
            ]
        }

        print("🔹 Sending prompt to Bedrock")

        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json"
        )

        raw = json.loads(response["body"].read())
        text = raw["content"][0]["text"]

        print("🔹 Bedrock response received")

        try:
            return json.loads(text)
        except Exception:
            print("⚠️ Invalid JSON returned:")
            print(text)
            raise

    def invoke_raw_prompt(self, prompt: str) -> str:
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1200,
            "temperature": 0,
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}]
                }
            ]
        }

        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json"
        )

        raw = json.loads(response["body"].read())
        return raw["content"][0]["text"]
    