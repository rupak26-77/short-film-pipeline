import React, { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

function durationScore(d) {
  const x = Number(d || 0);
  if (x >= 5 && x <= 15) return 1;
  return Math.min(x / 15, 1);
}

export default function SimilarityChart({ matches }) {
  const top = useMemo(() => {
    return (matches || [])
      .map((m) => {
        const c = (m.candidates || [])[0];
        if (!c) return null;
        return {
          scene: String(m.scene_number),
          Semantic: Number(c.semantic_score || 0),
          Motion: Number(c.motion_score || 0),
          Resolution: Number(c.resolution_score || 0),
          Duration: durationScore(c.duration_sec),
          quality: Number(c.quality_score || 0),
        };
      })
      .filter(Boolean);
  }, [matches]);

  return (
    <div className="glass rounded-2xl p-5">
      <div className="mono text-xs text-white/60">Similarity & quality charts (top candidate per scene)</div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-4">
        <div className="rounded-2xl bg-black/25 border border-white/10 p-4">
          <div className="mono text-xs text-white/60">Factor radar</div>
          <div className="h-72 mt-2">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={top}>
                <CartesianGrid stroke="rgba(255,255,255,0.08)" />
                <XAxis dataKey="scene" stroke="rgba(255,255,255,0.6)" />
                <YAxis domain={[0, 1]} stroke="rgba(255,255,255,0.35)" />
                <Tooltip contentStyle={{ background: "rgba(10,10,15,0.92)", border: "1px solid rgba(255,255,255,0.12)" }} />
                <Legend />
                <Radar name="Semantic" dataKey="Semantic" stroke="#6366f1" fill="#6366f1" fillOpacity={0.15} />
                <Radar name="Motion" dataKey="Motion" stroke="#f59e0b" fill="#f59e0b" fillOpacity={0.12} />
                <Radar name="Resolution" dataKey="Resolution" stroke="#10b981" fill="#10b981" fillOpacity={0.12} />
                <Radar name="Duration" dataKey="Duration" stroke="#38bdf8" fill="#38bdf8" fillOpacity={0.10} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-2xl bg-black/25 border border-white/10 p-4">
          <div className="mono text-xs text-white/60">Quality score per scene</div>
          <div className="h-72 mt-2">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={top}>
                <CartesianGrid stroke="rgba(255,255,255,0.08)" />
                <XAxis dataKey="scene" stroke="rgba(255,255,255,0.6)" />
                <YAxis domain={[0, 1]} stroke="rgba(255,255,255,0.35)" />
                <Tooltip contentStyle={{ background: "rgba(10,10,15,0.92)", border: "1px solid rgba(255,255,255,0.12)" }} />
                <Bar dataKey="quality" fill="rgba(99,102,241,0.85)" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}

