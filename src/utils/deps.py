"""First-run dependency management."""

import os
import sys
from pathlib import Path

from utils import platform_paths as pp


def ensure_ffmpeg_path() -> str:
    """Ensure ffmpeg is available. Downloads on first run if needed.

    Raises RuntimeError when ffmpeg cannot be found and cannot be downloaded:
    this runs on the pipeline's worker thread, where sys.exit() would raise
    SystemExit past the thread's `except Exception` and leave the UI stuck on
    the progress phase with no message.
    """
    ffmpeg_path = pp.cache_dir() / pp.ffmpeg_binary_name()

    # find_ffmpeg() already includes ffmpeg on PATH, so "ffmpeg" means nothing
    # was found anywhere and a download is the last option.
    found = pp.find_ffmpeg()
    if found != "ffmpeg":
        return found

    print("Downloading ffmpeg (required)... This may take a moment.")
    _download_ffmpeg(ffmpeg_path)
    return str(ffmpeg_path)


def _download_ffmpeg(dest: Path) -> None:
    """Download the static ffmpeg build for this platform into the cache dir."""
    import urllib.request

    url = pp.ffmpeg_download_url()
    zip_path = dest.parent / "ffmpeg.zip"
    dest.parent.mkdir(parents=True, exist_ok=True)

    print(f"Downloading ffmpeg from {url}...")
    if pp.ffmpeg_arch_note():
        print(f"Note: {pp.ffmpeg_arch_note()}.")
    try:
        urllib.request.urlretrieve(url, zip_path)
        print("Extracting ffmpeg...")
        import zipfile

        binary_name = pp.ffmpeg_binary_name()
        with zipfile.ZipFile(zip_path, "r") as z:
            # Both archives ship ffmpeg nested under a versioned folder.
            entries = [
                i for i in z.infolist()
                if not i.is_dir() and Path(i.filename).name == binary_name
            ]
            if not entries:
                raise RuntimeError(f"no {binary_name} found in archive")
            entries.sort(key=lambda i: "bin/" not in i.filename)
            info = entries[0]
            z.extract(info, dest.parent)
            (dest.parent / info.filename).rename(dest)

        # Windows runs a file by extension; POSIX needs the executable bit.
        if not pp.IS_WINDOWS:
            os.chmod(dest, 0o755)

        zip_path.unlink()
    except Exception as e:
        zip_path.unlink(missing_ok=True)
        raise RuntimeError(
            f"ffmpeg download failed: {e}. Install ffmpeg and point FFMPEG_PATH "
            f"at it, or place it at {dest}"
        ) from e
