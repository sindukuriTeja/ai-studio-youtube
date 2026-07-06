"""Stitches per-scene video clips + narration audio into one final film using ffmpeg."""
import shutil
import subprocess
from pathlib import Path


class AssemblyError(Exception):
    pass


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise AssemblyError(f"Command failed: {' '.join(cmd)}\n{result.stderr}")


def _probe_duration(path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise AssemblyError(f"ffprobe failed on {path}: {result.stderr}")
    return float(result.stdout.strip())


def mux_scene(video_path: Path, audio_path: Path | None, out_path: Path) -> Path:
    """Combines one scene's video with its narration audio, padding whichever is shorter
    so the two tracks end up the same length, then re-encodes to a consistent codec so the
    resulting clips can later be concatenated with a simple stream copy."""
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if audio_path is None or not audio_path.exists():
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-an",
            str(out_path),
        ]
        _run(cmd)
        return out_path

    video_dur = _probe_duration(video_path)
    audio_dur = _probe_duration(audio_path)

    video_filter = "null"
    audio_filter = "anull"

    if audio_dur > video_dur:
        pad = audio_dur - video_dur
        video_filter = f"tpad=stop_mode=clone:stop_duration={pad:.3f}"
    elif video_dur > audio_dur:
        pad = video_dur - audio_dur
        audio_filter = f"apad=pad_dur={pad:.3f}"

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-filter:v", video_filter,
        "-filter:a", audio_filter,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-map", "0:v:0", "-map", "1:a:0",
        str(out_path),
    ]
    _run(cmd)
    return out_path


def concat_clips(clip_paths: list[Path], out_path: Path) -> Path:
    if not clip_paths:
        raise AssemblyError("No clips to concatenate")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    list_file = out_path.parent / f"{out_path.stem}_concat_list.txt"
    with open(list_file, "w") as f:
        for clip in clip_paths:
            f.write(f"file '{clip.resolve().as_posix()}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(out_path),
    ]
    _run(cmd)
    list_file.unlink(missing_ok=True)
    return out_path


def assemble_film(scene_video_audio_pairs: list[tuple[Path, Path | None]], work_dir: Path, final_name: str = "final_film.mp4") -> Path:
    """scene_video_audio_pairs: list of (video_path, audio_path_or_None), in order."""
    if not ffmpeg_available():
        raise AssemblyError(
            "ffmpeg/ffprobe not found on PATH. Install ffmpeg to enable video assembly."
        )

    muxed_clips = []
    for i, (video_path, audio_path) in enumerate(scene_video_audio_pairs):
        muxed_out = work_dir / f"scene_{i:02d}_muxed.mp4"
        muxed_clips.append(mux_scene(video_path, audio_path, muxed_out))

    final_path = work_dir / final_name
    concat_clips(muxed_clips, final_path)
    return final_path
