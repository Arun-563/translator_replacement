# import json
# from app.local.bedrock_service import BedrockService


# from app.core.logger import (
#     get_logger,
#     log_stage_started,
#     log_stage_success,
#     log_stage_failure,
# )



# class LayoutAnalysisAgent:
#     def __init__(self):
#         self.bedrock = BedrockService()

#     def analyze(self, instruction: dict, matched_block: dict) -> dict:
#         prompt = f"""
# You are a STRICT layout analysis agent for PDF text replacement.
# STRICT RULES (MANDATORY):
# - Output must be VALID JSON ONLY
# - Do NOT use markdown (no ```json)
# - Do NOT include comments (no //)
# - Do NOT include explanations before or after JSON
# - Return ONLY JSON object
# Your task:
# Estimate the layout risk when replacing old_text with new_text inside the given matched block.
 
# You MUST analyze:
 
# 1. Text Length Change:
#    - Compare length of old_text vs new_text
#    - Significant increase → higher risk
 
# 2. Bounding Box (bbox):
#    - Check width/height availability
#    - Small bbox → higher overflow risk
 
# 3. Content Density:
#    - If text appears in dense paragraph → higher risk
#    - If standalone or short line → lower risk
 
# 4. Layout Constraints:
#    - Multi-line vs single-line usage
#    - Paragraph vs title vs label
 
# Decision Rules (STRICT):
 
# LOW:
# - Text length similar OR slightly increased
# - Sufficient bbox space
# - Not dense content
 
# MEDIUM:
# - Moderate length increase
# - Possibly fits but may wrap lines
# - Some layout impact likely
 
# HIGH:
# - Large length increase
# - High chance of overflow or text cut
# - Dense paragraph or tight space
 
# Output Rules:
# - Return ONLY valid JSON
# - No explanation outside JSON
# - Do NOT guess or assume missing layout info
 
# Return JSON in EXACT format:
# {{
#   "layout_risk": "LOW|MEDIUM|HIGH",
#   "warnings": [
#     "Short explanation if risk exists",
#     "Mention overflow, wrapping, or truncation risk if applicable"
#   ]
# }}

# Instruction:
# {json.dumps(instruction, indent=2)}

# Matched block:
# {json.dumps(matched_block, indent=2)}
# """
#         return self.bedrock.invoke_json_prompt(prompt)

import json
from app.local.bedrock_service import BedrockService

from app.core.logger import (
    get_logger,
    log_stage_started,
    log_stage_success,
    log_stage_failure,
)

logger = get_logger(__name__)


class LayoutAnalysisAgent:
    def __init__(self):
        self.bedrock = BedrockService()

    def analyze(self, instruction: dict, matched_block: dict) -> dict:
        stage = "LAYOUT ANALYSIS AGENT"
        log_stage_started(logger, stage, "Layout analysis started")

        try:
            logger.info(
                f"Preparing layout analysis prompt for segment_id={matched_block.get('matched_segment_id', matched_block.get('segment_id', 'N/A'))}",
                extra={"stage": stage, "status": "STARTED", "error": "None"}
            )

            prompt = f"""
You are a STRICT layout analysis agent for PDF text replacement.
STRICT RULES (MANDATORY):
- Output must be VALID JSON ONLY
- Do NOT use markdown (no ```json)
- Do NOT include comments (no //)
- Do NOT include explanations before or after JSON
- Return ONLY JSON object
Your task:
Estimate the layout risk when replacing old_text with new_text inside the given matched block.
 
You MUST analyze:
 
1. Text Length Change:
   - Compare length of old_text vs new_text
   - Significant increase → higher risk
 
2. Bounding Box (bbox):
   - Check width/height availability
   - Small bbox → higher overflow risk
 
3. Content Density:
   - If text appears in dense paragraph → higher risk
   - If standalone or short line → lower risk
 
4. Layout Constraints:
   - Multi-line vs single-line usage
   - Paragraph vs title vs label
 
Decision Rules (STRICT):
 
LOW:
- Text length similar OR slightly increased
- Sufficient bbox space
- Not dense content
 
MEDIUM:
- Moderate length increase
- Possibly fits but may wrap lines
- Some layout impact likely
 
HIGH:
- Large length increase
- High chance of overflow or text cut
- Dense paragraph or tight space
 
Output Rules:
- Return ONLY valid JSON
- No explanation outside JSON
- Do NOT guess or assume missing layout info
 
Return JSON in EXACT format:
{{
  "layout_risk": "LOW|MEDIUM|HIGH",
  "warnings": [
    "Short explanation if risk exists",
    "Mention overflow, wrapping, or truncation risk if applicable"
  ]
}}

Instruction:
{json.dumps(instruction, indent=2)}

Matched block:
{json.dumps(matched_block, indent=2)}
"""

            logger.info(
                "Prompt prepared successfully for layout analysis",
                extra={"stage": stage, "status": "SUCCESS", "error": "None"}
            )

            result = self.bedrock.invoke_json_prompt(prompt)

            logger.info(
                f"Layout analysis result received: {result}",
                extra={"stage": stage, "status": "SUCCESS", "error": "None"}
            )

            log_stage_success(logger, stage, "Layout analysis completed successfully")
            return result

        except Exception as e:
            log_stage_failure(logger, stage, "Layout analysis failed", e)
            raise
