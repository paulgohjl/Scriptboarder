"""Scene change detection using frame differencing with OpenCV."""

from dataclasses import dataclass

import cv2


@dataclass
class SceneChange:
    timestamp: float
    frame_index: int
    diff_score: float


SENSITIVITY_THRESHOLDS = {"low": 45, "medium": 30, "high": 18}


def detect_scene_changes(
    video_path: str,
    sensitivity: str = "medium",
    sample_interval: int = 2,
    merge_distance: float = 0.5,
) -> list[SceneChange]:
    """Detect scene changes using frame differencing.

    Returns list of SceneChange sorted by timestamp, with nearby changes merged.
    """
    threshold = SENSITIVITY_THRESHOLDS.get(sensitivity, 30)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0

    prev_gray = None
    scene_changes = []
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % sample_interval != 0:
            frame_idx += 1
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if prev_gray is not None:
            frame_diff = cv2.absdiff(prev_gray, gray)
            avg_diff = float(frame_diff.mean())

            if avg_diff > threshold:
                timestamp = frame_idx / fps
                scene_changes.append(SceneChange(timestamp, frame_idx, avg_diff))

        prev_gray = gray
        frame_idx += 1

    cap.release()

    if not scene_changes:
        return []

    # Merge nearby scene changes to avoid fragmentation
    return _merge_nearby(scene_changes, merge_distance)


def _merge_nearby(scenes: list[SceneChange], distance: float) -> list[SceneChange]:
    merged = [scenes[0]]
    for scene in scenes[1:]:
        if scene.timestamp - merged[-1].timestamp < distance:
            # Keep the one with the higher diff score
            if scene.diff_score > merged[-1].diff_score:
                merged[-1] = scene
        else:
            merged.append(scene)
    return merged
