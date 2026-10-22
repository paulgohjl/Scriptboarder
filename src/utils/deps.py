"""First-run dependency management."""

import os
import sys
from pathlib import Path


def ensure_ffmpeg_path() -> str:
    """Ensure ffmpeg is available. Downloads on first run if needed."""
    cache_dir = Path.home() / "AppData" / "Local" / "scriptboarder"
    cache_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg_path = cache_dir / "ffmpeg.exe"

    if ffmpeg_path.exists():
        return str(ffmpeg_path)

    # Check PyInstaller bundle (spec bundles ffmpeg.exe at the archive root)
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        bundled = Path(meipass) / "ffmpeg.exe"
        if bundled.exists():
            return str(bundled)

    # Check vendor dir (for source runs)
    vendor_path = Path(__file__).parent.parent.parent / "vendor" / "ffmpeg.exe"
    if vendor_path.exists():
        return str(vendor_path)

    # Check environment variable
    env_path = os.environ.get("FFMPEG_PATH")
    if env_path and Path(env_path).exists():
        return env_path

    # Download ffmpeg
    print("Downloading ffmpeg (required)... This may take a moment.")
    _download_ffmpeg(ffmpeg_path)
    return str(ffmpeg_path)


def _download_ffmpeg(dest: Path) -> None:
    """Download static ffmpeg build from ffmpeg.org."""
    import urllib.request

    # Windows x64 static build URL
    url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    zip_path = dest.parent / "ffmpeg.zip"

    print(f"Downloading ffmpeg from gyan.dev...")
    try:
        urllib.request.urlretrieve(url, zip_path)
        print("Extracting ffmpeg...")
        import zipfile
        with zipfile.ZipFile(zip_path, "r") as z:
            # gyan.dev builds ship ffmpeg at <dir>/bin/ffmpeg.exe
            ffmpeg_entries = [i for i in z.infolist() if i.filename.endswith("ffmpeg.exe")]
            if not ffmpeg_entries:
                raise RuntimeError("no ffmpeg.exe found in archive")
            ffmpeg_entries.sort(key=lambda i: "bin/" not in i.filename)
            info = ffmpeg_entries[0]
            z.extract(info, dest.parent)
            (dest.parent / info.filename).rename(dest)

        zip_path.unlink()
    except Exception as e:
        print(f"Failed to download ffmpeg: {e}")
        print("Please install ffmpeg manually and place it at:")
        print(f"  {dest}")
        sys.exit(1)
