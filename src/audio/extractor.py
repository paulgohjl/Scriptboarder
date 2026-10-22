"""Audio extraction from video using ffmpeg subprocess."""

import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from utils.platform_paths import find_ffmpeg


def extract_audio(
    video_path: str,
    output_dir: Optional[str] = None,
    ffmpeg_path: Optional[str] = None,
) -> Path:
    """Extract audio from video as 16kHz WAV.

    Returns path to the output audio file.
    """
    tmp_dir = Path(output_dir) if output_dir else Path(tempfile.gettempdir())
    audio_path = tmp_dir / f"sb_audio_{Path(video_path).stem}.wav"

    cmd = [
        ffmpeg_path or _find_ffmpeg(),
        "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(audio_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr}")

    if not audio_path.exists():
        raise RuntimeError("Audio file was not created")

    return audio_path


def _find_ffmpeg() -> str:
    """Deprecated alias for utils.platform_paths.find_ffmpeg.

    Kept for the existing tests; the app passes the path it resolved in
    utils.deps into extract_audio(ffmpeg_path=...) instead of calling this.
    """
    return find_ffmpeg()
