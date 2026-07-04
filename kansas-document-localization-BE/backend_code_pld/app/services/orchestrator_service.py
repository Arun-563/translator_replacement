# app/services/orchestrator_service.py

import json
import os
from app.core.config import settings
from app.services.s3_service import S3Service
from app.services.content_matching_agent import ContentMatchingAgent
from app.services.instruction_parser_agent import InstructionParserAgent
from app.services.json_parser_service import JsonParserService
from app.services.layout_analysis_agent import LayoutAnalysisAgent
#from app.services.downstream_service import DownstreamService


class OrchestratorService:

    def __init__(self):
        self.s3_service = S3Service()
        self.json_parser = JsonParserService()

        # Agents (Bedrock used inside them)
        self.instruction_agent = InstructionParserAgent()
        self.content_agent = ContentMatchingAgent()
        self.layout_agent = LayoutAnalysisAgent()

        #self.downstream_service = DownstreamService()

    def process(self, payload, background_tasks=None):

        print("Payload received:", payload)

        instructions = getattr(payload, "instructions", payload)
        results = []
        errors = []

        json_file_name = None 

        for item in instructions:
            item_data = item.model_dump() if hasattr(item, "model_dump") else item
            json_file = item_data["json_file"].strip()

            # print("Item:", item_data)
            json_file_name = json_file

            
            if json_file.lower().endswith(".json"):
                json_file = json_file[:-5]

            # STEP 1: Build S3 key
            # json_key = self.s3_service.build_json_key(json_file)
            json_key = f"{settings.S3_JSON_PREFIX}/{item['json_file']}"
           

            print("S3 KEY:", json_key)

            # STEP 2: Check existence
            if not self.s3_service.exists(json_key):
                errors.append({
                    "page_number": item_data["page_number"],
                    "section_name": item_data["section_name"],
                    "error_code": "JSON_NOT_FOUND",
                    "error_message": "JSON file not found in S3"
                })
                continue

            # STEP 3: Download locally
            local_path = f"{settings.LOCAL_DOWNLOAD_DIR}/{json_file}.json"

            self.s3_service.download_file(json_key, local_path)

            # STEP 4: Load JSON
            with open(local_path, "r") as f:
                json_data = json.loads(f.read())

            # ----------------------------------------------------
            # BEDROCK INTEGRATION STARTS HERE
            # ----------------------------------------------------

            # Precompute searchable blocks once
            blocks = self.json_parser.extract_blocks(json_data)

            # STEP 5: Instruction Parsing (Bedrock call)
            if hasattr(self.instruction_agent, "parse"):
                parsed_instruction = self.instruction_agent.parse(item_data, blocks)
            elif hasattr(self.instruction_agent, "run"):
                # InstructionParserAgent.run expects only the instruction dict
                parsed_instruction = self.instruction_agent.run(item_data)
            else:
                raise AttributeError("InstructionParserAgent has no method parse or run")

            print("Parsed Instruction:", parsed_instruction)

            # STEP 6: Local + semantic match
            match_result = self.content_agent.local_match(parsed_instruction, blocks)

            if not match_result["matched"]:
                errors.append({
                    "page_number": item_data["page_number"],
                    "section_name": item_data["section_name"],
                    "error_code": "TEXT_NOT_MATCHED",
                    "error_message": "old_text not found"
                })
                continue

            # STEP 7: Validate match using Bedrock
            semantic_result = self.content_agent.model_validate_match(
                instruction=parsed_instruction,
                matched_block={
                    "segment_id": match_result["matched_segment_id"],
                    "page_number": match_result["matched_page_number"],
                    "text": match_result["matched_text"],
                    "bbox": match_result["bbox"],
                    "type": match_result["block_type"]
                }
            )

            print("Semantic Match:", semantic_result)

            if not semantic_result.get("is_valid_match", False):
                errors.append({
                    "page_number": item_data["page_number"],
                    "section_name": item_data["section_name"],
                    "error_code": "TEXT_NOT_MATCHED",
                    "error_message": semantic_result.get("reason")
                })
                continue

            # STEP 8: Layout Analysis (Bedrock call)
            layout_result = self.layout_agent.analyze(
                parsed_instruction,
                match_result
            )

            print("Layout Result:", layout_result)

            # STEP 9: Final response object
            result = {
                "matched_segment_id": match_result["matched_segment_id"],
                "matched_page_number": match_result["matched_page_number"],
                "confidence": semantic_result.get("confidence"),
                "layout_risk": layout_result.get("layout_risk"),
                                    
                "old_text": item_data.get("old_text"),
                "new_text": item_data.get("new_text")

            }

            results.append(result)

            # STEP 10: Delete local file
            if os.path.exists(local_path):
                os.remove(local_path)

        # Final response
        final_response = {
            
            "request_id": json_file_name,
            "status": "SUCCESS" if results else "FAILED",
            "results": results,
            "errors": errors
        }




            

        # STEP 11: Send to next team
        # if background_tasks:
        #     background_tasks.add_task(
        #         self.downstream_service.send,
        #         final_response
        #     )
        # else:
        #     self.downstream_service.send(final_response)

        return final_response