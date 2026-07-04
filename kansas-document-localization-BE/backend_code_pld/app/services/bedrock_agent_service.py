import httpx


BEDROCK_AGENT_API_URL = "http://127.0.0.1:8000/pdf-update/process"


async def send_payload_to_bedrock_agent(payload: dict):
    """
    Sends payload to the downstream Bedrock agent API.

    Expected payload format:
    {
        "request_id": "2026-06-18_00_22_05.json",
        "instructions": [
            {
                "language": "english",
                "page_number": 1,
                "section_name": "Personal Information",
                "old_text": "James Robert Mitchell",
                "new_text": "Kansas POC",
                "json_file": "2026-06-18_00_22_05.json",
                "user_instructions": "NA"
            }
        ]
    }
    """
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                BEDROCK_AGENT_API_URL,
                json=payload
            )
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        raise Exception(
            f"Bedrock agent API returned {e.response.status_code}: {e.response.text}"
        )
    except Exception as e:
        raise Exception(f"Failed to call Bedrock agent API: {str(e)}")