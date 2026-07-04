import json
from app.utils.text_utils import similarity
from app.services.bedrock_service import BedrockService


class ContentMatchingAgent:
    def __init__(self):
        self.bedrock = BedrockService()

    def local_match(self, instruction: dict, blocks: list, threshold: float = 0.80):
        # support both original request shape and parsed instruction shape
        page_number = instruction.get("target_page_number") or instruction.get("page_number")
        old_text = instruction.get("old_text")

        print("LOCAL MATCH - Looking for:", old_text, "on page:", page_number)

        candidates = [b for b in blocks if b["page_number"] == page_number]
        print(f" Found {len(candidates)} candidates on page {page_number}")
        best = None
        best_score = 0.0

        normalized_old_text = old_text.strip().lower()

        for block in candidates:
            block_text = block["text"].strip().lower()
            if normalized_old_text and normalized_old_text in block_text:
                score = 1.0
            else:
                score = similarity(old_text, block["text"])

            if score > best_score:
                best_score = score
                best = block

        print(f"Best match - Score: {best_score}, Text: {best['text'][:50] if best else 'None'}")
        print(f"Match result: matched={best is not None and best_score >= threshold}, confidence={best_score if best else 0.0}")

        if not best or best_score < threshold:
            return {
                "matched": False,
                "confidence": best_score if best else 0.0
            }

        return {
            "matched": True,
            "matched_segment_id": best["segment_id"],
            "matched_page_number": best["page_number"],
            "matched_text": best["text"],
            "bbox": best["bbox"],
            "confidence": round(best_score, 2),
            "block_type": best["type"]
        }

    def model_validate_match(self, instruction: dict, matched_block: dict) -> dict:
        prompt = f"""
You are a content matching validator for a PDF update workflow.

Your task:
1. Decide whether the matched block is the correct replacement target.
2. Evaluate semantic alignment between instruction.old_text and matched block text.
3. Return ONLY valid JSON.

Return JSON in this exact structure:
{{
  "is_valid_match": true,
  "confidence": 0.98,
  "reason": "The matched block text strongly aligns with the requested old text."
}}

Instruction:
{json.dumps(instruction, indent=2)}

Matched block:
{json.dumps(matched_block, indent=2)}
"""
        return self.bedrock.invoke_json_prompt(prompt)