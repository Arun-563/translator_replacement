import sys
import os

# Step 1: Fix import path
sys.path.append(os.path.join(os.path.dirname(__file__), "backend_code"))

# Step 2: Imports
from app.schemas.request_models import UpdateAnalysisRequest
from app.services.orchestrator_service import UpdateAnalysisOrchestrator

# Step 3: HARDCODED PAYLOAD 
payload_dict = payload_dict = {
    "request_id": "REQ-LOCAL-001", #use file name as a request ID
    "instructions": [
        {
            "language": "english",
            "page_number": 1,
            "section_name": "Employee Information",
            "old_text": "Full Name",
            "new_text": "Candidate Full Name",
            "json_file": "2026-06-16_16_18",
            "user_instructions": ""
        }
    ]
}

# Step 4: Convert payload
payload = UpdateAnalysisRequest(**payload_dict)

# Step 5: Initialize orchestrator
orchestrator = UpdateAnalysisOrchestrator()

# Step 6: Run full pipeline
response = orchestrator.process(payload)

# Step 7: Print output
print("\nINAL RESPONSE:\n")
print(response)

print(" Script finished")

