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
# Fixes included:
# 1. Draw order: backgrounds/shapes first, text last.
# 2. Header text preserved from original spans.
# 3. Footer keeps original left/right layout, so page number stays right aligned.
# 4. Header logo/badge circular shape is preserved when extracted as square rect.
# 5. Return keys compatible with pdf_translation_service.py:
#    output_file_name, output_path, output_url, download_url.
# =============================================================================

APP_DIR = Path(__file__).resolve().parents[1]          # backend_code/app
BACKEND_DIR = APP_DIR.parent                           # backend_code
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
    Supports #RRGGBB, integer RGB, and tuple/list RGB.
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
    italic = "italic" in name or "oblique" in name or bool(safe_int(flags) & 2)

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
    values = bbox_to_values(bbox)
    if not values:
        return None
    x0, y0, x1, y1 = values
    return x0, page_h - y1, max(x1 - x0, 0), max(y1 - y0, 0)


def get_fill_value(props):
    return (
        props.get("fill_color")
        or props.get("fill")
        or props.get("color")
        or props.get("background")
    )


def is_whiteish_color(value):
    if value is None:
        return False
    try:
        if isinstance(value, str):
            v = value.strip().lower()
            return v in ("#fff", "#ffffff", "white")
        if isinstance(value, (list, tuple)) and len(value) >= 3:
            nums = [safe_float(x) for x in value[:3]]
            if max(nums) <= 1:
                return all(x >= 0.92 for x in nums)
            return all(x >= 235 for x in nums)
    except Exception:
        return False
    return False


def is_header_text_block(block, header_y_limit=55):
    if block.get("type") != "text":
        return False
    bbox = block.get("bbox")
    if not bbox or len(bbox) != 4:
        return False
    return safe_float(bbox[1]) <= header_y_limit


def is_footer_text_block(block, page_h, footer_y_limit=45):
    if block.get("type") != "text":
        return False
    bbox = block.get("bbox")
    if not bbox or len(bbox) != 4:
        return False
    return safe_float(bbox[1]) >= (page_h - footer_y_limit)


def is_logo_circle_candidate(block):
    """
    Fix for circular header badge becoming square.

    Some extractors output the white circular logo badge as a filled rectangle.
    We detect a near-square white filled shape in the header-left area and draw it
    as an ellipse/circle instead of a rectangle.
    """
    bbox = block.get("bbox")
    if not bbox or len(bbox) != 4:
        return False

    x0, y0, x1, y1 = [safe_float(v) for v in bbox]
    w = x1 - x0
    h = y1 - y0

    if w <= 0 or h <= 0:
        return False

    # Header logo badge is near top-left. Keep this broad enough for similar docs.
    in_header_left = x0 <= 170 and y0 <= 80
    nearly_square = abs(w - h) <= max(8, min(w, h) * 0.20)
    reasonable_logo_size = 25 <= w <= 120 and 25 <= h <= 120

    props = block.get("properties") or {}
    fill = get_fill_value(props)
    whiteish = is_whiteish_color(fill)

    return in_header_left and nearly_square and reasonable_logo_size and whiteish


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

    return {"font": "Helvetica", "font_size": 10.0, "color": "#000000", "flags": 0}


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
                if not block_id or block_id not in translated_text_by_block_id:
                    continue

                translated_text = sanitize_text(translated_text_by_block_id.get(block_id, ""))
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
    fill = get_fill_value(props) or "#FFFFFF"
    stroke = props.get("stroke_color") or props.get("stroke") or props.get("border_color")
    stroke_width = safe_float(props.get("stroke_width") or props.get("border_width"), 0)

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


def draw_ellipse_from_bbox(c, bbox, props, page_h):
    if not bbox or len(bbox) != 4:
        return
    rect = rl_rect_from_bbox(bbox, page_h)
    if not rect:
        return
    x, y, w, h = rect

    fill = get_fill_value(props) or "#FFFFFF"
    stroke = props.get("stroke_color") or props.get("stroke") or props.get("border_color")
    stroke_width = safe_float(props.get("stroke_width") or props.get("border_width"), 0)

    c.saveState()
    c.setFillColor(as_color(fill, white))
    if stroke and stroke_width > 0:
        c.setStrokeColor(as_color(stroke, black))
        c.setLineWidth(stroke_width)
        c.ellipse(x, y, x + w, y + h, fill=1, stroke=1)
    else:
        c.ellipse(x, y, x + w, y + h, fill=1, stroke=0)
    c.restoreState()


def draw_line_block(c, block, page_h):
    props = block.get("properties") or {}
    segments = props.get("segments") or [block.get("bbox")]

    c.saveState()
    c.setStrokeColor(as_color(props.get("stroke_color") or props.get("color"), black))
    c.setLineWidth(safe_float(props.get("stroke_width") or props.get("width"), 1.0))

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
                c.drawImage(reader, x, y, w, h, preserveAspectRatio=False, mask="auto")
                return

        if image_path and os.path.exists(image_path):
            reader = ImageReader(image_path)
            c.drawImage(reader, x, y, w, h, preserveAspectRatio=False, mask="auto")
            return
    except Exception as e:
        print(f"IMAGE_RENDER_ERROR block_id={block.get('block_id')} error={e}")


def draw_ellipse_block(c, block, page_h):
    draw_ellipse_from_bbox(c, block.get("bbox"), block.get("properties") or {}, page_h)


def draw_unknown_shape_block(c, block, page_h):
    props = block.get("properties") or {}
    bbox = block.get("bbox")
    if not bbox or len(bbox) != 4:
        return

    # If an unknown block is actually the logo badge, draw as circle.
    if is_logo_circle_candidate(block):
        draw_ellipse_block(c, block, page_h)
        return

    has_fill = props.get("fill_color") or props.get("fill") or props.get("color")
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

    font_name = resolve_font(span.get("font"), span.get("flags", 0), text)
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
    font_name = resolve_font(style.get("font"), style.get("flags", 0), translated_text)
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


def draw_footer_text_block(c, block, page_h):
    """
    Preserve footer left/right layout.
    Original footer has left text and right page number as separate spans.
    Translated text is often one combined string, so this splits the page label
    and draws it at the original right-side page-number bbox.
    """
    props = block.get("properties") or {}
    translated_text = sanitize_text(props.get("translated_text", ""))

    if not translated_text:
        draw_original_text_block(c, block, page_h)
        return

    lines = props.get("lines") or []
    page_span = None
    left_spans = []

    for line in lines:
        if not isinstance(line, dict):
            continue
        spans = line.get("spans") or []
        for span in spans:
            span_text = sanitize_text(span.get("text", ""))
            if re.search(r"\bPage\s+\d+\b", span_text, flags=re.IGNORECASE):
                page_span = span
            else:
                left_spans.append(span)

    if not page_span:
        draw_translated_text_block(c, block, page_h)
        return

    page_match = re.search(r"\b(Page|Página|Pagina)\s+\d+\b\s*$", translated_text, flags=re.IGNORECASE)
    if page_match:
        page_label = page_match.group(0).strip()
        left_text = translated_text[:page_match.start()].strip()
    else:
        page_label = sanitize_text(page_span.get("text", ""))
        left_text = translated_text.strip()

    # Draw left footer text at original left span position.
    if left_spans:
        first_left_span = left_spans[0]
        left_bbox = first_left_span.get("bbox") or block.get("bbox")
        if left_bbox and len(left_bbox) == 4:
            x0, y0, x1, y1 = [safe_float(v) for v in left_bbox]
            font_name = resolve_font(first_left_span.get("font"), first_left_span.get("flags", 0), left_text)
            font_size = safe_float(first_left_span.get("font_size"), 8.0)
            color = as_color(first_left_span.get("color"), black)
            try:
                descent = abs(getDescent(font_name) / 1000.0 * font_size)
            except Exception:
                descent = 0.20 * font_size
            baseline = page_h - y1 + descent
            c.saveState()
            c.setFillColor(color)
            c.setFont(font_name, font_size)
            c.drawString(x0, baseline, left_text)
            c.restoreState()

    # Draw page number at original right-side span position, right-aligned.
    page_bbox = page_span.get("bbox")
    if page_bbox and len(page_bbox) == 4:
        x0, y0, x1, y1 = [safe_float(v) for v in page_bbox]
        font_name = resolve_font(page_span.get("font"), page_span.get("flags", 0), page_label)
        font_size = safe_float(page_span.get("font_size"), 8.0)
        color = as_color(page_span.get("color"), black)
        try:
            descent = abs(getDescent(font_name) / 1000.0 * font_size)
        except Exception:
            descent = 0.20 * font_size
        baseline = page_h - y1 + descent
        label_width = stringWidth(page_label, font_name, font_size)
        draw_x = x1 - label_width
        c.saveState()
        c.setFillColor(color)
        c.setFont(font_name, font_size)
        c.drawString(draw_x, baseline, page_label)
        c.restoreState()


def draw_text_block(c, block, page_h):
    if block.get("type") != "text":
        return

    # Header text should stay on top of the green band and keep original span layout.
    if is_header_text_block(block):
        draw_original_text_block(c, block, page_h)
        return

    # Footer text needs special handling so Page number stays right aligned.
    if is_footer_text_block(block, page_h):
        draw_footer_text_block(c, block, page_h)
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


def draw_table_block(c, table_block, all_blocks, page_h):
    props = table_block.get("properties") or {}
    data = props.get("data") or props.get("rows") or []
    if not data:
        return

    table_bbox = table_block.get("bbox")
    if not table_bbox:
        return

    rows = safe_int(props.get("row_count"), len(data))
    cols = safe_int(props.get("column_count"), max((len(row) for row in data if isinstance(row, list)), default=0))
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
            fitted_size, lines = fit_text_to_cell(cell_text, font_name, 7.5, w, h)

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
    width = page.get("width") or page.get("page_width") or dims.get("width") or 612
    height = page.get("height") or page.get("page_height") or dims.get("height") or 792
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

        if block_type in ("filled_rect", "rect", "rectangle", "background", "shape_rect", "filled_rectangle"):
            background_blocks.append(block)
        elif block_type == "image":
            image_blocks.append(block)
        elif block_type in ("circle", "ellipse", "filled_circle", "filled_ellipse", "shape_circle", "shape_ellipse"):
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


def reconstruct_translated_pdf_from_json_payload(request_id, payload, output_dir=None, output_file_name=None):
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
    c = canvas.Canvas(output_path, pagesize=(first_page_w, first_page_h), bottomup=1)

    logs = []
    block_types = {}

    for document in documents:
        for page in document.get("pages", []):
            page_w, page_h = get_page_size(page)
            c.setPageSize((page_w, page_h))

            # Base white page background
            c.saveState()
            c.setFillColor(white)
            c.rect(0, 0, page_w, page_h, fill=1, stroke=0)
            c.restoreState()

            blocks = page.get("blocks", []) or []
            blocks = sorted(blocks, key=lambda b: (safe_int(b.get("z_index", 0)), str(b.get("block_id", ""))))

            for block in blocks:
                block_type = str(block.get("type", "unknown")).lower()
                block_types[block_type] = block_types.get(block_type, 0) + 1

            grouped = split_blocks_by_type(blocks)

            # 1. Background rectangles; logo badge candidate must draw as circle.
            for block in grouped["background"]:
                try:
                    if is_logo_circle_candidate(block):
                        draw_ellipse_block(c, block, page_h)
                    else:
                        draw_rect(c, block.get("bbox"), block.get("properties") or {}, page_h)
                except Exception as e:
                    logs.append({"status": "BACKGROUND_RENDER_ERROR", "block_id": block.get("block_id"), "error": str(e)})

            # 2. Images
            for block in grouped["image"]:
                try:
                    draw_image_block(c, block, page_h)
                except Exception as e:
                    logs.append({"status": "IMAGE_RENDER_ERROR", "block_id": block.get("block_id"), "error": str(e)})

            # 3. Ellipses / circles
            for block in grouped["ellipse"]:
                try:
                    draw_ellipse_block(c, block, page_h)
                except Exception as e:
                    logs.append({"status": "ELLIPSE_RENDER_ERROR", "block_id": block.get("block_id"), "error": str(e)})

            # 4. Unknown shape fallback
            for block in grouped["other"]:
                try:
                    draw_unknown_shape_block(c, block, page_h)
                except Exception as e:
                    logs.append({"status": "OTHER_RENDER_ERROR", "block_id": block.get("block_id"), "type": block.get("type"), "error": str(e)})

            # 5. Lines
            for block in grouped["line"]:
                try:
                    draw_line_block(c, block, page_h)
                except Exception as e:
                    logs.append({"status": "LINE_RENDER_ERROR", "block_id": block.get("block_id"), "error": str(e)})

            # 6. Tables
            for block in grouped["table"]:
                try:
                    draw_table_block(c, block, blocks, page_h)
                except Exception as e:
                    logs.append({"status": "TABLE_RENDER_ERROR", "block_id": block.get("block_id"), "error": str(e)})

            # 7. Text LAST: fixes header text being covered by header background.
            for block in grouped["text"]:
                try:
                    draw_text_block(c, block, page_h)
                except Exception as e:
                    logs.append({"status": "TEXT_RENDER_ERROR", "block_id": block.get("block_id"), "error": str(e)})

            c.showPage()

    c.save()

    return {
        "output_file_name": output_file_name,
        "output_name": output_file_name,
        "output_path": output_path,
        "output_url": f"/downloads/{output_file_name}",
        "download_url": f"/downloads/{output_file_name}",
        "logs": logs,
        "block_types": block_types,
    }


def reconstruct_translated_pdf(request_id, json_data, translated_text_by_block_id, output_dir=None, output_file_name=None):
    translated_json = apply_translations_to_json(
        json_data=json_data,
        translated_text_by_block_id=translated_text_by_block_id,
    )

    return reconstruct_translated_pdf_from_json_payload(
        request_id=request_id,
        payload=translated_json,
        output_dir=output_dir,
        output_file_name=output_file_name,
    )
