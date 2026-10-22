"""HTML export with 2-column layout: transcript on left, screenshots on right."""

import base64
import os
from html import escape


def _encode_image(path: str) -> str:
    """Read an image file and return a base64 data URI."""
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/png;base64,{data}"


def generate_html(
    video_name: str,
    output_path: str,
    segments: list,
    scene_changes: list,
    screenshot_cache: dict,
) -> str:
    """Generate an HTML file with aligned transcript and screenshots.

    Uses a CSS flex layout: transcript on the left, screenshot on the right.
    Each row represents a scene change point with its associated transcript.

    Args:
        video_name: Display name for the document
        output_path: Where to save the .html
        segments: List of TranscriptSegment objects
        scene_changes: List of SceneChange objects
        screenshot_cache: {timestamp: screenshot_path} dict

    Returns:
        Path to the generated HTML file
    """
    scene_by_ts = {}
    for sc in scene_changes:
        scene_by_ts[sc.timestamp] = sc

    html_parts = ["""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>""", escape(video_name), """</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #1a1a2e;
    color: #e0e0e0;
    padding: 2rem;
  }
  h1 {
    text-align: center;
    margin-bottom: 2rem;
    color: #ffffff;
    font-size: 1.8rem;
  }
  .row {
    display: flex;
    gap: 1.5rem;
    margin-bottom: 1rem;
    padding: 0.75rem;
    border-radius: 6px;
  }
  .row:hover {
    background: rgba(255,255,255,0.04);
  }
  .transcript {
    flex: 2;
    min-width: 0;
  }
  .screenshot {
    flex: 1;
    min-width: 150px;
    display: flex;
    align-items: flex-start;
    justify-content: center;
    padding-top: 0.25rem;
  }
  .screenshot img {
    max-width: 100%;
    max-height: 200px;
    border-radius: 4px;
    border: 1px solid #333;
  }
  .timestamp {
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 0.85rem;
    color: #888;
    margin-bottom: 0.25rem;
  }
  .text {
    font-size: 0.95rem;
    line-height: 1.5;
    color: #ccc;
  }
  @media print {
    body { background: #fff; color: #000; padding: 1rem; }
    .row { break-inside: avoid; }
    .timestamp { color: #666; }
    .text { color: #000; }
  }
</style>
</head>
<body>
<h1>""", escape(video_name), """</h1>
"""]

    scene_ts_set = set(scene_by_ts.keys())

    for seg in segments:
        nearest = None
        for sc in scene_changes:
            if abs(sc.timestamp - seg.start) <= 1.5:
                nearest = sc
                break

        screenshot_html = ""
        if nearest and nearest.timestamp in scene_ts_set:
            path = screenshot_cache.get(nearest.timestamp)
            if path and os.path.exists(path):
                data_uri = _encode_image(path)
                screenshot_html = f'<div class="screenshot"><img src="{data_uri}" alt="Scene at {seg.start:.1f}s"></div>'

        ts_text = f"{seg.time_str} - {seg.end_str}"

        row_html = (
            f'<div class="row">'
            f'<div class="transcript">'
            f'<div class="timestamp">{escape(ts_text)}</div>'
            f'<div class="text">{escape(seg.text)}</div>'
            f'</div>'
            f'{screenshot_html}'
            f'</div>'
            if screenshot_html
            else (
                f'<div class="row">'
                f'<div class="transcript">'
                f'<div class="timestamp">{escape(ts_text)}</div>'
                f'<div class="text">{escape(seg.text)}</div>'
                f'</div>'
                f'</div>'
            )
        )
        html_parts.append(row_html)

    html_parts.append("</body></html>\n")

    html_content = "".join(html_parts)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return output_path
