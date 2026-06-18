from __future__ import annotations

"""
Sermon Audio Processor
======================

This module contains the full command-line application.

Design goals:
- Watch a folder for sermon audio files.
- Accept MP3, WAV, Wave64/W64 originals.
- Always output MP3 files to the output folder.
- Preserve MP3 ID3 tags when the original is MP3.
- Create blank ID3 tags when the original is WAV/W64, with only an optional processing comment.
- Keep source files untouched by copying originals to the originals folder.
- Write JSON reports so later tuning/debugging is easier.

The processing itself is intentionally delegated to FFmpeg. Python handles orchestration,
file watching, metadata, folder management, and reporting. This keeps the audio side fast,
stable, and cross-platform.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from mutagen.id3 import ID3, COMM, ID3NoHeaderError
from mutagen.mp3 import MP3

# Watchdog is only required for --watch mode. Importing it inside a try block lets
# --batch, --file, and --check still provide useful errors if the package is missing.
try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
except Exception:  # pragma: no cover
    FileSystemEventHandler = object
    Observer = None


# Supported input extensions. FFmpeg handles the decoding; this list simply controls
# what the watcher/batch processor will pick up. Wave64 is normally .w64, but .wav64
# is included because some export tools use that extension.
SUPPORTED_INPUT_EXTENSIONS = {".mp3", ".wav", ".wave", ".w64", ".wav64"}


@dataclass
class Folders:
    """Resolved absolute paths for every working folder used by the app."""

    root: Path
    inbox: Path
    output: Path
    originals: Path
    failed: Path
    reports: Path
    processing: Path


class ProcessingError(RuntimeError):
    """Raised for user-actionable processing errors."""


# ---------------------------------------------------------------------------
# Configuration and folder handling
# ---------------------------------------------------------------------------

def load_config(path: Path) -> Dict[str, Any]:
    """Load YAML config from disk.

    The config file is intentionally plain YAML so you can tune LUFS, EQ, and
    folder paths without editing the Python code.
    """
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def resolve_folders(config_path: Path, config: Dict[str, Any]) -> Folders:
    """Resolve all configured folders and create them if they do not exist."""
    root = config_path.parent.resolve()
    folders = config.get("folders", {})

    def p(name: str) -> Path:
        # If the path in config.yaml is relative, treat it as relative to the
        # project folder. Absolute paths also work for long-term deployments.
        value = folders.get(name, name)
        path = Path(value)
        if not path.is_absolute():
            path = root / path
        path.mkdir(parents=True, exist_ok=True)
        return path

    return Folders(
        root=root,
        inbox=p("inbox"),
        output=p("output"),
        originals=p("originals"),
        failed=p("failed"),
        reports=p("reports"),
        processing=p("processing"),
    )


# ---------------------------------------------------------------------------
# Dependency and subprocess helpers
# ---------------------------------------------------------------------------

def ensure_ffmpeg() -> None:
    """Verify that ffmpeg and ffprobe are available in PATH."""
    for exe in ("ffmpeg", "ffprobe"):
        try:
            subprocess.run([exe, "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except Exception as exc:
            raise ProcessingError(
                f"{exe} was not found. Install FFmpeg and make sure '{exe}' is available in PATH."
            ) from exc


def run_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a command and raise a readable error if it fails."""
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise ProcessingError(
            "Command failed:\n" + " ".join(args) + "\n\nSTDERR:\n" + result.stderr[-4000:]
        )
    return result


# ---------------------------------------------------------------------------
# File naming, stability checks, and format helpers
# ---------------------------------------------------------------------------

def safe_stem(path: Path) -> str:
    """Return a filesystem-safe stem for temporary file names."""
    return re.sub(r"[^A-Za-z0-9._-]+", "_", path.stem).strip("._-") or "audio"


def output_name_for(input_file: Path) -> str:
    """Return the desired MP3 output filename for any supported input file.

    MP3 input:   My Sermon.mp3  -> My Sermon.mp3
    WAV input:   My Sermon.wav  -> My Sermon.mp3
    W64 input:   My Sermon.w64  -> My Sermon.mp3
    """
    return f"{input_file.stem}.mp3"


def is_supported_input(path: Path) -> bool:
    """Return True if a file extension is one the app is allowed to process."""
    return path.suffix.lower() in SUPPORTED_INPUT_EXTENSIONS


def is_mp3(path: Path) -> bool:
    """Return True for MP3 source files."""
    return path.suffix.lower() == ".mp3"


def unique_path(path: Path) -> Path:
    """Avoid overwriting an existing file by adding _1, _2, etc."""
    if not path.exists():
        return path
    base = path.with_suffix("")
    suffix = path.suffix
    for i in range(1, 10000):
        candidate = Path(f"{base}_{i}{suffix}")
        if not candidate.exists():
            return candidate
    raise ProcessingError(f"Could not create unique filename for {path}")


def is_file_stable(path: Path, checks: int, seconds: float) -> bool:
    """Wait until a copied file appears to be fully written.

    Watcher events often fire as soon as a copy begins, not when it finishes.
    This checks the file size several times before processing.
    """
    if not path.exists() or not path.is_file():
        return False
    last_size = -1
    for _ in range(checks):
        try:
            size = path.stat().st_size
        except FileNotFoundError:
            return False
        if size <= 0:
            return False
        if last_size != -1 and size != last_size:
            last_size = size
            time.sleep(seconds)
            continue
        last_size = size
        time.sleep(seconds)
    try:
        return path.stat().st_size == last_size
    except FileNotFoundError:
        return False


# ---------------------------------------------------------------------------
# FFmpeg loudness analysis and processing
# ---------------------------------------------------------------------------

def read_loudnorm_json(stderr: str) -> Dict[str, Any]:
    """Extract FFmpeg loudnorm JSON from stderr output."""
    start = stderr.rfind("{")
    end = stderr.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ProcessingError("Could not find loudnorm analysis JSON in FFmpeg output.")
    raw = stderr[start : end + 1]
    return json.loads(raw)


def build_pre_loudnorm_filters(cfg: Dict[str, Any]) -> list[str]:
    """Build the audio filter chain used before loudness normalization.

    Keep this section conservative. It is better for archival sermon processing
    to be consistently safe than aggressively polished. You can tune these
    values later after listening tests.
    """
    p = cfg["processing"]
    filters: list[str] = []

    hp = p.get("highpass_hz")
    if hp:
        # Removes rumble, HVAC thumps, handling noise, and useless sub-bass.
        filters.append(f"highpass=f={float(hp)}")

    if p.get("enable_speech_eq", True):
        filters.extend([
            # Small cut for boxiness/mud. Do not overdo this or voices get thin.
            f"equalizer=f={float(p.get('mud_cut_hz', 250))}:t=q:w={float(p.get('mud_cut_q', 1.0))}:g={float(p.get('mud_cut_db', -1.5))}",
            # Small boost for intelligibility. Too much can make lavs harsh.
            f"equalizer=f={float(p.get('presence_boost_hz', 3500))}:t=q:w={float(p.get('presence_boost_q', 1.0))}:g={float(p.get('presence_boost_db', 1.2))}",
        ])

    if p.get("enable_compression", True):
        # Gentle leveling before LUFS normalization. Loudnorm does most of the
        # consistency work; this just tames big spoken-word jumps a little.
        threshold = p.get("compressor_threshold", "-22dB")
        ratio = float(p.get("compressor_ratio", 2.2))
        attack = float(p.get("compressor_attack_ms", 20))
        release = float(p.get("compressor_release_ms", 250))
        makeup = float(p.get("compressor_makeup_db", 1.5))
        filters.append(
            f"acompressor=threshold={threshold}:ratio={ratio}:attack={attack}:release={release}:makeup={makeup}"
        )

    return filters


def first_pass_loudnorm(input_file: Path, cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Run FFmpeg loudnorm first pass and return measured loudness data."""
    p = cfg["processing"]
    filters = build_pre_loudnorm_filters(cfg)
    filters.append(
        f"loudnorm=I={p['target_lufs']}:TP={p['true_peak_db']}:LRA={p['lra']}:print_format=json"
    )
    cmd = [
        "ffmpeg", "-hide_banner", "-nostats", "-y", "-i", str(input_file),
        "-vn", "-af", ",".join(filters), "-f", "null", "-"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise ProcessingError("FFmpeg loudness analysis failed:\n" + result.stderr[-4000:])
    return read_loudnorm_json(result.stderr)


def db_to_linear(db_value: float) -> float:
    """Convert dBFS limit to the linear value expected by FFmpeg alimiter."""
    return 10 ** (db_value / 20.0)


def second_pass_process(input_file: Path, output_file: Path, analysis: Dict[str, Any], cfg: Dict[str, Any]) -> None:
    """Run the real processing pass and encode the final MP3."""
    p = cfg["processing"]
    filters = build_pre_loudnorm_filters(cfg)
    filters.append(
        "loudnorm="
        f"I={p['target_lufs']}:TP={p['true_peak_db']}:LRA={p['lra']}:"
        f"measured_I={analysis['input_i']}:"
        f"measured_TP={analysis['input_tp']}:"
        f"measured_LRA={analysis['input_lra']}:"
        f"measured_thresh={analysis['input_thresh']}:"
        f"offset={analysis['target_offset']}:"
        "linear=true:print_format=summary"
    )
    if p.get("enable_limiter", True):
        filters.append(f"alimiter=limit={db_to_linear(float(p['true_peak_db'])):.6f}")

    cmd = [
        "ffmpeg", "-hide_banner", "-y", "-i", str(input_file),
        "-vn",                         # ignore embedded artwork/video streams
        "-af", ",".join(filters),
        "-ar", str(int(p.get("sample_rate", 44100))),
        "-codec:a", "libmp3lame",
        "-b:a", str(p.get("mp3_bitrate", "192k")),
        "-id3v2_version", "3",          # broadly compatible ID3v2.3 tags
        str(output_file),
    ]
    run_command(cmd)


# ---------------------------------------------------------------------------
# Metadata and audio info
# ---------------------------------------------------------------------------

def copy_or_create_id3_tags(source: Path, dest: Path, cfg: Dict[str, Any]) -> None:
    """Preserve MP3 tags or create blank tags for WAV/W64 sources.

    - If the source is MP3 and preserve_id3_tags is enabled, copy the source
      ID3 frames into the new MP3.
    - If the source is WAV/W64, create an otherwise blank ID3 tag set. FFmpeg may
      write minimal encoder tags; this function clears those so your new file
      starts clean unless write_processing_comment is enabled.
    """
    metadata_cfg = cfg.get("metadata", {})
    preserve = metadata_cfg.get("preserve_id3_tags", True)

    # Start by clearing any tags FFmpeg may have written to the output file.
    try:
        dest_tags = ID3(dest)
        dest_tags.clear()
    except ID3NoHeaderError:
        dest_tags = ID3()

    if preserve and is_mp3(source):
        try:
            source_tags = ID3(source)
            for frame in source_tags.values():
                dest_tags.add(frame)
        except ID3NoHeaderError:
            # MP3 source with no ID3 header: intentionally keep tags blank.
            pass
        except Exception as exc:
            raise ProcessingError(f"Could not read ID3 tags from {source.name}: {exc}") from exc

    if metadata_cfg.get("write_processing_comment", True):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        source_type = source.suffix.lower().lstrip(".").upper()
        dest_tags.add(COMM(encoding=3, lang="eng", desc="SermonProcessor", text=f"Processed {timestamp} from {source_type}"))

    dest_tags.save(dest, v2_version=3)


def get_audio_info(path: Path) -> Dict[str, Any]:
    """Return useful audio info using ffprobe, with MP3 fallback info if available."""
    info: Dict[str, Any] = {}
    try:
        result = run_command([
            "ffprobe", "-v", "error", "-select_streams", "a:0",
            "-show_entries", "stream=codec_name,sample_rate,channels,bit_rate,duration",
            "-of", "json", str(path)
        ])
        data = json.loads(result.stdout or "{}")
        streams = data.get("streams") or []
        if streams:
            s = streams[0]
            info = {
                "codec": s.get("codec_name"),
                "duration_seconds": round(float(s["duration"]), 3) if s.get("duration") else None,
                "bitrate": int(s["bit_rate"]) if s.get("bit_rate") and str(s.get("bit_rate")).isdigit() else s.get("bit_rate"),
                "sample_rate": int(s["sample_rate"]) if s.get("sample_rate") and str(s.get("sample_rate")).isdigit() else s.get("sample_rate"),
                "channels": s.get("channels"),
            }
    except Exception:
        pass

    # Mutagen MP3 fallback can sometimes provide duration when ffprobe does not.
    if path.suffix.lower() == ".mp3" and not info.get("duration_seconds"):
        try:
            audio = MP3(path)
            info.update({
                "duration_seconds": round(float(audio.info.length), 3),
                "bitrate": getattr(audio.info, "bitrate", info.get("bitrate")),
                "sample_rate": getattr(audio.info, "sample_rate", info.get("sample_rate")),
                "channels": getattr(audio.info, "channels", info.get("channels")),
            })
        except Exception:
            pass
    return info


# ---------------------------------------------------------------------------
# Per-file processing workflow
# ---------------------------------------------------------------------------

def process_file(input_file: Path, folders: Folders, cfg: Dict[str, Any]) -> Optional[Path]:
    """Process one supported audio file into the output folder as MP3."""
    if not is_supported_input(input_file):
        print(f"Skipping unsupported file: {input_file.name}")
        return None

    output_file = folders.output / output_name_for(input_file)
    if cfg.get("processing", {}).get("skip_existing_outputs", True) and output_file.exists():
        print(f"Skipping existing output: {output_file.name}")
        return output_file

    print(f"Processing: {input_file.name}")
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    # The work input keeps the original extension so FFmpeg can infer format
    # correctly even for Wave64/W64 files.
    work_input = folders.processing / f"{safe_stem(input_file)}-{timestamp}{input_file.suffix.lower()}"
    work_output = folders.processing / f"{safe_stem(input_file)}-{timestamp}-processed.mp3"
    original_copy = unique_path(folders.originals / input_file.name)
    report_file = unique_path(folders.reports / f"{input_file.stem}.json")

    report: Dict[str, Any] = {
        "source_file": str(input_file),
        "source_format": input_file.suffix.lower().lstrip("."),
        "output_file": str(output_file),
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "status": "started",
        "input_audio_info": get_audio_info(input_file),
        "config": cfg.get("processing", {}),
    }

    try:
        # Copy original for safety and copy a working file for processing. This
        # means the inbox source can be moved/archived later without interrupting
        # FFmpeg once processing begins.
        shutil.copy2(input_file, original_copy)
        shutil.copy2(input_file, work_input)

        analysis = first_pass_loudnorm(work_input, cfg)
        report["loudnorm_analysis"] = analysis

        second_pass_process(work_input, work_output, analysis, cfg)
        copy_or_create_id3_tags(work_input, work_output, cfg)

        final_output = output_file if not output_file.exists() else unique_path(output_file)
        shutil.move(str(work_output), final_output)

        report["output_file"] = str(final_output)
        report["output_audio_info"] = get_audio_info(final_output)
        report["original_copy"] = str(original_copy)
        report["finished_at"] = datetime.now().isoformat(timespec="seconds")
        report["status"] = "completed"
        write_report(report_file, report)
        print(f"Completed: {final_output.name}")
        return final_output

    except Exception as exc:
        report["status"] = "failed"
        report["error"] = str(exc)
        report["finished_at"] = datetime.now().isoformat(timespec="seconds")
        write_report(report_file, report)
        failed_dest = unique_path(folders.failed / input_file.name)
        try:
            shutil.copy2(input_file, failed_dest)
        except Exception:
            pass
        print(f"FAILED: {input_file.name}: {exc}", file=sys.stderr)
        return None
    finally:
        # Always remove temporary working files after each attempt.
        for temp in (work_input, work_output):
            try:
                if temp.exists():
                    temp.unlink()
            except Exception:
                pass


def write_report(path: Path, report: Dict[str, Any]) -> None:
    """Write a per-file JSON report."""
    with path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


# ---------------------------------------------------------------------------
# Folder watcher and batch processing
# ---------------------------------------------------------------------------

class AudioFileHandler(FileSystemEventHandler):
    """Watchdog event handler for newly-created or moved-in audio files."""

    def __init__(self, folders: Folders, cfg: Dict[str, Any]):
        self.folders = folders
        self.cfg = cfg
        self.seen: set[Path] = set()

    def on_created(self, event):  # type: ignore[override]
        if getattr(event, "is_directory", False):
            return
        self._maybe_process(Path(event.src_path))

    def on_moved(self, event):  # type: ignore[override]
        if getattr(event, "is_directory", False):
            return
        self._maybe_process(Path(event.dest_path))

    def _maybe_process(self, path: Path) -> None:
        if not is_supported_input(path):
            return
        if path in self.seen:
            return
        self.seen.add(path)
        w = self.cfg.get("watcher", {})
        if is_file_stable(path, int(w.get("file_stable_checks", 3)), float(w.get("file_stable_seconds", 2))):
            process_file(path, self.folders, self.cfg)


def iter_inbox_audio_files(folders: Folders):
    """Yield supported audio files currently in the inbox, sorted by name."""
    for path in sorted(folders.inbox.iterdir()):
        if path.is_file() and is_supported_input(path):
            yield path


def process_existing_inbox(folders: Folders, cfg: Dict[str, Any]) -> None:
    """Process all supported files that are already sitting in inbox/."""
    for path in iter_inbox_audio_files(folders):
        process_file(path, folders, cfg)


def watch(folders: Folders, cfg: Dict[str, Any]) -> None:
    """Watch the inbox continuously until Ctrl+C."""
    if Observer is None:
        raise ProcessingError("watchdog is not installed. Run: pip install -r requirements.txt")
    print(f"Watching: {folders.inbox}")
    print(f"Supported inputs: {', '.join(sorted(SUPPORTED_INPUT_EXTENSIONS))}")
    print("Press Ctrl+C to stop.")
    process_existing_inbox(folders, cfg)
    handler = AudioFileHandler(folders, cfg)
    observer = Observer()
    observer.schedule(handler, str(folders.inbox), recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(float(cfg.get("watcher", {}).get("poll_seconds", 3)))
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


# ---------------------------------------------------------------------------
# Command-line interface
# ---------------------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Watch/process sermon MP3/WAV/W64 files to consistent spoken-word podcast loudness."
    )
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    parser.add_argument("--watch", action="store_true", help="Watch inbox folder continuously")
    parser.add_argument("--batch", action="store_true", help="Process all supported audio files currently in inbox")
    parser.add_argument("--file", help="Process one supported audio file")
    parser.add_argument("--check", action="store_true", help="Check dependencies and folders")
    args = parser.parse_args(argv)

    config_path = Path(args.config).resolve()
    cfg = load_config(config_path)
    folders = resolve_folders(config_path, cfg)

    try:
        ensure_ffmpeg()
        if args.check:
            print("FFmpeg and ffprobe found.")
            print(f"Project root: {folders.root}")
            print(f"Supported inputs: {', '.join(sorted(SUPPORTED_INPUT_EXTENSIONS))}")
            for name in ("inbox", "output", "originals", "failed", "reports", "processing"):
                print(f"{name}: {getattr(folders, name)}")
            return 0
        if args.file:
            process_file(Path(args.file).resolve(), folders, cfg)
            return 0
        if args.batch:
            process_existing_inbox(folders, cfg)
            return 0
        if args.watch:
            watch(folders, cfg)
            return 0
        parser.print_help()
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
