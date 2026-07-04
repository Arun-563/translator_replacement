from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import JSONResponse
import traceback

from app.local.pdf_translation_service import process_pdf_translation_request

router = APIRouter()

@router.post("/translate-pdf")
async def translate_pdf(
    request: Request,
    file: UploadFile = File(...),
    source_language: str = Form("English"),
    target_language: str = Form("Spanish"),
):
    """
    PDF Translation API.
    Keeps the existing /upload-pdf replacement flow untouched.

    UI sends only:
    - pdf file
    - source_language: English
    - target_language: Spanish
    """
    try:
        if source_language.strip().lower() != "english":
            raise HTTPException(status_code=400, detail="Only English source language is supported in V1")

        if target_language.strip().lower() != "spanish":
            raise HTTPException(status_code=400, detail="Only Spanish target language is supported in V1")

        result = await process_pdf_translation_request(
            file=file,
            source_language="English",
            target_language="Spanish",
        )

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "PDF translated successfully",
                "translation_result": result,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
