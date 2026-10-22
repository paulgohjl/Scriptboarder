"""Audio extraction from video using ffmpeg subprocess."""

import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional


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
    """Find ffmpeg binary, checking PyInstaller bundle, vendor dir, AppData, then PATH."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        bundled = Path(meipass) / "ffmpeg.exe"
        if bundled.exists():
            return str(bundled)

    env_path = Path(__file__).parent.parent.parent / "vendor" / "ffmpeg.exe"
    if env_path.exists():
        return str(env_path)

    appdata = Path.home() / "AppData" / "Local" / "scriptboarder" / "ffmpeg.exe"
    if appdata.exists():
        return str(appdata)

    return "ffmpeg"
