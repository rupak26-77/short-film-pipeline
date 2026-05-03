import json
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
import torch
from PIL import Image
from scenedetect import SceneManager, open_video
from scenedetect.detectors import ContentDetector
from sklearn.preprocessing import minmax_scale
from transformers import CLIPModel, CLIPProcessor

from utils.logger import get_logger
from utils.validators import slugify

logger = get_logger(__name__)


_VIDEO_EXTS = {".mp4", ".mov", ".avi"}


@dataclass
class VideoMeta:
    file: str
    path: Path
    fps: float
    frame_count: int
    width: int
    height: int
    duration_sec: float


@dataclass
class Segment:
    file: str
    path: Path
    start_sec: float
    end_sec: float
    duration_sec: float
    fps: float
    width: int
    height: int
    motion_entropy: float


def _scan_videos(video_dir: Path) -> Tuple[List[VideoMeta], List[Dict[str, Any]]]:
    metas: List[VideoMeta] = []
    rejected: List[Dict[str, Any]] = []
    for p in sorted(video_dir.glob("*")):
        if p.suffix.lower() not in _VIDEO_EXTS:
            continue
        cap = cv2.VideoCapture(str(p))
        if not cap.isOpened():
            rejected.append({"file": p.name, "reason": "cannot_open"})
            continue
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        cap.release()
        if fps <= 0 or frame_count <= 0:
            rejected.append({"file": p.name, "reason": "invalid_metadata"})
            continue
        duration = frame_count / fps
        if duration < 3.0:
            rejected.append({"file": p.name, "reason": "too_short"})
            continue
        metas.append(
            VideoMeta(
                file=p.name,
                path=p,
                fps=fps,
                frame_count=frame_count,
                width=width,
                height=height,
                duration_sec=float(duration),
            )
        )
    return metas, rejected


def _detect_scenes(meta: VideoMeta, threshold: float = 27.0) -> List[Tuple[float, float]]:
    try:
        video = open_video(str(meta.path))
        scene_manager = SceneManager()
        scene_manager.add_detector(ContentDetector(threshold=threshold))
        scene_manager.detect_scenes(video=video)
        scenes = scene_manager.get_scene_list()
        out: List[Tuple[float, float]] = []
        for start_tc, end_tc in scenes:
            out.append((start_tc.get_seconds(), end_tc.get_seconds()))
        if not out:
            return [(0.0, meta.duration_sec)]
        return out
    except Exception as e:
        logger.info("scenedetect_failed_fallback_full_video", {"file": meta.file, "detail": str(e)})
        return [(0.0, meta.duration_sec)]


def _entropy_of_diff(diff_gray: np.ndarray) -> float:
    hist = cv2.calcHist([diff_gray], [0], None, [256], [0, 256]).astype(np.float64).ravel()
    p = hist / (hist.sum() + 1e-12)
    ent = -np.sum(p * np.log2(p + 1e-12))
    return float(ent / 8.0)  # normalize by log2(256)=8


def _motion_entropy_segment(path: Path, start_sec: float, end_sec: float, sample_fps: float = 2.0) -> float:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return 0.0
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    if fps <= 0:
        cap.release()
        return 0.0

    start_frame = int(start_sec * fps)
    end_frame = int(end_sec * fps)
    step = max(1, int(round(fps / sample_fps)))
    frames = list(range(start_frame, max(start_frame + 1, end_frame), step))
    prev = None
    entropies: List[float] = []
    for fi in frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
        ok, frame = cap.read()
        if not ok or frame is None:
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if prev is not None:
            diff = cv2.absdiff(gray, prev)
            entropies.append(_entropy_of_diff(diff))
        prev = gray
    cap.release()
    if not entropies:
        return 0.0
    return float(np.mean(entropies))


def _build_segments(metas: List[VideoMeta]) -> List[Segment]:
    segments: List[Segment] = []
    for meta in metas:
        bounds = _detect_scenes(meta, threshold=27.0)
        for (s0, s1) in bounds:
            dur = float(s1 - s0)
            if dur < 2.0:
                continue
            ent = _motion_entropy_segment(meta.path, s0, s1, sample_fps=2.0)
            segments.append(
                Segment(
                    file=meta.file,
                    path=meta.path,
                    start_sec=float(s0),
                    end_sec=float(s1),
                    duration_sec=dur,
                    fps=meta.fps,
                    width=meta.width,
                    height=meta.height,
                    motion_entropy=float(ent),
                )
            )
    return segments


def _device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")  # DEVICE: cuda fallback to cpu — no GPU detected


_CLIP = {"model": None, "processor": None, "device": None}


def _get_clip() -> Tuple[CLIPModel, CLIPProcessor, torch.device]:
    if _CLIP["model"] is None:
        dev = _device()
        model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(dev)
        model.eval()
        proc = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        _CLIP["model"], _CLIP["processor"], _CLIP["device"] = model, proc, dev
        logger.info("clip_loaded", {"device": str(dev)})
    return _CLIP["model"], _CLIP["processor"], _CLIP["device"]


def _cosine_sim(a: torch.Tensor, b: torch.Tensor) -> float:
    a = a / (a.norm(dim=-1, keepdim=True) + 1e-12)
    b = b / (b.norm(dim=-1, keepdim=True) + 1e-12)
    sim = (a * b).sum(dim=-1).mean().item()
    return float(sim)


def _sim01(sim: float) -> float:
    return float(max(0.0, min(1.0, (sim + 1.0) / 2.0)))


def _sample_frames(path: Path, start_sec: float, end_sec: float, target_fps: float = 2.0) -> List[Image.Image]:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return []
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    if fps <= 0:
        cap.release()
        return []
    start_frame = int(start_sec * fps)
    end_frame = int(end_sec * fps)
    step = max(1, int(round(fps / target_fps)))

    frames: List[Image.Image] = []
    for fi in range(start_frame, max(start_frame + 1, end_frame), step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
        ok, frame = cap.read()
        if not ok or frame is None:
            continue
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frames.append(Image.fromarray(rgb))
        if len(frames) >= int(math.ceil((end_sec - start_sec) * target_fps)) + 2:
            break
    cap.release()
    return frames


def _embed_segment(seg: Segment) -> Optional[torch.Tensor]:
    model, proc, dev = _get_clip()
    frames = _sample_frames(seg.path, seg.start_sec, seg.end_sec, target_fps=2.0)
    if not frames:
        return None
    inputs = proc(images=frames, return_tensors="pt")
    pixel_values = inputs["pixel_values"].to(dev)
    with torch.no_grad():
        feats = model.get_image_features(pixel_values=pixel_values)
    feats = feats / (feats.norm(dim=-1, keepdim=True) + 1e-12)
    return feats.mean(dim=0, keepdim=True)


def _embed_text(text: str) -> torch.Tensor:
    model, proc, dev = _get_clip()
    inputs = proc(text=[text], return_tensors="pt", padding=True)
    input_ids = inputs["input_ids"].to(dev)
    attention_mask = inputs["attention_mask"].to(dev)
    with torch.no_grad():
        feats = model.get_text_features(input_ids=input_ids, attention_mask=attention_mask)
    feats = feats / (feats.norm(dim=-1, keepdim=True) + 1e-12)
    return feats


def _style_prompt(style: str) -> str:
    style = (style or "").strip()
    mapping = {
        "wide_shot": "wide shot cinematic establishing landscape",
        "close_up": "close up shot face emotion shallow depth of field",
        "medium_shot": "medium shot character conversation eye level",
        "aerial": "aerial drone shot overhead cinematic cityscape",
        "handheld": "handheld shaky camera documentary realism",
    }
    return mapping.get(style, "cinematic shot")


def analyze_videos(script: Dict[str, Any], video_dir: str = "assets/videos/") -> Dict[str, Any]:
    """
    Module 2: Advanced Video Analyzer
    Input: scenes list + video_dir
    Output: strict schema; also saved to outputs/analysis/{title_slug}_video_analysis.json
    """
    title = str(script.get("title") or "untitled")
    title_slug = slugify(title)
    scenes = script.get("scenes") or []
    if not isinstance(scenes, list):
        raise ValueError("script.scenes must be a list")

    repo_root = Path(__file__).resolve().parents[2]
    vdir = (repo_root / video_dir).resolve()
    vdir.mkdir(parents=True, exist_ok=True)

    metas, rejected = _scan_videos(vdir)
    segments = _build_segments(metas)

    if segments:
        motion_raw = np.array([s.motion_entropy for s in segments], dtype=np.float64)
        motion_norm = minmax_scale(motion_raw).astype(np.float64)
        for s, m in zip(segments, motion_norm):
            s.motion_entropy = float(m)

    seg_embeds: Dict[Tuple[str, float, float], Optional[torch.Tensor]] = {}
    for seg in segments:
        key = (seg.file, seg.start_sec, seg.end_sec)
        seg_embeds[key] = _embed_segment(seg)

    matches: List[Dict[str, Any]] = []
    unmatched: List[int] = []

    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        scene_no = int(scene.get("scene_number") or 0)
        tags = scene.get("tags") or []
        neg = scene.get("negative_tags") or []
        style = scene.get("visual_style") or "medium_shot"

        pos_text = " ".join([str(t).replace("_", " ") for t in tags])
        neg_text = " ".join([str(t).replace("_", " ") for t in neg])

        pos_vec = _embed_text(pos_text if pos_text else "cinematic scene")
        neg_vec = _embed_text(neg_text if neg_text else "low quality unwanted")
        style_vec = _embed_text(_style_prompt(style))

        candidates: List[Dict[str, Any]] = []
        for seg in segments:
            emb = seg_embeds.get((seg.file, seg.start_sec, seg.end_sec))
            if emb is None:
                continue
            pos_sim = _sim01(_cosine_sim(emb, pos_vec))
            neg_sim = _sim01(_cosine_sim(emb, neg_vec))
            semantic_score = float(max(0.0, min(1.0, pos_sim - 0.3 * neg_sim)))
            if semantic_score <= 0.22:
                continue

            style_sim = _sim01(_cosine_sim(emb, style_vec))
            style_match = bool(style_sim > 0.28)

            resolution_score = float(min(seg.width * seg.height, 1920 * 1080) / float(1920 * 1080))
            duration_score = 1.0 if (5.0 <= seg.duration_sec <= 15.0) else float(min(seg.duration_sec / 15.0, 1.0))
            motion_score = float(seg.motion_entropy)

            quality = (
                0.35 * semantic_score
                + 0.25 * motion_score
                + 0.20 * resolution_score
                + 0.20 * duration_score
            )
            if style_match:
                quality = min(1.0, quality + 0.1)

            candidates.append(
                {
                    "file": seg.file,
                    "start_sec": round(seg.start_sec, 3),
                    "end_sec": round(seg.end_sec, 3),
                    "duration_sec": round(seg.duration_sec, 3),
                    "semantic_score": round(semantic_score, 4),
                    "motion_score": round(motion_score, 4),
                    "resolution_score": round(resolution_score, 4),
                    "quality_score": round(float(quality), 4),
                    "resolution": f"{seg.width}x{seg.height}",
                    "fps": round(seg.fps, 3),
                    "visual_style_match": style_match,
                }
            )

        candidates.sort(key=lambda x: x["quality_score"], reverse=True)
        top3 = candidates[:3]
        for i, c in enumerate(top3, start=1):
            c["rank"] = i

        status = "matched" if top3 else "unmatched"
        if not top3:
            unmatched.append(scene_no)

        matches.append(
            {
                "scene_number": scene_no,
                "candidates": top3,
                "status": status,
            }
        )

    result: Dict[str, Any] = {
        "total_videos_scanned": len(metas),
        "total_segments_detected": len(segments),
        "matches": matches,
        "unmatched_scenes": unmatched,
    }

    out_path = repo_root / "outputs" / "analysis" / f"{title_slug}_video_analysis.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(
        "video_analysis_saved",
        {
            "path": str(out_path),
            "videos": len(metas),
            "segments": len(segments),
            "unmatched": len(unmatched),
        },
    )
    return result
