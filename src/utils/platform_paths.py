"""Everything platform-specific, in one place.

The app runs on Windows and macOS. What differs is small but load-bearing:
the ffmpeg binary is `ffmpeg.exe` on Windows and `ffmpeg` on macOS; the
download cache lives under %LOCALAPPDATA% on Windows and
~/Library/Application Support on macOS; opening the finished document is
os.startfile on Windows and `open` on macOS; and the UI font is Segoe UI on
Windows, which does not exist on macOS.

ffmpeg discovery is defined here once. audio.extractor and utils.deps both
need it and previously carried two divergent copies.
"""

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"


def ffmpeg_binary_name() -> str:
    return "ffmpeg.exe" if IS_WINDOWS else "ffmpeg"


def cache_dir() -> Path:
    """Where the app keeps its downloaded ffmpeg."""
    if IS_WINDOWS:
        return Path.home() / "AppData" / "Local" / "scriptboarder"
    if IS_MACOS:
        return Path.home() / "Library" / "Application Support" / "scriptboarder"
    return Path.home() / ".local" / "share" / "scriptboarder"


def documents_dir() -> Path:
    """Default output folder."""
    docs = Path.home() / "Documents"
    return docs if docs.is_dir() else Path.home()


# Homebrew on Apple Silicon installs to /opt/homebrew; Intel Homebrew and
# python.org/pyenv installs land in /usr/local. A packaged app inherits a
# login shell's PATH, so these are checked explicitly as well.
_MACOS_SYSTEM_FFMPEG = (
    "/opt/homebrew/bin/ffmpeg",
    "/usr/local/bin/ffmpeg",
    "/opt/local/bin/ffmpeg",
    "/usr/bin/ffmpeg",
)


def system_ffmpeg() -> Optional[str]:
    """An ffmpeg the system already provides (Homebrew, MacPorts, PATH)."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    if IS_MACOS:
        for candidate in _MACOS_SYSTEM_FFMPEG:
            path = Path(candidate)
            if path.is_file() and os.access(path, os.X_OK):
                return str(path)
    return None


def bundled_ffmpeg() -> Optional[str]:
    """ffmpeg shipped inside a PyInstaller bundle."""
    meipass = getattr(sys, "_MEIPASS", None)
    if not meipass:
        return None
    bundled = Path(meipass) / ffmpeg_binary_name()
    return str(bundled) if bundled.exists() else None


def vendored_ffmpeg() -> Optional[str]:
    """vendor/ffmpeg for source runs."""
    vendored = Path(__file__).parent.parent.parent / "vendor" / ffmpeg_binary_name()
    return str(vendored) if vendored.exists() else None


def find_ffmpeg() -> str:
    """Locate ffmpeg: bundle, vendor/, downloaded copy, FFMPEG_PATH, system.

    The bundle wins over the download cache: a packaged app ships a pinned
    ffmpeg, and a stale copy left by an earlier source run must not override
    it. Returns "ffmpeg" when nothing is found, so callers that only need a
    command name fail with ffmpeg's own error rather than a missing-file one.
    """
    for finder in (bundled_ffmpeg, vendored_ffmpeg):
        found = finder()
        if found:
            return found

    cached = cache_dir() / ffmpeg_binary_name()
    if cached.exists():
        return str(cached)

    env_path = os.environ.get("FFMPEG_PATH")
    if env_path and Path(env_path).exists():
        return env_path

    return system_ffmpeg() or "ffmpeg"


def ui_font() -> str:
    """A font family that exists on this platform.

    Tk silently substitutes an unknown family, so a hard-coded "Segoe UI"
    renders in whatever the fallback happens to be on macOS.
    """
    if IS_WINDOWS:
        return "Segoe UI"
    if IS_MACOS:
        return "Helvetica"
    return "DejaVu Sans"


def mono_font() -> str:
    """Monospace family for the log pane; Consolas ships only with Windows."""
    if IS_WINDOWS:
        return "Consolas"
    if IS_MACOS:
        return "Menlo"
    return "DejaVu Sans Mono"


def open_file(path: str) -> None:
    """Open a finished document in its default application."""
    if IS_WINDOWS:
        os.startfile(path)  # noqa: S606 - Windows-only, guarded above
    elif IS_MACOS:
        subprocess.run(["open", path], check=False)
    else:
        subprocess.run(["xdg-open", path], check=False)


def ffmpeg_download_url() -> str:
    """Static ffmpeg build for this platform.

    gyan.dev ships Windows builds; evermeet.cx ships macOS x86_64 builds,
    which run under Rosetta 2 on Apple Silicon.
    """
    if IS_MACOS:
        return "https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip"
    return "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"


def ffmpeg_arch_note() -> str:
    """Explain the architecture of the build this platform downloads."""
    if IS_MACOS and platform.machine() == "arm64":
        return (
            "the downloaded ffmpeg is an x86_64 build running under Rosetta 2; "
            "install `brew install ffmpeg` for a native arm64 binary"
        )
    return ""
