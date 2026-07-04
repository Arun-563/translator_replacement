# import httpx


# from app.core.logger import (
#     get_logger,
#     log_stage_started,
#     log_stage_success,
#     log_stage_failure,
# )


# # ✅ Toggle control
# ENABLE_DOWNSTREAM = False

# BEDROCK_AGENT_API_URL = "http://127.0.0.1:8000/pdf-update/process"


# async def send_payload_to_bedrock_agent(payload: dict):
#     """
#     Local-safe version.

#     If ENABLE_DOWNSTREAM = False:
#         → skip API call
#         → return dummy response

#     If ENABLE_DOWNSTREAM = True:
#         → call actual downstream API
#     """

#     # ✅ LOCAL MODE (skip downstream)
#     if not ENABLE_DOWNSTREAM:
#         return {
#             "status": "skipped",
#             "reason": "Downstream disabled for local testing",
#             "payload_received": payload
#         }

#     # ✅ REAL MODE (only if enabled)
#     try:
#         async with httpx.AsyncClient(timeout=120.0) as client:
#             response = await client.post(
#                 BEDROCK_AGENT_API_URL,
#                 json=payload
#             )
#             response.raise_for_status()
#             return response.json()

#     except httpx.HTTPStatusError as e:
#         raise Exception(
#             f"Bedrock agent API returned {e.response.status_code}: {e.response.text}"
#         )

#     except Exception as e:
#         raise Exception(f"Failed to call downstream API: {str(e)}")

import httpx

from app.core.logger import (
    get_logger,
    log_stage_started,
    log_stage_success,
    log_stage_failure,
)

logger = get_logger(__name__)

# ✅ Toggle control
ENABLE_DOWNSTREAM = False

BEDROCK_AGENT_API_URL = "http://127.0.0.1:8000/pdf-update/process"


async def send_payload_to_bedrock_agent(payload: dict):
    """
    Local-safe version.

    If ENABLE_DOWNSTREAM = False:
        → skip API call
        → return dummy response

    If ENABLE_DOWNSTREAM = True:
        → call actual downstream API
    """
    stage = "LOCAL AGENT SERVICE"
    log_stage_started(logger, stage, "Sending payload to downstream bedrock/local agent service")

    # ✅ LOCAL MODE (skip downstream)
    if not ENABLE_DOWNSTREAM:
        logger.info(
            "Downstream call skipped because ENABLE_DOWNSTREAM is False",
            extra={"stage": stage, "status": "SUCCESS", "error": "None"}
        )
        log_stage_success(logger, stage, "Downstream disabled for local testing; returning skipped response")
        return {
            "status": "skipped",
            "reason": "Downstream disabled for local testing",
            "payload_received": payload
        }

    # ✅ REAL MODE (only if enabled)
    try:
        logger.info(
            f"Calling downstream API at: {BEDROCK_AGENT_API_URL}",
            extra={"stage": stage, "status": "STARTED", "error": "None"}
        )

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                BEDROCK_AGENT_API_URL,
                json=payload
            )
            response.raise_for_status()

            logger.info(
                f"Downstream API call completed successfully with status code: {response.status_code}",
                extra={"stage": stage, "status": "SUCCESS", "error": "None"}
            )
            log_stage_success(logger, stage, "Payload sent successfully to downstream API")
            return response.json()

    except httpx.HTTPStatusError as e:
        log_stage_failure(
            logger,
            stage,
            "Downstream API returned HTTP error",
            Exception(f"{e.response.status_code}: {e.response.text}")
        )
        raise Exception(
            f"Bedrock agent API returned {e.response.status_code}: {e.response.text}"
        )

    except Exception as e:
        log_stage_failure(logger, stage, "Failed to call downstream API", e)
        raise Exception(f"Failed to call downstream API: {str(e)}")
