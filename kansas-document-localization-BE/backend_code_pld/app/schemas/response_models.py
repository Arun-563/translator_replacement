from typing import List, Optional
from pydantic import BaseModel


class MatchResult(BaseModel):
    matched_segment_id: str
    matched_page_number: int
    confidence: float
    layout_risk: str
    warnings: List[str] = []


class ErrorResult(BaseModel):
    page_number: Optional[int] = None
    section_name: Optional[str] = None
    error_code: str
    error_message: str


class UpdateAnalysisResponse(BaseModel):
    request_url: Optional[str] = None
    request_id: str
    status: str
    results: List[MatchResult] = []
    errors: List[ErrorResult] = []