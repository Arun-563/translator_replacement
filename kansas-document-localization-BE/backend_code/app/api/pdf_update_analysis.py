# from fastapi import APIRouter
# from app.schemas.request_models import UpdateAnalysisRequest
# from app.schemas.response_models import UpdateAnalysisResponse
# from app.services.orchestrator_service import UpdateAnalysisOrchestrator

# router = APIRouter(prefix="/pdf-update", tags=["PDF Update Analysis"])
# orchestrator = UpdateAnalysisOrchestrator()


# FastAPI receives HTTP request
# Converts JSON to Python object
# Passes it to payload.

# @router.post("/analyze", response_model=UpdateAnalysisResponse)
# def analyze_pdf_update(payload: UpdateAnalysisRequest):
#     return orchestrator.process(payload)


# payload = {
#     "request_id": "REQ-LOCAL-001",
#     "instructions": [
#         {
#             "language": "english",
#             "page_number": 2,
#             "section_name": "Declaration",
#             "old_text": "I hereby declare that all information provided",
#             "new_text": "I confirm all information is correct",
#             "json_file": "2026-06-16_16_18",
#             "user_instructions": ""
#         }
#     ]
# }

# app/api/pdf_update_analysis.py

from fastapi import APIRouter, BackgroundTasks
from app.local.orchestrator_service import OrchestratorService

router = APIRouter()

@router.post("/process")
def process_pdf_update(payload: dict, background_tasks: BackgroundTasks):
    
    print("Payload received:", payload)

    orchestrator = OrchestratorService()

    # ✅ Extract instructions list
    if "instructions" not in payload:
        return {
            "status": "FAILED",
            "errors": ["Invalid payload: 'instructions' missing"]
        }

    instructions = payload["instructions"]

    # ✅ Call your existing logic
    response = orchestrator.process(instructions, background_tasks)

    return response