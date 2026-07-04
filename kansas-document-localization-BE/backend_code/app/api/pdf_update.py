from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
import json
from services.pdf_update_service import PDFUpdateService

router = APIRouter()
pdf_update_service = PDFUpdateService()

@router.post("/update-pdf")
async def update_pdf(
    file: UploadFile = File(...),
    updates_json: str = Form(...),
):
    try:
        updates = json.loads(updates_json)
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "updates_json must be valid JSON"}
        )

    if isinstance(updates, dict):
        updates = updates.get("updates", [])

    if not isinstance(updates, list):
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "updates_json must be a JSON list"}
        )

    try:
        result = await pdf_update_service.process_update(file=file, updates=updates)
        return JSONResponse(status_code=200, content={"success": True, "data": result})
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"success": False, "error": exc.detail})
    except Exception as exc:
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})
