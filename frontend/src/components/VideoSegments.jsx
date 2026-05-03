import React from "react";

function fmt(sec) {
  const s = Math.max(0, Number(sec || 0));
  const m = Math.floor(s / 60);
  const r = Math.floor(s - m * 60);
  return `${String(m).padStart(2, "0")}:${String(r).padStart(2, "0")}`;
}

function ScorePill({ label, value, tone }) {
  const cls =
    tone === "green"
      ? "bg-emerald-500/15 border-emerald-400/30 text-emerald-200"
      : tone === "amber"
      ? "bg-amber-500/15 border-amber-400/30 text-amber-200"
      : tone === "red"
      ? "bg-red-500/15 border-red-400/30 text-red-200"
      : "bg-white/5 border-white/10 text-white/80";
  return (
    <span className={`inline-flex items-center px-2 py-1 rounded-lg border text-[11px] mono ${cls}`}>
      {label}: {value}
    </span>
  );
}

function factorDurationScore(durationSec) {
  const d = Number(durationSec || 0);
  if (d >= 5 && d <= 15) return 1;
  return Math.min(d / 15, 1);
}

function QualityBar({ semantic, motion, resolution, duration }) {
  const sum = semantic + motion + resolution + duration || 1;
  const w = (x) => `${Math.round((x / sum) * 100)}%`;
  return (
    <div className="mt-3 h-3 rounded-full overflow-hidden bg-black/30 border border-white/10 flex">
      <div className="h-full bg-indigo-500/70" style={{ width: w(semantic) }} title="Semantic" />
      <div className="h-full bg-amber-500/70" style={{ width: w(motion) }} title="Motion" />
      <div className="h-full bg-emerald-500/70" style={{ width: w(resolution) }} title="Resolution" />
      <div className="h-full bg-sky-500/70" style={{ width: w(duration) }} title="Duration" />
    </div>
  );
}

export default function VideoSegments({ videoMatches }) {
  const matches = videoMatches?.matches || [];
  const unmatched = videoMatches?.unmatched_scenes || [];
  const scanned = videoMatches?.total_videos_scanned ?? 0;
  const segs = videoMatches?.total_segments_detected ?? 0;
  const matched = matches.filter((m) => m.status === "matched").length;

  return (
    <div className="glass rounded-2xl p-5">
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-3">
        <div>
          <div className="mono text-xs text-white/60">Video analysis summary</div>
          <div className="text-white/80 mt-1">
            <span className="mono">scanned</span> {scanned} · <span className="mono">segments</span> {segs} ·{" "}
            <span className="mono">matched scenes</span> {matched}/{matches.length}
          </div>
        </div>
        {unmatched.length ? (
          <div className="px-3 py-2 rounded-xl bg-amber-500/10 border border-amber-400/30 text-amber-200 mono text-xs">
            Unmatched scenes: {unmatched.join(", ")}
          </div>
        ) : (
          <div className="px-3 py-2 rounded-xl bg-emerald-500/10 border border-emerald-400/30 text-emerald-200 mono text-xs">
            All scenes matched
          </div>
        )}
      </div>

      <div className="mt-6 space-y-4">
        {matches.map((m) => (
          <div key={m.scene_number} className="rounded-2xl bg-black/25 border border-white/10 p-4">
            <div className="flex items-center justify-between">
              <div className="mono text-sm">Scene {m.scene_number}</div>
              <div className="mono text-xs text-white/60">{m.status}</div>
            </div>

            {m.status !== "matched" ? (
              <div className="mt-3 p-3 rounded-xl bg-red-500/10 border border-red-400/25 text-red-200 mono text-xs">
                No candidate segment crossed the semantic threshold.
              </div>
            ) : null}

            <div className="mt-4 grid grid-cols-1 gap-3">
              {(m.candidates || []).map((c) => {
                const q = Number(c.quality_score || 0);
                const tone = q > 0.7 ? "green" : q >= 0.4 ? "amber" : "red";
                const durScore = factorDurationScore(c.duration_sec);
                return (
                  <div key={c.rank} className="rounded-2xl bg-black/20 border border-white/10 p-4">
                    <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2">
                      <div className="flex items-center gap-3">
                        <div className="mono text-xs text-white/60">Rank</div>
                        <div className="mono text-lg">{c.rank}</div>
                        <div className="mono text-xs text-white/60">File</div>
                        <div className="mono text-sm text-white/90">{c.file}</div>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <ScorePill label="res" value={c.resolution} />
                        <ScorePill label="fps" value={c.fps} />
                        <ScorePill
                          label="style"
                          value={c.visual_style_match ? "match" : "no"}
                          tone={c.visual_style_match ? "green" : "red"}
                        />
                      </div>
                    </div>

                    <div className="mt-2 mono text-xs text-white/70">
                      {fmt(c.start_sec)} → {fmt(c.end_sec)} ({c.duration_sec}s)
                    </div>

                    <QualityBar
                      semantic={0.35 * Number(c.semantic_score || 0)}
                      motion={0.25 * Number(c.motion_score || 0)}
                      resolution={0.2 * Number(c.resolution_score || 0)}
                      duration={0.2 * durScore}
                    />

                    <div className="mt-3 flex flex-wrap gap-2">
                      <ScorePill label="semantic" value={c.semantic_score} />
                      <ScorePill label="motion" value={c.motion_score} />
                      <ScorePill label="resolution" value={c.resolution_score} />
                      <ScorePill label="duration" value={durScore.toFixed(3)} />
                      <ScorePill label="quality" value={c.quality_score} tone={tone} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

