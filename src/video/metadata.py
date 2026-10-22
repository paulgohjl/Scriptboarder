"""Video metadata extraction."""

from pathlib import Path

import cv2


def get_video_metadata(video_path: str) -> dict:
    """Extract video metadata.

    Returns dict with duration, resolution, fps, frame_count.
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    duration = total_frames / fps if fps > 0 else 0

    cap.release()

    size_mb = Path(video_path).stat().st_size / (1024 * 1024)

    return {
        "path": str(video_path),
        "filename": Path(video_path).name,
        "duration": duration,
        "duration_formatted": _format_duration(duration),
        "resolution": f"{int(width)}x{int(height)}",
        "fps": fps,
        "frame_count": int(total_frames),
        "size_mb": round(size_mb, 1),
    }


def _format_duration(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
