from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import FileResponse
from app.services.translation_service import TranslationService

router = APIRouter()
translation_service = TranslationService()

@router.post("/convert")
async def convert_document(
    file: UploadFile = File(...),
    source_language: str = Form(...),
    target_language: str = Form(...),
    conversion_type: str = Form("full")
):
    output_path = await translation_service.process_document(
        file=file,
        source_language=source_language,
        target_language=target_language,
        conversion_type=conversion_type
    )
    print("test")

    return FileResponse(
        path=output_path,
        filename=output_path.split("/")[-1],
        media_type="application/octet-stream"
    )