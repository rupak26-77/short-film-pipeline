import React, { useMemo } from "react";

function Badge({ children, tone = "neutral" }) {
  const cls =
    tone === "green"
      ? "bg-emerald-500/15 border-emerald-400/30 text-emerald-200"
      : tone === "red"
      ? "bg-red-500/15 border-red-400/30 text-red-200"
      : tone === "amber"
      ? "bg-amber-500/15 border-amber-400/30 text-amber-200"
      : tone === "indigo"
      ? "bg-indigo-500/15 border-indigo-400/30 text-indigo-200"
      : "bg-white/5 border-white/10 text-white/80";
  return <span className={`inline-flex items-center px-2 py-1 rounded-lg border text-xs mono ${cls}`}>{children}</span>;
}

function ArcBar({ scenes }) {
  const total = scenes?.length || 0;
  const counts = { setup: 0, conflict: 0, resolution: 0 };
  for (const s of scenes || []) {
    if (counts[s.narrative_position] !== undefined) counts[s.narrative_position] += 1;
  }
  const w = (k) => (total ? `${Math.round((counts[k] / total) * 100)}%` : "0%");
  return (
    <div className="mt-4">
      <div className="mono text-xs text-white/60">Narrative arc</div>
      <div className="mt-2 h-3 rounded-full overflow-hidden bg-black/30 border border-white/10 flex">
        <div className="h-full bg-emerald-500/70" style={{ width: w("setup") }} />
        <div className="h-full bg-amber-500/70" style={{ width: w("conflict") }} />
        <div className="h-full bg-indigo-500/70" style={{ width: w("resolution") }} />
      </div>
      <div className="flex justify-between text-[11px] mono text-white/50 mt-2">
        <span>setup</span>
        <span>conflict</span>
        <span>resolution</span>
      </div>
    </div>
  );
}

export default function ScriptDisplay({ script }) {
  const scenes = script?.scenes || [];
  const total = useMemo(() => script?.total_estimated_duration_sec ?? 0, [script]);

  return (
    <div className="glass rounded-2xl p-5">
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-3">
        <div>
          <div className="mono text-xs text-white/60">Title</div>
          <div className="text-2xl font-heading font-bold">{script?.title || "—"}</div>
          <div className="text-white/70 mt-1">
            <span className="mono text-xs">genre:</span> <span className="capitalize">{script?.genre || "—"}</span>
          </div>
        </div>
        <div className="flex gap-2">
          <Badge tone="indigo">{Math.round(total)} sec</Badge>
          <Badge tone="amber">{scenes.length} scenes</Badge>
        </div>
      </div>

      <ArcBar scenes={scenes} />

      <div className="mt-6 grid grid-cols-1 gap-4">
        {scenes.map((s) => (
          <div key={s.scene_number} className="rounded-2xl bg-black/25 border border-white/10 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <div className="mono text-xs text-white/60">Scene</div>
                <div className="mono text-sm">{s.scene_number}</div>
              </div>
              <div className="flex flex-wrap gap-2">
                <Badge tone="indigo">{s.visual_style}</Badge>
                <Badge tone={s.narrative_position === "setup" ? "green" : s.narrative_position === "conflict" ? "amber" : "indigo"}>
                  {s.narrative_position}
                </Badge>
                <Badge>{s.audio_mood}</Badge>
                <Badge>{s.audio_tempo}</Badge>
              </div>
            </div>

            <p className="text-white/85 mt-3 leading-relaxed">{s.description}</p>

            <div className="mt-4">
              <div className="mono text-xs text-white/60">Tags</div>
              <div className="flex flex-wrap gap-2 mt-2">
                {(s.tags || []).map((t) => (
                  <Badge key={t} tone="green">
                    {t}
                  </Badge>
                ))}
              </div>
            </div>

            <div className="mt-4">
              <div className="mono text-xs text-white/60">Negative tags</div>
              <div className="flex flex-wrap gap-2 mt-2">
                {(s.negative_tags || []).map((t) => (
                  <Badge key={t} tone="red">
                    <span className="line-through">{t}</span>
                  </Badge>
                ))}
              </div>
            </div>

            <div className="mt-4">
              <div className="flex justify-between mono text-[11px] text-white/50">
                <span>Estimated duration</span>
                <span>{s.estimated_duration_sec}s</span>
              </div>
              <div className="mt-2 h-2 rounded-full overflow-hidden bg-white/5 border border-white/10">
                <div
                  className="h-full bg-accent/80"
                  style={{ width: `${Math.min(100, Math.round((s.estimated_duration_sec / 25) * 100))}%` }}
                />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

