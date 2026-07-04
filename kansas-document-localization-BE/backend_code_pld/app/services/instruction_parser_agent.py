# app/services/instruction_parser_agent.py

import json
from app.services.bedrock_service import BedrockService


class InstructionParserAgent:

    def __init__(self):
        self.bedrock = BedrockService()

    #  ADD THIS METHOD HERE
    def run(self, instruction: dict) -> dict:

        prompt = f"""
You are an instruction parsing agent for a PDF update workflow.

Your task:
1. Interpret the instruction
2. Normalize fields like language, page number, section
3. Return JSON ONLY

Input:
{json.dumps(instruction, indent=2)}

Output format:
{{
  "normalized_language": "english",
  "target_page_number": 1,
  "target_section_name": "Personal Information",
  "old_text": "James Robert Mitchell",
  "new_text": "Kansas POC",
  "user_intent_summary": "Replace the exact old text with new text."
}}
"""

        return self.bedrock.invoke_json_prompt(prompt)