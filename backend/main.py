import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.modules.audio_processor import process_audio
from backend.modules.script_generator import generate_script
from backend.modules.video_analyzer import analyze_videos
from backend.utils.logger import get_logger, log_timed
from backend.utils.validators import ensure_safe_filename, slugify, validate_asset_exists, validate_prompt


load_dotenv()
logger = get_logger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = REPO_ROOT / "assets"
ASSETS_VIDEOS = ASSETS_DIR / "videos"
ASSETS_AUDIO = ASSETS_DIR / "audio"
OUTPUTS_DIR = REPO_ROOT / "outputs"
OUTPUTS_SCRIPTS = OUTPUTS_DIR / "scripts"
OUTPUTS_ANALYSIS = OUTPUTS_DIR / "analysis"
OUTPUTS_REPORTS = OUTPUTS_DIR / "reports"

for d in [ASSETS_VIDEOS, ASSETS_AUDIO, OUTPUTS_SCRIPTS, OUTPUTS_ANALYSIS, OUTPUTS_REPORTS]:
    d.mkdir(parents=True, exist_ok=True)


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=500)
    audio_file: str


app = FastAPI(title="AI-Assisted Short Film Preparation Pipeline", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "modules": ["script", "video", "audio"]}


@app.get("/assets")
def list_assets() -> Dict[str, Any]:
    videos = sorted([p.name for p in ASSETS_VIDEOS.glob("*") if p.suffix.lower() in {".mp4", ".mov", ".avi"}])
    audio = sorted([p.name for p in ASSETS_AUDIO.glob("*") if p.suffix.lower() in {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}])
    return {"videos": videos, "audio": audio}


@app.get("/outputs")
def list_outputs() -> Dict[str, Any]:
    reports = sorted([p.name for p in OUTPUTS_REPORTS.glob("*.json")])
    return {"reports": reports}


@app.get("/outputs/{filename}")
def get_output(filename: str) -> Dict[str, Any]:
    ensure_safe_filename(filename)
    p = (OUTPUTS_REPORTS / filename).resolve()
    if not p.exists():
        raise HTTPException(status_code=404, detail="report not found")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to read report: {e}")


@app.post("/generate")
def generate(req: GenerateRequest) -> Dict[str, Any]:
    t0 = time.perf_counter()
    try:
        prompt = validate_prompt(req.prompt)
        audio_path = validate_asset_exists(ASSETS_AUDIO, req.audio_file)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    stage = 0
    try:
        stage = 1
        with log_timed(logger, "script_generator", stage=1):
            script = generate_script(prompt)

        title_slug = slugify(str(script.get("title") or "untitled"))

        stage = 2
        with log_timed(logger, "video_analyzer", stage=2, title_slug=title_slug):
            video_matches = analyze_videos(script, video_dir="assets/videos/")

        stage = 3
        with log_timed(logger, "audio_processor", stage=3, title_slug=title_slug, audio=req.audio_file):
            audio_sync = process_audio(str(audio_path), title_slug=title_slug)

        result: Dict[str, Any] = {
            "script": script,
            "video_analysis": video_matches,
            "audio_analysis": audio_sync,
        }

        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        out_file = OUTPUTS_REPORTS / f"{ts}_pipeline_result.json"
        out_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("pipeline_saved", {"path": str(out_file)})

        dt = time.perf_counter() - t0
        logger.info("pipeline_done", {"duration_sec": round(dt, 4)})
        return result
    except Exception as e:
        detail = str(e)
        raise HTTPException(
            status_code=500,
            detail={"error": "module_name failed", "detail": detail, "stage": stage},
        )

