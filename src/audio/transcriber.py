"""Audio transcription using faster-whisper."""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from faster_whisper import WhisperModel


def _resolve_model_arg(model_size: str) -> str:
    """Model argument for WhisperModel.

    Frozen builds ship the model inside the bundle at whisper_models/<size>/
    (flat CTranslate2 dir); faster-whisper loads directly from a local path.
    Source runs fall back to the model name, resolved via the HF cache.
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        bundled = Path(meipass) / "whisper_models" / model_size
        if bundled.is_dir():
            return str(bundled)
    return model_size


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str

    @property
    def time_str(self) -> str:
        """Format as HH:MM:SS."""
        total_ms = int(self.start * 1000)
        hours, remainder = divmod(total_ms, 3600000)
        minutes, remainder = divmod(remainder, 60000)
        seconds, ms = divmod(remainder, 1000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{ms:03d}"

    @property
    def end_str(self) -> str:
        total_ms = int(self.end * 1000)
        hours, remainder = divmod(total_ms, 3600000)
        minutes, remainder = divmod(remainder, 60000)
        seconds, ms = divmod(remainder, 1000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{ms:03d}"


def _detect_device() -> tuple[str, str]:
    """Detect available device and compute type."""
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda", "float16"
        mps = getattr(torch.backends, "mps", None)
        if mps is not None and mps.is_available():
            return "cpu", "int8"
    except Exception:
        # torch missing, old torch without backends.mps, or broken install
        pass
    return "cpu", "int8"


def transcribe_audio(
    audio_path: str,
    model_size: str = "medium",
    device: Optional[str] = None,
    compute_type: Optional[str] = None,
    vad_filter: bool = True,
) -> list[TranscriptSegment]:
    """Transcribe audio file using faster-whisper.

    Returns list of TranscriptSegment with start/end timestamps.
    """
    if device is None or compute_type is None:
        device, compute_type = _detect_device()

    model = WhisperModel(
        _resolve_model_arg(model_size),
        device=device,
        compute_type=compute_type,
        download_root=None,  # uses default cache
        # Model ships pre-cached with the app; never contact huggingface.co
        # at load time. The default revision check breaks on machines with
        # TLS interception (SSLError from certifi not trusting the proxy CA).
        local_files_only=True,
    )

    vad_params = (
        dict(min_silence_duration_ms=500)
        if vad_filter
        else None
    )

    segments, info = model.transcribe(
        audio_path,
        language=None,  # auto-detect
        word_timestamps=False,
        vad_filter=bool(vad_params),
        vad_parameters=vad_params,
    )

    segments = [
        TranscriptSegment(
            start=seg.start,
            end=seg.end,
            text=seg.text.strip(),
        )
        for seg in segments
        if seg.text.strip()
    ]

    return segments
