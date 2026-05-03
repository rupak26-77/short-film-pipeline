import React, { useEffect, useMemo, useState } from "react";
import PromptInput from "./components/PromptInput.jsx";
import PipelineStatus from "./components/PipelineStatus.jsx";
import ScriptDisplay from "./components/ScriptDisplay.jsx";
import VideoSegments from "./components/VideoSegments.jsx";
import SimilarityChart from "./components/SimilarityChart.jsx";
import AudioSync from "./components/AudioSync.jsx";

const TABS = ["Script", "Video Analysis", "Audio Analysis", "Combined Report"];

function cn(...xs) {
  return xs.filter(Boolean).join(" ");
}

export default function App() {
  const [prompt, setPrompt] = useState(
    "A tense night-time chase in a neon-lit city where a courier carries a mysterious package."
  );
  const [assets, setAssets] = useState({ videos: [], audio: [] });
  const [audioFile, setAudioFile] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState("Script");
  const [stage, setStage] = useState(0); // 0 idle, 1..3 running
  const [pipelineLog, setPipelineLog] = useState([]);

  useEffect(() => {
    fetch("/assets")
      .then((r) => r.json())
      .then((j) => {
        setAssets(j);
        if (!audioFile && j.audio?.length) setAudioFile(j.audio[0]);
      })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const matchedCount = useMemo(() => {
    const m = result?.video_analysis?.matches || [];
    return m.filter((x) => x.status === "matched").length;
  }, [result]);

  async function runPipeline() {
    setError("");
    setLoading(true);
    setResult(null);
    setActiveTab("Script");
    setPipelineLog(["Starting pipeline…", "Stage 1/3: Script generation"]);
    setStage(1);

    const t2 = setTimeout(() => {
      setPipelineLog((l) => [...l, "Stage 2/3: Video analysis"]);
      setStage(2);
    }, 1600);
    const t3 = setTimeout(() => {
      setPipelineLog((l) => [...l, "Stage 3/3: Audio processing"]);
      setStage(3);
    }, 3200);

    try {
      const res = await fetch("/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, audio_file: audioFile }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(typeof data?.detail === "string" ? data.detail : JSON.stringify(data?.detail || data));
      }
      setResult(data);
      setPipelineLog((l) => [...l, "Pipeline complete. Results ready."]);
    } catch (e) {
      setError(String(e?.message || e));
      setPipelineLog((l) => [...l, "Pipeline failed. See error."]);
    } finally {
      clearTimeout(t2);
      clearTimeout(t3);
      setLoading(false);
      setStage(0);
    }
  }

  return (
    <div className="min-h-screen">
      <div className="max-w-6xl mx-auto px-4 py-8">
        <header className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
          <div>
            <div className="text-sm mono text-white/60">AI-Assisted Short Film Preparation Pipeline</div>
            <h1 className="text-3xl md:text-4xl font-heading font-bold tracking-tight">
              Short Film Asset Generator
            </h1>
            <div className="text-white/70 mt-2">
              Script → semantic video matches → beat-aligned audio sync map
            </div>
          </div>
          <div className="glass rounded-xl px-4 py-3">
            <div className="mono text-xs text-white/60">Quick stats</div>
            <div className="flex gap-6 mt-1">
              <div>
                <div className="text-white/80 text-sm">Scenes</div>
                <div className="mono text-lg">{result?.script?.scenes?.length ?? "—"}</div>
              </div>
              <div>
                <div className="text-white/80 text-sm">Matched</div>
                <div className="mono text-lg">{result ? matchedCount : "—"}</div>
              </div>
              <div>
                <div className="text-white/80 text-sm">BPM</div>
                <div className="mono text-lg">{result?.audio_analysis?.tempo?.bpm ?? "—"}</div>
              </div>
            </div>
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-8">
          <div className="lg:col-span-1">
            <div className="glass rounded-2xl p-5">
              <PromptInput
                prompt={prompt}
                setPrompt={setPrompt}
                assets={assets}
                audioFile={audioFile}
                setAudioFile={setAudioFile}
                onRun={runPipeline}
                loading={loading}
              />
            </div>
            <div className="glass rounded-2xl p-5 mt-6">
              <PipelineStatus loading={loading} stage={stage} log={pipelineLog} />
              {error ? (
                <div className="mt-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-200 mono text-xs">
                  {error}
                </div>
              ) : null}
            </div>
          </div>

          <div className="lg:col-span-2">
            <div className="glass rounded-2xl p-3">
              <div className="flex flex-wrap gap-2">
                {TABS.map((t) => (
                  <button
                    key={t}
                    className={cn(
                      "px-3 py-2 rounded-xl text-sm transition",
                      activeTab === t
                        ? "bg-accent/20 border border-accent/40"
                        : "bg-white/5 border border-white/10 hover:bg-white/10"
                    )}
                    onClick={() => setActiveTab(t)}
                    disabled={!result}
                    title={!result ? "Run pipeline first" : ""}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>

            <div className="mt-6 fade-in">
              {!result ? (
                <div className="glass rounded-2xl p-8 text-white/70">
                  Run the pipeline to generate a complete film asset package.
                  <div className="mono text-xs text-white/50 mt-2">
                    Tip: add 3–10 short videos to <span className="text-white/70">assets/videos/</span> and one music
                    track to <span className="text-white/70">assets/audio/</span>.
                  </div>
                </div>
              ) : null}

              {result && activeTab === "Script" ? (
                <ScriptDisplay script={result.script} />
              ) : null}

              {result && activeTab === "Video Analysis" ? (
                <div className="space-y-6">
                  <VideoSegments videoMatches={result.video_analysis} />
                  <SimilarityChart matches={result.video_analysis?.matches || []} />
                </div>
              ) : null}

              {result && activeTab === "Audio Analysis" ? (
                <AudioSync audio={result.audio_analysis} />
              ) : null}

              {result && activeTab === "Combined Report" ? (
                <div className="glass rounded-2xl p-5">
                  <div className="mono text-xs text-white/60">Combined JSON</div>
                  <pre className="mono text-xs overflow-auto mt-3 p-4 rounded-xl bg-black/30 border border-white/10">
                    {JSON.stringify(result, null, 2)}
                  </pre>
                </div>
              ) : null}
            </div>
          </div>
        </div>

        <footer className="text-white/50 mono text-xs mt-10">
          Backend: FastAPI · Video: OpenCV + SceneDetect + CLIP · Audio: librosa + pydub · UI: Recharts
        </footer>
      </div>
    </div>
  );
}

