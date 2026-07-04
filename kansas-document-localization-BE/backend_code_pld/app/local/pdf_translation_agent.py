import json
from typing import Dict

from app.local.bedrock_service import BedrockService
from app.core.logger import (
    get_logger,
    log_stage_started,
    log_stage_success,
    log_stage_failure,
)

logger = get_logger(__name__)


class PdfTranslationAgent:
    """
    Translates extracted PDF text block-by-block.
    Input:  {block_id: english_text}
    Output: {block_id: spanish_text}
    """

    def __init__(self):
        self.bedrock = BedrockService()

    def translate_blocks(
        self,
        text_by_block_id: Dict[str, str],
        source_language: str = "English",
        target_language: str = "Spanish",
        batch_size: int = 3,
    ) -> Dict[str, str]:
        stage = "PDF TRANSLATION AGENT"
        log_stage_started(logger, stage, "Block translation started")

        try:
            final_translations = {}
            items = list(text_by_block_id.items())

            for start in range(0, len(items), batch_size):
                batch = dict(items[start:start + batch_size])
                translated_batch = self._translate_batch(batch, source_language, target_language)
                final_translations.update(translated_batch)

            log_stage_success(logger, stage, f"Translated {len(final_translations)} blocks")
            return final_translations

        except Exception as e:
            log_stage_failure(logger, stage, "Block translation failed", e)
            raise

    def _translate_batch(self, batch: Dict[str, str], source_language: str, target_language: str) -> Dict[str, str]:
        prompt = f"""
You are a STRICT PDF translation engine.

TASK:
Translate every text value from {source_language} to {target_language}.

STRICT RULES:
- Return VALID JSON ONLY.
- Do NOT use markdown.
- Do NOT add comments.
- Do NOT add explanations before or after JSON.
- Preserve every input key exactly.
- Output must be a single JSON object.
- Each key must map to only the translated text string.
- Do not translate IDs, numbers, dates, URLs, email addresses, file names, or code-like values unless they are part of natural text.
- Keep punctuation and line meaning as close as possible.
- Do not omit any key.

EXPECTED OUTPUT FORMAT:
{{
  "block_id_1": "translated text",
  "block_id_2": "translated text"
}}

INPUT JSON:
{json.dumps(batch, ensure_ascii=False, indent=2)}
"""
        result = self.bedrock.invoke_json_prompt(prompt)

        if not isinstance(result, dict):
            raise ValueError("Translation LLM output must be a JSON object")

        clean_result = {}
        for block_id, original_text in batch.items():
            translated = result.get(block_id)
            if translated is None:
                # Fallback: preserve original if model missed a key, so pipeline does not crash.
                translated = original_text
            clean_result[block_id] = str(translated).strip()

        return clean_result
