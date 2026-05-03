import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import librosa
import numpy as np
from pydub import AudioSegment
from pydub.silence import detect_silence
from scipy.signal import resample

from utils.logger import get_logger
from utils.validators import audio_info_from_pydub_channels_samplewidth, slugify

logger = get_logger(__name__)


_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _dbfs_from_rms(rms: float) -> float:
    return float(20.0 * math.log10(max(rms, 1e-12)))


def _safe_list_floats(x: np.ndarray, n: Optional[int] = None) -> List[float]:
    arr = np.asarray(x, dtype=np.float64).ravel()
    if n is not None:
        arr = arr[:n]
    return [float(v) for v in arr.tolist()]


def _key_from_chroma(chroma_mean: np.ndarray) -> str:
    chroma_mean = np.asarray(chroma_mean, dtype=np.float64).ravel()
    if chroma_mean.size != 12:
        return "Unknown"
    root = int(np.argmax(chroma_mean))
    major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
    minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

    def rot(v: np.ndarray, k: int) -> np.ndarray:
        return np.roll(v, k)

    x = chroma_mean / (np.linalg.norm(chroma_mean) + 1e-12)
    best_mode = "major"
    best_corr = -1e9
    best_root = root
    for r in range(12):
        maj = rot(major_profile, r)
        minr = rot(minor_profile, r)
        maj = maj / (np.linalg.norm(maj) + 1e-12)
        minr = minr / (np.linalg.norm(minr) + 1e-12)
        cmaj = float(np.dot(x, maj))
        cmin = float(np.dot(x, minr))
        if cmaj > best_corr:
            best_corr, best_mode, best_root = cmaj, "major", r
        if cmin > best_corr:
            best_corr, best_mode, best_root = cmin, "minor", r
    return f"{_NOTE_NAMES[best_root]} {best_mode}"


def _downsample_signal(y: np.ndarray, n: int) -> np.ndarray:
    y = np.asarray(y, dtype=np.float64).ravel()
    if y.size == 0:
        return np.zeros((n,), dtype=np.float64)
    if y.size == n:
        return y
    return resample(y, n).astype(np.float64)


def _normalize_amp(y: np.ndarray) -> np.ndarray:
    y = np.asarray(y, dtype=np.float64).ravel()
    mx = float(np.max(np.abs(y))) if y.size else 0.0
    if mx < 1e-12:
        return y
    return (y / mx).astype(np.float64)


def _classify_energy(rms_norm: float) -> str:
    if rms_norm > 0.7:
        return "high"
    if rms_norm >= 0.4:
        return "medium"
    return "low"


def _mood_label(bpm: float, zcr_mean: float, centroid_mean: float, contrast_mean: float, key: str) -> str:
    is_minor = "minor" in (key or "").lower()
    is_major = "major" in (key or "").lower()
    if bpm > 120 and zcr_mean > 0.08 and contrast_mean > 20:
        return "energetic"
    if bpm < 80 and centroid_mean < 2200 and is_minor:
        return "melancholic"
    if 90 <= bpm <= 130 and is_major and contrast_mean > 18:
        return "uplifting"
    if centroid_mean > 3200 and bpm >= 90:
        return "tense"
    if zcr_mean < 0.06 and contrast_mean < 16 and is_minor:
        return "dark"
    return "neutral"


def process_audio(audio_path: str, title_slug: Optional[str] = None) -> Dict[str, Any]:
    """
    Module 3: Advanced Audio Processor
    Input: audio_path (str)
    Output: strict schema; also saved to outputs/analysis/{title_slug}_audio_analysis.json
    """
    repo_root = Path(__file__).resolve().parents[2]
    ap = Path(audio_path)
    if not ap.is_absolute():
        ap = (repo_root / audio_path).resolve()

    if not ap.exists():
        return {"error": "file_not_found", "detail": f"{ap}", "file": str(ap)}

    # pydub metadata (channels, bit depth); analysis uses librosa mono
    seg = AudioSegment.from_file(str(ap))
    _channels, _bit_depth = audio_info_from_pydub_channels_samplewidth(seg.channels, seg.sample_width)
    duration_sec = float(len(seg) / 1000.0)

    # librosa load at high quality
    y, sr = librosa.load(str(ap), sr=44100, mono=True)
    if y.size == 0:
        return {"error": "empty_audio", "detail": "no samples decoded", "file": ap.name}

    # Step 2: Silence trimming + internal gaps
    y_trim, idx = librosa.effects.trim(y, top_db=30)
    trim_start = float(idx[0] / sr)
    _trim_end = float(idx[1] / sr)
    _trimmed_duration = float(y_trim.size / sr)

    # internal silence segments from librosa (in trimmed space)
    split_intervals = librosa.effects.split(y_trim, top_db=30)
    silence_gaps: List[Dict[str, float]] = []
    prev_end = 0
    for (s0, s1) in split_intervals:
        if s0 > prev_end:
            gap_dur = float((s0 - prev_end) / sr)
            if gap_dur >= 1.0:
                silence_gaps.append({"start": float(prev_end / sr + trim_start), "end": float(s0 / sr + trim_start)})
        prev_end = int(s1)
    if prev_end < y_trim.size:
        tail = float((y_trim.size - prev_end) / sr)
        if tail >= 1.0:
            silence_gaps.append({"start": float(prev_end / sr + trim_start), "end": float(y_trim.size / sr + trim_start)})

    # pydub silence detection (more robust in dBFS)
    sil_ms = detect_silence(seg, min_silence_len=500, silence_thresh=-40)
    for (s_ms, e_ms) in sil_ms:
        if (e_ms - s_ms) >= 1000:
            silence_gaps.append({"start": float(s_ms / 1000.0), "end": float(e_ms / 1000.0)})

    # Step 3: Loudness normalization (approximate -14 LUFS via dBFS gain)
    current_dbfs = float(seg.dBFS) if seg.dBFS != float("-inf") else -60.0
    target_dbfs = -14.0
    gain_db = target_dbfs - current_dbfs
    seg_norm = seg.apply_gain(gain_db)
    rms_dbfs = _dbfs_from_rms(float(np.sqrt(np.mean(np.square(y_trim)))))
    peak_dbfs = float(20.0 * math.log10(max(float(np.max(np.abs(y_trim))), 1e-12)))
    dynamic_range = float(peak_dbfs - rms_dbfs)

    # Step 4: Tempo & beat analysis
    onset_env = librosa.onset.onset_strength(y=y_trim, sr=sr)
    try:
        tempo, beat_frames = librosa.beat.beat_track(y=y_trim, sr=sr, onset_envelope=onset_env, tightness=100)
    except TypeError:
        tempo, beat_frames = librosa.beat.beat_track(y=y_trim, sr=sr, onset_envelope=onset_env)

    bpm = float(tempo) if tempo is not None else 0.0
    if bpm < 40 or bpm > 220 or bpm == 0.0:
        tempos = librosa.beat.tempo(onset_envelope=onset_env, sr=sr, aggregate=None)
        bpm = float(np.median(tempos)) if tempos is not None and len(tempos) else float(max(60.0, min(160.0, bpm or 120.0)))

    beat_times_trim = librosa.frames_to_time(beat_frames, sr=sr).astype(np.float64) if beat_frames is not None else np.array([], dtype=np.float64)
    beat_times = (beat_times_trim + trim_start).astype(np.float64)

    if beat_times.size >= 3:
        ibis = np.diff(beat_times)
        mean_ibi = float(np.mean(ibis))
        std_ibi = float(np.std(ibis))
        confidence = float(1.0 - min(std_ibi / (mean_ibi + 1e-12), 1.0))
    else:
        confidence = 0.0

    all_beats = _safe_list_floats(beat_times)
    half_beats = _safe_list_floats(beat_times[::2]) if beat_times.size else []
    bar_beats = _safe_list_floats(beat_times[::4]) if beat_times.size else []

    # Step 5: Spectral analysis
    centroid = librosa.feature.spectral_centroid(y=y_trim, sr=sr)
    rolloff = librosa.feature.spectral_rolloff(y=y_trim, sr=sr)
    zcr = librosa.feature.zero_crossing_rate(y=y_trim)
    mfcc = librosa.feature.mfcc(y=y_trim, sr=sr, n_mfcc=13)
    chroma = librosa.feature.chroma_stft(y=y_trim, sr=sr)
    contrast = librosa.feature.spectral_contrast(y=y_trim, sr=sr)

    centroid_mean = float(np.mean(centroid))
    centroid_std = float(np.std(centroid))
    rolloff_mean = float(np.mean(rolloff))
    zcr_mean = float(np.mean(zcr))
    mfcc_means = np.mean(mfcc, axis=1)
    chroma_mean = np.mean(chroma, axis=1)
    contrast_means = np.mean(contrast, axis=1)
    key = _key_from_chroma(chroma_mean)

    # Step 6: Mood & energy classification
    rms = librosa.feature.rms(y=y_trim).ravel()
    rms_norm = float(np.mean(rms) / (np.max(rms) + 1e-12)) if rms.size else 0.0
    energy_level = _classify_energy(rms_norm)
    mood = _mood_label(bpm, zcr_mean, centroid_mean, float(np.mean(contrast_means)), key)

    # Step 7: Edit points
    try:
        onset_frames = librosa.onset.onset_detect(y=y_trim, sr=sr, backtrack=True, onset_envelope=onset_env)
    except TypeError:
        onset_frames = librosa.onset.onset_detect(y=y_trim, sr=sr, backtrack=True)
    onset_times = (librosa.frames_to_time(onset_frames, sr=sr).astype(np.float64) + trim_start).astype(np.float64)
    onset_peaks = _safe_list_floats(onset_times)

    edit_points = {
        "beat_aligned": all_beats,
        "silence_gaps": silence_gaps,
        "onset_peaks": onset_peaks,
    }

    # Step 8: Waveform for visualization
    amp = _normalize_amp(y_trim)
    amp_ds = _downsample_signal(amp, 1000)
    rms_env = _downsample_signal(rms.astype(np.float64) if rms.size else np.zeros((1,), dtype=np.float64), 100)
    if rms_env.size:
        rms_env = (rms_env / (np.max(rms_env) + 1e-12)).astype(np.float64)

    result: Dict[str, Any] = {
        "file": ap.name,
        "duration_sec": round(duration_sec, 3),
        "sample_rate": int(sr),
        "tempo": {"bpm": round(bpm, 3), "confidence": round(confidence, 4), "time_signature": "4/4"},
        "beats": {"all_beats": all_beats, "half_beats": half_beats, "bar_beats": bar_beats},
        "edit_points": edit_points,
        "loudness": {
            "rms_dbfs": round(float(rms_dbfs), 3),
            "peak_dbfs": round(float(peak_dbfs), 3),
            "dynamic_range_db": round(float(dynamic_range), 3),
            "normalized_lufs": -14.0,
        },
        "spectral": {
            "centroid_mean": round(centroid_mean, 3),
            "centroid_std": round(centroid_std, 3),
            "rolloff_mean": round(rolloff_mean, 3),
            "zero_crossing_rate_mean": round(zcr_mean, 6),
            "mfcc_means": [round(float(x), 6) for x in mfcc_means.tolist()],
            "key": key,
            "spectral_contrast_means": [round(float(x), 6) for x in contrast_means.tolist()],
        },
        "classification": {"energy_level": energy_level, "mood_label": mood},
        "waveform": {
            "amplitude_data": [round(float(x), 6) for x in amp_ds.tolist()],
            "rms_envelope": [round(float(x), 6) for x in rms_env.tolist()],
        },
    }

    # Save analysis
    out_slug = title_slug or slugify(ap.stem)
    out_path = repo_root / "outputs" / "analysis" / f"{out_slug}_audio_analysis.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("audio_analysis_saved", {"path": str(out_path), "file": ap.name, "duration_sec": duration_sec})

    # Export normalized audio for demo playback (optional but useful)
    try:
        norm_path = repo_root / "outputs" / "analysis" / f"{out_slug}_normalized.wav"
        seg_norm.export(str(norm_path), format="wav")
        logger.info("audio_normalized_saved", {"path": str(norm_path), "target_dbfs": target_dbfs})
    except Exception as e:
        logger.info("audio_normalized_export_failed", {"detail": str(e)})

    return result
