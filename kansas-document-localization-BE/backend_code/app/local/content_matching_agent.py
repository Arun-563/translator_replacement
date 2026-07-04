# import json
# import re
# from app.utils.text_utils import similarity
# from app.local.bedrock_service import BedrockService


# from app.core.logger import (
#     get_logger,
#     log_stage_started,
#     log_stage_success,
#     log_stage_failure,
# )



# class ContentMatchingAgent:
#     def __init__(self):
#         self.bedrock = BedrockService()

#     def _normalize_text(self, text: str) -> str:
#         """
#         Normalize text for safer matching:
#         - converts None to empty string
#         - converts multiple spaces/newlines into single space
#         - strips leading/trailing spaces
#         """
#         if text is None:
#             return ""

#         text = str(text)
#         text = re.sub(r"\s+", " ", text)
#         return text.strip()

#     def local_match(self, instruction: dict, blocks: list, threshold: float = 0.80):
#         """
#         Local deterministic matching.

#         Priority:
#         1. Exact text match
#         2. Case-insensitive exact text match
#         3. Similarity score fallback
#         """

#         page_number = (
#             instruction.get("target_page_number")
#             or instruction.get("page_number")
#         )

#         old_text = instruction.get("old_text", "")

#         if page_number is not None:
#             page_number = int(page_number)

#         old_text = self._normalize_text(old_text)

#         print("LOCAL MATCH - Looking for:", old_text, "on page:", page_number)

#         if not old_text:
#             return {
#                 "matched": False,
#                 "confidence": 0.0,
#                 "reason": "old_text is missing or empty"
#             }

#         candidates = [
#             b for b in blocks
#             if int(b.get("page_number", -1)) == page_number
#         ]

#         print(f"Found {len(candidates)} candidates on page {page_number}")

#         best = None
#         best_score = 0.0

#         normalized_old_text = old_text.lower()

#         for block in candidates:
#             block_text_original = self._normalize_text(block.get("text", ""))
#             block_text_lower = block_text_original.lower()

#             print(f"BLOCK TEXT: {block_text_lower}")

#             # --------------------------------------------------
#             # ✅ Rule 1: Exact match
#             # --------------------------------------------------
#             if old_text and old_text in block_text_original:
#                 score = 1.0

#             # --------------------------------------------------
#             # ✅ Rule 2: Case-insensitive exact match
#             # --------------------------------------------------
#             elif normalized_old_text and normalized_old_text in block_text_lower:
#                 score = 0.98

#             # --------------------------------------------------
#             # ✅ Rule 3: Fuzzy fallback
#             # --------------------------------------------------
#             else:
#                 score = similarity(old_text, block_text_original)

#             if score > best_score:
#                 best_score = score
#                 best = block

#         print(
#             f"Best match - Score: {best_score}, "
#             f"Text: {best['text'][:80] if best else 'None'}"
#         )

#         matched = best is not None and best_score >= threshold

#         print(
#             f"Match result: matched={matched}, "
#             f"confidence={best_score if best else 0.0}"
#         )

#         if not matched:
#             return {
#                 "matched": False,
#                 "confidence": round(best_score, 2) if best else 0.0,
#                 "reason": "No block crossed matching threshold"
#             }

#         return {
#             "matched": True,
#             "matched_segment_id": best["segment_id"],
#             "matched_page_number": best["page_number"],
#             "matched_text": best["text"],
#             "bbox": best["bbox"],
#             "confidence": round(best_score, 2),
#             "block_type": best["type"]
#         }

#     def model_validate_match(self, instruction: dict, matched_block: dict) -> dict:
#         """
#         Validate matched block.

#         Important:
#         - If old_text exists exactly inside matched block, accept directly.
#         - LLM should not reject deterministic exact matches.
#         - LLM is only used for fuzzy/semantic cases.
#         """

#         old_text = self._normalize_text(instruction.get("old_text", ""))
#         matched_text = self._normalize_text(matched_block.get("text", ""))

#         instruction_page = instruction.get("page_number")
#         matched_page = matched_block.get("page_number")

#         if instruction_page is not None and matched_page is not None:
#             instruction_page = int(instruction_page)
#             matched_page = int(matched_page)

#         # --------------------------------------------------
#         # ✅ Rule 1: Page mismatch = invalid
#         # --------------------------------------------------
#         if (
#             instruction_page is not None
#             and matched_page is not None
#             and instruction_page != matched_page
#         ):
#             return {
#                 "is_valid_match": False,
#                 "confidence": 0.0,
#                 "reason": (
#                     f"Page mismatch. Instruction page={instruction_page}, "
#                     f"matched page={matched_page}."
#                 ),
#                 "validation_source": "deterministic_page_check"
#             }

#         # --------------------------------------------------
#         # ✅ Rule 2: Exact old_text found = valid
#         # --------------------------------------------------
#         if old_text and old_text in matched_text:
#             return {
#                 "is_valid_match": True,
#                 "confidence": 1.0,
#                 "reason": "Exact old_text found in matched block.",
#                 "validation_source": "deterministic_exact_match"
#             }

#         # --------------------------------------------------
#         # ✅ Rule 3: Case-insensitive exact old_text found = valid
#         # --------------------------------------------------
#         if old_text and old_text.lower() in matched_text.lower():
#             return {
#                 "is_valid_match": True,
#                 "confidence": 0.98,
#                 "reason": "Case-insensitive old_text found in matched block.",
#                 "validation_source": "deterministic_case_insensitive_match"
#             }

#         # --------------------------------------------------
#         # ✅ Rule 4: Use LLM only if deterministic checks fail
#         # --------------------------------------------------
#         prompt = f"""
# You are a STRICT content matching validator for a PDF update workflow.

# STRICT RULES:
# - Output must be VALID JSON ONLY.
# - Do NOT use markdown.
# - Do NOT include comments.
# - Do NOT include explanations before or after JSON.
# - Return ONLY one JSON object.
# - Confidence must be between 0 and 1.

# TASK:
# Determine whether matched_block.text is the correct replacement target for instruction.old_text.

# IMPORTANT DECISION RULES:
# - If instruction.old_text appears exactly or almost exactly in matched_block.text, is_valid_match must be true.
# - If is_valid_match is false, confidence must be below 0.70.
# - If confidence is above 0.85, is_valid_match must be true.
# - Do not reject a match just because surrounding context is different if old_text itself is present.
# - Reject only if the old_text is missing or the meaning is clearly unrelated.

# Return JSON in EXACT format:
# {{
#   "is_valid_match": true,
#   "confidence": 0.95,
#   "reason": "Short explanation"
# }}

# Instruction:
# {json.dumps(instruction, ensure_ascii=False, indent=2)}

# Matched block:
# {json.dumps(matched_block, ensure_ascii=False, indent=2)}
# """

#         result = self.bedrock.invoke_json_prompt(prompt)

#         is_valid = bool(result.get("is_valid_match", False))

#         try:
#             confidence = float(result.get("confidence", 0.0))
#         except Exception:
#             confidence = 0.0

#         reason = result.get("reason", "")

#         # --------------------------------------------------
#         # ✅ Rule 5: Fix inconsistent LLM output
#         # Example:
#         # is_valid_match=false but confidence=0.95
#         # --------------------------------------------------
#         if not is_valid and confidence >= 0.85:
#             confidence = 0.65
#             reason = (
#                 reason
#                 or "LLM returned invalid match with high confidence; confidence adjusted."
#             )

#         if is_valid and confidence < 0.70:
#             confidence = 0.70
#             reason = (
#                 reason
#                 or "LLM returned valid match with low confidence; confidence adjusted."
#             )

#         return {
#             "is_valid_match": is_valid,
#             "confidence": round(confidence, 2),
#             "reason": reason,
#             "validation_source": "llm_semantic_validation"
#         }

import json
import re
from app.utils.text_utils import similarity
from app.local.bedrock_service import BedrockService

from app.core.logger import (
    get_logger,
    log_stage_started,
    log_stage_success,
    log_stage_failure,
)

logger = get_logger(__name__)


class ContentMatchingAgent:
    def __init__(self):
        self.bedrock = BedrockService()

    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for safer matching:
        - converts None to empty string
        - converts multiple spaces/newlines into single space
        - strips leading/trailing spaces
        """
        stage = "CONTENT MATCHING AGENT"
        log_stage_started(logger, stage, "Normalizing text for content matching")

        try:
            if text is None:
                log_stage_success(logger, stage, "Input text is None; converted to empty string")
                return ""

            text = str(text)
            text = re.sub(r"\s+", " ", text)
            normalized_text = text.strip()

            log_stage_success(logger, stage, "Text normalized successfully")
            return normalized_text

        except Exception as e:
            log_stage_failure(logger, stage, "Text normalization failed", e)
            raise

    def local_match(self, instruction: dict, blocks: list, threshold: float = 0.80):
        """
        Local deterministic matching.

        Priority:
        1. Exact text match
        2. Case-insensitive exact text match
        3. Similarity score fallback
        """
        stage = "CONTENT MATCHING AGENT"
        log_stage_started(logger, stage, "Local content matching started")

        try:
            page_number = (
                instruction.get("target_page_number")
                or instruction.get("page_number")
            )

            old_text = instruction.get("old_text", "")

            if page_number is not None:
                page_number = int(page_number)

            old_text = self._normalize_text(old_text)

            print("LOCAL MATCH - Looking for:", old_text, "on page:", page_number)
            logger.info(
                f"Looking for old_text on page_number={page_number}",
                extra={"stage": stage, "status": "STARTED", "error": "None"}
            )

            if not old_text:
                log_stage_failure(logger, stage, "old_text is missing or empty", ValueError("old_text is missing or empty"))
                return {
                    "matched": False,
                    "confidence": 0.0,
                    "reason": "old_text is missing or empty"
                }

            candidates = [
                b for b in blocks
                if int(b.get("page_number", -1)) == page_number
            ]

            print(f"Found {len(candidates)} candidates on page {page_number}")
            logger.info(
                f"Found {len(candidates)} candidate block(s) on page_number={page_number}",
                extra={"stage": stage, "status": "SUCCESS", "error": "None"}
            )

            best = None
            best_score = 0.0

            normalized_old_text = old_text.lower()

            for block in candidates:
                block_text_original = self._normalize_text(block.get("text", ""))
                block_text_lower = block_text_original.lower()

                print(f"BLOCK TEXT: {block_text_lower}")
                logger.info(
                    f"Evaluating block segment_id={block.get('segment_id')} with block_type={block.get('type')}",
                    extra={"stage": stage, "status": "STARTED", "error": "None"}
                )

                # --------------------------------------------------
                # ✅ Rule 1: Exact match
                # --------------------------------------------------
                if old_text and old_text in block_text_original:
                    score = 1.0

                # --------------------------------------------------
                # ✅ Rule 2: Case-insensitive exact match
                # --------------------------------------------------
                elif normalized_old_text and normalized_old_text in block_text_lower:
                    score = 0.98

                # --------------------------------------------------
                # ✅ Rule 3: Fuzzy fallback
                # --------------------------------------------------
                else:
                    score = similarity(old_text, block_text_original)

                logger.info(
                    f"Block segment_id={block.get('segment_id')} scored {score}",
                    extra={"stage": stage, "status": "SUCCESS", "error": "None"}
                )

                if score > best_score:
                    best_score = score
                    best = block

            print(
                f"Best match - Score: {best_score}, "
                f"Text: {best['text'][:80] if best else 'None'}"
            )
            logger.info(
                f"Best match score={best_score}, best_segment_id={best.get('segment_id') if best else 'None'}",
                extra={"stage": stage, "status": "SUCCESS", "error": "None"}
            )

            matched = best is not None and best_score >= threshold

            print(
                f"Match result: matched={matched}, "
                f"confidence={best_score if best else 0.0}"
            )
            logger.info(
                f"Match result computed: matched={matched}, confidence={best_score if best else 0.0}",
                extra={"stage": stage, "status": "SUCCESS", "error": "None"}
            )

            if not matched:
                log_stage_failure(
                    logger,
                    stage,
                    "No block crossed matching threshold",
                    ValueError("No block crossed matching threshold")
                )
                return {
                    "matched": False,
                    "confidence": round(best_score, 2) if best else 0.0,
                    "reason": "No block crossed matching threshold"
                }

            result = {
                "matched": True,
                "matched_segment_id": best["segment_id"],
                "matched_page_number": best["page_number"],
                "matched_text": best["text"],
                "bbox": best["bbox"],
                "confidence": round(best_score, 2),
                "block_type": best["type"]
            }

            log_stage_success(
                logger,
                stage,
                f"Local content matching completed successfully for segment_id={result['matched_segment_id']}"
            )
            return result

        except Exception as e:
            log_stage_failure(logger, stage, "Local content matching failed", e)
            raise

    def model_validate_match(self, instruction: dict, matched_block: dict) -> dict:
        """
        Validate matched block.

        Important:
        - If old_text exists exactly inside matched block, accept directly.
        - LLM should not reject deterministic exact matches.
        - LLM is only used for fuzzy/semantic cases.
        """
        stage = "CONTENT MATCHING AGENT"
        log_stage_started(logger, stage, "Semantic match validation started")

        try:
            old_text = self._normalize_text(instruction.get("old_text", ""))
            matched_text = self._normalize_text(matched_block.get("text", ""))

            instruction_page = instruction.get("page_number")
            matched_page = matched_block.get("page_number")

            if instruction_page is not None and matched_page is not None:
                instruction_page = int(instruction_page)
                matched_page = int(matched_page)

            logger.info(
                f"Validating match for instruction_page={instruction_page}, matched_page={matched_page}",
                extra={"stage": stage, "status": "STARTED", "error": "None"}
            )

            # --------------------------------------------------
            # ✅ Rule 1: Page mismatch = invalid
            # --------------------------------------------------
            if (
                instruction_page is not None
                and matched_page is not None
                and instruction_page != matched_page
            ):
                log_stage_failure(
                    logger,
                    stage,
                    "Semantic validation failed due to page mismatch",
                    ValueError(
                        f"Page mismatch. Instruction page={instruction_page}, matched page={matched_page}."
                    )
                )
                return {
                    "is_valid_match": False,
                    "confidence": 0.0,
                    "reason": (
                        f"Page mismatch. Instruction page={instruction_page}, "
                        f"matched page={matched_page}."
                    ),
                    "validation_source": "deterministic_page_check"
                }

            # --------------------------------------------------
            # ✅ Rule 2: Exact old_text found = valid
            # --------------------------------------------------
            if old_text and old_text in matched_text:
                log_stage_success(logger, stage, "Deterministic exact match validation succeeded")
                return {
                    "is_valid_match": True,
                    "confidence": 1.0,
                    "reason": "Exact old_text found in matched block.",
                    "validation_source": "deterministic_exact_match"
                }

            # --------------------------------------------------
            # ✅ Rule 3: Case-insensitive exact old_text found = valid
            # --------------------------------------------------
            if old_text and old_text.lower() in matched_text.lower():
                log_stage_success(logger, stage, "Deterministic case-insensitive match validation succeeded")
                return {
                    "is_valid_match": True,
                    "confidence": 0.98,
                    "reason": "Case-insensitive old_text found in matched block.",
                    "validation_source": "deterministic_case_insensitive_match"
                }

            # --------------------------------------------------
            # ✅ Rule 4: Use LLM only if deterministic checks fail
            # --------------------------------------------------
            logger.info(
                "Deterministic validation did not confirm match; invoking LLM validation",
                extra={"stage": stage, "status": "STARTED", "error": "None"}
            )

            prompt = f"""
You are a STRICT content matching validator for a PDF update workflow.

STRICT RULES:
- Output must be VALID JSON ONLY.
- Do NOT use markdown.
- Do NOT include comments.
- Do NOT include explanations before or after JSON.
- Return ONLY one JSON object.
- Confidence must be between 0 and 1.

TASK:
Determine whether matched_block.text is the correct replacement target for instruction.old_text.

IMPORTANT DECISION RULES:
- If instruction.old_text appears exactly or almost exactly in matched_block.text, is_valid_match must be true.
- If is_valid_match is false, confidence must be below 0.70.
- If confidence is above 0.85, is_valid_match must be true.
- Do not reject a match just because surrounding context is different if old_text itself is present.
- Reject only if the old_text is missing or the meaning is clearly unrelated.

Return JSON in EXACT format:
{{
  "is_valid_match": true,
  "confidence": 0.95,
  "reason": "Short explanation"
}}

Instruction:
{json.dumps(instruction, ensure_ascii=False, indent=2)}

Matched block:
{json.dumps(matched_block, ensure_ascii=False, indent=2)}
"""

            result = self.bedrock.invoke_json_prompt(prompt)

            logger.info(
                f"LLM validation result received: {result}",
                extra={"stage": stage, "status": "SUCCESS", "error": "None"}
            )

            is_valid = bool(result.get("is_valid_match", False))

            try:
                confidence = float(result.get("confidence", 0.0))
            except Exception:
                confidence = 0.0

            reason = result.get("reason", "")

            # --------------------------------------------------
            # ✅ Rule 5: Fix inconsistent LLM output
            # Example:
            # is_valid_match=false but confidence=0.95
            # --------------------------------------------------
            if not is_valid and confidence >= 0.85:
                confidence = 0.65
                reason = (
                    reason
                    or "LLM returned invalid match with high confidence; confidence adjusted."
                )

            if is_valid and confidence < 0.70:
                confidence = 0.70
                reason = (
                    reason
                    or "LLM returned valid match with low confidence; confidence adjusted."
                )

            final_result = {
                "is_valid_match": is_valid,
                "confidence": round(confidence, 2),
                "reason": reason,
                "validation_source": "llm_semantic_validation"
            }

            log_stage_success(
                logger,
                stage,
                f"Semantic match validation completed successfully with is_valid_match={final_result['is_valid_match']}"
            )
            return final_result

        except Exception as e:
            log_stage_failure(logger, stage, "Semantic match validation failed", e)
            raise