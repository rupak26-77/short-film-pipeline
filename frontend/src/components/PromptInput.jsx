import React from "react";

export default function PromptInput({
  prompt,
  setPrompt,
  assets,
  audioFile,
  setAudioFile,
  onRun,
  loading,
}) {
  return (
    <div>
      <div className="mono text-xs text-white/60">Prompt</div>
      <textarea
        className="mt-2 w-full h-40 resize-none rounded-xl bg-black/30 border border-white/10 px-3 py-3 text-white/90 focus:outline-none focus:ring-2 focus:ring-accent/50"
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder="Describe the short film idea (10–500 chars)…"
      />

      <div className="mt-4">
        <div className="mono text-xs text-white/60">Audio file (from assets/audio/)</div>
        <select
          className="mt-2 w-full rounded-xl bg-black/30 border border-white/10 px-3 py-3 text-white/90 focus:outline-none focus:ring-2 focus:ring-accent/50"
          value={audioFile}
          onChange={(e) => setAudioFile(e.target.value)}
        >
          {(assets?.audio || []).length ? null : <option value="">No audio found</option>}
          {(assets?.audio || []).map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </select>
        <div className="mono text-[11px] text-white/50 mt-2">
          Add files to <span className="text-white/70">short-film-pipeline/assets/audio/</span>.
        </div>
      </div>

      <button
        onClick={onRun}
        disabled={loading || !audioFile || !prompt?.trim()}
        className="mt-5 w-full rounded-xl px-4 py-3 font-semibold bg-accent/90 hover:bg-accent disabled:opacity-40 disabled:hover:bg-accent/90 transition"
      >
        {loading ? "Running pipeline…" : "Generate Film Package"}
      </button>
    </div>
  );
}

