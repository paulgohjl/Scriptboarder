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

- **Windows 10/11** — the app uses `os.startfile` and `%LOCALAPPDATA%`.
- **Python 3.10+** (developed on 3.14).
- **ffmpeg** — supplied automatically; see below.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python src/main.py
```

Drag a video onto the drop zone (or click **Browse Files**), choose options, and
press **Start Processing**.

### ffmpeg

The app looks for `ffmpeg.exe` in this order and downloads a static build from
[gyan.dev](https://www.gyan.dev/ffmpeg/builds/) if it finds none:

1. `%LOCALAPPDATA%\scriptboarder\ffmpeg.exe` — the download cache
2. The PyInstaller bundle (`ffmpeg.exe` at the archive root)
3. `vendor/ffmpeg.exe` — for source runs
4. The `FFMPEG_PATH` environment variable

The download runs on first launch and prints its progress. To skip it, drop
`ffmpeg.exe` into `vendor/` yourself.

### Whisper model

Transcription loads the `medium` model with `local_files_only=True` — it never
contacts huggingface.co at load time, which keeps it working behind TLS
interception (proxy / antivirus). Populate the local cache once with internet
access:

```powershell
python -c "from faster_whisper import WhisperModel; WhisperModel('medium')"
```

## Packaging a Windows build

`scriptboarder.spec` bundles the interpreter, ffmpeg, the tkdnd native
libraries, and the Whisper model, so the result runs fully offline.

```powershell
pip install pyinstaller
copy ffmpeg.exe vendor\ffmpeg.exe      # required by the spec
pyinstaller scriptboarder.spec --noconfirm
```

Output lands in `dist\Scriptboarder\`. Zip that folder to ship it.

The spec **fails the build** if the `medium` model is not in the local
Hugging Face cache, and it excludes `torch` (~4 GB) because faster-whisper runs
on CTranslate2.

## Project layout

```
src/
  main.py            entry point
  gui/               window, drop zone, progress panel
  video/             metadata, scene detection, screenshots
  audio/             ffmpeg extraction, whisper transcription
  xlsx_gen/          spreadsheet export
  html_gen/          HTML export
  utils/             logging, first-run dependency setup
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
registration, and output file naming.

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
three backups. A failing log location falls back to the temp directory and
never takes the app down.

## Known limitations

- Windows-only.
- Scene detection decodes every frame, so long videos take time — a 20-minute
  clip runs in a few minutes.
- Transcription quality depends on audio quality; overlapping speech and music
  degrade it, as with any Whisper-based transcript.
- Only the first file in a multi-file drop is used.

## License

MIT — see [LICENSE](LICENSE).

Bundled components carry their own terms: faster-whisper is Apache-2.0, the
Systran Whisper model is MIT, ffmpeg is LGPL/GPL, and tkdnd is BSD-style.
