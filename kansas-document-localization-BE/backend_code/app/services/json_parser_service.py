from typing import List, Dict


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
        results = []

        documents = payload.get("documents", [])
        for document in documents:
            for page in document.get("pages", []):
                page_number = page.get("page_number")
                for block in page.get("blocks", []):
                    block_type = block.get("type")
                    block_id = block.get("block_id")
                    bbox = block.get("bbox")

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

        return results

    def _extract_text_from_text_block(self, block: dict) -> str:
        lines = block.get("properties", {}).get("lines", [])
        line_texts = []
        for line in lines:
            text = line.get("text", "").strip()
            if text:
                line_texts.append(text)
        return " ".join(line_texts).strip()