# scriptboarder.spec — PyInstaller configuration (onedir, fully offline)
#
# The build bundles everything the app needs at runtime:
#   - ffmpeg (vendor/ffmpeg.exe on Windows, vendor/ffmpeg on macOS)
#   - the faster-whisper "medium" model, taken from the local Hugging Face
#     cache and placed at whisper_models/medium/ (transcriber._resolve_model_arg
#     loads it from sys._MEIPASS; the app never touches huggingface.co)
#   - tkinterdnd2's tkdnd native libraries (drag-and-drop in frozen builds)
#
# Windows: output is dist/Scriptboarder/ (exe + support files). Zip it to ship.
# macOS: output is dist/Scriptboarder/ plus dist/Scriptboarder.app.
#
# Build on the OS you are shipping for — PyInstaller cannot cross-compile.

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"
ffmpeg_bin = "ffmpeg.exe" if IS_WINDOWS else "ffmpeg"

# --- Locate the ffmpeg to bundle ---
_spec_dir = Path(SPEC).parent
ffmpeg_to_bundle = _spec_dir / "vendor" / ffmpeg_bin
if not ffmpeg_to_bundle.is_file():
    raise SystemExit(
        f"{ffmpeg_to_bundle} not found. The bundle ships ffmpeg so the app runs "
        f"offline; put a static build there first. On macOS the easy route is "
        f"`cp $(which ffmpeg) vendor/ffmpeg` after `brew install ffmpeg`."
    )

# --- Locate the pre-cached faster-whisper model snapshot ---
_hub = Path.home() / ".cache" / "huggingface" / "hub" / "models--Systran--faster-whisper-medium"
_ref = _hub / "refs" / "main"
if not _ref.is_file():
    raise SystemExit(
        "faster-whisper-medium not found in the local Hugging Face cache "
        f"({_hub}). Run the app once with internet access to populate it, "
        "then build again."
    )
_rev = _ref.read_text().strip()
_snapshot = _hub / "snapshots" / _rev
# Snapshot entries are symlinks into blobs/; PyInstaller copies real contents.
model_datas = [(str(f), "whisper_models/medium") for f in sorted(_snapshot.iterdir()) if f.is_file()]
if not model_datas:
    raise SystemExit(f"faster-whisper snapshot dir is empty: {_snapshot}")

# faster_whisper ships silero_vad.onnx as package data (vad_filter needs it)
datas = collect_data_files("tkinterdnd2") + collect_data_files("faster_whisper") + model_datas

hiddenimports = collect_submodules("faster_whisper") + [
    "cv2",
    "openpyxl",
    "openpyxl.cell",
    "openpyxl.cell.cell",
    "openpyxl.drawing",
    "openpyxl.drawing.image",
    "ctranslate2",
    "onnxruntime",
    "PIL",
    "PIL.Image",
]

a = Analysis(
    ['src/main.py'],
    # main.py's sys.path.insert is a no-op in the frozen app (its __file__
    # lives in the bundle), so Analysis must see src/ to collect gui/, utils/, ...
    pathex=[str(_spec_dir / 'src')],
    binaries=[
        (str(ffmpeg_to_bundle), '.'),
    ],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter.test',
        # torch is imported only by transcriber._detect_device() behind a
        # try/except; faster-whisper runs on ctranslate2 and the frozen app
        # runs CPU/int8. Keeping torch would add ~4GB to the bundle.
        'torch',
        'torchvision',
        'bitsandbytes',
        'llvmlite',
        'numba',
        'transformers',
        'scipy',
        'imageio_ffmpeg',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

# target_arch is Windows-only (and macOS-only in newer PyInstaller for
# cross-building); leaving it unset builds for the host architecture.
exe_kwargs = {}
if IS_WINDOWS:
    exe_kwargs['target_arch'] = 'x86_64'

# UPX cannot pack Mach-O binaries, and is not installed on macOS runners.
compress = {'strip': False, 'upx': IS_WINDOWS, 'upx_exclude': []}

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Scriptboarder',
    debug=False,
    bootloader_ignore_signals=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    codesign_identity=None,
    entitlements_file=None,
    **exe_kwargs,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name='Scriptboarder',
    **compress,
)

if IS_MACOS:
    BUNDLE(
        coll,
        name='Scriptboarder.app',
        bundle_identifier='com.paulgoh.scriptboarder',
        info_plist={
            'NSHighResolutionCapable': True,
            # macOS asks the user before an app may read ~/Documents, which is
            # the default output folder; these supply the wording of that ask.
            'NSDocumentsFolderUsageDescription':
                'Scriptboarder writes the transcript document you choose to your Documents folder.',
            'NSDownloadsFolderUsageDescription':
                'Scriptboarder reads the video file you drop on it.',
        },
    )
