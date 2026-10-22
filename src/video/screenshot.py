"""Screenshot capture at specific timestamps from video."""

import os
import tempfile
from typing import Optional

import cv2
from PIL import Image


def capture_screenshot(
    video_path: str,
    timestamp: float,
    max_width: int = 640,
    temp_dir: Optional[str] = None,
) -> str:
    """Capture a frame from video at the given timestamp.

    Returns path to saved PNG file.
    """
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0

    target_frame = int(timestamp * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)

    ret, frame = cap.read()
    cap.release()

    if not ret:
        cap = cv2.VideoCapture(video_path)
        cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
        ret, frame = cap.read()
        cap.release()

    if not ret:
        raise ValueError(f"Cannot capture frame at {timestamp}s from {video_path}")

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(frame_rgb)

    orig_w, orig_h = img.size
    if orig_w > max_width:
        ratio = max_width / orig_w
        new_w = max_width
        new_h = int(orig_h * ratio)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    out_dir = temp_dir or tempfile.gettempdir()
    filename = f"sb_frame_{int(timestamp * 1000)}_{orig_w}x{orig_h}.png"
    out_path = os.path.join(out_dir, filename)
    img.save(out_path, "PNG")
    return out_path


def capture_frame_at_index(
    video_path: str,
    frame_index: int,
    max_width: int = 640,
    temp_dir: Optional[str] = None,
) -> str:
    """Capture a frame by frame index instead of timestamp."""
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0

    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        raise ValueError(f"Cannot capture frame {frame_index} from {video_path}")

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(frame_rgb)

    orig_w, orig_h = img.size
    if orig_w > max_width:
        ratio = max_width / orig_w
        new_w = max_width
        new_h = int(orig_h * ratio)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    out_dir = temp_dir or tempfile.gettempdir()
    filename = f"sb_frame_idx_{frame_index}_{orig_w}x{orig_h}.png"
    out_path = os.path.join(out_dir, filename)
    img.save(out_path, "PNG")
    return out_path
