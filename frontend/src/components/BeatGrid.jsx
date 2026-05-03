import React, { useMemo, useState } from "react";

function cn(...xs) {
  return xs.filter(Boolean).join(" ");
}

export default function BeatGrid({ beats, duration_sec, bpm }) {
  const duration = Number(duration_sec || 1);
  const [zoom, setZoom] = useState("full"); // full | 30 | 10

  const windowSec = zoom === "full" ? duration : zoom === "30" ? 30 : 10;
  const scale = 100 / windowSec;

  const bars = useMemo(() => {
    const bb = beats?.bar_beats || [];
    return bb.map((t) => Number(t)).filter((t) => t >= 0 && t <= duration);
  }, [beats, duration]);
  const all = useMemo(() => {
    const ab = beats?.all_beats || [];
    return ab.map((t) => Number(t)).filter((t) => t >= 0 && t <= duration);
  }, [beats, duration]);

  return (
    <div className="rounded-2xl bg-black/25 border border-white/10 p-4">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        <div>
          <div className="mono text-xs text-white/60">Beat grid</div>
          <div className="mono text-xs text-white/50 mt-1">
            bpm: {Number(bpm || 0).toFixed(1)} · duration: {duration.toFixed(1)}s · zoom: {zoom}
          </div>
        </div>
        <div className="flex gap-2">
          {["full", "30", "10"].map((z) => (
            <button
              key={z}
              onClick={() => setZoom(z)}
              className={cn(
                "px-3 py-2 rounded-xl text-sm transition border",
                zoom === z ? "bg-accent/20 border-accent/40" : "bg-white/5 border-white/10 hover:bg-white/10"
              )}
            >
              {z === "full" ? "Full" : `${z}s`}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-4 h-12 rounded-xl bg-black/20 border border-white/10 relative overflow-hidden">
        {all.slice(0, 600).map((t, i) => {
          const x = (t % windowSec) * scale;
          return (
            <div
              key={`b-${i}`}
              className="absolute top-0 bottom-0 w-[1px] bg-amber-400/40"
              style={{ left: `${x}%` }}
              title={`${t.toFixed(2)}s`}
            />
          );
        })}
        {bars.slice(0, 200).map((t, i) => {
          const x = (t % windowSec) * scale;
          return (
            <div
              key={`bar-${i}`}
              className="absolute top-0 bottom-0 w-[2px] bg-emerald-400/65"
              style={{ left: `${x}%` }}
              title={`bar @ ${t.toFixed(2)}s`}
            />
          );
        })}
      </div>
    </div>
  );
}

