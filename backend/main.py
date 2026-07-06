"""FastAPI app: serves the frontend and exposes the film-generation pipeline API."""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.jobs import create_job, get_job
from backend.models import FilmRequest, JobStatus

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(title="AI Film Studio")


@app.get("/api/health")
def health():
    problems = settings.validate()
    return {
        "ok": len(problems) == 0,
        "problems": problems,
        # RAG (Pinecone TV-loglines inspiration step) is optional — surfaced for
        # visibility only, never blocks film generation.
        "rag_enabled": settings.rag_configured(),
    }


@app.post("/api/films", response_model=JobStatus)
def create_film(request: FilmRequest):
    problems = settings.validate()
    if problems:
        raise HTTPException(status_code=400, detail=f"Missing configuration: {', '.join(problems)}")
    job_id = create_job(request)
    job = get_job(job_id)
    return job


@app.get("/api/films/{job_id}", response_model=JobStatus)
def get_film_status(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/api/films/{job_id}/download")
def download_film(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "done" or not job.final_video_path:
        raise HTTPException(status_code=409, detail="Film is not ready yet")
    return FileResponse(job.final_video_path, media_type="video/mp4", filename=f"{job_id}.mp4")


@app.get("/api/films/{job_id}/scene/{scene_index}/video")
def get_scene_video(job_id: str, scene_index: int):
    job = get_job(job_id)
    if job is None or not job.script:
        raise HTTPException(status_code=404, detail="Job not found")
    if scene_index >= len(job.script.scenes):
        raise HTTPException(status_code=404, detail="Scene not found")
    scene = job.script.scenes[scene_index]
    if not scene.video_path:
        raise HTTPException(status_code=409, detail="Scene video not ready yet")
    return FileResponse(scene.video_path, media_type="video/mp4")


# Serve the static frontend last so /api routes above take priority.
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
