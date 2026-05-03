import React, { useMemo, useState } from "react";
import WaveformVisualizer from "./WaveformVisualizer.jsx";
import BeatGrid from "./BeatGrid.jsx";

function Card({ title, value, sub }) {
  return (
    <div className="rounded-2xl bg-black/25 border border-white/10 p-4">
      <div className="mono text-xs text-white/60">{title}</div>
      <div className="mono text-lg mt-1 text-white/90">{value}</div>
      {sub ? <div className="mono text-[11px] text-white/50 mt-1">{sub}</div> : null}
    </div>
  );
}

function chips(xs) {
  return (xs || []).slice(0, 400).map((t, i) => (
    <span key={i} className="inline-flex items-center px-2 py-1 rounded-lg border border-white/10 bg-white/5 mono text-[11px] text-white/80">
      {Number(t).toFixed(2)}s
    </span>
  ));
}

export default function AudioSync({ audio }) {
  const [mode, setMode] = useState("beats"); // beats | half | bar
  const bpm = audio?.tempo?.bpm ?? 0;
  const key = audio?.spectral?.key ?? "—";
  const mood = audio?.classification?.mood_label ?? "—";
  const energy = audio?.classification?.energy_level ?? "—";
  const dur = audio?.duration_sec ?? 0;

  const editList = useMemo(() => {
    if (mode === "half") return audio?.beats?.half_beats || [];
    if (mode === "bar") return audio?.beats?.bar_beats || [];
    return audio?.beats?.all_beats || [];
  }, [audio, mode]);

  return (
    <div className="space-y-6">
      <div className="glass rounded-2xl p-5">
        <div className="mono text-xs text-white/60">Audio analysis</div>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mt-4">
          <Card title="BPM" value={Number(bpm).toFixed(1)} sub={`confidence: ${audio?.tempo?.confidence ?? "—"}`} />
          <Card title="Key" value={key} />
          <Card title="Mood" value={mood} />
          <Card title="Energy" value={energy} />
          <Card title="Duration" value={`${Number(dur).toFixed(1)}s`} sub={audio?.file || ""} />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
          <div className="rounded-2xl bg-black/25 border border-white/10 p-4">
            <div className="mono text-xs text-white/60">Loudness</div>
            <div className="mt-2 grid grid-cols-3 gap-2 mono text-[11px] text-white/75">
              <div className="p-2 rounded-xl bg-white/5 border border-white/10">RMS: {audio?.loudness?.rms_dbfs} dBFS</div>
              <div className="p-2 rounded-xl bg-white/5 border border-white/10">Peak: {audio?.loudness?.peak_dbfs} dBFS</div>
              <div className="p-2 rounded-xl bg-white/5 border border-white/10">DR: {audio?.loudness?.dynamic_range_db} dB</div>
            </div>
            <div className="mt-3 h-2 rounded-full overflow-hidden bg-black/30 border border-white/10">
              <div
                className="h-full bg-emerald-500/70"
                style={{ width: `${Math.min(100, Math.max(0, (Number(audio?.loudness?.dynamic_range_db || 0) / 20) * 100))}%` }}
              />
            </div>
          </div>

          <div className="rounded-2xl bg-black/25 border border-white/10 p-4">
            <div className="mono text-xs text-white/60">MFCC (means)</div>
            <div className="mt-3 grid grid-cols-13 gap-1">
              {(audio?.spectral?.mfcc_means || []).slice(0, 13).map((v, i) => (
                <div
                  key={i}
                  className="h-10 rounded bg-indigo-500/20 border border-indigo-400/20"
                  style={{ opacity: Math.min(1, 0.15 + Math.abs(Number(v)) / 150) }}
                  title={`mfcc${i + 1}: ${v}`}
                />
              ))}
            </div>
            <div className="mono text-[11px] text-white/50 mt-2">Visualized as intensity bars.</div>
          </div>

          <div className="rounded-2xl bg-black/25 border border-white/10 p-4">
            <div className="mono text-xs text-white/60">Spectral stats</div>
            <div className="mt-2 space-y-2 mono text-[11px] text-white/75">
              <div className="p-2 rounded-xl bg-white/5 border border-white/10">Centroid μ: {audio?.spectral?.centroid_mean}</div>
              <div className="p-2 rounded-xl bg-white/5 border border-white/10">Centroid σ: {audio?.spectral?.centroid_std}</div>
              <div className="p-2 rounded-xl bg-white/5 border border-white/10">Rolloff μ: {audio?.spectral?.rolloff_mean}</div>
              <div className="p-2 rounded-xl bg-white/5 border border-white/10">ZCR μ: {audio?.spectral?.zero_crossing_rate_mean}</div>
            </div>
          </div>
        </div>
      </div>

      <WaveformVisualizer
        amplitude_data={audio?.waveform?.amplitude_data || []}
        rms_envelope={audio?.waveform?.rms_envelope || []}
        beats={audio?.beats || {}}
        duration_sec={audio?.duration_sec || 1}
      />

      <BeatGrid beats={audio?.beats || {}} duration_sec={audio?.duration_sec || 1} bpm={bpm} />

      <div className="glass rounded-2xl p-5">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
          <div>
            <div className="mono text-xs text-white/60">Edit points</div>
            <div className="mono text-[11px] text-white/50 mt-1">
              Toggle beat density for cinematic pacing.
            </div>
          </div>
          <div className="flex gap-2">
            {[
              ["beats", "Beat"],
              ["half", "Half-Beat"],
              ["bar", "Bar-Beat"],
            ].map(([k, label]) => (
              <button
                key={k}
                onClick={() => setMode(k)}
                className={`px-3 py-2 rounded-xl text-sm transition border ${
                  mode === k ? "bg-accent/20 border-accent/40" : "bg-white/5 border-white/10 hover:bg-white/10"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2 max-h-44 overflow-auto">
          {chips(editList)}
        </div>

        <div className="mt-6">
          <div className="mono text-xs text-white/60">Silence gaps (natural transitions)</div>
          <div className="mt-3 space-y-2">
            {(audio?.edit_points?.silence_gaps || []).slice(0, 50).map((g, i) => (
              <div key={i} className="p-3 rounded-xl bg-black/25 border border-white/10 mono text-[11px] text-white/75">
                {Number(g.start).toFixed(2)}s → {Number(g.end).toFixed(2)}s
              </div>
            ))}
            {!(audio?.edit_points?.silence_gaps || []).length ? (
              <div className="mono text-[11px] text-white/45">No long internal silences detected.</div>
            ) : null}
          </div>
        </div>

        <div className="mt-6">
          <div className="mono text-xs text-white/60">Onset peaks (energy bursts)</div>
          <div className="mt-3 flex flex-wrap gap-2 max-h-28 overflow-auto">
            {chips(audio?.edit_points?.onset_peaks || [])}
          </div>
        </div>
      </div>
    </div>
  );
}

