import json
from app.services.bedrock_service import BedrockService


class LayoutAnalysisAgent:
    def __init__(self):
        self.bedrock = BedrockService()

    def analyze(self, instruction: dict, matched_block: dict) -> dict:
        prompt = f"""
You are a layout analysis agent for PDF text replacement.

Your task:
1. Estimate the layout risk of replacing old_text with new_text.
2. Consider text length increase, bbox size, and whether the matched block is likely in dense content.
3. Return ONLY valid JSON.

Allowed layout_risk values: LOW, MEDIUM, HIGH

Return JSON in this exact structure:
{{
  "layout_risk": "LOW",
  "warnings": []
}}

Instruction:
{json.dumps(instruction, indent=2)}

Matched block:
{json.dumps(matched_block, indent=2)}
"""
        return self.bedrock.invoke_json_prompt(prompt)