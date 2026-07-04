import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend_code"))

from app.services.s3_service import S3Service


# Initialize service
s3 = S3Service()

# Step 1: give filename manually
json_file = "2026-06-16_16_18"

# Step 2: convert to S3 key
json_key = s3.build_json_key(json_file)

print("Bucket:", "kansas-document-files")
print("Key:", json_key)

print(" Checking S3 KEY:", json_key)

# Step 3: check existence
exists = s3.exists(json_key)

if exists:
    print(" SUCCESS: File EXISTS in S3")
else:
    print(" ERROR: File DOES NOT exist in S3")