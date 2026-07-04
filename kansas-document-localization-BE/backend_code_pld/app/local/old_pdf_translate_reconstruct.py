# import os
# import re
# import math
# import json
# import zipfile
# from pathlib import Path
# from collections import Counter
# from copy import deepcopy

# from reportlab.pdfgen import canvas
# from reportlab.lib.colors import HexColor, black, white
# from reportlab.pdfbase.pdfmetrics import stringWidth, getDescent
# from reportlab.lib.utils import ImageReader


# # =============================================================================
# # PDF TRANSLATION RECONSTRUCTION
# # -----------------------------------------------------------------------------
# # Purpose:
# #   Reconstruct a fully translated PDF from extracted layout JSON.
# #
# # Why separate from pdf_replace.py:
# #   pdf_replace.py is good for targeted old_text -> new_text replacement.
# #   For full PDF translation, we need full layout rendering from JSON:
# #     - text block bbox
# #     - span font
# #     - span font size
# #     - span color
# #     - images
# #     - shapes
# #     - lines
# #     - tables
# #
# # Main usage:
# #   translated_json = apply_translations_to_json(json_data, translated_text_by_block_id)
# #   result = reconstruct_translated_pdf_from_json_payload(
# #       request_id=json_file_name,
# #       payload=translated_json,
# #   )
# # =============================================================================


# # =============================================================================
# # PATH CONFIG
# # =============================================================================

# APP_DIR = Path(__file__).resolve().parents[1]          # backend_code/app
# BACKEND_DIR = APP_DIR.parent                           # backend_code

# STATIC_DIR = BACKEND_DIR / "static"
# DOWNLOADS_DIR = STATIC_DIR / "downloads"

# DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)


# # =============================================================================
# # FONT CONFIG
# # =============================================================================

# SUPPORTED_EXACT_FONTS = {
#     "Helvetica": "Helvetica",
#     "Helvetica-Bold": "Helvetica-Bold",
#     "Helvetica-Oblique": "Helvetica-Oblique",
#     "Helvetica-BoldOblique": "Helvetica-BoldOblique",
#     "Times-Roman": "Times-Roman",
#     "Times-Bold": "Times-Bold",
#     "Times-Italic": "Times-Italic",
#     "Times-BoldItalic": "Times-BoldItalic",
#     "Courier": "Courier",
#     "Courier-Bold": "Courier-Bold",
#     "Courier-Oblique": "Courier-Oblique",
#     "Courier-BoldOblique": "Courier-BoldOblique",
#     "Symbol": "Symbol",
#     "ZapfDingbats": "ZapfDingbats",
# }


# # =============================================================================
# # BASIC UTILS
# # =============================================================================

# def safe_float(value, default=0.0):
#     try:
#         return float(value)
#     except Exception:
#         return default


# def safe_int(value, default=0):
#     try:
#         return int(value)
#     except Exception:
#         return default


# def sanitize_text(text):
#     if text is None:
#         return ""

#     if not isinstance(text, str):
#         text = str(text)

#     return text.replace("\x00", "").strip()


# def as_color(value, default=black):
#     if not value:
#         return default

#     try:
#         return HexColor(value)
#     except Exception:
#         return default


# def hex_to_reportlab_color(value, default=black):
#     return as_color(value, default)


# def resolve_font(font_name, flags=0, sample_text=""):
#     """
#     Resolves extracted PDF font names to ReportLab built-in fonts.

#     ReportLab cannot use every PDF embedded font directly unless registered.
#     This function maps close equivalents.
#     """

#     font_name = sanitize_text(font_name)

#     if font_name in SUPPORTED_EXACT_FONTS:
#         return SUPPORTED_EXACT_FONTS[font_name]

#     name = font_name.lower()

#     bold = ("bold" in name) or bool(flags & 16)
#     italic = (
#         "italic" in name
#         or "oblique" in name
#         or bool(flags & 2)
#     )

#     if "zapfdingbats" in name:
#         return "ZapfDingbats"

#     if "symbol" in name:
#         return "Symbol"

#     family = "Helvetica"

#     if "times" in name:
#         family = "Times"
#     elif "courier" in name or "mono" in name:
#         family = "Courier"
#     elif "helvetica" in name or "arial" in name or "sans" in name:
#         family = "Helvetica"

#     if family == "Helvetica":
#         if bold and italic:
#             return "Helvetica-BoldOblique"
#         if bold:
#             return "Helvetica-Bold"
#         if italic:
#             return "Helvetica-Oblique"
#         return "Helvetica"

#     if family == "Times":
#         if bold and italic:
#             return "Times-BoldItalic"
#         if bold:
#             return "Times-Bold"
#         if italic:
#             return "Times-Italic"
#         return "Times-Roman"

#     if family == "Courier":
#         if bold and italic:
#             return "Courier-BoldOblique"
#         if bold:
#             return "Courier-Bold"
#         if italic:
#             return "Courier-Oblique"
#         return "Courier"

#     return "Helvetica"


# def rl_rect_from_bbox(bbox, page_h):
#     """
#     Converts PyMuPDF-style bbox:
#         [x0, y0, x1, y1] with origin top-left

#     To ReportLab rect:
#         x, y, width, height with origin bottom-left
#     """

#     x0, y0, x1, y1 = [safe_float(v) for v in bbox]

#     return (
#         x0,
#         page_h - y1,
#         x1 - x0,
#         y1 - y0,
#     )


# def bbox_to_values(bbox):
#     if not bbox or len(bbox) != 4:
#         return None

#     return [safe_float(v) for v in bbox]


# # =============================================================================
# # TEXT WRAPPING / FITTING
# # =============================================================================

# def wrap_text(text, font_name, font_size, max_width):
#     """
#     Wraps text to fit within max_width using ReportLab stringWidth.
#     """

#     text = sanitize_text(text)

#     if not text:
#         return []

#     if stringWidth(text, font_name, font_size) <= max_width:
#         return [text]

#     parts = re.split(r"(\s+)", text)
#     lines = []
#     current = ""

#     for part in parts:
#         trial = current + part

#         if not trial.strip():
#             current = trial
#             continue

#         if stringWidth(trial, font_name, font_size) <= max_width or not current:
#             current = trial
#         else:
#             lines.append(current.rstrip())
#             current = part.lstrip()

#     if current:
#         lines.append(current.rstrip())

#     # hard-break long unbroken tokens
#     final_lines = []

#     for line in lines:
#         if stringWidth(line, font_name, font_size) <= max_width:
#             final_lines.append(line)
#             continue

#         buffer = ""

#         for ch in line:
#             if not buffer:
#                 buffer = ch
#                 continue

#             if stringWidth(buffer + ch, font_name, font_size) <= max_width:
#                 buffer += ch
#             else:
#                 final_lines.append(buffer)
#                 buffer = ch

#         if buffer:
#             final_lines.append(buffer)

#     return final_lines


# def fit_text_to_box(
#     text,
#     font_name,
#     start_font_size,
#     box_width,
#     box_height,
#     min_font_size=4.5,
#     horizontal_padding=1.5,
#     vertical_padding=1.5,
# ):
#     """
#     Fits text inside a box by wrapping and shrinking font size.
#     """

#     text = sanitize_text(text)

#     max_width = max(box_width - (horizontal_padding * 2), 2)
#     max_height = max(box_height - (vertical_padding * 2), 2)

#     font_size = safe_float(start_font_size, 10.0)

#     while font_size >= min_font_size:
#         lines = wrap_text(text, font_name, font_size, max_width)
#         line_height = font_size * 1.18

#         needed_height = len(lines) * line_height

#         if needed_height <= max_height:
#             return font_size, lines, True

#         font_size -= 0.35

#     fallback_lines = wrap_text(text, font_name, min_font_size, max_width)
#     return min_font_size, fallback_lines, False


# def get_first_span_style(block):
#     """
#     Extracts the first available span style from a text block.
#     Used for translated block rendering.
#     """

#     props = block.get("properties", {}) or {}
#     lines = props.get("lines") or []

#     for line in lines:
#         if not isinstance(line, dict):
#             continue

#         spans = line.get("spans") or []

#         for span in spans:
#             if not isinstance(span, dict):
#                 continue

#             return {
#                 "font": span.get("font", "Helvetica"),
#                 "font_size": safe_float(span.get("font_size"), 10.0),
#                 "color": span.get("color", "#000000"),
#                 "flags": safe_int(span.get("flags", 0)),
#             }

#     return {
#         "font": "Helvetica",
#         "font_size": 10.0,
#         "color": "#000000",
#         "flags": 0,
#     }


# # =============================================================================
# # TRANSLATION JSON UPDATE
# # =============================================================================

# def apply_translations_to_json(json_data, translated_text_by_block_id):
#     """
#     Adds translated text into the original JSON without destroying original spans.

#     Why:
#       - Original spans are still needed for font, font_size, color.
#       - Renderer checks properties["translated_text"] first.
#       - If translated_text exists, it renders translated text at block level
#         with wrapping inside the original block bbox.
#     """

#     updated_json = deepcopy(json_data)

#     for document in updated_json.get("documents", []):
#         for page in document.get("pages", []):
#             for block in page.get("blocks", []):
#                 block_id = block.get("block_id")

#                 if not block_id:
#                     continue

#                 if block_id not in translated_text_by_block_id:
#                     continue

#                 translated_text = sanitize_text(
#                     translated_text_by_block_id.get(block_id, "")
#                 )

#                 if not translated_text:
#                     continue

#                 block_type = block.get("type")

#                 if block_type == "text":
#                     props = block.setdefault("properties", {})
#                     props["translated_text"] = translated_text

#                 elif block_type == "table":
#                     # Optional support for full table translation.
#                     # For now, table cell translation can be added separately
#                     # using block_id + cell coordinates if your dictionary includes them.
#                     pass

#     return updated_json


# # =============================================================================
# # DRAW BASIC BLOCKS
# # =============================================================================

# def draw_rect(c, bbox, props, page_h):
#     if not bbox:
#         return

#     x, y, w, h = rl_rect_from_bbox(bbox, page_h)

#     fill = as_color(props.get("fill_color"), white)
#     stroke = props.get("stroke_color")
#     stroke_width = safe_float(props.get("stroke_width"), 1.0)

#     c.saveState()

#     try:
#         if props.get("fill_opacity") is not None:
#             c.setFillAlpha(safe_float(props.get("fill_opacity"), 1.0))

#         if props.get("stroke_opacity") is not None:
#             c.setStrokeAlpha(safe_float(props.get("stroke_opacity"), 1.0))
#     except Exception:
#         pass

#     c.setFillColor(fill)

#     if stroke:
#         c.setStrokeColor(as_color(stroke, black))
#         c.setLineWidth(stroke_width)
#         c.rect(x, y, w, h, fill=1, stroke=1)
#     else:
#         c.rect(x, y, w, h, fill=1, stroke=0)

#     c.restoreState()


# def draw_line_block(c, block, page_h):
#     props = block.get("properties", {}) or {}
#     segments = props.get("segments") or [block.get("bbox")]

#     c.saveState()

#     c.setStrokeColor(as_color(props.get("stroke_color"), black))
#     c.setLineWidth(safe_float(props.get("stroke_width"), 1.0))

#     try:
#         if props.get("stroke_opacity") is not None:
#             c.setStrokeAlpha(safe_float(props.get("stroke_opacity"), 1.0))
#     except Exception:
#         pass

#     for segment in segments:
#         if not segment or len(segment) != 4:
#             continue

#         x0, y0, x1, y1 = [safe_float(v) for v in segment]
#         c.line(x0, page_h - y0, x1, page_h - y1)

#     c.restoreState()


# def draw_image_block(c, block, page_h):
#     props = block.get("properties", {}) or {}

#     image_data = (
#         props.get("image")
#         or props.get("image_data")
#         or props.get("data")
#         or props.get("base64")
#     )

#     image_path = (
#         props.get("image_path")
#         or props.get("path")
#         or props.get("file_path")
#         or props.get("saved_path")
#         or props.get("image_file")
#     )

#     bbox = block.get("bbox")
#     if not bbox or len(bbox) != 4:
#         return

#     x, y, w, h = rl_rect_from_bbox(bbox, page_h)

#     import io
#     import base64

#     try:
#         if image_data:
#             if isinstance(image_data, str) and image_data.startswith("data:image"):
#                 image_data = image_data.split(",", 1)[1]

#             if isinstance(image_data, str):
#                 raw = base64.b64decode(image_data)
#                 reader = ImageReader(io.BytesIO(raw))

#                 c.drawImage(
#                     reader,
#                     x,
#                     y,
#                     w,
#                     h,
#                     preserveAspectRatio=False,
#                     mask="auto",
#                 )
#                 return

#         if image_path and os.path.exists(image_path):
#             reader = ImageReader(image_path)

#             c.drawImage(
#                 reader,
#                 x,
#                 y,
#                 w,
#                 h,
#                 preserveAspectRatio=False,
#                 mask="auto",
#             )
#             return

#     except Exception as e:
#         print(f"IMAGE_RENDER_ERROR block_id={block.get('block_id')} error={e}")


# # =============================================================================
# # DRAW TEXT
# # =============================================================================

# def draw_span(c, span, page_h, rotation=0):
#     text = sanitize_text(span.get("text", ""))

#     if not text:
#         return

#     bbox = span.get("bbox")

#     if not bbox or len(bbox) != 4:
#         return

#     font_name = resolve_font(
#         span.get("font"),
#         span.get("flags", 0),
#         text,
#     )

#     font_size = safe_float(span.get("font_size"), 10.0)
#     color = as_color(span.get("color"), black)

#     x0, y0, x1, y1 = [safe_float(v) for v in bbox]

#     try:
#         descent = abs(getDescent(font_name) / 1000.0 * font_size)
#     except Exception:
#         descent = 0.20 * font_size

#     baseline = page_h - y1 + descent

#     c.saveState()
#     c.setFillColor(color)
#     c.setFont(font_name, font_size)

#     if rotation:
#         c.translate(x0, baseline)
#         c.rotate(-safe_float(rotation, 0.0))
#         c.drawString(0, 0, text)
#     else:
#         c.drawString(x0, baseline, text)

#     c.restoreState()


# def draw_translated_text_block(c, block, page_h):
#     """
#     Draw translated text inside original block bbox.

#     This is the most important function for full PDF translation:
#       - uses original block bbox
#       - uses first span font/font_size/color
#       - wraps text
#       - shrinks text if needed
#     """

#     props = block.get("properties", {}) or {}
#     translated_text = sanitize_text(props.get("translated_text", ""))

#     if not translated_text:
#         return False

#     bbox = block.get("bbox")

#     if not bbox or len(bbox) != 4:
#         return False

#     x0, y0, x1, y1 = [safe_float(v) for v in bbox]

#     block_width = max(x1 - x0, 1)
#     block_height = max(y1 - y0, 1)

#     style = get_first_span_style(block)

#     font_name = resolve_font(
#         style.get("font"),
#         style.get("flags", 0),
#         translated_text,
#     )

#     start_font_size = safe_float(style.get("font_size"), 10.0)
#     color = as_color(style.get("color"), black)

#     fitted_size, lines, fitted = fit_text_to_box(
#         text=translated_text,
#         font_name=font_name,
#         start_font_size=start_font_size,
#         box_width=block_width,
#         box_height=block_height,
#     )

#     c.saveState()
#     c.setFillColor(color)
#     c.setFont(font_name, fitted_size)

#     line_height = fitted_size * 1.18

#     # Top-left drawing within original PDF bbox
#     current_y = page_h - y0 - fitted_size

#     min_y = page_h - y1

#     for line in lines:
#         if current_y < min_y:
#             break

#         c.drawString(x0, current_y, line)
#         current_y -= line_height

#     c.restoreState()

#     return True


# def draw_text_block(c, block, page_h):
#     """
#     Draws text block.

#     If block has properties["translated_text"], draw translated wrapped text.
#     Otherwise draw original spans exactly.
#     """

#     props = block.get("properties", {}) or {}

#     if props.get("translated_text"):
#         rendered = draw_translated_text_block(c, block, page_h)

#         if rendered:
#             return

#     rotation = safe_float(block.get("rotation"), 0.0)

#     lines = props.get("lines") or []

#     for line in lines:
#         if not isinstance(line, dict):
#             continue

#         spans = line.get("spans") or []

#         if spans:
#             for span in spans:
#                 draw_span(c, span, page_h, rotation=rotation)
#         else:
#             text = sanitize_text(line.get("text", ""))
#             bbox = line.get("bbox")

#             if text and bbox and len(bbox) == 4:
#                 fake_span = {
#                     "text": text,
#                     "bbox": bbox,
#                     "font": "Helvetica",
#                     "font_size": 10,
#                     "color": "#000000",
#                     "flags": 0,
#                 }

#                 draw_span(c, fake_span, page_h, rotation=rotation)


# # =============================================================================
# # TABLE SUPPORT
# # =============================================================================

# def cluster_positions(values, tol=1.0):
#     values = sorted(float(v) for v in values)

#     if not values:
#         return []

#     groups = [[values[0]]]

#     for value in values[1:]:
#         if abs(value - groups[-1][-1]) <= tol:
#             groups[-1].append(value)
#         else:
#             groups.append([value])

#     return [sum(group) / len(group) for group in groups]


# def flatten_cell_bboxes(cell_bboxes):
#     flat = []

#     def walk(node):
#         if isinstance(node, list):
#             if len(node) == 4 and all(isinstance(x, (int, float)) for x in node):
#                 flat.append([float(x) for x in node])
#             else:
#                 for item in node:
#                     walk(item)

#     walk(cell_bboxes)
#     return flat

# def draw_ellipse_block(c, block, page_h):
#     """
#     Draws circle/ellipse-like blocks such as logo circles.
#     Expected bbox: [x0, y0, x1, y1]
#     """
#     bbox = block.get("bbox")
#     if not bbox or len(bbox) != 4:
#         return

#     props = block.get("properties", {}) or {}

#     x, y, w, h = rl_rect_from_bbox(bbox, page_h)

#     fill_color = (
#         props.get("fill_color")
#         or props.get("color")
#         or props.get("fill")
#         or "#FFFFFF"
#     )

#     stroke_color = props.get("stroke_color")
#     stroke_width = safe_float(props.get("stroke_width"), 0)

#     c.saveState()

#     try:
#         if props.get("fill_opacity") is not None:
#             c.setFillAlpha(safe_float(props.get("fill_opacity"), 1.0))
#         if props.get("stroke_opacity") is not None:
#             c.setStrokeAlpha(safe_float(props.get("stroke_opacity"), 1.0))
#     except Exception:
#         pass

#     c.setFillColor(as_color(fill_color, white))

#     if stroke_color and stroke_width > 0:
#         c.setStrokeColor(as_color(stroke_color, black))
#         c.setLineWidth(stroke_width)
#         c.ellipse(x, y, x + w, y + h, fill=1, stroke=1)
#     else:
#         c.ellipse(x, y, x + w, y + h, fill=1, stroke=0)

#     c.restoreState()

# def infer_table_line_boundaries(table_bbox, all_blocks):
#     table_bbox = [safe_float(v) for v in table_bbox]
#     x0, y0, x1, y1 = table_bbox

#     xs = [x0, x1]
#     ys = [y0, y1]

#     for block in all_blocks:
#         if block.get("type") != "line":
#             continue

#         props = block.get("properties", {}) or {}

#         for segment in props.get("segments") or []:
#             if not segment or len(segment) != 4:
#                 continue

#             sx0, sy0, sx1, sy1 = [safe_float(v) for v in segment]

#             # horizontal line
#             if (
#                 abs(sy0 - sy1) <= 1.0
#                 and min(sx0, sx1) <= x1 + 1
#                 and max(sx0, sx1) >= x0 - 1
#                 and y0 - 1 <= sy0 <= y1 + 1
#             ):
#                 ys.append(sy0)

#             # vertical line
#             if (
#                 abs(sx0 - sx1) <= 1.0
#                 and min(sy0, sy1) <= y1 + 1
#                 and max(sy0, sy1) >= y0 - 1
#                 and x0 - 1 <= sx0 <= x1 + 1
#             ):
#                 xs.append(sx0)

#     xs = cluster_positions(xs, tol=1.5)
#     ys = cluster_positions(ys, tol=1.5)

#     return xs, ys


# def normalize_table_cells(
#     table_bbox,
#     data,
#     row_count,
#     column_count,
#     cell_bboxes=None,
#     line_boundaries=None,
# ):
#     rows = row_count
#     cols = column_count

#     if rows == 0 or cols == 0:
#         return []

#     x0, y0, x1, y1 = [safe_float(v) for v in table_bbox]
#     flat = flatten_cell_bboxes(cell_bboxes or [])

#     # Handles column-grouped cell bbox extraction
#     if len(flat) == rows * cols:
#         sorted_by_x = sorted(
#             flat,
#             key=lambda b: (round(b[0], 2), round(b[1], 2)),
#         )

#         col_groups = []

#         for col_index in range(cols):
#             col_groups.append(
#                 sorted_by_x[col_index * rows:(col_index + 1) * rows]
#             )

#         for col_index in range(cols):
#             col_groups[col_index] = sorted(
#                 col_groups[col_index],
#                 key=lambda b: b[1],
#             )

#         matrix = []

#         for row_index in range(rows):
#             row = []

#             for col_index in range(cols):
#                 row.append(col_groups[col_index][row_index])

#             matrix.append(row)

#         return matrix

#     # fallback uniform grid
#     matrix = []

#     dx = (x1 - x0) / cols
#     dy = (y1 - y0) / rows

#     for row_index in range(rows):
#         row_boxes = []

#         for col_index in range(cols):
#             row_boxes.append([
#                 x0 + col_index * dx,
#                 y0 + row_index * dy,
#                 x0 + (col_index + 1) * dx,
#                 y0 + (row_index + 1) * dy,
#             ])

#         matrix.append(row_boxes)

#     return matrix


# def fit_text_to_cell(text, font_name, start_size, cell_w, cell_h, max_lines=None):
#     size = safe_float(start_size, 8.0)

#     max_width = max(cell_w - 6, 4)
#     max_height = max(cell_h - 4, 4)

#     while size >= 4.5:
#         lines = wrap_text(text, font_name, size, max_width)
#         line_height = size + 1.2

#         if (
#             (max_lines is None or len(lines) <= max_lines)
#             and len(lines) * line_height <= max_height
#         ):
#             return size, lines

#         size -= 0.3

#     return 4.5, wrap_text(text, font_name, 4.5, max_width)


# def draw_table_block(c, table_block, all_blocks, page_h):
#     props = table_block.get("properties", {}) or {}
#     data = props.get("data") or []

#     if not data:
#         return

#     table_bbox = table_block.get("bbox")

#     if not table_bbox:
#         return

#     rows = safe_int(props.get("row_count", 0))
#     cols = safe_int(props.get("column_count", 0))

#     if rows == 0 or cols == 0:
#         return

#     # normalize table data row-major
#     flat_data = []

#     for row in data:
#         if isinstance(row, list):
#             flat_data.extend(row)
#         else:
#             flat_data.append(row)

#     normalized_data = []
#     idx = 0

#     for _ in range(rows):
#         row = flat_data[idx:idx + cols]
#         idx += cols

#         if len(row) < cols:
#             row += [""] * (cols - len(row))

#         normalized_data.append(row)

#     data = normalized_data

#     line_boundaries = infer_table_line_boundaries(table_bbox, all_blocks)

#     cell_matrix = normalize_table_cells(
#         table_bbox=table_bbox,
#         data=data,
#         row_count=rows,
#         column_count=cols,
#         cell_bboxes=props.get("cell_bboxes"),
#         line_boundaries=line_boundaries,
#     )

#     header_info = props.get("header", {}) or {}
#     header_texts = {
#         sanitize_text(text)
#         for text in (header_info.get("texts") or [])
#     }

#     header_fill = header_info.get("fill_color")

#     for row_index in range(rows):
#         for col_index in range(cols):
#             if row_index >= len(cell_matrix):
#                 continue

#             if col_index >= len(cell_matrix[row_index]):
#                 continue

#             bbox = cell_matrix[row_index][col_index]

#             if not bbox:
#                 continue

#             x0, y0, x1, y1 = [safe_float(v) for v in bbox]
#             cell_w = x1 - x0
#             cell_h = y1 - y0

#             cell_text = sanitize_text(data[row_index][col_index])

#             is_header = (
#                 row_index == 0
#                 or cell_text in header_texts
#             )

#             font_name = "Helvetica-Bold" if is_header else "Helvetica"
#             preferred_size = 8.5 if is_header else 7.8

#             if (
#                 is_header
#                 and header_fill
#                 and str(header_fill).upper() not in ("#FFFFFF", "WHITE")
#             ):
#                 color = white
#             else:
#                 color = black

#             fitted_size, lines = fit_text_to_cell(
#                 text=cell_text,
#                 font_name=font_name,
#                 start_size=preferred_size,
#                 cell_w=cell_w,
#                 cell_h=cell_h,
#             )

#             c.saveState()
#             c.setFillColor(color)
#             c.setFont(font_name, fitted_size)

#             line_height = fitted_size + 1.2
#             start_y = page_h - y0 - fitted_size - 1.5
#             min_y = page_h - y1 + 1

#             for line in lines:
#                 if start_y < min_y:
#                     break

#                 c.drawString(x0 + 3, start_y, line)
#                 start_y -= line_height

#             c.restoreState()


# # =============================================================================
# # RECONSTRUCTION MAIN
# # =============================================================================

# def get_documents_from_payload(payload):
#     if isinstance(payload, dict) and "documents" in payload:
#         return payload["documents"]

#     if isinstance(payload, list):
#         return payload

#     raise ValueError("Unsupported JSON structure. Expected dict with 'documents' or list.")


# def build_output_file_name(request_id):
#     base_name = str(request_id).replace(".json", "")
#     return f"translated_{base_name}.pdf"


# def reconstruct_translated_pdf_from_json_payload(
#     request_id,
#     payload,
#     output_dir=None,
#     output_file_name=None,
# ):
#     """
#     Reconstructs translated PDF from layout JSON payload.

#     Fixes:
#     - Background rectangles are drawn first.
#     - Images/logos are drawn after backgrounds.
#     - Circle/ellipse logo shapes are supported.
#     - Text is drawn LAST so header text is not hidden behind green banner.
#     - Tables are drawn after structural objects.
#     """

#     if output_dir is None:
#         output_dir = str(DOWNLOADS_DIR)

#     os.makedirs(output_dir, exist_ok=True)

#     documents = get_documents_from_payload(payload)

#     output_file_name = output_file_name or build_output_file_name(request_id)
#     output_path = os.path.join(output_dir, output_file_name)

#     block_counter = Counter()
#     logs = []

#     if not documents:
#         raise ValueError("No documents found in JSON payload.")

#     first_doc = documents[0]
#     pages = first_doc.get("pages", [])

#     if not pages:
#         raise ValueError("No pages found in JSON payload.")

#     first_dims = pages[0].get("dimensions", {}) or {}
#     page_w = safe_float(first_dims.get("width"), 612)
#     page_h = safe_float(first_dims.get("height"), 792)

#     c = canvas.Canvas(output_path, pagesize=(page_w, page_h), bottomup=1)

#     for document in documents:
#         for page in document.get("pages", []):
#             dims = page.get("dimensions", {}) or {}

#             page_w = safe_float(dims.get("width"), 612)
#             page_h = safe_float(dims.get("height"), 792)

#             c.setPageSize((page_w, page_h))

#             # Base white page background
#             c.setFillColor(white)
#             c.rect(0, 0, page_w, page_h, fill=1, stroke=0)

#             blocks = sorted(
#                 page.get("blocks", []) or [],
#                 key=lambda b: (
#                     safe_int(b.get("z_index", 0)),
#                     str(b.get("block_id", "")),
#                 ),
#             )

#             # Count all block types for debugging
#             for block in blocks:
#                 block_counter[block.get("type", "unknown")] += 1

#             print("BLOCK TYPES FOUND:", dict(block_counter))

#             # -----------------------------------------------------------------
#             # IMPORTANT DRAW ORDER
#             # -----------------------------------------------------------------
#             # 1. Background rectangles / filled shapes
#             # 2. Images / logos
#             # 3. Circle / ellipse logo badges
#             # 4. Lines
#             # 5. Tables
#             # 6. Text LAST
#             #
#             # This prevents the green header rectangle from covering
#             # logo text and header text.
#             # -----------------------------------------------------------------

#             background_blocks = []
#             image_blocks = []
#             ellipse_blocks = []
#             line_blocks = []
#             table_blocks = []
#             text_blocks = []
#             other_blocks = []

#             for block in blocks:
#                 block_type = block.get("type", "unknown")

#                 if block_type in (
#                     "filled_rect",
#                     "rect",
#                     "rectangle",
#                     "background",
#                     "shape_rect",
#                     "filled_rectangle",
#                 ):
#                     background_blocks.append(block)

#                 elif block_type == "image":
#                     image_blocks.append(block)

#                 elif block_type in (
#                     "circle",
#                     "ellipse",
#                     "filled_circle",
#                     "filled_ellipse",
#                     "shape_circle",
#                     "shape_ellipse",
#                 ):
#                     ellipse_blocks.append(block)

#                 elif block_type == "line":
#                     line_blocks.append(block)

#                 elif block_type == "table":
#                     table_blocks.append(block)

#                 elif block_type == "text":
#                     text_blocks.append(block)

#                 else:
#                     other_blocks.append(block)

#             # -----------------------------------------------------------------
#             # 1. Draw background rectangles first
#             # -----------------------------------------------------------------
#             for block in background_blocks:
#                 try:
#                     draw_rect(
#                         c,
#                         block.get("bbox"),
#                         block.get("properties", {}) or {},
#                         page_h,
#                     )
#                 except Exception as e:
#                     logs.append({
#                         "status": "BACKGROUND_RENDER_ERROR",
#                         "block_id": block.get("block_id"),
#                         "type": block.get("type"),
#                         "error": str(e),
#                     })

#             # -----------------------------------------------------------------
#             # 2. Draw images/logos
#             # -----------------------------------------------------------------
#             for block in image_blocks:
#                 try:
#                     draw_image_block(c, block, page_h)
#                 except Exception as e:
#                     logs.append({
#                         "status": "IMAGE_RENDER_ERROR",
#                         "block_id": block.get("block_id"),
#                         "type": block.get("type"),
#                         "error": str(e),
#                     })

#             # -----------------------------------------------------------------
#             # 3. Draw circle/ellipse shapes such as white AH logo badge
#             # -----------------------------------------------------------------
#             for block in ellipse_blocks:
#                 try:
#                     draw_ellipse_block(c, block, page_h)
#                 except Exception as e:
#                     logs.append({
#                         "status": "ELLIPSE_RENDER_ERROR",
#                         "block_id": block.get("block_id"),
#                         "type": block.get("type"),
#                         "error": str(e),
#                     })

#             # -----------------------------------------------------------------
#             # 4. Draw other unknown shape-like blocks as best effort
#             # -----------------------------------------------------------------
#             for block in other_blocks:
#                 try:
#                     block_type = block.get("type", "unknown")

#                     # Some extractors may call shapes "path" or "drawing".
#                     # If bbox + fill_color exists, render it as rectangle fallback.
#                     props = block.get("properties", {}) or {}
#                     has_bbox = block.get("bbox") and len(block.get("bbox")) == 4
#                     has_fill = (
#                         props.get("fill_color")
#                         or props.get("color")
#                         or props.get("fill")
#                     )

#                     if block_type in ("path", "drawing", "shape") and has_bbox and has_fill:
#                         draw_rect(
#                             c,
#                             block.get("bbox"),
#                             props,
#                             page_h,
#                         )

#                 except Exception as e:
#                     logs.append({
#                         "status": "OTHER_BLOCK_RENDER_ERROR",
#                         "block_id": block.get("block_id"),
#                         "type": block.get("type"),
#                         "error": str(e),
#                     })

#             # -----------------------------------------------------------------
#             # 5. Draw lines
#             # -----------------------------------------------------------------
#             for block in line_blocks:
#                 try:
#                     draw_line_block(c, block, page_h)
#                 except Exception as e:
#                     logs.append({
#                         "status": "LINE_RENDER_ERROR",
#                         "block_id": block.get("block_id"),
#                         "type": block.get("type"),
#                         "error": str(e),
#                     })

#             # -----------------------------------------------------------------
#             # 6. Draw tables before normal text
#             # -----------------------------------------------------------------
#             for table_block in table_blocks:
#                 try:
#                     draw_table_block(c, table_block, blocks, page_h)
#                 except Exception as e:
#                     logs.append({
#                         "status": "TABLE_RENDER_ERROR",
#                         "block_id": table_block.get("block_id"),
#                         "type": table_block.get("type"),
#                         "error": str(e),
#                     })

#             # -----------------------------------------------------------------
#             # 7. Draw text LAST
#             # -----------------------------------------------------------------
#             # This is the key fix for your header:
#             # green banner is drawn first, then AH/logo/header text appears on top.
#             # -----------------------------------------------------------------
#             for block in text_blocks:
#                 try:
#                     draw_text_block(c, block, page_h)
#                 except Exception as e:
#                     logs.append({
#                         "status": "TEXT_RENDER_ERROR",
#                         "block_id": block.get("block_id"),
#                         "type": block.get("type"),
#                         "error": str(e),
#                     })

#             c.showPage()

#     c.save()

#     return {
#         "output_file_name": output_file_name,
#         "output_path": output_path,
#         "output_url": f"/static/downloads/{output_file_name}",
#         "logs": logs,
#         "block_types": dict(block_counter),
#     }


# def reconstruct_translated_pdf(
#     request_id,
#     json_data,
#     translated_text_by_block_id,
#     output_dir=None,
#     output_file_name=None,
# ):
#     """
#     High-level function used by pdf_translation_service.py.

#     Steps:
#       1. Add translated_text to text blocks in JSON.
#       2. Reconstruct full PDF from translated JSON.
#     """

#     translated_json = apply_translations_to_json(
#         json_data=json_data,
#         translated_text_by_block_id=translated_text_by_block_id,
#     )

#     result = reconstruct_translated_pdf_from_json_payload(
#         request_id=request_id,
#         payload=translated_json,
#         output_dir=output_dir,
#         output_file_name=output_file_name,
#     )

#     return result

import os
import re
import base64
from pathlib import Path
from copy import deepcopy

from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, black, white
from reportlab.pdfbase.pdfmetrics import stringWidth, getDescent
from reportlab.lib.utils import ImageReader


# =============================================================================
# PDF TRANSLATION RECONSTRUCTION
# =============================================================================

APP_DIR = Path(__file__).resolve().parents[1]          # backend_code/app
BACKEND_DIR = APP_DIR.parent                          # backend_code
STATIC_DIR = BACKEND_DIR / "static"
DOWNLOADS_DIR = STATIC_DIR / "downloads"

DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)


SUPPORTED_EXACT_FONTS = {
    "Helvetica": "Helvetica",
    "Helvetica-Bold": "Helvetica-Bold",
    "Helvetica-Oblique": "Helvetica-Oblique",
    "Helvetica-BoldOblique": "Helvetica-BoldOblique",
    "Times-Roman": "Times-Roman",
    "Times-Bold": "Times-Bold",
    "Times-Italic": "Times-Italic",
    "Times-BoldItalic": "Times-BoldItalic",
    "Courier": "Courier",
    "Courier-Bold": "Courier-Bold",
    "Courier-Oblique": "Courier-Oblique",
    "Courier-BoldOblique": "Courier-BoldOblique",
    "Symbol": "Symbol",
    "ZapfDingbats": "ZapfDingbats",
}


# =============================================================================
# BASIC UTILS
# =============================================================================

def safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def sanitize_text(text):
    if text is None:
        return ""

    if not isinstance(text, str):
        text = str(text)

    return text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n").strip()


def as_color(value, default=black):
    """
    Converts extracted colors to ReportLab color.
    Supports:
    - #RRGGBB
    - integer RGB
    - tuple/list RGB
    """

    if value is None or value == "":
        return default

    try:
        if isinstance(value, str):
            value = value.strip()

            if value.startswith("#"):
                return HexColor(value)

            if value.isdigit():
                value = int(value)

        if isinstance(value, int):
            r = (value >> 16) & 255
            g = (value >> 8) & 255
            b = value & 255
            return (r / 255.0, g / 255.0, b / 255.0)

        if isinstance(value, (list, tuple)) and len(value) >= 3:
            r, g, b = value[:3]
            r = safe_float(r)
            g = safe_float(g)
            b = safe_float(b)

            if r > 1 or g > 1 or b > 1:
                r /= 255.0
                g /= 255.0
                b /= 255.0

            return (r, g, b)

    except Exception:
        return default

    return default


def resolve_font(font_name, flags=0, sample_text=""):
    font_name = sanitize_text(font_name)

    if font_name in SUPPORTED_EXACT_FONTS:
        return SUPPORTED_EXACT_FONTS[font_name]

    name = font_name.lower()

    bold = ("bold" in name) or bool(safe_int(flags) & 16)
    italic = (
        "italic" in name
        or "oblique" in name
        or bool(safe_int(flags) & 2)
    )

    if "zapfdingbats" in name:
        return "ZapfDingbats"

    if "symbol" in name:
        return "Symbol"

    if "times" in name:
        if bold and italic:
            return "Times-BoldItalic"
        if bold:
            return "Times-Bold"
        if italic:
            return "Times-Italic"
        return "Times-Roman"

    if "courier" in name or "mono" in name:
        if bold and italic:
            return "Courier-BoldOblique"
        if bold:
            return "Courier-Bold"
        if italic:
            return "Courier-Oblique"
        return "Courier"

    if bold and italic:
        return "Helvetica-BoldOblique"
    if bold:
        return "Helvetica-Bold"
    if italic:
        return "Helvetica-Oblique"

    return "Helvetica"


def bbox_to_values(bbox):
    if not bbox or len(bbox) != 4:
        return None

    return [safe_float(v) for v in bbox]


def rl_rect_from_bbox(bbox, page_h):
    """
    Converts PyMuPDF bbox [x0, y0, x1, y1]
    to ReportLab rect x, y, width, height.
    """

    values = bbox_to_values(bbox)

    if not values:
        return None

    x0, y0, x1, y1 = values

    return (
        x0,
        page_h - y1,
        max(x1 - x0, 0),
        max(y1 - y0, 0),
    )


def is_header_text_block(block, header_y_limit=55):
    """
    Header text blocks are preserved from original spans.
    This fixes the issue where green header band is visible
    but header text/logo disappears.
    """

    if block.get("type") != "text":
        return False

    bbox = block.get("bbox")

    if not bbox or len(bbox) != 4:
        return False

    y0 = safe_float(bbox[1])
    return y0 <= header_y_limit


# =============================================================================
# TEXT WRAPPING / FITTING
# =============================================================================

def wrap_text(text, font_name, font_size, max_width):
    text = sanitize_text(text)

    if not text:
        return []

    all_lines = []

    for paragraph in text.split("\n"):
        paragraph = paragraph.strip()

        if not paragraph:
            all_lines.append("")
            continue

        words = paragraph.split()
        current = ""

        for word in words:
            trial = word if not current else current + " " + word

            if stringWidth(trial, font_name, font_size) <= max_width:
                current = trial
            else:
                if current:
                    all_lines.append(current)
                current = word

        if current:
            all_lines.append(current)

    final_lines = []

    for line in all_lines:
        if stringWidth(line, font_name, font_size) <= max_width:
            final_lines.append(line)
            continue

        buffer = ""

        for ch in line:
            trial = buffer + ch

            if stringWidth(trial, font_name, font_size) <= max_width:
                buffer = trial
            else:
                if buffer:
                    final_lines.append(buffer)
                buffer = ch

        if buffer:
            final_lines.append(buffer)

    return final_lines


def fit_text_to_box(
    text,
    font_name,
    start_font_size,
    box_width,
    box_height,
    min_font_size=4.5,
    horizontal_padding=1.5,
    vertical_padding=1.5,
):
    text = sanitize_text(text)

    max_width = max(box_width - (horizontal_padding * 2), 2)
    max_height = max(box_height - (vertical_padding * 2), 2)

    font_size = safe_float(start_font_size, 10.0)

    while font_size >= min_font_size:
        lines = wrap_text(text, font_name, font_size, max_width)
        line_height = font_size * 1.18
        needed_height = len(lines) * line_height

        if needed_height <= max_height:
            return font_size, lines, True

        font_size -= 0.35

    fallback_lines = wrap_text(text, font_name, min_font_size, max_width)
    return min_font_size, fallback_lines, False


def get_first_span_style(block):
    props = block.get("properties") or {}
    lines = props.get("lines") or []

    for line in lines:
        if not isinstance(line, dict):
            continue

        spans = line.get("spans") or []

        for span in spans:
            if not isinstance(span, dict):
                continue

            return {
                "font": span.get("font", "Helvetica"),
                "font_size": safe_float(span.get("font_size"), 10.0),
                "color": span.get("color", "#000000"),
                "flags": safe_int(span.get("flags", 0)),
            }

    return {
        "font": "Helvetica",
        "font_size": 10.0,
        "color": "#000000",
        "flags": 0,
    }


# =============================================================================
# TRANSLATION JSON UPDATE
# =============================================================================

def apply_translations_to_json(json_data, translated_text_by_block_id):
    """
    Adds translated text into properties['translated_text'].
    Does NOT destroy original spans.
    """

    updated_json = deepcopy(json_data)

    for document in updated_json.get("documents", []):
        for page in document.get("pages", []):
            for block in page.get("blocks", []):
                block_id = block.get("block_id")

                if not block_id:
                    continue

                if block_id not in translated_text_by_block_id:
                    continue

                translated_text = sanitize_text(
                    translated_text_by_block_id.get(block_id, "")
                )

                if not translated_text:
                    continue

                if block.get("type") == "text":
                    props = block.setdefault("properties", {})
                    props["translated_text"] = translated_text

    return updated_json


# =============================================================================
# DRAW BASIC BLOCKS
# =============================================================================

def draw_rect(c, bbox, props, page_h):
    if not bbox:
        return

    rect = rl_rect_from_bbox(bbox, page_h)

    if not rect:
        return

    x, y, w, h = rect

    fill = (
        props.get("fill_color")
        or props.get("fill")
        or props.get("color")
        or props.get("background")
        or "#FFFFFF"
    )

    stroke = (
        props.get("stroke_color")
        or props.get("stroke")
        or props.get("border_color")
    )

    stroke_width = safe_float(
        props.get("stroke_width")
        or props.get("border_width"),
        0,
    )

    c.saveState()

    try:
        if props.get("fill_opacity") is not None:
            c.setFillAlpha(safe_float(props.get("fill_opacity"), 1.0))

        if props.get("stroke_opacity") is not None:
            c.setStrokeAlpha(safe_float(props.get("stroke_opacity"), 1.0))
    except Exception:
        pass

    c.setFillColor(as_color(fill, white))

    if stroke and stroke_width > 0:
        c.setStrokeColor(as_color(stroke, black))
        c.setLineWidth(stroke_width)
        c.rect(x, y, w, h, fill=1, stroke=1)
    else:
        c.rect(x, y, w, h, fill=1, stroke=0)

    c.restoreState()


def draw_line_block(c, block, page_h):
    props = block.get("properties") or {}
    segments = props.get("segments") or [block.get("bbox")]

    c.saveState()

    c.setStrokeColor(
        as_color(
            props.get("stroke_color")
            or props.get("color"),
            black,
        )
    )

    c.setLineWidth(
        safe_float(
            props.get("stroke_width")
            or props.get("width"),
            1.0,
        )
    )

    for segment in segments:
        if not segment or len(segment) != 4:
            continue

        x0, y0, x1, y1 = [safe_float(v) for v in segment]
        c.line(x0, page_h - y0, x1, page_h - y1)

    c.restoreState()


def draw_image_block(c, block, page_h):
    props = block.get("properties") or {}

    image_data = (
        props.get("image")
        or props.get("image_data")
        or props.get("data")
        or props.get("base64")
        or props.get("image_base64")
    )

    image_path = (
        props.get("image_path")
        or props.get("path")
        or props.get("file_path")
        or props.get("saved_path")
        or props.get("image_file")
    )

    bbox = block.get("bbox")

    if not bbox or len(bbox) != 4:
        return

    rect = rl_rect_from_bbox(bbox, page_h)

    if not rect:
        return

    x, y, w, h = rect

    try:
        if image_data:
            if isinstance(image_data, str) and image_data.startswith("data:image"):
                image_data = image_data.split(",", 1)[1]

            if isinstance(image_data, str):
                import io
                raw = base64.b64decode(image_data)
                reader = ImageReader(io.BytesIO(raw))

                c.drawImage(
                    reader,
                    x,
                    y,
                    w,
                    h,
                    preserveAspectRatio=False,
                    mask="auto",
                )

                return

        if image_path and os.path.exists(image_path):
            reader = ImageReader(image_path)

            c.drawImage(
                reader,
                x,
                y,
                w,
                h,
                preserveAspectRatio=False,
                mask="auto",
            )

            return

    except Exception as e:
        print(f"IMAGE_RENDER_ERROR block_id={block.get('block_id')} error={e}")


def draw_ellipse_block(c, block, page_h):
    bbox = block.get("bbox")

    if not bbox or len(bbox) != 4:
        return

    rect = rl_rect_from_bbox(bbox, page_h)

    if not rect:
        return

    x, y, w, h = rect
    props = block.get("properties") or {}

    fill = (
        props.get("fill_color")
        or props.get("color")
        or props.get("fill")
        or "#FFFFFF"
    )

    stroke = (
        props.get("stroke_color")
        or props.get("stroke")
        or props.get("border_color")
    )

    stroke_width = safe_float(
        props.get("stroke_width")
        or props.get("border_width"),
        0,
    )

    c.saveState()
    c.setFillColor(as_color(fill, white))

    if stroke and stroke_width > 0:
        c.setStrokeColor(as_color(stroke, black))
        c.setLineWidth(stroke_width)
        c.ellipse(x, y, x + w, y + h, fill=1, stroke=1)
    else:
        c.ellipse(x, y, x + w, y + h, fill=1, stroke=0)

    c.restoreState()


def draw_unknown_shape_block(c, block, page_h):
    props = block.get("properties") or {}
    bbox = block.get("bbox")

    if not bbox or len(bbox) != 4:
        return

    has_fill = (
        props.get("fill_color")
        or props.get("fill")
        or props.get("color")
    )

    if has_fill:
        draw_rect(c, bbox, props, page_h)


# =============================================================================
# DRAW TEXT
# =============================================================================

def draw_span(c, span, page_h, rotation=0):
    text = sanitize_text(span.get("text", ""))

    if not text:
        return

    bbox = span.get("bbox")

    if not bbox or len(bbox) != 4:
        return

    font_name = resolve_font(
        span.get("font"),
        span.get("flags", 0),
        text,
    )

    font_size = safe_float(span.get("font_size"), 10.0)
    color = as_color(span.get("color"), black)

    x0, y0, x1, y1 = [safe_float(v) for v in bbox]

    try:
        descent = abs(getDescent(font_name) / 1000.0 * font_size)
    except Exception:
        descent = 0.20 * font_size

    baseline = page_h - y1 + descent

    c.saveState()
    c.setFillColor(color)
    c.setFont(font_name, font_size)

    if rotation:
        c.translate(x0, baseline)
        c.rotate(-safe_float(rotation, 0.0))
        c.drawString(0, 0, text)
    else:
        c.drawString(x0, baseline, text)

    c.restoreState()


def draw_original_text_block(c, block, page_h):
    props = block.get("properties") or {}
    rotation = safe_float(block.get("rotation"), 0.0)
    lines = props.get("lines") or []

    for line in lines:
        if not isinstance(line, dict):
            continue

        spans = line.get("spans") or []

        if spans:
            for span in spans:
                draw_span(c, span, page_h, rotation=rotation)
        else:
            text = sanitize_text(line.get("text", ""))
            bbox = line.get("bbox")

            if text and bbox and len(bbox) == 4:
                fake_span = {
                    "text": text,
                    "bbox": bbox,
                    "font": "Helvetica",
                    "font_size": 10,
                    "color": "#000000",
                    "flags": 0,
                }
                draw_span(c, fake_span, page_h, rotation=rotation)


def draw_translated_text_block(c, block, page_h):
    props = block.get("properties") or {}
    translated_text = sanitize_text(props.get("translated_text", ""))

    if not translated_text:
        return False

    bbox = block.get("bbox")

    if not bbox or len(bbox) != 4:
        return False

    x0, y0, x1, y1 = [safe_float(v) for v in bbox]

    block_width = max(x1 - x0, 1)
    block_height = max(y1 - y0, 1)

    style = get_first_span_style(block)

    font_name = resolve_font(
        style.get("font"),
        style.get("flags", 0),
        translated_text,
    )

    start_font_size = safe_float(style.get("font_size"), 10.0)
    color = as_color(style.get("color"), black)

    fitted_size, lines, fitted = fit_text_to_box(
        text=translated_text,
        font_name=font_name,
        start_font_size=start_font_size,
        box_width=block_width,
        box_height=block_height,
    )

    c.saveState()
    c.setFillColor(color)
    c.setFont(font_name, fitted_size)

    line_height = fitted_size * 1.18

    current_y = page_h - y0 - fitted_size
    min_y = page_h - y1

    for line in lines:
        if current_y < min_y:
            break

        c.drawString(x0, current_y, line)
        current_y -= line_height

    c.restoreState()

    return True


def draw_text_block(c, block, page_h):
    """
    Important:
    - Header blocks are drawn from original spans.
    - Other blocks use translated_text when available.
    """

    if block.get("type") != "text":
        return

    # ✅ Header fix: keep original header text exactly.
    if is_header_text_block(block):
        draw_original_text_block(c, block, page_h)
        return

    props = block.get("properties") or {}

    if props.get("translated_text"):
        rendered = draw_translated_text_block(c, block, page_h)

        if rendered:
            return

    draw_original_text_block(c, block, page_h)


# =============================================================================
# TABLE SUPPORT
# =============================================================================

def cluster_positions(values, tol=1.0):
    values = sorted(float(v) for v in values)

    if not values:
        return []

    groups = [[values[0]]]

    for value in values[1:]:
        if abs(value - groups[-1][-1]) <= tol:
            groups[-1].append(value)
        else:
            groups.append([value])

    return [sum(group) / len(group) for group in groups]


def flatten_cell_bboxes(cell_bboxes):
    flat = []

    def walk(node):
        if isinstance(node, list):
            if len(node) == 4 and all(isinstance(x, (int, float)) for x in node):
                flat.append([float(x) for x in node])
            else:
                for item in node:
                    walk(item)

    walk(cell_bboxes)
    return flat


def normalize_table_cells(table_bbox, rows, cols):
    if not table_bbox or len(table_bbox) != 4:
        return []

    x0, y0, x1, y1 = [safe_float(v) for v in table_bbox]

    dx = (x1 - x0) / max(cols, 1)
    dy = (y1 - y0) / max(rows, 1)

    matrix = []

    for r in range(rows):
        row_boxes = []

        for c_index in range(cols):
            row_boxes.append([
                x0 + c_index * dx,
                y0 + r * dy,
                x0 + (c_index + 1) * dx,
                y0 + (r + 1) * dy,
            ])

        matrix.append(row_boxes)

    return matrix


def fit_text_to_cell(text, font_name, start_size, cell_w, cell_h):
    fitted_size, lines, fitted = fit_text_to_box(
        text=text,
        font_name=font_name,
        start_font_size=start_size,
        box_width=cell_w,
        box_height=cell_h,
        min_font_size=4.5,
        horizontal_padding=2,
        vertical_padding=2,
    )

    return fitted_size, lines


def draw_table_block(c, table_block, all_blocks, page_h):
    props = table_block.get("properties") or {}
    data = props.get("data") or props.get("rows") or []

    if not data:
        return

    table_bbox = table_block.get("bbox")

    if not table_bbox:
        return

    rows = safe_int(props.get("row_count"), len(data))
    cols = safe_int(
        props.get("column_count"),
        max((len(row) for row in data if isinstance(row, list)), default=0),
    )

    if rows <= 0 or cols <= 0:
        return

    flat_data = []

    for row in data:
        if isinstance(row, list):
            flat_data.extend(row)
        else:
            flat_data.append(row)

    normalized_data = []
    idx = 0

    for _ in range(rows):
        row = flat_data[idx:idx + cols]
        idx += cols

        if len(row) < cols:
            row += [""] * (cols - len(row))

        normalized_data.append(row)

    cell_matrix = normalize_table_cells(table_bbox, rows, cols)

    for row_index in range(rows):
        for col_index in range(cols):
            try:
                bbox = cell_matrix[row_index][col_index]
                cell_text = sanitize_text(normalized_data[row_index][col_index])
            except Exception:
                continue

            rect = rl_rect_from_bbox(bbox, page_h)

            if not rect:
                continue

            x, y, w, h = rect

            c.saveState()
            c.setStrokeColor(black)
            c.setLineWidth(0.3)
            c.rect(x, y, w, h, stroke=1, fill=0)
            c.restoreState()

            if not cell_text:
                continue

            font_name = "Helvetica"
            start_size = 7.5

            fitted_size, lines = fit_text_to_cell(
                cell_text,
                font_name,
                start_size,
                w,
                h,
            )

            c.saveState()
            c.setFont(font_name, fitted_size)
            c.setFillColor(black)

            line_height = fitted_size * 1.18
            current_y = y + h - fitted_size - 2
            min_y = y + 1

            for line in lines:
                if current_y < min_y:
                    break

                c.drawString(x + 2, current_y, line)
                current_y -= line_height

            c.restoreState()


# =============================================================================
# RECONSTRUCTION MAIN
# =============================================================================

def get_documents_from_payload(payload):
    if isinstance(payload, dict) and "documents" in payload:
        return payload["documents"]

    if isinstance(payload, dict) and "document" in payload:
        return [payload["document"]]

    if isinstance(payload, list):
        return payload

    raise ValueError("Unsupported JSON structure. Expected dict/list payload.")


def build_output_file_name(request_id):
    base_name = str(request_id).replace(".json", "")
    return f"translated_{base_name}.pdf"


def get_page_size(page):
    dims = page.get("dimensions") or {}

    width = (
        page.get("width")
        or page.get("page_width")
        or dims.get("width")
        or 612
    )

    height = (
        page.get("height")
        or page.get("page_height")
        or dims.get("height")
        or 792
    )

    return safe_float(width, 612), safe_float(height, 792)


def split_blocks_by_type(blocks):
    background_blocks = []
    image_blocks = []
    ellipse_blocks = []
    line_blocks = []
    table_blocks = []
    text_blocks = []
    other_blocks = []

    for block in blocks:
        block_type = str(block.get("type", "unknown")).lower()

        if block_type in (
            "filled_rect",
            "rect",
            "rectangle",
            "background",
            "shape_rect",
            "filled_rectangle",
        ):
            background_blocks.append(block)

        elif block_type == "image":
            image_blocks.append(block)

        elif block_type in (
            "circle",
            "ellipse",
            "filled_circle",
            "filled_ellipse",
            "shape_circle",
            "shape_ellipse",
        ):
            ellipse_blocks.append(block)

        elif block_type == "line":
            line_blocks.append(block)

        elif block_type == "table":
            table_blocks.append(block)

        elif block_type == "text":
            text_blocks.append(block)

        else:
            other_blocks.append(block)

    return {
        "background": background_blocks,
        "image": image_blocks,
        "ellipse": ellipse_blocks,
        "line": line_blocks,
        "table": table_blocks,
        "text": text_blocks,
        "other": other_blocks,
    }


def reconstruct_translated_pdf_from_json_payload(
    request_id,
    payload,
    output_dir=None,
    output_file_name=None,
):
    """
    Reconstructs translated PDF from layout JSON.

    Correct order:
    1. white page background
    2. rectangles/backgrounds
    3. images
    4. ellipses/circles
    5. unknown shape fallback
    6. lines
    7. tables
    8. text LAST
    """

    if output_dir is None:
        output_dir = str(DOWNLOADS_DIR)

    os.makedirs(output_dir, exist_ok=True)

    documents = get_documents_from_payload(payload)

    if not documents:
        raise ValueError("No documents found in JSON payload.")

    output_file_name = output_file_name or build_output_file_name(request_id)
    output_path = os.path.join(output_dir, output_file_name)

    first_pages = documents[0].get("pages", [])

    if not first_pages:
        raise ValueError("No pages found in JSON payload.")

    first_page_w, first_page_h = get_page_size(first_pages[0])

    c = canvas.Canvas(
        output_path,
        pagesize=(first_page_w, first_page_h),
        bottomup=1,
    )

    logs = []
    block_types = {}

    for document in documents:
        for page in document.get("pages", []):
            page_w, page_h = get_page_size(page)

            c.setPageSize((page_w, page_h))

            # Base white background
            c.saveState()
            c.setFillColor(white)
            c.rect(0, 0, page_w, page_h, fill=1, stroke=0)
            c.restoreState()

            blocks = page.get("blocks", []) or []

            blocks = sorted(
                blocks,
                key=lambda b: (
                    safe_int(b.get("z_index", 0)),
                    str(b.get("block_id", "")),
                ),
            )

            for block in blocks:
                block_type = str(block.get("type", "unknown")).lower()
                block_types[block_type] = block_types.get(block_type, 0) + 1

            grouped = split_blocks_by_type(blocks)

            # 1. Background rectangles
            for block in grouped["background"]:
                try:
                    draw_rect(
                        c,
                        block.get("bbox"),
                        block.get("properties") or {},
                        page_h,
                    )
                except Exception as e:
                    logs.append({
                        "status": "BACKGROUND_RENDER_ERROR",
                        "block_id": block.get("block_id"),
                        "error": str(e),
                    })

            # 2. Images
            for block in grouped["image"]:
                try:
                    draw_image_block(c, block, page_h)
                except Exception as e:
                    logs.append({
                        "status": "IMAGE_RENDER_ERROR",
                        "block_id": block.get("block_id"),
                        "error": str(e),
                    })

            # 3. Ellipses / circles
            for block in grouped["ellipse"]:
                try:
                    draw_ellipse_block(c, block, page_h)
                except Exception as e:
                    logs.append({
                        "status": "ELLIPSE_RENDER_ERROR",
                        "block_id": block.get("block_id"),
                        "error": str(e),
                    })

            # 4. Unknown shape-like fallback
            for block in grouped["other"]:
                try:
                    draw_unknown_shape_block(c, block, page_h)
                except Exception as e:
                    logs.append({
                        "status": "OTHER_RENDER_ERROR",
                        "block_id": block.get("block_id"),
                        "type": block.get("type"),
                        "error": str(e),
                    })

            # 5. Lines
            for block in grouped["line"]:
                try:
                    draw_line_block(c, block, page_h)
                except Exception as e:
                    logs.append({
                        "status": "LINE_RENDER_ERROR",
                        "block_id": block.get("block_id"),
                        "error": str(e),
                    })

            # 6. Tables
            for block in grouped["table"]:
                try:
                    draw_table_block(c, block, blocks, page_h)
                except Exception as e:
                    logs.append({
                        "status": "TABLE_RENDER_ERROR",
                        "block_id": block.get("block_id"),
                        "error": str(e),
                    })

            # 7. Text LAST
            for block in grouped["text"]:
                try:
                    draw_text_block(c, block, page_h)
                except Exception as e:
                    logs.append({
                        "status": "TEXT_RENDER_ERROR",
                        "block_id": block.get("block_id"),
                        "error": str(e),
                    })

            c.showPage()

    c.save()

    # IMPORTANT:
    # pdf_translation_service.py expects these exact keys.
    return {
        "output_file_name": output_file_name,
        "output_name": output_file_name,
        "output_path": output_path,

        # Your app.py mounts static/downloads as /downloads.
        "output_url": f"/downloads/{output_file_name}",
        "download_url": f"/downloads/{output_file_name}",

        "logs": logs,
        "block_types": block_types,
    }


def reconstruct_translated_pdf(
    request_id,
    json_data,
    translated_text_by_block_id,
    output_dir=None,
    output_file_name=None,
):
    """
    High-level function used by pdf_translation_service.py.

    Steps:
    1. Add translated_text to JSON text blocks.
    2. Reconstruct PDF from updated JSON.
    """

    translated_json = apply_translations_to_json(
        json_data=json_data,
        translated_text_by_block_id=translated_text_by_block_id,
    )

    result = reconstruct_translated_pdf_from_json_payload(
        request_id=request_id,
        payload=translated_json,
        output_dir=output_dir,
        output_file_name=output_file_name,
    )

    return result