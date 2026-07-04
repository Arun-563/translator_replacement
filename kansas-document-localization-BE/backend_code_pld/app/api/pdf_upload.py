from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import JSONResponse
import json
import traceback
import os

from app.local.local_pdf_extraction_service import process_pdf_request
from app.local.orchestrator_service import OrchestratorService
from app.local.pdf_replace import replace_text

router = APIRouter()

# ✅ IMPORTANT: Absolute downloads directory (SAME as static mount)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOWNLOADS_DIR = os.path.join(BASE_DIR, "static", "downloads")

# ✅ Ensure directory exists
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

print("✅ DOWNLOADS_DIR:", DOWNLOADS_DIR)


@router.post("/upload-pdf")
async def upload_pdf(
    request: Request,
    file: UploadFile = File(...),
    payload: str = Form(...)
):

    # --------------------------------------------------
    # STEP 0: Validate uploaded file
    # --------------------------------------------------
    if not file:
        raise HTTPException(status_code=400, detail="File is required")

    # --------------------------------------------------
    # STEP 1: Parse payload string
    # --------------------------------------------------
    try:
        payload_obj = json.loads(payload)
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "payload must be valid JSON"
            }
        )

    # --------------------------------------------------
    # STEP 2: Validate payload format
    # --------------------------------------------------
    if not isinstance(payload_obj, list):
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "payload must be a JSON array"
            }
        )

    try:
        # --------------------------------------------------
        # STEP 3: Extract PDF → JSON
        # --------------------------------------------------
        result = await process_pdf_request(
            file=file,
            payload=payload_obj
        )

        print("✅ PDF extraction completed")

        # --------------------------------------------------
        # STEP 4: Get downstream payload
        # --------------------------------------------------
        downstream_payload = result.get("downstream_payload")

        if not downstream_payload:
            raise Exception("downstream_payload not returned")

        instructions = downstream_payload.get("instructions")

        if not instructions or not isinstance(instructions, list):
            raise Exception("instructions missing or invalid")

        print("➡️ Calling Orchestrator")

        # --------------------------------------------------
        # STEP 5: Call Orchestrator
        # --------------------------------------------------
        orchestrator = OrchestratorService()
        update_response = orchestrator.process(instructions)

        print("✅ Orchestrator completed")

        # --------------------------------------------------
        # STEP 6: Replace Text
        # --------------------------------------------------
        replace_output = None

        if (
            update_response
            and update_response.get("status") == "SUCCESS"
            and update_response.get("results")
        ):
            print("➡️ Calling replace_text()...")

            request_id = update_response.get("request_id")

            if not request_id:
                raise Exception("request_id missing")

            replaced_count, logs, output_file_name, output_path = replace_text(
                request_id=request_id,
                payload=update_response
            )

            # ✅ CRITICAL FIX — ensure file is in correct static folder
            correct_output_path = os.path.join(DOWNLOADS_DIR, output_file_name)

            if output_path != correct_output_path:
                print("⚠️ Moving file to correct static directory")

                if os.path.exists(output_path):
                    os.rename(output_path, correct_output_path)

            # ✅ Final check
            print("✅ Final file location:", correct_output_path)
            print("✅ File exists:", os.path.exists(correct_output_path))

            # ✅ URL creation
            base_url = str(request.base_url).rstrip("/")
            output_url = f"{base_url}/downloads/{output_file_name}"

            replace_output = {
                "replaced_count": replaced_count,
                "logs": logs,
                "output_file_name": output_file_name,
                "output_url": output_url
            }

            print("✅ RESPONSE URL:", output_url)

        else:
            print("⚠️ No matches found")

        # --------------------------------------------------
        # STEP 7: Return response
        # --------------------------------------------------
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "PDF processed successfully",
                "extraction": result,
                "update_result": update_response,
                "replacement_result": replace_output
            }
        )

    except HTTPException as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": exc.detail
            }
        )

    except Exception as exc:
        print("❌ ERROR:")
        print(traceback.format_exc())

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(exc)
            }
        )