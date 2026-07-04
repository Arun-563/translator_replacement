# from typing import List, Dict


# from app.core.logger import (
#     get_logger,
#     log_stage_started,
#     log_stage_success,
#     log_stage_failure,
# )



# class JsonParserService:
#     def extract_blocks(self, payload: dict) -> List[Dict]:
#         """
#         Converts uploaded PDF JSON into a normalized list of searchable blocks.
#         Output example:
#         [
#           {
#             "segment_id": "sample2.pdf_p2_b16",
#             "page_number": 2,
#             "text": "I hereby declare ...",
#             "bbox": [61.0, 135.28, 540.97, 161.34],
#             "type": "text"
#           }
#         ]
#         """
#         results = []

#         documents = payload.get("documents", [])
#         for document in documents:
#             for page in document.get("pages", []):
#                 page_number = page.get("page_number")
#                 for block in page.get("blocks", []):
#                     block_type = block.get("type")
#                     block_id = block.get("block_id")
#                     bbox = block.get("bbox")

#                     # text blocks
#                     if block_type == "text":
#                         text = self._extract_text_from_text_block(block)
#                         if text:
#                             results.append({
#                                 "segment_id": block_id,
#                                 "page_number": page_number,
#                                 "text": text,
#                                 "bbox": bbox,
#                                 "type": "text"
#                             })

#                     # table blocks
#                     elif block_type == "table":
#                         table_rows = block.get("properties", {}).get("data", [])
#                         for row_idx, row in enumerate(table_rows):
#                             row_text = " | ".join([cell for cell in row if cell])
#                             if row_text:
#                                 results.append({
#                                     "segment_id": f"{block_id}_row_{row_idx+1}",
#                                     "page_number": page_number,
#                                     "text": row_text,
#                                     "bbox": bbox,
#                                     "type": "table_row"
#                                 })

#         return results

#     def _extract_text_from_text_block(self, block: dict) -> str:
#         lines = block.get("properties", {}).get("lines", [])
#         line_texts = []
#         for line in lines:
#             text = line.get("text", "").strip()
#             if text:
#                 line_texts.append(text)
#         return " ".join(line_texts).strip()

from typing import List, Dict

from app.core.logger import (
    get_logger,
    log_stage_started,
    log_stage_success,
    log_stage_failure,
)

logger = get_logger(__name__)


class JsonParserService:
    def extract_blocks(self, payload: dict) -> List[Dict]:
        """
        Converts uploaded PDF JSON into a normalized list of searchable blocks.
        Output example:
        [
          {
            "segment_id": "sample2.pdf_p2_b16",
            "page_number": 2,
            "text": "I hereby declare ...",
            "bbox": [61.0, 135.28, 540.97, 161.34],
            "type": "text"
          }
        ]
        """
        stage = "JSON PARSER SERVICE"
        log_stage_started(logger, stage, "JSON block extraction started")

        results = []

        try:
            documents = payload.get("documents", [])
            logger.info(
                f"Documents found in payload: {len(documents)}",
                extra={"stage": stage, "status": "STARTED", "error": "None"}
            )

            for document in documents:
                for page in document.get("pages", []):
                    page_number = page.get("page_number")
                    logger.info(
                        f"Processing page_number={page_number}",
                        extra={"stage": stage, "status": "STARTED", "error": "None"}
                    )

                    for block in page.get("blocks", []):
                        block_type = block.get("type")
                        block_id = block.get("block_id")
                        bbox = block.get("bbox")

                        logger.info(
                            f"Processing block_id={block_id}, block_type={block_type}, page_number={page_number}",
                            extra={"stage": stage, "status": "STARTED", "error": "None"}
                        )

                        # text blocks
                        if block_type == "text":
                            text = self._extract_text_from_text_block(block)
                            if text:
                                results.append({
                                    "segment_id": block_id,
                                    "page_number": page_number,
                                    "text": text,
                                    "bbox": bbox,
                                    "type": "text"
                                })

                        # table blocks
                        elif block_type == "table":
                            table_rows = block.get("properties", {}).get("data", [])
                            for row_idx, row in enumerate(table_rows):
                                row_text = " | ".join([cell for cell in row if cell])
                                if row_text:
                                    results.append({
                                        "segment_id": f"{block_id}_row_{row_idx+1}",
                                        "page_number": page_number,
                                        "text": row_text,
                                        "bbox": bbox,
                                        "type": "table_row"
                                    })

            log_stage_success(
                logger,
                stage,
                f"JSON parser completed successfully. Extracted blocks: {len(results)}"
            )
            return results

        except Exception as e:
            log_stage_failure(logger, stage, "JSON block extraction failed", e)
            raise

    def _extract_text_from_text_block(self, block: dict) -> str:
        stage = "JSON PARSER SERVICE"
        log_stage_started(logger, stage, "Extracting text from text block")

        try:
            lines = block.get("properties", {}).get("lines", [])
            line_texts = []

            for line in lines:
                text = line.get("text", "").strip()
                if text:
                    line_texts.append(text)

            extracted_text = " ".join(line_texts).strip()

            log_stage_success(logger, stage, "Text extracted from text block successfully")
            return extracted_text

        except Exception as e:
            log_stage_failure(logger, stage, "Failed to extract text from text block", e)
            raise