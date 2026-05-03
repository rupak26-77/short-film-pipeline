import React, { useEffect, useMemo, useState } from "react";
import PromptInput from "./components/PromptInput.jsx";
import PipelineStatus from "./components/PipelineStatus.jsx";
import ScriptDisplay from "./components/ScriptDisplay.jsx";
import VideoSegments from "./components/VideoSegments.jsx";
import SimilarityChart from "./components/SimilarityChart.jsx";
import AudioSync from "./components/AudioSync.jsx";

const API_URL = import.meta.env.VITE_API_URL || "";

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
  const [stage, setStage] = useState(0);
  const [pipelineLog, setPipelineLog] = useState([]);

  useEffect(() => {
    fetch(`${API_URL}/assets`)
      .then((r) => r.json())
      .then((j) => {
        setAssets(j);
        if (!audioFile && j.audio?.length) setAudioFile(j.audio[0]);
      })
      .catch(() => {});
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

    try {
      const res = await fetch(`${API_URL}/generate`, {
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
      setLoading(false);
      setStage(0);
    }
  }

  return <div>App Updated</div>;
}
