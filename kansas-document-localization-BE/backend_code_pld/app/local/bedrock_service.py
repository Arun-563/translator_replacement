# import json
# import re
# import httpx
# from app.core.config import settings


# from app.core.logger import (
#     get_logger,
#     log_stage_started,
#     log_stage_success,
#     log_stage_failure,
# )



# class BedrockService:

#     def __init__(self):
#         self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
#         self.model_id = settings.OLLAMA_MODEL_ID

#     def invoke_json_prompt(self, prompt: str) -> dict:
#         """
#         Sends prompt to Ollama and returns parsed JSON from model response.
#         Handles:
#         - Ollama response JSON
#         - streamed/multi-line JSON fallback
#         - model output wrapped with extra text
#         """

#         payload = {
#             "model": self.model_id,
#             "messages": [
#                 {
#                     "role": "user",
#                     "content": prompt
#                 }
#             ],
#             "options": {
#                 "temperature": 0
#             },
#             "stream": False
#         }

#         print("🔹 Sending prompt to Ollama...")

#         response = httpx.post(
#             f"{self.base_url}/api/chat",
#             json=payload,
#             timeout=settings.OLLAMA_TIMEOUT
#         )

#         response.raise_for_status()

#         raw_response = response.text

#         print("🔹 Raw Ollama HTTP response:")
#         print(raw_response)

#         # --------------------------------------------------
#         # STEP 1: Parse Ollama HTTP response safely
#         # --------------------------------------------------
#         try:
#             data = response.json()
#         except json.JSONDecodeError:
#             print("⚠️ response.json() failed. Trying line-by-line Ollama stream parsing...")

#             combined_content = ""

#             for line in raw_response.splitlines():
#                 line = line.strip()

#                 if not line:
#                     continue

#                 try:
#                     chunk = json.loads(line)
#                     combined_content += chunk.get("message", {}).get("content", "")
#                 except json.JSONDecodeError:
#                     continue

#             if not combined_content:
#                 raise ValueError(
#                     f"Could not parse Ollama response as JSON or stream. Raw response: {raw_response}"
#                 )

#             text = combined_content

#         else:
#             text = data.get("message", {}).get("content", "")

#         print("🔹 Ollama message content:")
#         print(text)

#         if not text:
#             raise ValueError("Ollama returned empty message content")

#         # --------------------------------------------------
#         # STEP 2: Clean markdown wrappers if model used them
#         # --------------------------------------------------
#         text = text.strip()

#         if text.startswith("```json"):
#             text = text.replace("```json", "", 1).strip()

#         if text.startswith("```"):
#             text = text.replace("```", "", 1).strip()

#         if text.endswith("```"):
#             text = text[:-3].strip()

#         # --------------------------------------------------
#         # STEP 3: Try direct JSON parse first
#         # --------------------------------------------------
#         try:
#             return json.loads(text)
#         except json.JSONDecodeError:
#             print("⚠️ Direct JSON parse failed. Trying JSON object extraction...")

#         # --------------------------------------------------
#         # STEP 4: Extract JSON object from extra text
#         # --------------------------------------------------
#         match = re.search(r"\{.*\}", text, re.DOTALL)

#         if not match:
#             raise ValueError(f"No JSON object found in LLM output: {text}")

#         json_str = match.group(0)

#         try:
#             return json.loads(json_str)
#         except json.JSONDecodeError as e:
#             print("❌ Extracted JSON is still invalid:")
#             print(json_str)
#             raise ValueError(f"Invalid JSON returned by LLM: {e}")

#     def invoke_raw_prompt(self, prompt: str) -> str:
#         """
#         Sends prompt to Ollama and returns raw model text.
#         """

#         payload = {
#             "model": self.model_id,
#             "messages": [
#                 {
#                     "role": "user",
#                     "content": prompt
#                 }
#             ],
#             "options": {
#                 "temperature": 0
#             },
#             "stream": False
#         }

#         response = httpx.post(
#             f"{self.base_url}/api/chat",
#             json=payload,
#             timeout=settings.OLLAMA_TIMEOUT
#         )

#         response.raise_for_status()

#         try:
#             data = response.json()
#             return data.get("message", {}).get("content", "")
#         except json.JSONDecodeError:
#             combined_content = ""

#             for line in response.text.splitlines():
#                 line = line.strip()

#                 if not line:
#                     continue

#                 try:
#                     chunk = json.loads(line)
#                     combined_content += chunk.get("message", {}).get("content", "")
#                 except json.JSONDecodeError:
#                     continue

#             return combined_content

import json
import re
import httpx
from app.core.config import settings

from app.core.logger import (
    get_logger,
    log_stage_started,
    log_stage_success,
    log_stage_failure,
)

logger = get_logger(__name__)


class BedrockService:

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self.model_id = settings.OLLAMA_MODEL_ID

    def invoke_json_prompt(self, prompt: str) -> dict:
        """
        Sends prompt to Ollama and returns parsed JSON from model response.
        Handles:
        - Ollama response JSON
        - streamed/multi-line JSON fallback
        - model output wrapped with extra text
        """
        stage = "LLM SERVICE"
        log_stage_started(logger, stage, "invoke_json_prompt started")

        payload = {
            "model": self.model_id,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "options": {
                "temperature": 0
            },
            "stream": False
        }

        try:
            logger.info(
                f"Sending JSON prompt to Ollama model={self.model_id}, url={self.base_url}/api/chat",
                extra={"stage": stage, "status": "STARTED", "error": "None"}
            )

            print("🔹 Sending prompt to Ollama...")

            timeout = httpx.Timeout(
            connect=30.0,
            read=float(settings.OLLAMA_TIMEOUT),
            write=30.0,
            pool=30.0,
            )

            try:
                response = httpx.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=timeout,
                )
                response.raise_for_status()

            except httpx.ReadTimeout as e:
                raise TimeoutError(
                    f"Ollama read timed out after {settings.OLLAMA_TIMEOUT} seconds. "
                    "Reduce translation batch_size or increase OLLAMA_TIMEOUT."
                ) from e

            except httpx.ConnectError as e:
                raise ConnectionError(
                    "Could not connect to Ollama. Make sure Ollama is running on localhost:11434."
                ) from e

            response.raise_for_status()

            logger.info(
                f"Ollama HTTP response received with status_code={response.status_code}",
                extra={"stage": stage, "status": "SUCCESS", "error": "None"}
            )

            raw_response = response.text

            print("🔹 Raw Ollama HTTP response:")
            print(raw_response)

            logger.info(
                "Raw Ollama HTTP response received",
                extra={"stage": stage, "status": "SUCCESS", "error": "None"}
            )

            # --------------------------------------------------
            # STEP 1: Parse Ollama HTTP response safely
            # --------------------------------------------------
            try:
                data = response.json()
                logger.info(
                    "response.json() parsed successfully",
                    extra={"stage": stage, "status": "SUCCESS", "error": "None"}
                )
            except json.JSONDecodeError:
                print("⚠️ response.json() failed. Trying line-by-line Ollama stream parsing...")

                logger.info(
                    "response.json() failed. Trying line-by-line Ollama stream parsing",
                    extra={"stage": stage, "status": "STARTED", "error": "response.json() failed"}
                )

                combined_content = ""

                for line in raw_response.splitlines():
                    line = line.strip()

                    if not line:
                        continue

                    try:
                        chunk = json.loads(line)
                        combined_content += chunk.get("message", {}).get("content", "")
                    except json.JSONDecodeError:
                        continue

                if not combined_content:
                    log_stage_failure(
                        logger,
                        stage,
                        "Could not parse Ollama response as JSON or stream",
                        ValueError(f"Could not parse Ollama response as JSON or stream. Raw response: {raw_response}")
                    )
                    raise ValueError(
                        f"Could not parse Ollama response as JSON or stream. Raw response: {raw_response}"
                    )

                text = combined_content

                logger.info(
                    "Line-by-line Ollama stream parsing succeeded",
                    extra={"stage": stage, "status": "SUCCESS", "error": "None"}
                )

            else:
                text = data.get("message", {}).get("content", "")

            print("🔹 Ollama message content:")
            print(text)

            logger.info(
                "Ollama message content extracted successfully",
                extra={"stage": stage, "status": "SUCCESS", "error": "None"}
            )

            if not text:
                log_stage_failure(logger, stage, "Ollama returned empty message content", ValueError("Ollama returned empty message content"))
                raise ValueError("Ollama returned empty message content")

            # --------------------------------------------------
            # STEP 2: Clean markdown wrappers if model used them
            # --------------------------------------------------
            text = text.strip()

            if text.startswith("```json"):
                text = text.replace("```json", "", 1).strip()

            if text.startswith("```"):
                text = text.replace("```", "", 1).strip()

            if text.endswith("```"):
                text = text[:-3].strip()

            logger.info(
                "Cleaned markdown wrappers from Ollama response if present",
                extra={"stage": stage, "status": "SUCCESS", "error": "None"}
            )

            # --------------------------------------------------
            # STEP 3: Try direct JSON parse first
            # --------------------------------------------------
            try:
                result = json.loads(text)
                log_stage_success(logger, stage, "Direct JSON parse from Ollama response succeeded")
                return result
            except json.JSONDecodeError:
                print("⚠️ Direct JSON parse failed. Trying JSON object extraction...")

                logger.info(
                    "Direct JSON parse failed. Trying JSON object extraction",
                    extra={"stage": stage, "status": "STARTED", "error": "Direct JSON parse failed"}
                )

            # --------------------------------------------------
            # STEP 4: Extract JSON object from extra text
            # --------------------------------------------------
            match = re.search(r"\{.*\}", text, re.DOTALL)

            if not match:
                log_stage_failure(logger, stage, "No JSON object found in LLM output", ValueError(f"No JSON object found in LLM output: {text}"))
                raise ValueError(f"No JSON object found in LLM output: {text}")

            json_str = match.group(0)

            logger.info(
                "JSON object extracted from Ollama output successfully",
                extra={"stage": stage, "status": "SUCCESS", "error": "None"}
            )

            try:
                result = json.loads(json_str)
                log_stage_success(logger, stage, "Extracted JSON parsed successfully from LLM output")
                return result
            except json.JSONDecodeError as e:
                print("❌ Extracted JSON is still invalid:")
                print(json_str)

                log_stage_failure(logger, stage, "Extracted JSON is invalid", e)
                raise ValueError(f"Invalid JSON returned by LLM: {e}")

        except Exception as e:
            log_stage_failure(logger, stage, "invoke_json_prompt failed", e)
            raise

    def invoke_raw_prompt(self, prompt: str) -> str:
        """
        Sends prompt to Ollama and returns raw model text.
        """
        stage = "LLM SERVICE"
        log_stage_started(logger, stage, "invoke_raw_prompt started")

        payload = {
            "model": self.model_id,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "options": {
                "temperature": 0
            },
            "stream": False
        }

        try:
            logger.info(
                f"Sending raw prompt to Ollama model={self.model_id}, url={self.base_url}/api/chat",
                extra={"stage": stage, "status": "STARTED", "error": "None"}
            )

            response = httpx.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=settings.OLLAMA_TIMEOUT
            )

            response.raise_for_status()

            logger.info(
                f"Ollama raw prompt HTTP response received with status_code={response.status_code}",
                extra={"stage": stage, "status": "SUCCESS", "error": "None"}
            )

            try:
                data = response.json()
                result = data.get("message", {}).get("content", "")

                log_stage_success(logger, stage, "Raw prompt response parsed successfully using response.json()")
                return result

            except json.JSONDecodeError:
                logger.info(
                    "response.json() failed for raw prompt. Trying line-by-line stream parsing",
                    extra={"stage": stage, "status": "STARTED", "error": "response.json() failed"}
                )

                combined_content = ""

                for line in response.text.splitlines():
                    line = line.strip()

                    if not line:
                        continue

                    try:
                        chunk = json.loads(line)
                        combined_content += chunk.get("message", {}).get("content", "")
                    except json.JSONDecodeError:
                        continue

                log_stage_success(logger, stage, "Raw prompt response parsed successfully using line-by-line stream parsing")
                return combined_content

        except Exception as e:
            log_stage_failure(logger, stage, "invoke_raw_prompt failed", e)
            raise