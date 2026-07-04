import json
import os
import boto3
from botocore.exceptions import ClientError
from app.core.config import settings
from app.core.logger import logger


class S3Service:
    # def __init__(self):
    #     self.client = boto3.client(
    # "s3",
    # region_name=settings.AWS_REGION,
    # aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    # aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY

    def __init__(self):
        if settings.AWS_PROFILE:
            session = boto3.Session(profile_name=settings.AWS_PROFILE, region_name=settings.AWS_REGION)
            self.client = session.client("s3")
        else:
            s3_kwargs = {"region_name": settings.AWS_REGION}
            if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
                s3_kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
                s3_kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
            if settings.AWS_SESSION_TOKEN:
                s3_kwargs["aws_session_token"] = settings.AWS_SESSION_TOKEN

            self.client = boto3.client("s3", **s3_kwargs)
            # self.client = session.client("s3")


    # Boto3 reads credentials from env variables if not provided explicitly


    # def build_json_key(self, json_file: str) -> str:
    #     json_file = json_file.strip()
    #     if not json_file.endswith(".json"):
    #         json_file = f"{json_file}.json"
    #     return f"{settings.S3_PREFIX}{json_file}"

    
    def build_json_key(self, json_file: str) -> str:
        json_file = json_file.strip()

        if not json_file.endswith(".json"):
            json_file = f"{json_file}.json"

        prefix = settings.S3_PREFIX.strip("/")
        return f"{prefix}/{json_file}" if prefix else json_file

        

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(
                Bucket=settings.S3_BUCKET,
                Key=key
            )
            return True

        except ClientError as e:
            error_code = e.response["Error"]["Code"]

            if error_code in ("404", "NoSuchKey", "NotFound"):
                print("File definitely does NOT exist")
                return False

            elif error_code in ("403", "AccessDenied", "UnauthorizedOperation", "AccessDeniedException", "AllAccessDisabled"):
                print("Access denied → File may exist but not accessible")
                logger.error("S3 head_object access denied for Bucket=%s Key=%s: %s", settings.S3_BUCKET, key, error_code)
                return False

            else:
                raise

    def load_json(self, key: str) -> dict:
        obj = self.client.get_object(Bucket=settings.S3_BUCKET, Key=key)
        content = obj["Body"].read().decode("utf-8")
        return json.loads(content) 
    

    def download_file(self, key: str, local_path: str):
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            self.client.download_file(
                settings.S3_BUCKET,
                key,
                local_path
            )

            logger.info(f"Downloaded file to {local_path}")
            return local_path

        except Exception as e:
            logger.error(f"Download failed for {key}: {str(e)}")
            raise
