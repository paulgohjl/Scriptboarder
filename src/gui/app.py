"""Main application window with phase management."""

import os
import re
import shutil
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from tkinter.filedialog import askdirectory, askopenfilename

import ttkbootstrap as ttkb
from ttkbootstrap.constants import *

try:
    import tkinterdnd2
    from tkinterdnd2 import TkinterDnD, DND_FILES
except ImportError:
    tkinterdnd2 = None

from gui.dropzone import DropZone
from gui.progress_panel import ProgressPanel
from video.scene_detector import detect_scene_changes
from video.screenshot import capture_screenshot
from video.metadata import get_video_metadata
from audio.extractor import extract_audio
from audio.transcriber import transcribe_audio
from xlsx_gen.generator import generate_xlsx
from html_gen.html_generator import generate_html
from utils.deps import ensure_ffmpeg_path
from utils import applog

# Windows refuses these in a file name; the Document name field is free text.
_INVALID_NAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED_NAMES = (
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)


def safe_output_name(raw: str, ext: str) -> str:
    """Turn the Document name field into one valid file name.

    The field is free text, so it can carry a path (which would point at a
    directory the pipeline never creates) or characters Windows rejects — both
    fail at the very end of a run, after transcription is already spent.
    """
    name = raw.strip()
    # The extension is displayed beside the field, so a typed one is redundant.
    if name.lower().endswith((".xlsx", ".html")):
        name = name[:-5]
    name = _INVALID_NAME_CHARS.sub("_", name)
    # Leading dots are the traversal marker; trailing ones Windows strips
    # silently, which desyncs the name from the file it wrote.
    name = name.strip(" .")
    if not name:
        name = "transcript"
    if name.upper() in _RESERVED_NAMES:
        name = f"_{name}"
    return f"{name}.{ext}"


class MainWindow:
    """Main application window."""

    def __init__(self):
        self.root = ttkb.Window(themename="darkly")
        self.root.title("Scriptboarder")
        self.root.resizable(True, True)

        # Open at ~80% of the screen, centered, with a floor so the
        # config-phase options are never clipped on small displays.
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        width = min(max(950, int(screen_w * 0.8)), screen_w)
        height = min(max(700, int(screen_h * 0.8)), screen_h)
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")

        self.video_path = None
        self.video_metadata = None
        self.output_path = None
        self.temp_dir = tempfile.mkdtemp(prefix="sb_")
        self.output_format = "xlsx"  # "xlsx" or "html"

        self._build_ui()
        self._show_phase("input")

    def _build_ui(self):
        # Load the tkdnd Tcl library into this interpreter. It must be loaded
        # before any widget can register as a drop target, so it happens here,
        # before the DropZone exists. Registration itself is done on the
        # DropZone once it is built.
        #
        # The drop target is the DropZone, not the root window: tkinterdnd2
        # installs drop_target_register/dnd_bind by patching tkinter.BaseWidget,
        # and since Python 3.14 Tk's MRO is Tk -> Misc -> Wm -> object, which
        # skips BaseWidget. The root window therefore never gains those methods,
        # while child widgets (Canvas, Frame) do.
        self.dnd_enabled = False
        if tkinterdnd2 is not None:
            try:
                TkinterDnD.require(self.root)
                self.dnd_enabled = True
            except (RuntimeError, tk.TclError) as e:
                applog.log_error(
                    "Drag-and-drop unavailable (tkdnd Tcl library failed to load)", e
                )
        else:
            applog.log_progress(
                "tkinterdnd2 not installed; drag-and-drop disabled (click Browse to select a video)"
            )

        main = ttkb.Frame(self.root)
        main.pack(fill=BOTH, expand=True, padx=20, pady=20)

        # Title
        self.title = ttkb.Label(
            main, text="Scriptboarder",
            font=("Segoe UI", 20, "bold"), bootstyle=PRIMARY
        )
        self.title.pack(pady=(0, 15))

        # Frame containers for each phase
        self.frame_input = ttkb.Frame(main)
        self.frame_config = ttkb.Frame(main)
        self.frame_processing = ttkb.Frame(main)
        self.frame_result = ttkb.Frame(main)

        # --- Input Phase ---
        self.drop_zone = DropZone(
            self.frame_input,
            callback=self._on_file_selected,
            width=600,
            height=180,
        )
        self.drop_zone.pack(pady=10)
        # DropZone advertises click-to-browse; wire the click to the browse dialog
        self.drop_zone.bind("<Button-1>", lambda e: self._browse_file())
        if self.dnd_enabled:
            self.drop_zone.drop_target_register(DND_FILES)
            self.drop_zone.dnd_bind("<<Drop>>", self._on_drop)
            applog.log_progress("Drag-and-drop enabled (drop a video on the drop zone)")

        self.browse_btn = ttkb.Button(
            self.frame_input, text="Browse Files", command=self._browse_file,
            bootstyle=(PRIMARY, OUTLINE), width=20,
        )
        self.browse_btn.pack(pady=(5, 0))

        # --- Config Phase ---
        info_frame = ttkb.Frame(self.frame_config)
        info_frame.pack(fill=X, pady=(0, 15))
        ttkb.Label(info_frame, text="Video Info:", font=("Segoe UI", 12, "bold")).pack(anchor=W)

        self.info_text = ttkb.Label(info_frame, text="", font=("Segoe UI", 10))
        self.info_text.pack(anchor=W, pady=(5, 0))

        config_frame = ttkb.LabelFrame(self.frame_config, text="Options")
        config_frame.pack(fill=X, pady=(10, 0))

        # Sensitivity
        sens_frame = ttkb.Frame(config_frame)
        sens_frame.pack(fill=X, pady=5)
        ttkb.Label(sens_frame, text="Scene sensitivity:", font=("Segoe UI", 10)).pack(side=LEFT, padx=(0, 10))
        self.sensitivity = ttkb.StringVar(value="medium")
        ttkb.Radiobutton(sens_frame, text="Low", variable=self.sensitivity, value="low").pack(side=LEFT, padx=5)
        ttkb.Radiobutton(sens_frame, text="Medium", variable=self.sensitivity, value="medium").pack(side=LEFT, padx=5)
        ttkb.Radiobutton(sens_frame, text="High", variable=self.sensitivity, value="high").pack(side=LEFT, padx=5)

        # Output path
        out_frame = ttkb.Frame(config_frame)
        out_frame.pack(fill=X, pady=(10, 0))
        ttkb.Label(out_frame, text="Output folder:", font=("Segoe UI", 10)).pack(side=LEFT, padx=(0, 10))
        self.output_var = ttkb.StringVar(value=str(Path.home() / "Documents"))
        self.output_entry = ttkb.Entry(out_frame, textvariable=self.output_var, width=50)
        self.output_entry.pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        ttkb.Button(
            out_frame, text="Browse", command=self._browse_output,
            bootstyle=(SECONDARY, OUTLINE), width=8,
        ).pack(side=RIGHT)

        # Video name
        name_frame = ttkb.Frame(config_frame)
        name_frame.pack(fill=X, pady=(10, 0))
        ttkb.Label(name_frame, text="Document name:", font=("Segoe UI", 10)).pack(side=LEFT, padx=(0, 10))
        base_name = Path(self.video_path).stem if self.video_path else "transcript"
        self.name_var = ttkb.StringVar(value=f"{base_name}_annotated")
        ttkb.Entry(name_frame, textvariable=self.name_var, width=30).pack(side=LEFT)
        self._name_ext_label = ttkb.Label(name_frame, text=".xlsx", font=("Segoe UI", 10))
        self._name_ext_label.pack(side=LEFT)

        # Output format
        fmt_frame = ttkb.Frame(config_frame)
        fmt_frame.pack(fill=X, pady=(10, 0))
        ttkb.Label(fmt_frame, text="Output format:", font=("Segoe UI", 10)).pack(side=LEFT, padx=(0, 10))
        self.output_format_var = ttkb.StringVar(value="xlsx")
        ttkb.Radiobutton(fmt_frame, text="XLSX", variable=self.output_format_var, value="xlsx",
                         command=self._on_format_change).pack(side=LEFT, padx=5)
        ttkb.Radiobutton(fmt_frame, text="HTML", variable=self.output_format_var, value="html",
                         command=self._on_format_change).pack(side=LEFT, padx=5)

        self.start_btn = ttkb.Button(
            config_frame, text="Start Processing", command=self._start_processing,
            bootstyle=(SUCCESS, OUTLINE), width=20,
        )
        self.start_btn.pack(pady=(15, 0))

        # --- Processing Phase ---
        self.progress = ProgressPanel(self.frame_processing)
        self.progress.pack(fill=BOTH, expand=True, pady=10)

        # --- Result Phase ---
        self.result_text = ttkb.Label(
            self.frame_result,
            text="Processing complete!",
            font=("Segoe UI", 14),
            bootstyle=SUCCESS,
        )
        self.result_text.pack(pady=(0, 10))

        self.open_btn = ttkb.Button(
            self.frame_result, text="Open XLSX File", command=self._open_output,
            bootstyle=(SUCCESS, OUTLINE), width=20,
        )
        self.open_btn.pack(pady=5)

        self.reset_btn = ttkb.Button(
            self.frame_result, text="Process another video", command=self._reset,
            bootstyle=(SECONDARY, OUTLINE), width=20,
        )
        self.reset_btn.pack(pady=5)

    def _on_drop(self, event):
        # event.data is a Tcl list string: "path1 {path with spaces/file.mp4}"
        paths = self.root.tk.splitlist(event.data)
        if paths:
            self._load_video(paths[0])
        return "copy"

    def _on_file_selected(self, file_path):
        self._load_video(file_path)

    def _on_format_change(self):
        fmt = self.output_format_var.get()
        self._name_ext_label.config(text=f".{fmt}")
        self.output_format = fmt

    def _browse_file(self):
        file_path = askopenfilename(
            title="Select Video",
            filetypes=[
                ("Video Files", "*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm"),
                ("All Files", "*.*"),
            ],
        )
        if file_path:
            self._load_video(file_path)

    def _load_video(self, file_path: str):
        """Validate video and switch to config phase."""
        try:
            self.video_path = file_path
            self.video_metadata = get_video_metadata(file_path)

            meta = self.video_metadata
            info = (
                f"Filename: {meta['filename']}\n"
                f"Resolution: {meta['resolution']}\n"
                f"Duration: {meta['duration_formatted']}\n"
                f"FPS: {meta['fps']}\n"
                f"Size: {meta['size_mb']} MB"
            )
            self.info_text.config(text=info)

            # Update name suggestion and format
            base_name = Path(file_path).stem
            self.name_var.set(f"{base_name}_annotated")
            self.output_format = self.output_format_var.get()

            self._show_phase("config")
        except Exception as e:
            applog.log_error(f"Cannot process video: {file_path}", e)
            self._show_error(f"Cannot process this video: {e}")

    def _browse_output(self):
        dir_path = askdirectory(title="Select Output Folder")
        if dir_path:
            self.output_var.set(dir_path)

    def _start_processing(self):
        """Run pipeline in background thread."""
        self._set_ui_enabled(False)
        self.progress.reset()
        self._show_phase("processing")

        sensitivity = self.sensitivity.get()
        output_dir = self.output_var.get()
        self.output_format = self.output_format_var.get()
        ext = "xlsx" if self.output_format == "xlsx" else "html"
        output_name = safe_output_name(self.name_var.get(), ext)

        def worker():
            try:
                os.makedirs(output_dir, exist_ok=True)
                ffmpeg = ensure_ffmpeg_path()
                os.environ["FFMPEG_PATH"] = ffmpeg
                applog.log_progress(
                    f"Processing: {self.video_path} -> {output_name} "
                    f"in {output_dir} ({self.output_format})"
                )

                # Phase 1: Scene detection
                self._update_progress(0, 0, "Detecting scenes...")
                self._log_progress("Starting scene detection...")
                scenes = detect_scene_changes(
                    self.video_path,
                    sensitivity=sensitivity,
                )
                self._log_progress(f"Found {len(scenes)} scene changes")
                self._update_progress(0, 1.0, f"{len(scenes)} scenes found")

                # Phase 2: Screenshots
                self._update_progress(1, 0, "Capturing screenshots...")
                self._log_progress("Capturing screenshots...")
                screenshot_cache = {}
                for i, scene in enumerate(scenes):
                    pct = (i + 1) / max(len(scenes), 1)
                    self._update_progress(1, pct, f"{i+1}/{len(scenes)}")
                    try:
                        path = capture_screenshot(
                            self.video_path,
                            scene.timestamp,
                            max_width=640,
                            temp_dir=self.temp_dir,
                        )
                        screenshot_cache[scene.timestamp] = path
                    except Exception as e:
                        self._log_progress(f"  Warning: screenshot failed at {scene.timestamp}s: {e}")
                self._update_progress(1, 1.0, "Done")

                # Phase 3: Audio + transcription
                self._update_progress(2, 0, "Extracting audio...")
                self._log_progress("Extracting audio...")
                audio_path = extract_audio(self.video_path, output_dir=self.temp_dir, ffmpeg_path=ffmpeg)
                self._log_progress(f"Audio extracted: {audio_path.name}")

                self._update_progress(2, 0.3, "Transcribing...")
                self._log_progress("Transcribing audio...")
                segments = transcribe_audio(str(audio_path))
                self._log_progress(f"Transcribed {len(segments)} segments")
                self._update_progress(2, 1.0, "Done")

                # Phase 4: Output generation
                full_path = os.path.join(output_dir, output_name)
                if self.output_format == "html":
                    self._update_progress(3, 0, "Generating HTML...")
                    self._log_progress("Generating HTML document...")
                    generate_html(
                        self.video_metadata["filename"],
                        full_path,
                        segments,
                        scenes,
                        screenshot_cache,
                    )
                    self._log_progress(f"HTML saved to: {full_path}")
                else:
                    self._update_progress(3, 0, "Generating XLSX...")
                    self._log_progress("Generating XLSX document...")
                    generate_xlsx(
                        self.video_metadata["filename"],
                        full_path,
                        segments,
                        scenes,
                        screenshot_cache,
                    )
                    self._log_progress(f"XLSX saved to: {full_path}")
                self._update_progress(3, 1.0, "Done")

                self.output_path = full_path
                self.root.after(0, lambda: self._show_phase("result"))

            except Exception as e:
                import traceback
                error_msg = f"Error: {e}\n\n{traceback.format_exc()}"
                applog.log_error("Processing failed", e)
                self._log_progress(error_msg)
                self.root.after(0, lambda: self._show_error(error_msg))
            finally:
                self._cleanup_temp_files()
                self.root.after(0, lambda: self._set_ui_enabled(True))

        threading.Thread(target=worker, daemon=True).start()

    def _cleanup_temp_files(self):
        """Remove screenshots/audio left in the temp dir (output files embed them)."""
        temp_dir = Path(self.temp_dir)
        if not temp_dir.exists():
            return
        for f in temp_dir.iterdir():
            if f.is_file():
                try:
                    f.unlink()
                except OSError:
                    pass

    def _cleanup_temp_dir(self):
        """mkdtemp() runs once per launch, so the directory itself goes on exit."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _open_output(self):
        if self.output_path and os.path.exists(self.output_path):
            os.startfile(self.output_path)

    def _reset(self):
        """Reset to input phase."""
        self.video_path = None
        self.video_metadata = None
        self.output_path = None
        self.progress.reset()
        self._show_phase("input")

    def _show_phase(self, phase: str):
        for frame in [self.frame_input, self.frame_config,
                       self.frame_processing, self.frame_result]:
            frame.pack_forget()

        if phase == "input":
            self.frame_input.pack(fill=BOTH, expand=True)
        elif phase == "config":
            self.frame_config.pack(fill=BOTH, expand=True)
        elif phase == "processing":
            self.frame_processing.pack(fill=BOTH, expand=True)
        elif phase == "result":
            self.frame_result.pack(fill=BOTH, expand=True)
            fmt = self.output_format_var.get()
            btn_text = f"Open {fmt.upper()} File"
            self.open_btn.config(text=btn_text)

    def _set_ui_enabled(self, enabled: bool):
        state = NORMAL if enabled else DISABLED
        for widget in self.frame_config.winfo_children():
            self._set_children_state(widget, state)

    def _set_children_state(self, widget, state):
        for child in widget.winfo_children():
            if isinstance(child, tk.Text) or isinstance(child, tk.Entry):
                try:
                    child.config(state=state)
                except tk.TclError:
                    pass
            else:
                self._set_children_state(child, state)
        try:
            widget.config(state=state)
        except tk.TclError:
            pass

    def _update_progress(self, phase_idx: int, pct: float, status: str):
        self.root.after(0, lambda: self.progress.set_phase_status(phase_idx, pct * 100, status))

    def _log_progress(self, msg: str):
        applog.log_progress(msg)
        self.root.after(0, lambda: self.progress.log_message(msg))

    def _show_error(self, msg: str):
        from tkinter import messagebox as mb
        mb.showerror("Error", msg)

    def run(self):
        self.root.mainloop()
        self._cleanup_temp_dir()


def main():
    applog.setup_logging()
    applog.log_progress(
        f"Scriptboarder starting (Python {sys.version.split()[0]}, "
        f"frozen={getattr(sys, 'frozen', False)})"
    )
    app = MainWindow()
    app.run()
    applog.shutdown()


if __name__ == "__main__":
    main()
