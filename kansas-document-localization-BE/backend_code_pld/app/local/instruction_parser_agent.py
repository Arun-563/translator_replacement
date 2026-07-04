# # app/local/instruction_parser_agent.py

# import html


# from app.core.logger import (
#     get_logger,
#     log_stage_started,
#     log_stage_success,
#     log_stage_failure,
# )



# class InstructionParserAgent:
#     """
#     Deterministic instruction parser for PDF update workflow.

#     This does NOT call Ollama/LLM because the required fields are already
#     present in the API payload. Using LLM here can hallucinate page_number,
#     section_name, old_text, and new_text.
#     """

#     def __init__(self):
#         pass

#     def parse(self, instruction: dict, blocks=None) -> dict:
#         return self._normalize_instruction(instruction)

#     def run(self, instruction: dict) -> dict:
#         return self._normalize_instruction(instruction)

#     def _normalize_instruction(self, instruction: dict) -> dict:
#         language = instruction.get("language", "english")
#         page_number = instruction.get("page_number")
#         section_name = instruction.get("section_name", "")
#         old_text = instruction.get("old_text", "")
#         new_text = instruction.get("new_text", "")
#         user_instructions = instruction.get("user_instructions", "")

#         language = str(language).strip().lower()
#         section_name = html.unescape(str(section_name).strip())
#         old_text = str(old_text).strip()
#         new_text = str(new_text).strip()
#         user_instructions = str(user_instructions).strip()

#         if not language:
#             language = "english"

#         if page_number is None:
#             raise ValueError("Missing page_number in instruction")

#         if not section_name:
#             raise ValueError("Missing section_name in instruction")

#         if not old_text:
#             raise ValueError("Missing old_text in instruction")

#         if not new_text:
#             raise ValueError("Missing new_text in instruction")

#         return {
#             "normalized_language": language,
#             "page_number": int(page_number),
#             "target_section_name": section_name,
#             "old_text": old_text,
#             "new_text": new_text,
#             "user_intent_summary": f"Replace '{old_text}' with '{new_text}'",
#             "section_confidence": 1.0,
#             "notes": [
#                 "Parsed directly from user payload without LLM to avoid hallucination."
#             ],
#             "user_instructions": user_instructions
#         }

# app/local/instruction_parser_agent.py

import html

from app.core.logger import (
    get_logger,
    log_stage_started,
    log_stage_success,
    log_stage_failure,
)

logger = get_logger(__name__)


class InstructionParserAgent:
    """
    Deterministic instruction parser for PDF update workflow.

    This does NOT call Ollama/LLM because the required fields are already
    present in the API payload. Using LLM here can hallucinate page_number,
    section_name, old_text, and new_text.
    """

    def __init__(self):
        pass

    def parse(self, instruction: dict, blocks=None) -> dict:
        stage = "INSTRUCTION PARSER AGENT"
        log_stage_started(logger, stage, "Instruction parsing started via parse()")

        try:
            result = self._normalize_instruction(instruction)
            log_stage_success(logger, stage, "Instruction parsing completed successfully via parse()")
            return result
        except Exception as e:
            log_stage_failure(logger, stage, "Instruction parsing failed via parse()", e)
            raise

    def run(self, instruction: dict) -> dict:
        stage = "INSTRUCTION PARSER AGENT"
        log_stage_started(logger, stage, "Instruction parsing started via run()")

        try:
            result = self._normalize_instruction(instruction)
            log_stage_success(logger, stage, "Instruction parsing completed successfully via run()")
            return result
        except Exception as e:
            log_stage_failure(logger, stage, "Instruction parsing failed via run()", e)
            raise

    def _normalize_instruction(self, instruction: dict) -> dict:
        stage = "INSTRUCTION PARSER AGENT"
        log_stage_started(logger, stage, "Normalizing instruction payload")

        try:
            language = instruction.get("language", "english")
            page_number = instruction.get("page_number")
            section_name = instruction.get("section_name", "")
            old_text = instruction.get("old_text", "")
            new_text = instruction.get("new_text", "")
            user_instructions = instruction.get("user_instructions", "")

            logger.info(
                f"Raw instruction received for page_number={page_number}, section_name={section_name}",
                extra={"stage": stage, "status": "STARTED", "error": "None"}
            )

            language = str(language).strip().lower()
            section_name = html.unescape(str(section_name).strip())
            old_text = str(old_text).strip()
            new_text = str(new_text).strip()
            user_instructions = str(user_instructions).strip()

            logger.info(
                "Instruction fields normalized successfully",
                extra={"stage": stage, "status": "SUCCESS", "error": "None"}
            )

            if not language:
                language = "english"

            if page_number is None:
                log_stage_failure(logger, stage, "Missing page_number in instruction", ValueError("Missing page_number in instruction"))
                raise ValueError("Missing page_number in instruction")

            if not section_name:
                log_stage_failure(logger, stage, "Missing section_name in instruction", ValueError("Missing section_name in instruction"))
                raise ValueError("Missing section_name in instruction")

            if not old_text:
                log_stage_failure(logger, stage, "Missing old_text in instruction", ValueError("Missing old_text in instruction"))
                raise ValueError("Missing old_text in instruction")

            if not new_text:
                log_stage_failure(logger, stage, "Missing new_text in instruction", ValueError("Missing new_text in instruction"))
                raise ValueError("Missing new_text in instruction")

            result = {
                "normalized_language": language,
                "page_number": int(page_number),
                "target_section_name": section_name,
                "old_text": old_text,
                "new_text": new_text,
                "user_intent_summary": f"Replace '{old_text}' with '{new_text}'",
                "section_confidence": 1.0,
                "notes": [
                    "Parsed directly from user payload without LLM to avoid hallucination."
                ],
                "user_instructions": user_instructions
            }

            logger.info(
                f"Normalized instruction prepared successfully for page_number={result['page_number']}, target_section_name={result['target_section_name']}",
                extra={"stage": stage, "status": "SUCCESS", "error": "None"}
            )

            log_stage_success(logger, stage, "Instruction normalization completed successfully")
            return result

        except Exception as e:
            log_stage_failure(logger, stage, "Instruction normalization failed", e)
            raise