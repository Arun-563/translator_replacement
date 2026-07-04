import fitz  # PyMuPDF
import json
import os
from collections import Counter
from datetime import datetime

# =========================================================
# CONFIG
# =========================================================


# Overlap threshold to skip text blocks that are already covered by a table
TABLE_TEXT_OVERLAP_THRESHOLD = 0.60

# Bullet marker size thresholds (points)
MAX_BULLET_SIZE = 14

# =========================================================
# HELPERS
# =========================================================
def is_text_page(page, min_chars=20):
    text = page.get_text().strip()
    return len(text) > min_chars


def rect_to_list(rect):
    if rect is None:
        return None
    if isinstance(rect, fitz.Rect):
        return [rect.x0, rect.y0, rect.x1, rect.y1]
    return list(rect)


def normalize_rect(rect):
    """Return fitz.Rect safely from tuple/list/Rect."""
    if rect is None:
        return None
    if isinstance(rect, fitz.Rect):
        return rect
    return fitz.Rect(rect)


def intersect_ratio(inner_rect, outer_rect):
    """
    Ratio of intersection area over inner_rect area.
    Useful to know if a text block is mostly inside a table bbox.
    """
    r1 = normalize_rect(inner_rect)
    r2 = normalize_rect(outer_rect)
    if not r1 or not r2:
        return 0.0
    inter = r1 & r2
    if inter.is_empty:
        return 0.0
    a1 = max(r1.get_area(), 1e-6)
    return inter.get_area() / a1


def color_to_hex(color):
    """
    Convert PyMuPDF color values to #RRGGBB.
    Supports:
      - int colors from text spans (0xRRGGBB)
      - tuple/list floats in range 0..1
      - tuple/list ints in range 0..255
      - None
    """
    if color is None:
        return None

    # Text spans usually return int like 0xRRGGBB
    if isinstance(color, int):
        r = (color >> 16) & 255
        g = (color >> 8) & 255
        b = color & 255
        return f"#{r:02X}{g:02X}{b:02X}"

    # Drawings may return tuple/list
    if isinstance(color, (tuple, list)):
        vals = list(color)
        if len(vals) >= 3:
            # floats 0..1
            if all(isinstance(v, (int, float)) for v in vals[:3]):
                if all(0.0 <= float(v) <= 1.0 for v in vals[:3]):
                    r = round(vals[0] * 255)
                    g = round(vals[1] * 255)
                    b = round(vals[2] * 255)
                    return f"#{r:02X}{g:02X}{b:02X}"
                # ints 0..255
                r = int(vals[0])
                g = int(vals[1])
                b = int(vals[2])
                return f"#{r:02X}{g:02X}{b:02X}"

    return None


def get_span_text(span):
    """
    Reconstruct exact span text from raw chars if available.
    Helps preserve bullets and special glyphs better than plain 'dict'.
    """
    chars = span.get("chars", [])
    if chars:
        return "".join(ch.get("c", "") for ch in chars)
    return span.get("text", "")


def block_inside_any_table(block_bbox, table_bboxes, threshold=TABLE_TEXT_OVERLAP_THRESHOLD):
    bb = normalize_rect(block_bbox)
    for tb in table_bboxes:
        if intersect_ratio(bb, tb) >= threshold:
            return True
    return False


def detect_document_source_type(doc):
    text_pages = 0
    scanned_pages = 0

    for page in doc:
        if is_text_page(page):
            text_pages += 1
        else:
            scanned_pages += 1

    if text_pages > 0 and scanned_pages == 0:
        return "digital"
    elif scanned_pages > 0 and text_pages == 0:
        return "scanned"
    elif text_pages > 0 and scanned_pages > 0:
        return "mixed"
    return "unknown"


def is_probable_bullet_rect(rect, fill_hex, stroke_hex):
    """
    Detect small filled rectangles likely used as square bullets.
    Example in your sample: little black squares before 'Full-Time', etc.
    """
    if rect is None:
        return False
    w = rect.width
    h = rect.height
    if w <= MAX_BULLET_SIZE and h <= MAX_BULLET_SIZE:
        if fill_hex is not None:
            # Most bullet squares are nearly square and filled
            aspect = max(w, h) / max(min(w, h), 0.0001)
            if aspect <= 1.6:
                return True
    return False


def extract_drawings(page, file_name, page_num, start_id):
    """
    Extract vector graphics:
      - filled rectangles (header/footer bars, table header fills, etc.)
      - stroked rectangles
      - lines
      - generic vector paths
      - bullet markers drawn as shapes
    """
    blocks = []
    background_regions = []
    vector_regions_for_style = []  # keep filled regions for table/header color reasoning
    block_id_counter = start_id

    page_area = page.rect.get_area()
    drawings = page.get_drawings()

    for d in drawings:
        d_rect = normalize_rect(d.get("rect"))
        items = d.get("items", [])
        fill_hex = color_to_hex(d.get("fill"))
        stroke_hex = color_to_hex(d.get("color"))
        stroke_width = d.get("width")
        fill_opacity = d.get("fill_opacity")
        stroke_opacity = d.get("stroke_opacity")

        # Determine basic vector type
        item_ops = [it[0] for it in items] if items else []

        # --- Small filled rect bullet markers ---
        if d_rect and is_probable_bullet_rect(d_rect, fill_hex, stroke_hex):
            bullet_block = {
                "block_id": f"{file_name}_p{page_num}_b{block_id_counter}",
                "type": "bullet_marker",
                "bbox": rect_to_list(d_rect),
                "z_index": block_id_counter,
                "rotation": 0,
                "properties": {
                    "shape": "square",
                    "fill_color": fill_hex,
                    "stroke_color": stroke_hex,
                    "stroke_width": stroke_width,
                    "fill_opacity": fill_opacity,
                    "stroke_opacity": stroke_opacity
                }
            }
            blocks.append(bullet_block)
            block_id_counter += 1
            continue

        # --- Filled/stroked rectangles and vector regions ---
        if d_rect and ("re" in item_ops or len(item_ops) == 0):
            vector_type = "vector_rect"
            if fill_hex and not stroke_hex:
                vector_type = "filled_rect"
            elif fill_hex and stroke_hex:
                vector_type = "filled_stroked_rect"
            elif stroke_hex:
                vector_type = "stroked_rect"

            vector_block = {
                "block_id": f"{file_name}_p{page_num}_b{block_id_counter}",
                "type": vector_type,
                "bbox": rect_to_list(d_rect),
                "z_index": block_id_counter,
                "rotation": 0,
                "properties": {
                    "fill_color": fill_hex,
                    "stroke_color": stroke_hex,
                    "stroke_width": stroke_width,
                    "fill_opacity": fill_opacity,
                    "stroke_opacity": stroke_opacity
                }
            }
            blocks.append(vector_block)

            # Save filled regions as page/background/layout regions
            if fill_hex:
                region = {
                    "bbox": rect_to_list(d_rect),
                    "fill_color": fill_hex,
                    "stroke_color": stroke_hex,
                    "stroke_width": stroke_width,
                    "fill_opacity": fill_opacity,
                    "stroke_opacity": stroke_opacity
                }
                vector_regions_for_style.append(region)

                # Treat large filled rectangles as background regions
                if d_rect.get_area() / max(page_area, 1e-6) > 0.02 or d_rect.width > page.rect.width * 0.50:
                    background_regions.append(region)

            block_id_counter += 1
            continue

        # --- Line / polyline / path ---
        if items:
            line_points = []
            for it in items:
                op = it[0]
                if op == "l":
                    p1, p2 = it[1], it[2]
                    line_points.append([p1.x, p1.y, p2.x, p2.y])

            if line_points:
                line_block = {
                    "block_id": f"{file_name}_p{page_num}_b{block_id_counter}",
                    "type": "line",
                    "bbox": rect_to_list(d_rect) if d_rect else None,
                    "z_index": block_id_counter,
                    "rotation": 0,
                    "properties": {
                        "segments": line_points,
                        "stroke_color": stroke_hex,
                        "stroke_width": stroke_width,
                        "stroke_opacity": stroke_opacity
                    }
                }
            else:
                line_block = {
                    "block_id": f"{file_name}_p{page_num}_b{block_id_counter}",
                    "type": "vector_path",
                    "bbox": rect_to_list(d_rect) if d_rect else None,
                    "z_index": block_id_counter,
                    "rotation": 0,
                    "properties": {
                        "ops": item_ops,
                        "fill_color": fill_hex,
                        "stroke_color": stroke_hex,
                        "stroke_width": stroke_width,
                        "fill_opacity": fill_opacity,
                        "stroke_opacity": stroke_opacity
                    }
                }

            blocks.append(line_block)
            block_id_counter += 1

    return blocks, background_regions, vector_regions_for_style, block_id_counter


def build_cell_bboxes(table):
    """
    Build a 2D matrix of cell bboxes if available.
    PyMuPDF table.cells is usually a flat list row-major.
    """
    try:
        cells = table.cells
        row_count = table.row_count
        col_count = table.col_count
        if not cells or row_count <= 0 or col_count <= 0:
            return []

        grid = []
        idx = 0
        for _ in range(row_count):
            row = []
            for _ in range(col_count):
                c = cells[idx] if idx < len(cells) else None
                row.append(rect_to_list(c) if c else None)
                idx += 1
            grid.append(row)
        return grid
    except Exception:
        return []


def detect_table_header_fill_color(header_bbox, vector_regions_for_style):
    """
    Infer dominant fill color overlapping the table header row area.
    """
    if not header_bbox:
        return None

    header_rect = normalize_rect(header_bbox)
    colors = []

    for region in vector_regions_for_style:
        fill_color = region.get("fill_color")
        bbox = region.get("bbox")
        if not fill_color or not bbox:
            continue

        overlap = intersect_ratio(bbox, header_rect)
        # Region mostly lies in the header row
        if overlap > 0.30 or intersect_ratio(header_rect, bbox) > 0.30:
            colors.append(fill_color)

    if not colors:
        return None

    return Counter(colors).most_common(1)[0][0]


def extract_tables(page, file_name, page_num, start_id, vector_regions_for_style):
    """
    Extract tables once, with bbox, data, cell bboxes, and header styling if detectable.
    """
    blocks = []
    table_bboxes = []
    block_id_counter = start_id

    try:
        tables = page.find_tables()
        if tables.tables:
            for t_idx, table in enumerate(tables.tables, start=1):
                table_bbox = normalize_rect(table.bbox)
                table_bboxes.append(table_bbox)

                data = table.extract()
                row_count = getattr(table, "row_count", len(data))
                col_count = getattr(table, "col_count", max((len(row) for row in data), default=0))

                cell_bboxes = build_cell_bboxes(table)

                # header bbox from first row cell rects if possible
                header_bbox = None
                if cell_bboxes and cell_bboxes[0]:
                    first_row = [normalize_rect(c) for c in cell_bboxes[0] if c]
                    if first_row:
                        x0 = min(c.x0 for c in first_row)
                        y0 = min(c.y0 for c in first_row)
                        x1 = max(c.x1 for c in first_row)
                        y1 = max(c.y1 for c in first_row)
                        header_bbox = fitz.Rect(x0, y0, x1, y1)

                header_fill_color = detect_table_header_fill_color(header_bbox, vector_regions_for_style)

                table_block = {
                    "block_id": f"{file_name}_p{page_num}_b{block_id_counter}",
                    "type": "table",
                    "bbox": rect_to_list(table_bbox),
                    "z_index": block_id_counter,
                    "rotation": 0,
                    "properties": {
                        "table_index": t_idx,
                        "row_count": row_count,
                        "column_count": col_count,
                        "data": data,
                        "cell_bboxes": cell_bboxes,
                        "header": {
                            "bbox": rect_to_list(header_bbox) if header_bbox else None,
                            "fill_color": header_fill_color,
                            "texts": data[0] if data else []
                        }
                    }
                }

                blocks.append(table_block)
                block_id_counter += 1

    except Exception:
        pass

    return blocks, table_bboxes, block_id_counter


def extract_text_blocks(page, file_name, page_num, start_id, table_bboxes):
    """
    Extract text blocks while skipping blocks mostly inside tables
    (to avoid duplicate table text extraction).
    Uses RAWDICT to better preserve bullets and symbol glyphs.
    """
    blocks = []
    block_id_counter = start_id

    text_dict = page.get_text("rawdict")

    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:
            continue

        block_bbox = block.get("bbox")
        if block_inside_any_table(block_bbox, table_bboxes):
            # Prevent duplicate table text
            continue

        block_entry = {
            "block_id": f"{file_name}_p{page_num}_b{block_id_counter}",
            "type": "text",
            "bbox": list(block_bbox),
            "z_index": block_id_counter,
            "rotation": 0,
            "properties": {}
        }

        lines_data = []

        for line in block.get("lines", []):
            line_entry = {
                "bbox": list(line.get("bbox")),
                "spans": [],
                "text": ""
            }

            for span in line.get("spans", []):
                text_val = get_span_text(span)
                if text_val is None:
                    continue

                # Preserve spaces/newlines if present, only fully skip empty spans
                if text_val == "":
                    continue

                span_entry = {
                    "text": text_val,
                    "font": span.get("font"),
                    "font_size": span.get("size"),
                    "color": color_to_hex(span.get("color")),
                    "bbox": list(span.get("bbox")) if span.get("bbox") else None,
                    "flags": span.get("flags")
                }

                line_entry["spans"].append(span_entry)

            if line_entry["spans"]:
                line_entry["text"] = "".join(s["text"] for s in line_entry["spans"])
                lines_data.append(line_entry)

        if lines_data:
            block_entry["properties"]["lines"] = lines_data
            blocks.append(block_entry)
            block_id_counter += 1

    return blocks, block_id_counter


def extract_images(page, file_name, page_num, start_id, table_bboxes):
    """
    Extract image blocks. If an image is completely inside a table area, skip it
    to avoid duplicate nested extraction noise.
    """
    blocks = []
    block_id_counter = start_id

    images = page.get_images(full=True)

    for img in images:
        xref = img[0]
        try:
            rects = page.get_image_rects(xref)
        except Exception:
            rects = []

        for rect in rects:
            if block_inside_any_table(rect, table_bboxes):
                continue

            image_block = {
                "block_id": f"{file_name}_p{page_num}_b{block_id_counter}",
                "type": "image",
                "bbox": [rect.x0, rect.y0, rect.x1, rect.y1],
                "z_index": block_id_counter,
                "rotation": 0,
                "properties": {
                    "xref": xref
                }
            }

            blocks.append(image_block)
            block_id_counter += 1

    return blocks, block_id_counter


# =========================================================
# MAIN
# =========================================================

# =========================================================
# DEPLOYMENT ENTRYPOINT
# =========================================================
def process_pdf(input_pdf_path: str, output_json_path: str, payload=None) -> dict:
    """
    PDF extraction entrypoint used by pdf_service.py.

    Flow:
      1. pdf_service.py receives a PDF from frontend.
      2. pdf_service.py saves it temporarily and decides the timestamp-based JSON path.
      3. This function reads input_pdf_path, applies the extraction logic from manual.py,
         and writes the JSON exactly to output_json_path.
      4. pdf_service.py uploads that JSON to S3.

    Parameters
    ----------
    input_pdf_path:
        Local temporary PDF path created by pdf_service.py.
    output_json_path:
        Local JSON output path created by pdf_service.py.
    payload:
        Frontend payload/instructions. It is preserved in the JSON for traceability.

    Returns
    -------
    dict
        The same JSON-compatible object that is written to output_json_path.
    """
    if payload is None:
        payload = []

    # -----------------------------
    # Input validation
    # -----------------------------
    if not input_pdf_path:
        raise ValueError("input_pdf_path is required")

    if not output_json_path:
        raise ValueError("output_json_path is required")

    if not os.path.exists(input_pdf_path):
        raise FileNotFoundError(f"Input PDF does not exist: {input_pdf_path}")

    if not input_pdf_path.lower().endswith(".pdf"):
        raise ValueError("Invalid file type. Only PDF file is allowed.")

    output_dir = os.path.dirname(output_json_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    file_name = os.path.basename(input_pdf_path)
    doc = None

    try:
        # -----------------------------
        # Open PDF
        # -----------------------------
        try:
            doc = fitz.open(input_pdf_path)
        except Exception as e:
            raise RuntimeError(f"Failed to open PDF {file_name}: {e}") from e

        # -----------------------------
        # Process document
        # -----------------------------
        source_type = detect_document_source_type(doc)

        document_data = {
            "document_metadata": {
                "file_name": file_name,
                "total_pages": len(doc),
                "source_type": source_type,
                "processed_at": datetime.now().isoformat(timespec="seconds")
            },
            "pages": []
        }

        for page_num, page in enumerate(doc, start=1):
            page_data = {
                "page_number": page_num,
                "dimensions": {
                    "width": page.rect.width,
                    "height": page.rect.height
                },
                "background": {
                    "color": None,
                    "image": None,
                    "regions": []
                },
                "blocks": []
            }

            block_id_counter = 1

            # 1) Drawings / vector graphics / background regions
            drawing_blocks, background_regions, vector_regions_for_style, block_id_counter = extract_drawings(
                page, file_name, page_num, block_id_counter
            )

            if background_regions:
                largest_region = max(
                    background_regions,
                    key=lambda r: normalize_rect(r["bbox"]).get_area() if r.get("bbox") else 0
                )
                page_data["background"]["color"] = largest_region.get("fill_color")
                page_data["background"]["regions"] = background_regions

            # 2) Tables - before text so table text can be skipped from normal text blocks
            table_blocks, table_bboxes, block_id_counter = extract_tables(
                page, file_name, page_num, block_id_counter, vector_regions_for_style
            )

            # 3) Text blocks - skips text already covered by detected table bboxes
            text_blocks, block_id_counter = extract_text_blocks(
                page, file_name, page_num, block_id_counter, table_bboxes
            )

            # 4) Images / logos
            image_blocks, block_id_counter = extract_images(
                page, file_name, page_num, block_id_counter, table_bboxes
            )

            # Preserve extraction order from manual.py
            page_data["blocks"].extend(drawing_blocks)
            page_data["blocks"].extend(table_blocks)
            page_data["blocks"].extend(text_blocks)
            page_data["blocks"].extend(image_blocks)

            document_data["pages"].append(page_data)

        final_output = {
            "documents": [document_data],
            "payload": payload
        }

        # -----------------------------
        # Save exactly where pdf_service.py tells us
        # -----------------------------
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(final_output, f, indent=4, ensure_ascii=False)

        return final_output

    finally:
        if doc is not None:
            doc.close()

 