import React, { useMemo, useState } from "react";
import { Area, AreaChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis, Line, LineChart } from "recharts";

export default function WaveformVisualizer({ amplitude_data, rms_envelope, beats, duration_sec }) {
  const amp = amplitude_data || [];
  const rms = rms_envelope || [];
  const beatTimes = beats?.all_beats || [];
  const duration = Number(duration_sec || 1);

  const ampData = useMemo(() => amp.map((y, i) => ({ x: (i / Math.max(1, amp.length - 1)) * duration, y })), [amp, duration]);
  const rmsData = useMemo(() => rms.map((y, i) => ({ x: (i / Math.max(1, rms.length - 1)) * duration, y })), [rms, duration]);

  const [playhead, setPlayhead] = useState(0);

  return (
    <div className="rounded-2xl bg-black/25 border border-white/10 p-4">
      <div className="flex items-center justify-between gap-3">
        <div className="mono text-xs text-white/60">Waveform + beat grid overlay</div>
        <div className="mono text-xs text-white/60">playhead: {playhead.toFixed(2)}s</div>
      </div>

      <div className="mt-3 h-44">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={ampData}>
            <defs>
              <linearGradient id="wave" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.8} />
                <stop offset="95%" stopColor="#6366f1" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
            <XAxis dataKey="x" type="number" domain={[0, duration]} hide />
            <YAxis domain={[-1, 1]} hide />
            <Tooltip
              contentStyle={{ background: "rgba(10,10,15,0.92)", border: "1px solid rgba(255,255,255,0.12)" }}
              labelFormatter={(v) => `${Number(v).toFixed(2)}s`}
            />
            {beatTimes.slice(0, 400).map((t, i) => (
              <ReferenceLine key={i} x={t} stroke="rgba(245,158,11,0.35)" strokeWidth={1} />
            ))}
            <ReferenceLine x={playhead} stroke="rgba(16,185,129,0.8)" strokeWidth={2} />
            <Area type="monotone" dataKey="y" stroke="#6366f1" fill="url(#wave)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-3">
        <input
          className="w-full"
          type="range"
          min={0}
          max={duration}
          step={0.01}
          value={playhead}
          onChange={(e) => setPlayhead(Number(e.target.value))}
        />
      </div>

      <div className="mt-4 h-28">
        <div className="mono text-xs text-white/60">RMS envelope</div>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rmsData}>
            <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
            <XAxis dataKey="x" type="number" domain={[0, duration]} tick={{ fill: "rgba(255,255,255,0.55)", fontSize: 11 }} />
            <YAxis domain={[0, 1]} tick={{ fill: "rgba(255,255,255,0.45)", fontSize: 11 }} />
            <Tooltip contentStyle={{ background: "rgba(10,10,15,0.92)", border: "1px solid rgba(255,255,255,0.12)" }} />
            <Line type="monotone" dataKey="y" stroke="#10b981" dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

