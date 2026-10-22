# Scriptboarder

**Turn a video into a spreadsheet of everything that was said in it — with a screenshot next to each line.**

Drop a video on the window. Scriptboarder finds every scene change, grabs a screenshot of each one, transcribes the speech, and writes you a document where each line of the transcript sits next to the frame the speaker was on when they said it. Useful for lecture notes, interview records, meeting minutes, subtitles you can actually read.

Two output formats: **XLSX** (a spreadsheet with the images embedded in the cells) and **HTML** (one self-contained web file you can open in any browser and print).

Everything runs on your own computer. Your video is not uploaded anywhere, and there is no account, no sign-up, and no cloud service involved.

```
video ─▶ find scene changes ─▶ take screenshots ─▶ extract audio ─▶ transcribe ─▶ XLSX / HTML
```

## What you get

| Timestamp | Transcript | Screenshot |
| --- | --- | --- |
| `00:00:04.120` | So today we're going to look at the budget. | *(frame from that moment)* |
| `00:00:11.860` | First, the numbers from last quarter. | *(frame from that moment)* |

The HTML version is the same table in a single `.html` file, with the images built in.

---

## Can I run this?

| | Requirement |
| --- | --- |
| **Operating system** | Windows 10 or 11, **or** macOS 12 and newer (Intel or Apple Silicon) |
| **Python** | Version **3.11, 3.12, 3.13 or 3.14** — not 3.10 or older (see [Troubleshooting](#troubleshooting)) |
| **Disk space** | About 4 GB free (the transcription model is a one-time 1.5 GB download) |
| **Internet** | Needed once, for the first run, to fetch the transcription model. After that it works offline. |
| **Graphics card** | Not needed. It runs on the CPU. |

You do **not** need to know Git, and you do not need a GitHub account to use this.

---

## Step 1 — Get the code (no Git needed)

1. Go to `https://github.com/paulgohjl/Scriptboarder` in your browser.
2. Press the green **Code** button near the top right.
3. Choose **Download ZIP**.
4. Unzip the downloaded file (right-click → *Extract All* on Windows, double-click on macOS). You get a folder named `Scriptboarder-main`.

That's it. A GitHub "repository" is just a folder of files that this button downloads. You never have to type a Git command.

> There are no compiled installers to download yet — you run the app from these files. Step 3 makes it runnable.

## Step 2 — Install Python

**Windows:** open `https://www.python.org/downloads/`, press **Download Python 3.x**, run the installer, and on the very first installer screen **tick "Add python.exe to PATH"** before pressing *Install*. Skipping that tick is the single most common reason the next step fails.

**macOS:** open `https://www.python.org/downloads/`, download the macOS installer, run it. (If you use Homebrew, `brew install python` works too.)

Check it worked — open a terminal and type:

```
python --version
```

On macOS type `python3 --version` instead. You should see `Python 3.1x.y`.

**How to open a terminal:**
- **Windows:** open the `Scriptboarder-main` folder in File Explorer, click into the address bar at the top, type `cmd`, press Enter. A black window opens already inside that folder.
- **macOS:** open the **Terminal** app (Launchpad → type "Terminal"), then type `cd ` (with a space), drag the `Scriptboarder-main` folder onto the Terminal window, and press Enter.

## Step 3 — Install what the app needs

Type these commands one at a time, pressing Enter after each. The `$` means "type what follows it"; do not type the `$` itself.

**Windows:**
```bat
cd Scriptboarder-main
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**macOS:**
```bash
cd Scriptboarder-main
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
pip install -r requirements.txt
```

The first two commands create a private "virtual environment" (a `.venv` folder) so this app's packages don't disturb anything else on your computer. After the `activate` line your prompt shows `(.venv)` — that means you are inside it. If you close the terminal and come back, run the `activate` line again.

`pip install -r requirements.txt` downloads the libraries the app uses (OpenCV for video, faster-whisper for transcription, and friends). It needs internet and takes a couple of minutes.

## Step 4 — Download the transcription model (once)

Transcription uses a speech-recognition model that is about **1.5 GB**. The app deliberately never downloads anything while it runs, so you fetch it once yourself:

**Windows:**
```bat
python -c "from faster_whisper import WhisperModel; WhisperModel('medium')"
```

**macOS:**
```bash
python3 -c "from faster_whisper import WhisperModel; WhisperModel('medium')"
```

This takes a while and prints a progress bar. It stores the model in your user folder (`~/.cache/huggingface`) and you only ever need to do it once per computer.

## Step 5 — Run it

**Windows:** `python src/main.py`
**macOS:** `python3 src/main.py`

A window opens. On the very first run the app also fetches a small free tool called **ffmpeg** (it converts your video's audio into a form the transcriber can read) — you'll see `Downloading ffmpeg (required)...` in the terminal. That is normal and happens once.

## Step 6 — Use it

1. Drag a video file onto the drop zone, or press **Browse Files**.
2. The app shows the video's length and resolution. Check it looks right.
3. Pick **Scene sensitivity** — *Low* finds few scene changes, *High* finds many. *Medium* is the right answer most of the time.
4. Check the **Output folder** (defaults to your Documents folder) and the **Document name**.
5. Choose **XLSX** or **HTML**, then press **Start Processing**.
6. Watch the four progress bars. When it finishes, press **Open XLSX File**.

A 20-minute video takes a few minutes. Longer videos take longer — the app reads every frame.

---

## Troubleshooting

| What you see | What it means | What to do |
| --- | --- | --- |
| `'python' is not recognized as an internal or external command` | Python isn't installed, or the PATH tick was skipped | Re-run the Python installer and tick **Add python.exe to PATH** |
| `python: command not found` (macOS) | macOS calls it `python3` | Use `python3` in every command |
| `ERROR: No matching distribution found for numpy==2.4.6` | Your Python is 3.10 or older | Install Python 3.12 or 3.13 and repeat Step 3 |
| `python -m venv` fails, or `pip` is missing | Virtual environment not created | Delete the `.venv` folder and repeat Step 3 |
| Transcription fails with a message about cached files / `LocalEntryNotFoundError` | The 1.5 GB model isn't downloaded yet | Run the Step 4 command with internet |
| `ffmpeg download failed` | The app couldn't fetch ffmpeg | Install ffmpeg (`brew install ffmpeg` on macOS), then set `FFMPEG_PATH` to it, or place the binary in a `vendor` folder in the project |
| Dragging a file does nothing | The drag-and-drop library didn't install | Press **Browse Files** instead (it always works), and check `pip install tkinterdnd2` succeeded |
| `Cannot open video: ...` | The file isn't a video, or its codec isn't supported | Try an `.mp4` file. If it is `.mkv`/`.mov`, convert it: `ffmpeg -i input.mkv -c:v libx264 output.mp4` |
| Screenshots come out black | Same codec problem as above | Convert the video to plain H.264 `.mp4` first |
| It's slow | Normal — every frame is decoded, and transcription runs on the CPU | Use *Medium* sensitivity, or process shorter clips |
| Only one file processed from a multi-file drop | Known limitation | Drop one video at a time |
| macOS: "app cannot be opened" | macOS privacy prompt, or an unsigned build | Click through the Documents-folder permission prompt; for a packaged `.app`, see [Packaging](#packaging) |

Still stuck? The app writes everything it did to a file named **`scriptboarder.log`** in the project folder. Open it, read the last lines, and paste them into a [new Issue](https://github.com/paulgohjl/Scriptboarder/issues/new) on GitHub. An Issue is just a message to the author — no Git needed, a GitHub account is enough.

---

## Questions people ask

**Is my video sent to anyone?** No. Video, audio, and transcript all stay on your machine.

**Do I need a powerful computer?** No GPU needed. Expect roughly the length of your video in processing time, give or take.

**Which languages does it transcribe?** It auto-detects the spoken language. Whisper is strong on English and good on many others; accents, overlapping speech, and background music reduce accuracy.

**Does it work offline?** After Steps 3 and 4 have been done once, yes.

**Is it free?** Yes, MIT-licensed. You can use it, change it, and sell what it produces.

**Why is the transcript not perfect?** It is machine transcription. Treat it as a strong first draft, not a legal transcript.

---

## For developers

### Project layout

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

### How it works

1. **Scene detection** — frame differencing on grayscale, Gaussian-blurred frames, sampled every 2nd frame. Nearby detections merge so one cut does not fragment into several rows.
2. **Screenshots** — one frame per detected scene, downscaled to 640 px wide.
3. **Audio** — extracted to 16 kHz mono WAV with ffmpeg.
4. **Transcription** — faster-whisper `medium`, VAD-filtered, language auto-detected. CUDA when available, otherwise CPU with `int8`.
5. **Output** — rows of `Timestamp | Transcript | Screenshot`. XLSX embeds the images; HTML inlines them as base64 data URIs.

### Dependencies

`requirements.txt` is **pinned** to exact versions, so a clone installs the same tree CI runs. Unpinned lower bounds let CI resolve newer releases than the dev machine — that is how a ttkbootstrap release that enforces a single Tk root per process once broke the suite. Updating a pin is a deliberate act: change it, run the suite, and let CI prove it.

The pinned set installs on Python 3.11 through 3.14. It does **not** install on 3.10 (`numpy==2.4.6` publishes no 3.10 wheels).

### Tests

No external test framework, no network access:

```
python -m unittest discover -s tests -v
```

Covers scene merging, timestamp formatting, offline model loading, ffmpeg lookup paths, XLSX row heights, log fallbacks, drag-and-drop registration, output file naming, and the platform layer (ffmpeg binary name, cache folders, the open-document call, font families, download source).

GUI tests skip with a reason when the machine has no window server for Tk to draw on; a POSIX-only test (the downloaded ffmpeg's executable bit) skips on Windows. CI runs the suite on **Linux, macOS and Windows**, so each platform's own code paths are exercised on that platform — dropping a matrix leg silently un-runs a platform's branches.

### ffmpeg lookup order

1. The PyInstaller bundle (`ffmpeg` at the archive root)
2. `vendor/ffmpeg` — for source runs
3. The download cache — `%LOCALAPPDATA%\scriptboarder\` on Windows, `~/Library/Application Support/scriptboarder/` on macOS
4. The `FFMPEG_PATH` environment variable
5. An ffmpeg already on the system: `PATH`, plus `/opt/homebrew/bin`, `/usr/local/bin`, `/opt/local/bin` and `/usr/bin` on macOS

Nothing is downloaded until the earlier steps fail, so a machine with ffmpeg installed never fetches a second copy. The bundle ranks first because a packaged app ships a pinned ffmpeg that a stale download from an earlier source run must not override. Downloads come from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) on Windows and [evermeet.cx](https://evermeet.cx/ffmpeg/) on macOS.

### Whisper model

Transcription loads `medium` with `local_files_only=True` — it never contacts huggingface.co at load time, which keeps it working behind TLS interception (proxy / antivirus). Populate the cache once, with internet:

```
python -c "from faster_whisper import WhisperModel; WhisperModel('medium')"
```

### Packaging

`scriptboarder.spec` bundles the interpreter, ffmpeg, the tkdnd native libraries, and the Whisper model, so the result runs fully offline. Build it on the OS you are shipping for — PyInstaller cannot cross-compile. The spec **fails the build** if ffmpeg or the `medium` model is missing locally, and excludes `torch` (~4 GB) because faster-whisper runs on CTranslate2.

**Windows:**
```powershell
pip install pyinstaller
copy ffmpeg.exe vendor\ffmpeg.exe      # required by the spec
pyinstaller scriptboarder.spec --noconfirm
```
Output lands in `dist\Scriptboarder\`. Zip that folder to ship it.

**macOS:**
```bash
pip install pyinstaller
cp "$(which ffmpeg)" vendor/ffmpeg     # required by the spec
pyinstaller scriptboarder.spec --noconfirm
open dist/Scriptboarder.app
```
The spec emits both `dist/Scriptboarder/` and `dist/Scriptboarder.app`; use the `.app`. Two things to know before shipping it: it is **unsigned and unnotarized**, so Gatekeeper blocks the first launch on a Mac it was not built on (`xattr -dr com.apple.quarantine /Applications/Scriptboarder.app`, or a Developer ID signature plus `--codesign-identity`/`--codesign-entitlements`); and bundle an arm64 ffmpeg (Homebrew on Apple Silicon) if you want the app native on both architectures — an x86_64 ffmpeg runs under Rosetta 2.

### Logging

Progress and errors go to `scriptboarder.log` next to the app (project root from source, exe folder when packaged), rotating at 2 MB with three backups. On macOS a packaged app logs to `~/Library/Application Support/scriptboarder/`, because a `.app` in `/Applications` is not user-writable. A failing log location falls back to the temp directory and never takes the app down.

---

## Known limitations

- Runs on Windows and macOS. Not packaged for Linux — the code has Linux fallbacks, but there is no Linux build and no support commitment.
- On Apple Silicon, ffmpeg from the automatic download is x86_64 running under Rosetta 2. `brew install ffmpeg` gives a native arm64 binary.
- A macOS `.app` built locally is unsigned, so Gatekeeper blocks it on a Mac it was not built on.
- macOS asks permission the first time the app reads your Documents folder, which is the default output location.
- Scene detection decodes every frame, so long videos take time — a 20-minute clip runs in a few minutes.
- Transcription quality depends on audio quality; overlapping speech and music degrade it, as with any Whisper-based transcript.
- Only the first file in a multi-file drop is used.
- The XLSX timestamp column is written with the `Consolas` font name, which macOS does not ship, so Excel substitutes a monospace font there.

## License

MIT — see [LICENSE](LICENSE).

Bundled components carry their own terms: faster-whisper is Apache-2.0, the Systran Whisper model is MIT, ffmpeg is LGPL/GPL, and tkdnd is BSD-style.
