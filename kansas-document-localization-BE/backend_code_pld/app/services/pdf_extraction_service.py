import os
import tempfile
from datetime import datetime

from fastapi import UploadFile, HTTPException

from app.processors.pdf_processor import process_pdf
from app.services.s3_service_bucket import upload_file_to_s3
from app.services.bedrock_agent_service import send_payload_to_bedrock_agent

BUCKET_NAME = "kansas-document-files"


async def process_pdf_request(file: UploadFile, payload: list):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    if not isinstance(payload, list) or len(payload) == 0:
        raise HTTPException(status_code=400, detail="Payload must be a non-empty list")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")

    pdf_file_name = f"{timestamp}.pdf"
    json_file_name = f"{timestamp}.json"

    pdf_s3_key = f"upload_file/{pdf_file_name}"
    json_s3_key = f"json_file/{json_file_name}"

    temp_pdf_path = None
    temp_json_path = None

    try:
        # 1. Save uploaded PDF temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            content = await file.read()
            if not content:
                raise HTTPException(status_code=400, detail="Uploaded file is empty")

            temp_pdf.write(content)
            temp_pdf_path = temp_pdf.name

        # 2. Upload renamed PDF to S3
        pdf_s3_uri = upload_file_to_s3(
            file_path=temp_pdf_path,
            bucket=BUCKET_NAME,
            key=pdf_s3_key,
            content_type="application/pdf"
        )

        # 3. Generate JSON using extracted PDF
        temp_json_path = os.path.join(tempfile.gettempdir(), json_file_name)

        process_pdf(
            input_pdf_path=temp_pdf_path,
            output_json_path=temp_json_path
        )

        if not os.path.exists(temp_json_path):
            raise HTTPException(status_code=500, detail="JSON file was not created")

        # 4. Upload JSON to S3
        json_s3_uri = upload_file_to_s3(
            file_path=temp_json_path,
            bucket=BUCKET_NAME,
            key=json_s3_key,
            content_type="application/json"
        )

        # 5. Build downstream payload for Bedrock agent
        instructions = []
        for item in payload:
            instructions.append({
                "language": item.get("language", ""),
                "page_number": item.get("page_number"),
                "section_name": item.get("section_name", ""),
                "old_text": item.get("old_text", ""),
                "new_text": item.get("new_text", ""),
                "json_file": json_file_name,   # send full json filename
                "user_instructions": item.get("user_instructions", "")
            })

        downstream_payload = {
            "request_id": json_file_name,   # full json filename
            "instructions": instructions
        }

        # 6. Call Bedrock agent API
        bedrock_agent_response = await send_payload_to_bedrock_agent(downstream_payload)

        # 7. Return combined response to FE
        return {
            "message": "Success",
            "pdf_s3": pdf_s3_uri,
            "json_s3": json_s3_uri,
            "pdf_name": pdf_file_name,
            "json_name": json_file_name,
            "downstream_payload": downstream_payload,
            "bedrock_agent_response": bedrock_agent_response
        }

    finally:
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)

        if temp_json_path and os.path.exists(temp_json_path):
            os.remove(temp_json_path)

# import os
# import tempfile
# from datetime import datetime

# from fastapi import UploadFile, HTTPException

# from app.processors.pdf_processor import process_pdf
# from app.services.s3_service_bucket import upload_file_to_s3


# BUCKET_NAME = "kansas-document-files"


# async def process_pdf_request(file: UploadFile, payload: list):

#     if not file.filename.lower().endswith(".pdf"):
#         raise HTTPException(status_code=400, detail="Only PDF files allowed")

#     # ✅ timestamp naming
#     timestamp = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")

#     pdf_file_name = f"{timestamp}.pdf"
#     json_file_name = f"{timestamp}.json"

#     # ✅ S3 paths
#     pdf_s3_key = f"upload_file/{pdf_file_name}"
#     json_s3_key = f"json_file/{json_file_name}"


#     # ✅ save temp pdf
#     with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
#         content = await file.read()

#         if not content:
#             raise HTTPException(status_code=400, detail="Empty file")

#         temp_pdf.write(content)
#         temp_pdf_path = temp_pdf.name

#     temp_json_path = os.path.join(tempfile.gettempdir(), json_file_name)

#     try:
#         # ✅ Upload renamed PDF
#         pdf_s3_uri = upload_file_to_s3(
#             file_path=temp_pdf_path,
#             bucket=BUCKET_NAME,
#             key=pdf_s3_key,
#             content_type="application/pdf"
#         )

#         # ✅ Process PDF
#         temp_json_path = os.path.join(tempfile.gettempdir(), json_file_name)

#         process_pdf(
#             input_pdf_path=temp_pdf_path,
#             output_json_path=temp_json_path,
#             payload=payload
#         )

#         # ✅ Upload JSON
#         json_s3_uri = upload_file_to_s3(
#             file_path=temp_json_path,
#             bucket=BUCKET_NAME,
#             key=json_s3_key,
#             content_type="application/json"
#         )

#     finally:
#         os.remove(temp_pdf_path)
#         if os.path.exists(temp_json_path):
#             os.remove(temp_json_path)

#     return {
#         "message": "Success",
#         "pdf_s3": pdf_s3_uri,
#         "json_s3": json_s3_uri,
#         "pdf_name": pdf_file_name,
#         "json_name": json_file_name
#     } 