import json
from typing import Dict
from app.core.config import settings

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
    Translates extracted PDF text block-by-block and validates the translations
    using a SEPARATE LLM (to avoid self-evaluation bias).

    Input:  {block_id: english_text}
    Output: {block_id: spanish_text} + validation report
    """

    def __init__(self):
        # Translation model (e.g. Qwen2.5:3b via Ollama)
        self.bedrock = BedrockService()

        # Validation model — DIFFERENT from translation model
        # e.g. qwen2.5:14b via Ollama
        self.validation_model = BedrockService(model_name=settings.OLLAMA_VALIDATION_MODEL_ID)

        
        print("===================================")
        print("TRANSLATION MODEL FROM SETTINGS:", settings.OLLAMA_MODEL_ID)
        print("VALIDATION MODEL FROM SETTINGS:", settings.OLLAMA_VALIDATION_MODEL_ID)
        print("TRANSLATION MODEL INSTANCE:", self.bedrock.model_id)
        print("VALIDATION MODEL INSTANCE:", self.validation_model.model_id)
        print("===================================")

    # =========================================================================
    # TRANSLATION
    # =========================================================================

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
                translated_batch = self._translate_batch(
                    batch, source_language, target_language
                )
                final_translations.update(translated_batch)

            log_stage_success(
                logger, stage, f"Translated {len(final_translations)} blocks"
            )
            return final_translations

        except Exception as e:
            log_stage_failure(logger, stage, "Block translation failed", e)
            raise

    def _translate_batch(
        self,
        batch: Dict[str, str],
        source_language: str,
        target_language: str,
    ) -> Dict[str, str]:
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
                # Fallback: preserve original if model missed a key.
                translated = original_text
            clean_result[block_id] = str(translated).strip()

        return clean_result

    # =========================================================================
    # VALIDATION (uses a DIFFERENT model)
    # =========================================================================

    def validate_translations(
        self,
        original_text_by_block_id: Dict[str, str],
        translated_text_by_block_id: Dict[str, str],
        source_language: str = "English",
        target_language: str = "Spanish",
        batch_size: int = 2,
    ) -> Dict[str, dict]:
        """
        Validates translated text block-by-block using a DIFFERENT LLM.

        Returns:
            {
              block_id: {
                "is_valid": bool,
                "score": float,
                "severity": "LOW" | "MEDIUM" | "HIGH",
                "issues": [str],
                "suggested_fix": str
              }
            }
        """
        stage = "PDF TRANSLATION VALIDATION AGENT"
        log_stage_started(logger, stage, "Translation validation started")

        try:
            final_validation = {}
            items = list(original_text_by_block_id.items())

            for start in range(0, len(items), batch_size):
                original_batch = dict(items[start:start + batch_size])

                translated_batch = {
                    block_id: translated_text_by_block_id.get(block_id, "")
                    for block_id in original_batch.keys()
                }

                validation_batch = self._validate_batch(
                    original_batch=original_batch,
                    translated_batch=translated_batch,
                    source_language=source_language,
                    target_language=target_language,
                )

                final_validation.update(validation_batch)

            log_stage_success(
                logger,
                stage,
                f"Validated {len(final_validation)} translated blocks",
            )
            return final_validation

        except Exception as e:
            log_stage_failure(logger, stage, "Translation validation failed", e)
            raise

    def _validate_batch(
        self,
        original_batch: Dict[str, str],
        translated_batch: Dict[str, str],
        source_language: str,
        target_language: str,
    ) -> Dict[str, dict]:
        prompt = f"""
You are a STRICT translation validation engine.

TASK:
Validate whether each translated text correctly preserves the meaning
of the original text.

SOURCE LANGUAGE: {source_language}
TARGET LANGUAGE: {target_language}

VALIDATION RULES:
- Return VALID JSON ONLY.
- Do NOT use markdown.
- Do NOT add explanations before or after JSON.
- Preserve every input key exactly.
- Output must be a single JSON object.
- For each block_id, evaluate ONLY that block.
- Check semantic correctness.
- Check whether any important meaning is missing.
- Check whether the translation adds hallucinated information.
- Check whether numbers, dates, IDs, URLs, email addresses, names,
  file names, and code-like values are preserved.
- Check whether the translated text is actually in {target_language}.
- If valid, suggested_fix must be an empty string.
- If invalid, suggested_fix should contain a corrected translated version
  in {target_language}.

SEVERITY RULES:
- LOW: minor wording issue, meaning mostly correct.
- MEDIUM: partially incorrect or missing some meaning.
- HIGH: wrong meaning, untranslated text, hallucinated content,
  or key information missing.

EXPECTED OUTPUT FORMAT:
{{
  "block_id_1": {{
    "is_valid": true,
    "score": 0.95,
    "severity": "LOW",
    "issues": [],
    "suggested_fix": ""
  }},
  "block_id_2": {{
    "is_valid": false,
    "score": 0.45,
    "severity": "HIGH",
    "issues": ["Translation misses important meaning"],
    "suggested_fix": "corrected translated text"
  }}
}}

ORIGINAL JSON:
{json.dumps(original_batch, ensure_ascii=False, indent=2)}

TRANSLATED JSON:
{json.dumps(translated_batch, ensure_ascii=False, indent=2)}
"""
        
        # IMPORTANT: use the SEPARATE validation model, not self.bedrock
        result = self.validation_model.invoke_json_prompt(prompt)

        print(f"validation llm output: {result}")

        if not isinstance(result, dict):
            raise ValueError(
                "Translation validation LLM output must be a JSON object"
            )

        clean_result = {}

        for block_id in original_batch.keys():
            validation = result.get(block_id)

            if not isinstance(validation, dict):
                validation = {
                    "is_valid": False,
                    "score": 0.0,
                    "severity": "HIGH",
                    "issues": ["Validator did not return result for this block"],
                    "suggested_fix": "",
                }

            try:
                score = float(validation.get("score", 0.0))
            except Exception:
                score = 0.0

            clean_result[block_id] = {
                "is_valid": bool(validation.get("is_valid", False)),
                "score": score,
                "severity": str(validation.get("severity", "HIGH")).upper(),
                "issues": validation.get("issues", []) or [],
                "suggested_fix": str(
                    validation.get("suggested_fix", "")
                ).strip(),
            }

        return clean_result