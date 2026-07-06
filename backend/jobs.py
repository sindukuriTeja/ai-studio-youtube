"""In-memory job store + orchestration of the full idea -> film pipeline."""
import threading
import traceback
import uuid
from pathlib import Path

from backend.config import settings
from backend.models import FilmRequest, JobStatus
from backend.services import claude_service, elevenlabs_service, rag_service, runway_service, video_assembly

_jobs: dict[str, JobStatus] = {}
_lock = threading.Lock()


def get_job(job_id: str) -> JobStatus | None:
    with _lock:
        return _jobs.get(job_id)


def _update(job_id: str, **kwargs) -> None:
    with _lock:
        _jobs[job_id] = _jobs[job_id].model_copy(update=kwargs)


def create_job(request: FilmRequest) -> str:
    job_id = uuid.uuid4().hex[:12]
    job = JobStatus(job_id=job_id, status="pending", progress=0.0, message="Queued")
    with _lock:
        _jobs[job_id] = job

    thread = threading.Thread(target=_run_pipeline, args=(job_id, request), daemon=True)
    thread.start()
    return job_id


def _job_dir(job_id: str) -> Path:
    d = settings.STORAGE_DIR / job_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _run_pipeline(job_id: str, request: FilmRequest) -> None:
    job_dir = _job_dir(job_id)
    try:
        _update(
            job_id,
            status="finding_inspiration",
            progress=0.02,
            message="Searching similar TV episodes for inspiration...",
        )
        premise = request.idea
        try:
            loglines, similar = rag_service.suggest_loglines(
                idea=request.idea,
                genre=request.genre,
                num_loglines=3,
            )
            if loglines:
                premise = loglines[0]
            _update(job_id, refined_logline=premise if loglines else None, inspired_by=similar or None)
        except Exception as e:
            # The RAG step is a best-effort enhancement. Never fail the whole film
            # job because Pinecone/embedding lookup had a problem — just proceed
            # with the user's raw idea.
            traceback.print_exc()
            print(f"RAG logline suggestion skipped due to error: {e}")

        _update(job_id, status="writing_script", progress=0.06, message="Writing script with Claude...")
        script = claude_service.generate_script(
            idea=premise,
            num_scenes=request.num_scenes,
            style=request.style,
        )
        _update(job_id, script=script)

        total_scenes = max(len(script.scenes), 1)
        scene_pairs: list[tuple[Path, Path | None]] = []

        for i, scene in enumerate(script.scenes):
            scene.status = "generating"
            _update(
                job_id,
                status="generating_scenes",
                progress=0.1 + 0.7 * (i / total_scenes),
                message=f"Generating scene {i + 1}/{total_scenes}: {scene.title}",
                script=script,
            )

            video_path = job_dir / f"scene_{i:02d}.mp4"
            try:
                runway_service.generate_scene_video(
                    prompt_text=scene.video_prompt,
                    out_path=video_path,
                    ratio=request.aspect_ratio,
                    duration=request.scene_duration,
                )
                scene.video_path = str(video_path)
            except Exception as e:
                scene.status = "error"
                scene.error = str(e)
                _update(job_id, script=script)
                raise

            audio_path = None
            if request.include_narration and scene.narration.strip():
                audio_path = job_dir / f"scene_{i:02d}.mp3"
                try:
                    elevenlabs_service.generate_narration_audio(
                        text=scene.narration,
                        out_path=audio_path,
                        voice_id=request.voice_id,
                    )
                    scene.audio_path = str(audio_path)
                except Exception as e:
                    # Narration failure shouldn't kill the whole film; continue without audio.
                    scene.audio_path = None
                    scene.error = f"Narration failed: {e}"
                    audio_path = None

            scene.status = "done"
            scene_pairs.append((video_path, audio_path))
            _update(job_id, script=script)

        _update(job_id, status="assembling", progress=0.85, message="Assembling final film with ffmpeg...")
        final_path = video_assembly.assemble_film(scene_pairs, job_dir)

        _update(
            job_id,
            status="done",
            progress=1.0,
            message="Done",
            final_video_path=str(final_path),
        )
    except Exception as e:
        traceback.print_exc()
        _update(job_id, status="error", message="Pipeline failed", error=str(e))
