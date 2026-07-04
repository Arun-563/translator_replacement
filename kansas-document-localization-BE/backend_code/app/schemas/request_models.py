from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class UpdateInstruction(BaseModel):
    language: str
    page_number: int
    section_name: str
    old_text: str
    new_text: str
    json_file: str
    user_instructions: Optional[str] = ""

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str):
        value = value.strip().lower()
        if value not in {"english", "spanish"}:
            raise ValueError("language must be 'english' or 'spanish'")
        return value

    @field_validator("section_name", "old_text", "new_text", "json_file")
    @classmethod
    def validate_non_empty(cls, value: str):
        if not value or not value.strip():
            raise ValueError("field cannot be empty")
        return value.strip()


class UpdateAnalysisRequest(BaseModel):
    request_id: str = Field(..., description="Unique request id")
    instructions: List[UpdateInstruction]

    @field_validator("instructions")
    @classmethod
    def validate_instructions(cls, value):
        if not value:
            raise ValueError("instructions cannot be empty")
        return value