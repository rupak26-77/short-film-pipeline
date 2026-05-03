# AI-Assisted Short Film Preparation Pipeline

An end-to-end **demo-ready** pipeline that accepts a text prompt and produces a synchronized short-film asset package:

- **Module 1**: AI screenplay JSON (Groq LLaMA 3 70B)
- **Module 2**: Semantic video segment matching + quality scoring (SceneDetect + OpenCV + CLIP)
- **Module 3**: Beat-aligned audio synchronization map + edit points (librosa DSP + pydub)
- **Frontend**: Cinematic dark UI with **Recharts** visualizations

---

## Folder structure

```
short-film-pipeline/
├── backend/
├── frontend/
├── assets/
│   ├── videos/
│   └── audio/
├── outputs/
│   ├── scripts/
│   ├── analysis/
│   └── reports/
└── README.md
```

---

## Architecture (pipeline diagram)

```
             +--------------------+
Prompt ----> | Script Generator   | ----> outputs/scripts/*_script.json
             | (Groq LLaMA3-70B)  |
             +---------+----------+
                       |
                       v
             +--------------------+
             | Video Analyzer     | ----> outputs/analysis/*_video_analysis.json
             | (SceneDetect+CLIP) |
             +---------+----------+
                       |
                       v
             +--------------------+
Audio file ->| Audio Processor    | ----> outputs/analysis/*_audio_analysis.json
             | (librosa+pydub)    |
             +---------+----------+
                       |
                       v
             +--------------------+
             | Combined Report    | ----> outputs/reports/*_pipeline_result.json
             +--------------------+
```

---

## Setup (Backend)

### 1) Create virtualenv + install deps

```bash
cd short-film-pipeline/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Configure Groq key

Create `backend/.env`:

```bash
GROQ_API_KEY=your_groq_api_key_here
```

### 3) Add demo media

- Put **videos** into `assets/videos/` (`.mp4`, `.mov`, `.avi`)
- Put **audio** into `assets/audio/` (`.mp3`, `.wav`, `.m4a`, etc.)

### 4) Run FastAPI

```bash
cd short-film-pipeline
python3 -m uvicorn backend.main:app --reload --port 8000
```

Health check: `GET /health`

---

## Setup (Frontend)

```bash
cd short-film-pipeline/frontend
npm install
npm run dev
```

Open: `http://localhost:5173`

---

## API

### `POST /generate`

Request:

```json
{ "prompt": "string", "audio_file": "string" }
```

Response:

- `script`: Module 1 output
- `video_analysis`: Module 2 output
- `audio_analysis`: Module 3 output

Also saves:

- `outputs/scripts/{title_slug}_script.json`
- `outputs/analysis/{title_slug}_video_analysis.json`
- `outputs/analysis/{title_slug}_audio_analysis.json`
- `outputs/reports/{timestamp}_pipeline_result.json`

### `GET /assets`

Returns available files in `assets/videos/` and `assets/audio/`.

### `GET /outputs`

Lists saved pipeline reports.

### `GET /outputs/{filename}`

Fetch a saved report JSON.

---

## Viva-ready technical notes

- **Script JSON enforcement**: strict JSON-only prompting + retry strategy on parse failures.
- **Video semantics**: CLIP embeddings averaged over sampled frames (\(2\) FPS) with **negative tag suppression** and a **visual-style boost**.
- **Quality scoring**: weighted multi-factor score combining semantics, motion entropy, resolution, and duration preference.
- **DSP**: onset envelope + beat tracking, beat-regularity confidence, spectral feature extraction, key estimation via chroma-profile correlation, and beat/silence/onset edit points.

