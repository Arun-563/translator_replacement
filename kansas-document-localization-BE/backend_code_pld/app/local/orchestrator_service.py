# # app/services/orchestrator_service.py

# import json
# import os
# from app.core.config import settings
# # from app.services.s3_service import S3Service   ❌ NOT NEEDED NOW
# from app.local.content_matching_agent import ContentMatchingAgent
# from app.local.instruction_parser_agent import InstructionParserAgent
# from app.local.json_parser_service import JsonParserService
# from app.local.layout_analysis_agent import LayoutAnalysisAgent
# #from app.services.downstream_service import DownstreamService


# from app.core.logger import (
#     get_logger,
#     log_stage_started,
#     log_stage_success,
#     log_stage_failure,
# )



# class OrchestratorService:

#     def __init__(self):
#         # self.s3_service = S3Service()  ❌ REMOVED (no AWS now)
#         self.json_parser = JsonParserService()

#         # Agents (now using Ollama inside BedrockService replacement)
#         self.instruction_agent = InstructionParserAgent()
#         self.content_agent = ContentMatchingAgent()
#         self.layout_agent = LayoutAnalysisAgent()

#         # self.downstream_service = DownstreamService()

#     def process(self, payload, background_tasks=None):

#         print("Payload received:", payload)

#         instructions = getattr(payload, "instructions", payload)
#         results = []
#         errors = []

#         json_file_name = None 

#         for item in instructions:
#             item_data = item.model_dump() if hasattr(item, "model_dump") else item
#             json_file = item_data["json_file"].strip()

#             json_file_name = json_file

#             if json_file.lower().endswith(".json"):
#                 json_file = json_file[:-5]

#             # ----------------------------------------------------
#             # ✅ LOCAL FILE REPLACEMENT (Instead of S3)
#             # ----------------------------------------------------
            
#             json_file = item_data.get("json_file", "")

#             BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            
#             if not json_file:
#                 raise ValueError("Missing json_file")

#             local_path = os.path.join(
#                 BASE_DIR,
#                 "static",
#                 "json",
#                 json_file
#             )

#             local_path = os.path.normpath(local_path)


#             print("LOCAL PATH:", local_path)
#             print("EXISTS:", os.path.exists(local_path))



#             # ✅ STEP 2: Check existence
#             if not os.path.exists(local_path):
#                 errors.append({
#                     "page_number": item_data["page_number"],
#                     "section_name": item_data["section_name"],
#                     "error_code": "JSON_NOT_FOUND",
#                     "error_message": "JSON file not found in local static folder"
#                 })
#                 continue

#             # ✅ STEP 4: Load JSON (same as before)
#             with open(local_path, "r", encoding="utf-8") as f:
#                 json_data = json.load(f)

#             # ----------------------------------------------------
#             # ✅ PIPELINE CONTINUES SAME (NO CHANGE)
#             # ----------------------------------------------------

#             # Precompute searchable blocks once
#             blocks = self.json_parser.extract_blocks(json_data)

#             # STEP 5: Instruction Parsing
#             if hasattr(self.instruction_agent, "parse"):
#                 parsed_instruction = self.instruction_agent.parse(item_data, blocks)
#             elif hasattr(self.instruction_agent, "run"):
#                 parsed_instruction = self.instruction_agent.run(item_data)
#             else:
#                 raise AttributeError("InstructionParserAgent has no method parse or run")

#             print("Parsed Instruction:", parsed_instruction)

#             # STEP 6: Local + semantic match
#             match_result = self.content_agent.local_match(parsed_instruction, blocks)

#             if not match_result["matched"]:
#                 errors.append({
#                     "page_number": item_data["page_number"],
#                     "section_name": item_data["section_name"],
#                     "error_code": "TEXT_NOT_MATCHED",
#                     "error_message": "old_text not found"
#                 })
#                 continue

#             # STEP 7: Validate match using LLM
#             semantic_result = self.content_agent.model_validate_match(
#                 instruction=parsed_instruction,
#                 matched_block={
#                     "segment_id": match_result["matched_segment_id"],
#                     "page_number": match_result["matched_page_number"],
#                     "text": match_result["matched_text"],
#                     "bbox": match_result["bbox"],
#                     "type": match_result["block_type"]
#                 }
#             )

#             print("Semantic Match:", semantic_result)

#             if not semantic_result.get("is_valid_match", False):
#                 errors.append({
#                     "page_number": item_data["page_number"],
#                     "section_name": item_data["section_name"],
#                     "error_code": "TEXT_NOT_MATCHED",
#                     "error_message": semantic_result.get("reason")
#                 })
#                 continue

#             # STEP 8: Layout Analysis
#             layout_result = self.layout_agent.analyze(
#                 parsed_instruction,
#                 match_result
#             )

#             print("Layout Result:", layout_result)

#             # STEP 9: Final response object
#             result = {
#                 "matched_segment_id": match_result["matched_segment_id"],
#                 "matched_page_number": match_result["matched_page_number"],
#                 "confidence": semantic_result.get("confidence"),
#                 "layout_risk": layout_result.get("layout_risk"),

#                 "old_text": item_data.get("old_text"),
#                 "new_text": item_data.get("new_text")
#             }

#             results.append(result)

#             # ❌ REMOVED: do NOT delete local static file
#             # if os.path.exists(local_path):
#             #     os.remove(local_path)

#         # Final response
#         final_response = {
#             "request_id": json_file_name,
#             "status": "SUCCESS" if results else "FAILED",
#             "results": results,
#             "errors": errors
#         }

#         # STEP 11: Send to next team (kept same)
#         # if background_tasks:
#         #     background_tasks.add_task(
#         #         self.downstream_service.send,
#         #         final_response
#         #     )
#         # else:
#         #     self.downstream_service.send(final_response)

#         return final_response
    



# app/services/orchestrator_service.py

import json
import os
from app.core.config import settings
# from app.services.s3_service import S3Service   ❌ NOT NEEDED NOW
from app.local.content_matching_agent import ContentMatchingAgent
from app.local.instruction_parser_agent import InstructionParserAgent
from app.local.json_parser_service import JsonParserService
from app.local.layout_analysis_agent import LayoutAnalysisAgent
# from app.services.downstream_service import DownstreamService

from app.core.logger import (
    get_logger,
    log_stage_started,
    log_stage_success,
    log_stage_failure,
)

logger = get_logger(__name__)


class OrchestratorService:

    def __init__(self):
        # self.s3_service = S3Service()  ❌ REMOVED (no AWS now)
        self.json_parser = JsonParserService()

        # Agents (now using Ollama inside BedrockService replacement)
        self.instruction_agent = InstructionParserAgent()
        self.content_agent = ContentMatchingAgent()
        self.layout_agent = LayoutAnalysisAgent()

        # self.downstream_service = DownstreamService()

    def process(self, payload, background_tasks=None):
        stage = "ORCHESTRATOR SERVICE"
        log_stage_started(logger, stage, "Pipeline started for one PDF")

        print("Payload received:", payload)
        logger.info(
            f"Payload received: {payload}",
            extra={"stage": stage, "status": "STARTED", "error": "None"}
        )

        instructions = getattr(payload, "instructions", payload)
        results = []
        errors = []

        json_file_name = None 

        for item in instructions:
            try:
                item_data = item.model_dump() if hasattr(item, "model_dump") else item
                logger.info(
                    f"Processing instruction for page_number={item_data.get('page_number')}, section_name={item_data.get('section_name')}",
                    extra={"stage": stage, "status": "STARTED", "error": "None"}
                )

                json_file = item_data["json_file"].strip()

                json_file_name = json_file

                if json_file.lower().endswith(".json"):
                    json_file = json_file[:-5]

                # ----------------------------------------------------
                # ✅ LOCAL FILE REPLACEMENT (Instead of S3)
                # ----------------------------------------------------
                
                json_file = item_data.get("json_file", "")

                BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
                
                if not json_file:
                    logger.info(
                        "Missing json_file in instruction payload",
                        extra={"stage": stage, "status": "FAILURE", "error": "Missing json_file"}
                    )
                    raise ValueError("Missing json_file")

                local_path = os.path.join(
                    BASE_DIR,
                    "static",
                    "json",
                    json_file
                )

                local_path = os.path.normpath(local_path)

                print("LOCAL PATH:", local_path)
                print("EXISTS:", os.path.exists(local_path))
                logger.info(
                    f"Resolved local JSON path: {local_path}",
                    extra={"stage": stage, "status": "STARTED", "error": "None"}
                )
                logger.info(
                    f"JSON file exists: {os.path.exists(local_path)}",
                    extra={"stage": stage, "status": "STARTED", "error": "None"}
                )

                # ✅ STEP 2: Check existence
                if not os.path.exists(local_path):
                    errors.append({
                        "page_number": item_data["page_number"],
                        "section_name": item_data["section_name"],
                        "error_code": "JSON_NOT_FOUND",
                        "error_message": "JSON file not found in local static folder"
                    })
                    logger.info(
                        f"JSON file not found at local path: {local_path}",
                        extra={"stage": stage, "status": "FAILURE", "error": "JSON_NOT_FOUND"}
                    )
                    continue

                # ✅ STEP 4: Load JSON (same as before)
                with open(local_path, "r", encoding="utf-8") as f:
                    json_data = json.load(f)

                logger.info(
                    f"JSON loaded successfully from local path: {local_path}",
                    extra={"stage": stage, "status": "SUCCESS", "error": "None"}
                )

                # ----------------------------------------------------
                # ✅ PIPELINE CONTINUES SAME (NO CHANGE)
                # ----------------------------------------------------

                # Precompute searchable blocks once
                blocks = self.json_parser.extract_blocks(json_data)
                logger.info(
                    f"JSON parser completed successfully. Extracted blocks: {len(blocks)}",
                    extra={"stage": stage, "status": "SUCCESS", "error": "None"}
                )

                # STEP 5: Instruction Parsing
                if hasattr(self.instruction_agent, "parse"):
                    parsed_instruction = self.instruction_agent.parse(item_data, blocks)
                elif hasattr(self.instruction_agent, "run"):
                    parsed_instruction = self.instruction_agent.run(item_data)
                else:
                    logger.info(
                        "InstructionParserAgent has no method parse or run",
                        extra={"stage": stage, "status": "FAILURE", "error": "InstructionParserAgent method missing"}
                    )
                    raise AttributeError("InstructionParserAgent has no method parse or run")

                print("Parsed Instruction:", parsed_instruction)
                logger.info(
                    f"Parsed Instruction: {parsed_instruction}",
                    extra={"stage": stage, "status": "SUCCESS", "error": "None"}
                )

                # STEP 6: Local + semantic match
                match_result = self.content_agent.local_match(parsed_instruction, blocks)
                logger.info(
                    "Content local_match completed",
                    extra={"stage": stage, "status": "SUCCESS", "error": "None"}
                )

                if not match_result["matched"]:
                    errors.append({
                        "page_number": item_data["page_number"],
                        "section_name": item_data["section_name"],
                        "error_code": "TEXT_NOT_MATCHED",
                        "error_message": "old_text not found"
                    })
                    logger.info(
                        f"Content matching failed for page_number={item_data.get('page_number')}, section_name={item_data.get('section_name')}",
                        extra={"stage": stage, "status": "FAILURE", "error": "TEXT_NOT_MATCHED"}
                    )
                    continue

                # STEP 7: Validate match using LLM
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
                logger.info(
                    f"Semantic Match: {semantic_result}",
                    extra={"stage": stage, "status": "SUCCESS", "error": "None"}
                )

                if not semantic_result.get("is_valid_match", False):
                    errors.append({
                        "page_number": item_data["page_number"],
                        "section_name": item_data["section_name"],
                        "error_code": "TEXT_NOT_MATCHED",
                        "error_message": semantic_result.get("reason")
                    })
                    logger.info(
                        f"Semantic validation failed for page_number={item_data.get('page_number')}, section_name={item_data.get('section_name')}",
                        extra={"stage": stage, "status": "FAILURE", "error": semantic_result.get('reason')}
                    )
                    continue

                # STEP 8: Layout Analysis
                layout_result = self.layout_agent.analyze(
                    parsed_instruction,
                    match_result
                )

                print("Layout Result:", layout_result)
                logger.info(
                    f"Layout Result: {layout_result}",
                    extra={"stage": stage, "status": "SUCCESS", "error": "None"}
                )

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
                logger.info(
                    f"Instruction processed successfully for page_number={item_data.get('page_number')}, section_name={item_data.get('section_name')}",
                    extra={"stage": stage, "status": "SUCCESS", "error": "None"}
                )

                # ❌ REMOVED: do NOT delete local static file
                # if os.path.exists(local_path):
                #     os.remove(local_path)

            except Exception as e:
                logger.error(
                    f"Instruction processing failed for page_number={item_data.get('page_number') if 'item_data' in locals() else None}, section_name={item_data.get('section_name') if 'item_data' in locals() else None}",
                    extra={"stage": stage, "status": "FAILURE", "error": str(e)}
                )
                raise

        # Final response
        final_response = {
            "request_id": json_file_name,
            "status": "SUCCESS" if results else "FAILED",
            "results": results,
            "errors": errors
        }

        log_stage_success(
            logger,
            stage,
            f"Pipeline finished. results={len(results)}, errors={len(errors)}"
        )

        # STEP 11: Send to next team (kept same)
        # if background_tasks:
        #     background_tasks.add_task(
        #         self.downstream_service.send,
        #         final_response
        #     )
        # else:
        #     self.downstream_service.send(final_response)

        return final_response
