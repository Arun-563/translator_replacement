import os
from lxml import etree

class XDPProcessor:

    def extract_text(self, input_path: str) -> list:
        segments = []

        parser = etree.XMLParser(remove_blank_text=False)
        tree = etree.parse(input_path, parser)

        text_nodes = tree.xpath("//text()")

        for index, node in enumerate(text_nodes):
            text = str(node).strip()

            if text and not self.is_placeholder(text):
                segments.append({
                    "segment_id": f"xdp_t{index}",
                    "page": None,
                    "text": text,
                    "bbox": None,
                    "document_type": "xdp"
                })

        return segments

    def rebuild_document(self, input_path: str, translated_segments: list, output_dir: str) -> str:
        # POC placeholder: actual XML node replacement will be added by backend dev
        output_path = os.path.join(output_dir, "translated_output.xdp")

        parser = etree.XMLParser(remove_blank_text=False)
        tree = etree.parse(input_path, parser)
        tree.write(output_path, encoding="utf-8", xml_declaration=True)

        return output_path

    def is_placeholder(self, text: str) -> bool:
        return text.startswith("{{") and text.endswith("}}")