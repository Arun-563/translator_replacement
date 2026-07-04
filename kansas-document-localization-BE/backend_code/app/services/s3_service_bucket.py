import boto3
from app.core.config import settings


# def get_s3_client():
#     return boto3.Session(
#         profile_name="temp-creds-tttt4"
#     ).client("s3")

def get_s3_client():
    return boto3.Session(
        profile_name=settings.AWS_PROFILE,
        region_name=settings.AWS_REGION
    ).client("s3")


def upload_file_to_s3(file_path, bucket, key, content_type=None):
    s3_client = get_s3_client()

    extra_args = {}
    if content_type:
        extra_args["ContentType"] = content_type

    try:
        if extra_args:
            s3_client.upload_file(file_path, bucket, key, ExtraArgs=extra_args)
        else:
            s3_client.upload_file(file_path, bucket, key)
    except Exception as e:
        raise Exception(f"Failed to upload {file_path} to {bucket}/{key}: {str(e)}")

    return f"s3://{bucket}/{key}"

