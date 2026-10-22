# Scriptboarder

Convert a video into an annotated transcript: scene changes, screenshots, and
transcribed speech laid out side by side, exported as **XLSX** or **HTML**.

Drop a video in, pick a sensitivity, get a document where every line of
transcription is paired with the frame the speaker was on when they said it.

## Pipeline

```
video ─▶ scene detection ─▶ screenshots ─▶ audio ─▶ transcription ─▶ XLSX / HTML
         (OpenCV)          (OpenCV)     (ffmpeg)   (faster-whisper)
```

1. **Scene detection** — frame differencing on grayscale, Gaussian-blurred
   frames, sampled every 2nd frame. Nearby detections are merged so a single
   cut does not fragment into several rows.
2. **Screenshots** — one frame captured per detected scene, downscaled to
   640 px wide.
3. **Audio** — extracted to 16 kHz mono WAV with ffmpeg.
4. **Transcription** — faster-whisper (`medium`), VAD-filtered, language
   auto-detected. CUDA is used when available, otherwise CPU with `int8`.
5. **Output** — rows of `Timestamp | Transcript | Screenshot`. XLSX embeds the
   images; HTML inlines them as base64 data URIs.

## Requirements

- **Windows 10/11** or **macOS 12+** (Apple Silicon or Intel).
- **Python 3.10+** (developed on 3.14).
- **ffmpeg** — supplied automatically; see below.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python src/main.py
```

On macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 src/main.py
```

Drag a video onto the drop zone (or click **Browse Files**), choose options, and
press **Start Processing**.

### ffmpeg

The app looks for ffmpeg in this order and downloads a static build if it
finds none:

1. The PyInstaller bundle (`ffmpeg` at the archive root)
2. `vendor/ffmpeg` — for source runs
3. The download cache — `%LOCALAPPDATA%\scriptboarder\` on Windows,
   `~/Library/Application Support/scriptboarder/` on macOS
4. The `FFMPEG_PATH` environment variable
5. An ffmpeg already on the system: `PATH`, plus `/opt/homebrew/bin`,
   `/usr/local/bin`, `/opt/local/bin` and `/usr/bin` on macOS

Nothing is downloaded until the earlier steps fail, so a machine with
ffmpeg installed never fetches a second copy. The bundle ranks first
because a packaged app ships a pinned ffmpeg that a stale download from an
earlier source run must not override.

The download is a static build: [gyan.dev](https://www.gyan.dev/ffmpeg/builds/)
for Windows, [evermeet.cx](https://evermeet.cx/ffmpeg/) for macOS. On Apple
Silicon the downloaded build is x86_64 and runs under Rosetta 2, which is
fine for audio extraction; for a native binary install ffmpeg yourself:

```bash
brew install ffmpeg
cp "$(which ffmpeg)" vendor/ffmpeg     # for source runs
```

To skip the download on any platform, place ffmpeg where step 2 or 3 points.

### Whisper model

Transcription loads the `medium` model with `local_files_only=True` — it never
contacts huggingface.co at load time, which keeps it working behind TLS
interception (proxy / antivirus). Populate the local cache once with internet
access:

```powershell
python -c "from faster_whisper import WhisperModel; WhisperModel('medium')"
```

## Packaging

`scriptboarder.spec` bundles the interpreter, ffmpeg, the tkdnd native
libraries, and the Whisper model, so the result runs fully offline. Build it
on the OS you are shipping for — PyInstaller cannot cross-compile.

The spec **fails the build** if ffmpeg or the `medium` model is missing from
the local machine, and it excludes `torch` (~4 GB) because faster-whisper runs
on CTranslate2.

### Windows build

```powershell
pip install pyinstaller
copy ffmpeg.exe vendor\ffmpeg.exe      # required by the spec
pyinstaller scriptboarder.spec --noconfirm
```

Output lands in `dist\Scriptboarder\`. Zip that folder to ship it.

### macOS build

```bash
pip install pyinstaller
cp "$(which ffmpeg)" vendor/ffmpeg     # required by the spec
pyinstaller scriptboarder.spec --noconfirm
open dist/Scriptboarder.app
```

The spec emits both `dist/Scriptboarder/` and `dist/Scriptboarder.app`; use
the `.app`. Drag it to `/Applications`.

Two things to know before shipping a `.app` to someone else:

- It is **unsigned and unnotarized**, so Gatekeeper blocks the first launch.
  A locally built app is fine; one you hand to another Mac needs
  `xattr -dr com.apple.quarantine /Applications/Scriptboarder.app`, or a
  Developer ID signature plus `--codesign-identity`/`--codesign-entitlements`.
- The bundled ffmpeg is copied as-is. Bundle an arm64 build (Homebrew on
  Apple Silicon) to ship one app that runs natively on both architectures;
  an x86_64 ffmpeg runs under Rosetta 2.

## Project layout

```
src/
  main.py            entry point
  gui/               window, drop zone, progress panel
  video/             metadata, scene detection, screenshots
  audio/             ffmpeg extraction, whisper transcription
  xlsx_gen/          spreadsheet export
  html_gen/          HTML export
  utils/             logging, first-run dependency setup,
                   platform_paths.py (everything OS-specific)
tests/               stdlib unittest suite
scriptboarder.spec   PyInstaller configuration
```

## Tests

No external test framework and no network access required:

```powershell
python -m unittest discover -s tests -v
```

The suite covers scene merging, timestamp formatting, offline model loading,
ffmpeg lookup paths, XLSX row heights, log fallbacks, drag-and-drop
registration, output file naming, and the platform layer (ffmpeg binary name,
cache folders, the open-document call, font families, the download source).

GUI tests skip with a reason when the machine has no window server for Tk to
draw on. A POSIX-only test (the downloaded ffmpeg's executable bit) skips on
Windows. CI runs the suite on Linux, macOS and Windows, so each platform's
own branches are exercised on that platform.

## Output format

| Column | Contents |
| --- | --- |
| Timestamp | `HH:MM:SS.mmm` segment start, monospace |
| Transcript | Spoken text, wrapped; row height scales to fit it |
| Screenshot | Frame at the nearest scene change, embedded in the cell |

The HTML export is a single self-contained file with a print stylesheet.

## Logging

Progress and errors are written to `scriptboarder.log` next to the app
(project root from source, exe folder when packaged), rotating at 2 MB with
three backups. On macOS a packaged app logs to
`~/Library/Application Support/scriptboarder/`, because a `.app` in
`/Applications` is not user-writable. A failing log location falls back to
the temp directory and never takes the app down.

## Known limitations

- Runs on Windows and macOS; not packaged for Linux (the code has Linux
  fallbacks, but there is no Linux build or support for one).
- On Apple Silicon, ffmpeg from the automatic download is x86_64 running
  under Rosetta 2. `brew install ffmpeg` gives a native arm64 binary.
- A macOS `.app` built locally is unsigned, so Gatekeeper blocks it on a
  Mac it was not built on.
- macOS asks permission the first time the app reads your Documents folder,
  which is the default output location.
- Scene detection decodes every frame, so long videos take time — a 20-minute
  clip runs in a few minutes.
- Transcription quality depends on audio quality; overlapping speech and music
  degrade it, as with any Whisper-based transcript.
- Only the first file in a multi-file drop is used.

## License

MIT — see [LICENSE](LICENSE).

Bundled components carry their own terms: faster-whisper is Apache-2.0, the
Systran Whisper model is MIT, ffmpeg is LGPL/GPL, and tkdnd is BSD-style.
