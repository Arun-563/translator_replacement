# import os
# from utils.file_handler import save_upload_file
# from utils.file_detector import detect_file_type
# from processors.pdf_processor import PDFProcessor
# from processors.docx_processor import DOCXProcessor
# from processors.xdp_processor import XDPProcessor
# from services.bedrock_service import BedrockService
# from services.layout_validator import LayoutValidator
# from core.config import settings

# class TranslationService:

#     def __init__(self):
#         self.bedrock_service = BedrockService()
#         self.layout_validator = LayoutValidator()

#     async def process_document(self, file, source_language, target_language, conversion_type):
#         input_path = await save_upload_file(file)
#         file_type = detect_file_type(file.filename)

#         processor = self.get_processor(file_type)

#         segments = processor.extract_text(input_path)

#         translated_segments = []

#         for segment in segments:
#             translated_text = self.bedrock_service.translate_text(
#                 text=segment["text"],
#                 source_language=source_language,
#                 target_language=target_language
#             )

#             risk = self.layout_validator.check_risk(
#                 original_text=segment["text"],
#                 translated_text=translated_text,
#                 segment=segment
#             )

#             translated_segments.append({
#                 **segment,
#                 "translated_text": translated_text,
#                 "risk_level": risk
#             })

#         os.makedirs(settings.OUTPUT_DIR, exist_ok=True)

#         output_path = processor.rebuild_document(
#             input_path=input_path,
#             translated_segments=translated_segments,
#             output_dir=settings.OUTPUT_DIR
#         )

#         return output_path

#     def get_processor(self, file_type):
#         if file_type == "pdf":
#             return PDFProcessor()
#         elif file_type == "docx":
#             return DOCXProcessor()
#         elif file_type == "xdp":
#             return XDPProcessor()

#         raise ValueError("Invalid file type")