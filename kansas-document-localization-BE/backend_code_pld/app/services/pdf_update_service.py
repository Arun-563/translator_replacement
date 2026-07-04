# import os
# import re
# import json
# import boto3
# from datetime import datetime, timedelta
# from difflib import SequenceMatcher
# from fastapi import HTTPException
# from utils.file_handler import save_upload_file
# from processors.pdf_processor import PDFProcessor
# from services.bedrock_service import BedrockService
# from services.layout_validator import LayoutValidator
# from core.config import settings
# from prompts.pdf_update_prompts import (
#     SECTION_IDENTIFICATION_SYSTEM_PROMPT,
#     TEXT_MATCH_SYSTEM_PROMPT,
#     LAYOUT_RISK_SYSTEM_PROMPT,
# )


# class PDFUpdateService:
#     def __init__(self):
#         self.processor = PDFProcessor()
#         self.layout_validator = LayoutValidator()
#         self.bedrock_service = BedrockService()
#         self.s3_client = boto3.client("s3", region_name=settings.AWS_REGION)
#         self.bucket = settings.S3_BUCKET
#         self.input_prefix = settings.S3_INPUT_PREFIX
#         self.output_prefix = settings.S3_OUTPUT_PREFIX

#     async def process_update(self, file, updates: list) -> dict:
#         if not updates:
#             raise HTTPException(status_code=400, detail="Updates payload cannot be empty")

#         self._validate_pdf_file(file)

#         first_update = updates[0]
#         json_file = first_update.get("json_file")
#         user_instructions = first_update.get("user_instructions", "")

#         if not json_file:
#             raise HTTPException(status_code=400, detail="json_file is required in the update payload")

#         source_json_key = self._resolve_source_json_key(json_file)
#         self._validate_json_file_name(source_json_key)

#         if not self._s3_key_exists(source_json_key):
#             raise HTTPException(
#                 status_code=404,
#                 detail=f"Required JSON file was not found in S3: s3://{self.bucket}/{source_json_key}"
#             )

#         input_path = await save_upload_file(file)
#         timestamp = datetime.now().strftime("%Y%m%d_%H%M")
#         s3_folder = f"{self.input_prefix}/{timestamp}"

#         segments = self.processor.extract_text(input_path)

#         results = []
#         replacements = []

#         for update in updates:
#             parsed_update = self._parse_update_instruction(update)
#             matched_segment, match_info = self._content_matching_agent(parsed_update, segments)
#             layout_risk = self._layout_analysis_agent(parsed_update, matched_segment)

#             replacements.append({
#                 "page_number": matched_segment["page_number"],
#                 "old_text": parsed_update["old_text"],
#                 "new_text": parsed_update["new_text"],
#                 "segment_id": matched_segment["segment_id"],
#             })

#             results.append({
#                 "matched_segment_id": matched_segment["segment_id"],
#                 "matched_page_number": matched_segment["page_number"],
#                 "confidence": round(match_info.get("confidence", 0.0), 2),
#                 "layout_risk": layout_risk,
#             })

#         output_path = self.processor.rebuild_document(
#             input_path=input_path,
#             replacements=replacements,
#             output_dir=settings.OUTPUT_DIR,
#         )

#         updated_pdf_key = f"{s3_folder}/updated_{os.path.basename(output_path)}"
#         self._upload_file_to_s3(output_path, updated_pdf_key)

#         result_payload = {
#             "request_url": self._get_presigned_url(updated_pdf_key),
#             "results": results,
#             "analysis": {
#                 "bedrock_section_summary": self._summarize_section_analysis(updates, segments),
#                 "bedrock_layout_summary": self._summarize_layout_analysis(updates),
#             },
#         }

#         return result_payload

#     def _validate_pdf_file(self, file):
#         if not file.filename.lower().endswith(".pdf"):
#             raise HTTPException(status_code=400, detail="Only one PDF file is accepted.")

#     def _validate_update_entry(self, update):
#         required_fields = ["language", "page_number", "section_name", "old_text", "new_text"]
#         missing = [field for field in required_fields if field not in update or not update[field]]
#         if missing:
#             raise HTTPException(
#                 status_code=400,
#                 detail=f"Update entry is missing required fields: {', '.join(missing)}"
#             )

#         if update["old_text"].strip().lower() == update["new_text"].strip().lower():
#             raise HTTPException(
#                 status_code=400,
#                 detail="old_text and new_text must differ for an update."
#             )

#     def _parse_update_instruction(self, update: dict) -> dict:
#         parsed = {
#             "language": str(update.get("language", "")).strip(),
#             "page_number": int(update.get("page_number", 0)),
#             "section_name": str(update.get("section_name", "")).strip(),
#             "old_text": str(update.get("old_text", "")).strip(),
#             "new_text": str(update.get("new_text", "")).strip(),
#             "json_file": str(update.get("json_file", "")).strip(),
#             "user_instructions": str(update.get("user_instructions", "")).strip(),
#         }
#         self._validate_update_entry(parsed)
#         return parsed

#     def _content_matching_agent(self, update: dict, segments: list) -> tuple:
#         matched_segment = self._find_matching_segment(
#             segments,
#             update["page_number"],
#             update["old_text"],
#             update["section_name"],
#         )

#         if matched_segment is None:
#             raise HTTPException(
#                 status_code=400,
#                 detail=(
#                     f"Old text not found on page {update['page_number']} "
#                     f"for section '{update['section_name']}'."
#                 )
#             )

#         match_info = self._evaluate_text_match(update["old_text"], matched_segment["text"])
#         if not match_info.get("matched", False):
#             raise HTTPException(
#                 status_code=400,
#                 detail="Old text does not sufficiently match the PDF content."
#             )

#         section_info = self._section_identification_agent(update, matched_segment)
#         if section_info.get("section_match") != "YES":
#             raise HTTPException(
#                 status_code=400,
#                 detail=f"Section identification failed for section '{update['section_name']}'."
#             )

#         return matched_segment, match_info

#     def _layout_analysis_agent(self, update: dict, matched_segment: dict) -> str:
#         layout_risk = self.layout_validator.check_risk(
#             original_text=update["old_text"],
#             translated_text=update["new_text"],
#             segment=matched_segment,
#         )
#         return layout_risk.upper()

#     def _validate_json_file_name(self, json_file: str):
#         basename = os.path.basename(json_file)
#         if basename.lower().endswith(".json"):
#             basename = basename[:-5]

#         if not re.match(r"^\d{8}[_-]\d{4}$", basename):
#             raise HTTPException(
#                 status_code=400,
#                 detail="json_file must use a filename format like YYYYMMDD_HHMM or YYYYMMDD-HHMM"
#             )

#         now = datetime.now()
#         valid_names = {
#             now.strftime("%Y%m%d_%H%M"),
#             now.strftime("%Y%m%d-%H%M"),
#             (now - timedelta(minutes=1)).strftime("%Y%m%d_%H%M"),
#             (now - timedelta(minutes=1)).strftime("%Y%m%d-%H%M"),
#             (now + timedelta(minutes=1)).strftime("%Y%m%d_%H%M"),
#             (now + timedelta(minutes=1)).strftime("%Y%m%d-%H%M"),
#         }

#         if basename not in valid_names:
#             expected = now.strftime("%Y%m%d_%H%M")
#             raise HTTPException(
#                 status_code=400,
#                 detail=(
#                     f"json_file basename must match today's date and time in format {expected} "
#                     "(allowing +/- 1 minute)."
#                 )
#             )

#     def _evaluate_text_match(self, expected_text: str, segment_text: str) -> dict:
#         prompt = self._build_text_matching_prompt(expected_text, segment_text)
#         try:
#             response = self.bedrock_service.generate_text(
#                 system_prompt=TEXT_MATCH_SYSTEM_PROMPT,
#                 user_prompt=prompt,
#             )
#             parsed = json.loads(response)
#             return {
#                 "matched": parsed.get("matched", False),
#                 "confidence": float(parsed.get("confidence", 0.0)),
#                 "normalized_segment_text": parsed.get("normalized_segment_text", segment_text),
#             }
#         except Exception:
#             confidence = self._compute_confidence(expected_text, segment_text)
#             return {
#                 "matched": confidence >= 0.7,
#                 "confidence": confidence,
#                 "normalized_segment_text": segment_text,
#             }

#     def _section_identification_agent(self, update: dict, matched_segment: dict) -> dict:
#         prompt = self._build_section_identification_prompt(update, matched_segment)
#         try:
#             response = self.bedrock_service.generate_text(
#                 system_prompt=SECTION_IDENTIFICATION_SYSTEM_PROMPT,
#                 user_prompt=prompt,
#             )
#             return json.loads(response)
#         except Exception:
#             return {"section_match": "YES", "reason": "fallback accepted"}

#     def _build_text_matching_prompt(self, expected_text: str, segment_text: str) -> str:
#         return (
#             f"Expected old text: {expected_text}\n"
#             f"Candidate segment text: {segment_text}\n"
#             "Please compare them and return JSON with matched, confidence, and normalized_segment_text."
#         )

#     def _build_section_identification_prompt(self, update: dict, matched_segment: dict) -> str:
#         return (
#             f"Section name: {update['section_name']}\n"
#             f"Page number: {update['page_number']}\n"
#             f"Candidate segment text: {matched_segment['text']}\n"
#             "Does this segment belong to the requested section? Return JSON with section_match and reason."
#         )

#     def _build_layout_prompt(self, updates):
#         pieces = [
#             f"Old text: {update['old_text']}\nNew text: {update['new_text']}\n" for update in updates
#         ]
#         return "\n".join(pieces)

#     def _resolve_source_json_key(self, json_file: str) -> str:
#         normalized = json_file.strip()
#         if normalized.startswith("s3://"):
#             normalized = normalized.replace(f"s3://{self.bucket}/", "", 1)
#         if normalized.startswith("/"):
#             normalized = normalized[1:]
#         if normalized.endswith(".json"):
#             return normalized
#         return f"{self.input_prefix}/{normalized}.json"

#     def _s3_key_exists(self, key: str) -> bool:
#         try:
#             self.s3_client.head_object(Bucket=self.bucket, Key=key)
#             return True
#         except self.s3_client.exceptions.NoSuchKey:
#             return False
#         except Exception:
#             return False

#     def _upload_file_to_s3(self, local_path: str, s3_key: str):
#         self.s3_client.upload_file(local_path, self.bucket, s3_key)

#     def _get_presigned_url(self, s3_key: str) -> str:
#         try:
#             return self.s3_client.generate_presigned_url(
#                 ClientMethod="get_object",
#                 Params={"Bucket": self.bucket, "Key": s3_key},
#                 ExpiresIn=3600,
#             )
#         except Exception:
#             return f"s3://{self.bucket}/{s3_key}"

#     def _find_matching_segment(self, segments, page_number, old_text, section_name):
#         normalized_old = old_text.strip().lower()
#         first_match = None
#         for segment in segments:
#             if segment["page_number"] != page_number:
#                 continue
#             if normalized_old in segment["text"].strip().lower():
#                 first_match = segment
#                 break

#         if first_match:
#             return first_match
#         return None

#     def _validate_json_file_name(self, json_file: str):
#         basename = os.path.basename(json_file)
#         if basename.lower().endswith(".json"):
#             basename = basename[:-5]

#         if not re.match(r"^\d{8}[_-]\d{4}$", basename):
#             raise HTTPException(
#                 status_code=400,
#                 detail="json_file must use a filename format like YYYYMMDD_HHMM or YYYYMMDD-HHMM"
#             )

#         now = datetime.now()
#         valid_names = {
#             now.strftime("%Y%m%d_%H%M"),
#             now.strftime("%Y%m%d-%H%M"),
#             (now - timedelta(minutes=1)).strftime("%Y%m%d_%H%M"),
#             (now - timedelta(minutes=1)).strftime("%Y%m%d-%H%M"),
#             (now + timedelta(minutes=1)).strftime("%Y%m%d_%H%M"),
#             (now + timedelta(minutes=1)).strftime("%Y%m%d-%H%M"),
#         }

#         if basename not in valid_names:
#             expected = now.strftime("%Y%m%d_%H%M")
#             raise HTTPException(
#                 status_code=400,
#                 detail=(
#                     f"json_file basename must match today's date and time in format {expected} "
#                     "(allowing +/- 1 minute)."
#                 )
#             )

#     def _compute_confidence(self, expected_text: str, segment_text: str) -> float:
#         matcher = SequenceMatcher(None, expected_text.strip().lower(), segment_text.strip().lower())
#         return matcher.ratio()

#     def _summarize_section_analysis(self, updates, segments):
#         try:
#             prompt = self._build_section_prompt(updates, segments)
#             return self.bedrock_service.generate_text(
#                 system_prompt=SECTION_IDENTIFICATION_SYSTEM_PROMPT,
#                 user_prompt=prompt,
#             )
#         except Exception:
#             return "Section analysis summary not available."

#     def _summarize_layout_analysis(self, updates):
#         try:
#             prompt = self._build_layout_prompt(updates)
#             return self.bedrock_service.generate_text(
#                 system_prompt=LAYOUT_RISK_SYSTEM_PROMPT,
#                 user_prompt=prompt,
#             )
#         except Exception:
#             return "Layout analysis summary not available."

#     def _build_section_prompt(self, updates, segments):
#         pieces = [
#             f"Update {idx + 1}: section_name={update['section_name']}, page_number={update['page_number']}, old_text={update['old_text']}"
#             for idx, update in enumerate(updates)
#         ]
#         return "\n".join(pieces)

#     def _build_layout_prompt(self, updates):
#         pieces = [
#             f"Old text: {update['old_text']}\nNew text: {update['new_text']}\n" for update in updates
#         ]
#         return "\n".join(pieces)
