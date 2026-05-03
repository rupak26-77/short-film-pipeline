import React from "react";

function Step({ label, active, done }) {
  return (
    <div className="flex items-center gap-3">
      <div
        className={[
          "w-3 h-3 rounded-full border",
          done ? "bg-emerald-400/80 border-emerald-300/60" : "",
          active ? "bg-amber-400/80 border-amber-300/60 animate-pulse" : "",
          !done && !active ? "bg-white/10 border-white/20" : "",
        ].join(" ")}
      />
      <div className="text-sm text-white/80">{label}</div>
    </div>
  );
}

export default function PipelineStatus({ loading, stage, log }) {
  const s = loading ? stage : 0;
  return (
    <div>
      <div className="mono text-xs text-white/60">Pipeline status</div>
      <div className="mt-3 space-y-3">
        <Step label="Script Generation" active={s === 1} done={!loading && log?.length > 2} />
        <Step label="Video Analysis" active={s === 2} done={!loading && log?.some((x) => x.includes("Video"))} />
        <Step label="Audio Processing" active={s === 3} done={!loading && log?.some((x) => x.includes("Audio"))} />
      </div>

      <div className="mt-4 mono text-xs text-white/60">Log</div>
      <div className="mt-2 h-32 overflow-auto rounded-xl bg-black/25 border border-white/10 p-3 mono text-[11px] text-white/70">
        {(log || []).length ? (
          (log || []).map((l, i) => (
            <div key={i} className="whitespace-pre-wrap">
              {l}
            </div>
          ))
        ) : (
          <div className="text-white/40">Idle.</div>
        )}
      </div>
    </div>
  );
}

