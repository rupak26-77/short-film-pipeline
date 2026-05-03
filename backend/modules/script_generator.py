import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from groq import Groq

from utils.logger import get_logger
from utils.validators import slugify

logger = get_logger(__name__)


_GENRES = {
    "thriller": ["thriller", "suspense", "mystery", "crime", "detective", "investigation", "stalker"],
    "romance": ["romance", "love", "relationship", "couple", "date", "heartbreak", "wedding"],
    "action": ["action", "chase", "fight", "explosion", "heist", "escape", "combat"],
    "horror": ["horror", "ghost", "haunted", "demon", "curse", "nightmare", "slasher"],
    "documentary": ["documentary", "interview", "real", "true story", "archive", "narration", "nonfiction"],
}

_SETTINGS = {
    "urban": ["urban", "city", "street", "subway", "traffic", "neon", "skyscraper"],
    "rural": ["rural", "village", "farm", "fields", "countryside", "barn", "mountain"],
    "indoor": ["indoor", "inside", "room", "hallway", "kitchen", "office", "apartment"],
    "outdoor": ["outdoor", "outside", "forest", "beach", "river", "rooftop", "market"],
    "night": ["night", "midnight", "dark", "moon", "streetlights", "shadow", "rainy night"],
    "day": ["day", "morning", "afternoon", "sunlight", "bright", "golden hour", "sunny"],
}

_STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "to",
    "of",
    "in",
    "on",
    "with",
    "for",
    "at",
    "as",
    "by",
    "from",
    "into",
    "over",
    "under",
    "after",
    "before",
    "through",
    "during",
    "between",
    "without",
    "within",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "it",
    "this",
    "that",
    "these",
    "those",
    "i",
    "you",
    "we",
    "they",
    "he",
    "she",
    "his",
    "her",
    "their",
    "our",
    "your",
    "my",
    "me",
    "us",
    "them",
    "not",
    "no",
    "yes",
    "but",
    "so",
    "if",
    "then",
    "than",
    "just",
    "very",
    "really",
    "can",
    "could",
    "should",
    "would",
    "will",
    "may",
    "might",
    "must",
}


def _keyword_score(prompt: str, vocab: List[str]) -> float:
    p = prompt.lower()
    score = 0.0
    for w in vocab:
        if w in p:
            score += 1.0
    return score


def _detect_best(prompt: str, mapping: Dict[str, List[str]]) -> Tuple[str, float]:
    best_key = ""
    best_score = 0.0
    for k, vocab in mapping.items():
        s = _keyword_score(prompt, vocab)
        if s > best_score:
            best_key, best_score = k, s
    return best_key, best_score


def _infer_from_context(prompt: str) -> Tuple[str, str]:
    genre, gs = _detect_best(prompt, _GENRES)
    setting, ss = _detect_best(prompt, _SETTINGS)
    if gs >= 1.0 and ss >= 1.0:
        return genre, setting
    if not genre:
        if re.search(r"\b(ghost|haunt|demon|curse|blood)\b", prompt, re.I):
            genre = "horror"
        elif re.search(r"\b(chase|heist|fight|escape|explosion)\b", prompt, re.I):
            genre = "action"
        elif re.search(r"\b(love|kiss|couple|heartbreak)\b", prompt, re.I):
            genre = "romance"
        elif re.search(r"\b(interview|real|true|archive|narration)\b", prompt, re.I):
            genre = "documentary"
        else:
            genre = "thriller"
    if not setting:
        if re.search(r"\b(room|apartment|office|hallway|kitchen)\b", prompt, re.I):
            setting = "indoor"
        elif re.search(r"\b(forest|beach|street|market|rooftop|field)\b", prompt, re.I):
            setting = "outdoor"
        else:
            setting = "urban"
    return genre, setting


def _extract_keywords(text: str, k: int = 8) -> List[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z'-]{2,}", (text or "").lower())
    freq: Dict[str, int] = {}
    for w in words:
        if w in _STOPWORDS:
            continue
        if len(w) > 22:
            continue
        freq[w] = freq.get(w, 0) + 1
    ranked = sorted(freq.items(), key=lambda x: (-x[1], x[0]))
    return [w for (w, _) in ranked[:k]]


def _infer_visual_style(desc: str) -> str:
    d = (desc or "").lower()
    if any(x in d for x in ["drone", "aerial", "bird's-eye", "from above", "overhead skyline", "over the city"]):
        return "aerial"
    if any(x in d for x in ["handheld", "shaky", "run-and-gun", "found footage", "wobbling camera"]):
        return "handheld"
    if any(x in d for x in ["close-up", "close up", "face fills", "tear", "eyes", "whisper", "lip", "hands trembling"]):
        return "close_up"
    if any(x in d for x in ["wide", "establishing", "panoramic", "landscape", "crowd", "cityscape", "long shot"]):
        return "wide_shot"
    return "medium_shot"


def _estimate_duration_sec(desc: str) -> int:
    wc = len(re.findall(r"\w+", desc or ""))
    sec = int(round(max(6.0, min(25.0, wc / 2.6))))
    return sec


def _ensure_scene_fields(scene: Dict[str, Any], idx: int, total: int) -> Dict[str, Any]:
    scene_number = scene.get("scene_number") or (idx + 1)
    desc = str(scene.get("description") or "").strip()
    if not desc:
        raise ValueError(f"scene {scene_number}: missing description")

    tags = scene.get("tags") or []
    if not isinstance(tags, list):
        tags = []
    tags = [str(t).strip().lower().replace(" ", "_") for t in tags if str(t).strip()]

    base_kw = _extract_keywords(desc, k=10)
    primary = []
    for t in tags + base_kw:
        t = t.replace("-", "_")
        if t and t not in primary:
            primary.append(t)
        if len(primary) >= 5:
            break
    while len(primary) < 5:
        primary.append(f"scene_{scene_number}_{len(primary)+1}")

    negative = scene.get("negative_tags") or []
    if not isinstance(negative, list):
        negative = []
    negative = [str(t).strip().lower().replace(" ", "_") for t in negative if str(t).strip()]
    # Heuristic negative tags: avoid opposite settings & generic mismatches
    neg_pool = negative + ["cartoon", "text_overlay", "logo", "low_light_noise", "blurry"]
    if re.search(r"\b(night|dark)\b", desc, re.I):
        neg_pool.append("daylight")
    if re.search(r"\b(day|sunlight|morning)\b", desc, re.I):
        neg_pool.append("night")
    if re.search(r"\b(indoor|room|apartment|office)\b", desc, re.I):
        neg_pool.append("outdoor")
    if re.search(r"\b(outdoor|street|forest|beach|market)\b", desc, re.I):
        neg_pool.append("indoor")

    neg_final = []
    for t in neg_pool:
        t = str(t).strip().lower().replace(" ", "_")
        if t and t not in neg_final and t not in primary:
            neg_final.append(t)
        if len(neg_final) >= 3:
            break
    while len(neg_final) < 3:
        neg_final.append(f"not_{primary[len(neg_final)]}")

    audio_mood = str(scene.get("audio_mood") or "neutral").strip().lower()
    audio_tempo = str(scene.get("audio_tempo") or "medium").strip().lower()
    if audio_mood not in {"tense", "melancholic", "euphoric", "dark", "uplifting", "neutral"}:
        audio_mood = "neutral"
    if audio_tempo not in {"fast", "medium", "slow"}:
        audio_tempo = "medium"

    visual_style = str(scene.get("visual_style") or "").strip()
    if visual_style not in {"wide_shot", "close_up", "medium_shot", "aerial", "handheld"}:
        visual_style = _infer_visual_style(desc)

    estimated = int(scene.get("estimated_duration_sec") or _estimate_duration_sec(desc))

    narrative_position = str(scene.get("narrative_position") or "").strip().lower()
    if narrative_position not in {"setup", "conflict", "resolution"}:
        if total <= 2:
            narrative_position = "setup" if idx == 0 else "resolution"
        else:
            third = max(1, total // 3)
            if idx < third:
                narrative_position = "setup"
            elif idx < 2 * third:
                narrative_position = "conflict"
            else:
                narrative_position = "resolution"

    return {
        "scene_number": int(scene_number),
        "description": desc,
        "tags": primary,
        "negative_tags": neg_final,
        "audio_mood": audio_mood,
        "audio_tempo": audio_tempo,
        "visual_style": visual_style,
        "estimated_duration_sec": int(estimated),
        "narrative_position": narrative_position,
    }


def _build_system_prompt(genre: str, setting: str) -> str:
    return (
        "You are a senior professional screenplay writer and film editor.\n"
        "Write a short film plan with a 3-tone narrative arc: setup -> conflict -> resolution.\n"
        "Return STRICT JSON only (no markdown, no preamble, no explanation).\n"
        "JSON must include: title, genre, scenes[]. Each scene must include: scene_number, description, tags, "
        "negative_tags, audio_mood, audio_tempo, visual_style, estimated_duration_sec, narrative_position.\n"
        "Tags MUST be visually descriptive and suitable for CLIP matching (objects, locations, actions, lighting).\n"
        "negative_tags are visuals that should NOT appear (for filtering mismatches).\n"
        "audio_mood must use professional music terminology among: tense, melancholic, euphoric, dark, uplifting.\n"
        "audio_tempo must be one of: fast, medium, slow.\n"
        "visual_style must be one of: wide_shot, close_up, medium_shot, aerial, handheld.\n"
        f"Target genre: {genre}. Target setting: {setting}.\n"
        "Keep total runtime about 90-150 seconds. Use 6-10 scenes.\n"
    )


def _call_groq_json(prompt: str, genre: str, setting: str, temperature: float) -> Dict[str, Any]:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set. Create backend/.env with your key.")

    client = Groq(api_key=api_key)
    messages = [
        {"role": "system", "content": _build_system_prompt(genre, setting)},
        {"role": "user", "content": f"User prompt: {prompt}\nReturn JSON now."},
    ]
    resp = client.chat.completions.create(
        model="llama3-70b-8192",
        temperature=temperature,
        max_tokens=2048,
        messages=messages,
    )
    content = resp.choices[0].message.content
    return json.loads(content)


def generate_script(prompt: str) -> Dict[str, Any]:
    """
    Module 1: Advanced Script Generator
    Input: prompt (str)
    Output: dict matching the strict schema; also saved to outputs/scripts/{title_slug}_script.json
    """
    prompt = (prompt or "").strip()
    genre, setting = _infer_from_context(prompt)
    enriched = f"{prompt}\n\nInferred genre={genre}, setting={setting}."

    try:
        raw = _call_groq_json(enriched, genre, setting, temperature=0.7)
    except json.JSONDecodeError:
        stricter = enriched + "\n\nIMPORTANT: Output must be valid JSON with double quotes, no trailing commas."
        try:
            raw = _call_groq_json(stricter, genre, setting, temperature=0.3)
        except json.JSONDecodeError as e2:
            raise ValueError("Groq returned invalid JSON twice; try a different prompt.") from e2

    title = str(raw.get("title") or "Untitled").strip()
    out_genre = str(raw.get("genre") or genre).strip().lower()
    scenes = raw.get("scenes") or []
    if not isinstance(scenes, list) or len(scenes) == 0:
        raise ValueError("Groq JSON missing scenes[]")

    processed_scenes: List[Dict[str, Any]] = []
    total = len(scenes)
    for i, sc in enumerate(scenes):
        if not isinstance(sc, dict):
            continue
        processed_scenes.append(_ensure_scene_fields(sc, i, total))

    total_est = int(sum(s["estimated_duration_sec"] for s in processed_scenes))
    narrative_arc = "setup | conflict | resolution per scene"

    result: Dict[str, Any] = {
        "title": title,
        "genre": out_genre,
        "total_estimated_duration_sec": total_est,
        "narrative_arc": narrative_arc,
        "scenes": processed_scenes,
    }

    title_slug = slugify(title)
    repo_root = Path(__file__).resolve().parents[2]
    out_path = repo_root / "outputs" / "scripts" / f"{title_slug}_script.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("script_saved", {"path": str(out_path), "title": title, "scenes": len(processed_scenes)})
    return result
