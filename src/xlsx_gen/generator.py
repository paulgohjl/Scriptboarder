"""XLSX export with 2-column layout: transcript + embedded screenshots."""

from openpyxl import Workbook
from openpyxl.drawing.image import Image
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

# Row-height sizing: greedy word-wrap at the Transcript column's width
# (55 units at font size 10 fits ~58 chars), 12.75pt per line.
_CHARS_PER_LINE = 58
_LINE_HEIGHT = 12.75
_MIN_ROW_HEIGHT = 15.0
_SCREENSHOT_MIN_HEIGHT = 70.0


def _wrapped_line_count(text: str, chars_per_line: int = _CHARS_PER_LINE) -> int:
    """Count display lines when word-wrapping text at chars_per_line."""
    if not text:
        return 1
    lines = 1
    current = 0
    for word in text.split():
        w = len(word)
        if current == 0:
            current = w
        elif current + 1 + w <= chars_per_line:
            current += 1 + w
        else:
            lines += 1
            current = w
    return lines


def _row_height(text: str) -> float:
    """Row height in points to fit wrapped transcript text."""
    return max(_MIN_ROW_HEIGHT, _wrapped_line_count(text) * _LINE_HEIGHT)


def generate_xlsx(
    video_name: str,
    output_path: str,
    segments: list,
    scene_changes: list,
    screenshot_cache: dict,
) -> str:
    """Generate an .xlsx file with inline screenshots and transcript.

    Layout: 3 columns — Timestamp | Transcript | Screenshot
    Screenshots are embedded in row C for scene change rows.

    Args:
        video_name: Display name for the document
        output_path: Where to save the .xlsx
        segments: List of TranscriptSegment objects
        scene_changes: List of SceneChange objects
        screenshot_cache: {timestamp: screenshot_path} dict

    Returns:
        Path to the generated XLSX file
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Transcript"

    scene_by_ts = {sc.timestamp: sc for sc in scene_changes}

    # Titles
    ws.cell(row=1, column=1, value=video_name)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=3)
    ws.cell(row=1, column=1).font = Font(bold=True, size=14)
    ws.cell(row=1, column=1).alignment = Alignment(horizontal="center")

    # Headers
    headers = ["Timestamp", "Transcript", "Screenshot"]
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)

    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(row=2, column=col_idx, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center" if col_idx != 2 else "left", wrap_text=True)

    # Column widths (in character widths)
    ws.column_dimensions["A"].width = 19
    ws.column_dimensions["B"].width = 55
    ws.column_dimensions["C"].width = 22

    # Styles
    normal_font = Font(size=10)
    ts_font = Font(size=9, name="Consolas")
    text_wrap = Alignment(wrap_text=True, vertical="top")
    thin_border = Side(style="thin", color="B4C6E7")
    border = Border(left=thin_border, right=thin_border, top=thin_border, bottom=thin_border)

    # Track which scenes we've already inserted
    added_scenes = set()

    # Row 3 is the first data row
    row = 3
    for seg in segments:
        ws.cell(row=row, column=1, value=seg.time_str).font = ts_font
        ws.cell(row=row, column=1).alignment = Alignment(horizontal="center", vertical="top")

        text_cell = ws.cell(row=row, column=2, value=seg.text)
        text_cell.font = normal_font
        text_cell.alignment = text_wrap
        text_cell.border = border

        # Find first scene change within 1.5 seconds of segment start
        nearest_scene = None
        for sc_ts in sorted(scene_by_ts.keys()):
            if abs(sc_ts - seg.start) <= 1.5:
                nearest_scene = sc_ts
                break

        # Scale the row to the transcript text; screenshot rows also need
        # room for the embedded image (110px ≈ 70pt).
        height = _row_height(seg.text)

        if nearest_scene and nearest_scene not in added_scenes:
            screenshot_path = screenshot_cache.get(nearest_scene)
            if screenshot_path:
                img = Image(screenshot_path)
                # Scale image to fit in column C
                img.width = 160
                img.height = 110
                # Anchor at column C
                ws.add_image(img, f"C{row}")
                ws.row_dimensions[row].height = max(_SCREENSHOT_MIN_HEIGHT, height)
                added_scenes.add(nearest_scene)
            else:
                ws.row_dimensions[row].height = height
        else:
            ws.row_dimensions[row].height = height

        row += 1

    wb.save(output_path)
    return output_path
