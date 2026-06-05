# Speech-AI 🎙️

A speech-fluency assistant that reads text, identifies phonetically risky or hard-to-say words, and replaces them with easier alternatives — while preserving meaning, tense, and factual accuracy.

Built with **FastAPI + Gemini** (backend) and **React + Vite** (frontend).

---

## Project Structure

```
speech-ai/
├── speech-backend/          # Python FastAPI backend
│   ├── main.py              # Core API server
│   ├── grammar_module.py    # GrammarGuard — 5-layer grammar checker
│   ├── cluster_cache.pkl    # Phoneme cluster data
│   ├── freq_rank.pkl        # Word frequency rankings
│   ├── phoneme_index.pkl    # ARPAbet phoneme index
│   ├── pos_map.pkl          # POS tag lookup table
│   └── synonym_map.pkl      # Pre-computed synonym map
│
├── speech-app/              # React + Vite frontend
│   ├── src/
│   │   ├── SpeechAI.jsx     # Main UI component
│   │   ├── GrammarPanel.jsx # Grammar check panel
│   │   ├── main.jsx
│   │   └── index.css
│   ├── package.json
│   └── vite.config.js
│
├── requirements.txt         # Python dependencies
├── .gitignore
└── README.md
```

---

## Prerequisites

| Tool | Minimum version |
|------|----------------|
| Python | 3.10+ |
| Node.js | 18+ |
| npm | 9+ |
| Gemini API Key | Use yours ;) |

> **Java is only needed if you want LanguageTool (Layer 4 of GrammarGuard).** It's optional — the system works without it.

---

## Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/speech-ai.git
cd speech-ai
```

---

### 2. Backend Setup

#### 2a. Create and activate a virtual environment (recommended)

```bash
cd speech-backend

# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

#### 2b. Install Python dependencies

```bash
pip install -r ../requirements.txt
```

#### 2c. Set your Gemini API key

The backend reads the key from the environment variable `GEMINI_API_KEY`.

**Windows (Command Prompt)**
```cmd
set GEMINI_API_KEY=your_key_here
```

**Windows (PowerShell)**
```powershell
$env:GEMINI_API_KEY="your_key_here"
```

**macOS / Linux**
```bash
export GEMINI_API_KEY=your_key_here
```

> Get a free Gemini API key at [aistudio.google.com](https://aistudio.google.com).

#### 2d. Start the backend server

```bash
uvicorn main:app --reload --port 8000
```

You should see:
```
INFO | GrammarGuard initialised (LT=False, Gemini=True, ...)
INFO:     Uvicorn running on http://127.0.0.1:8000
```

The backend is now live at **http://localhost:8000**.

---

### 3. Frontend Setup

Open a **new terminal window/tab** and leave the backend running.

```bash
cd speech-app
npm install
npm run dev
```

You should see:
```
  VITE v6.x.x  ready in xxx ms
  ➜  Local:   http://localhost:5173/
```

Open **http://localhost:5173** in your browser — the app is running.

---

## How It Works

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/transform-paragraph` | POST | Main pipeline — tokenises input, scores phonetic risk, fetches substitutions |
| `/api/synonyms` | POST | Fetch deeper synonym list for a specific word |
| `/api/user/report-spike` | POST | Report a stutter spike; re-runs transform with adjusted risk weights |
| `/api/grammar-check` | POST | 5-layer grammar + tense + fact integrity check |

### Backend Pipeline

1. **LocalEngine** — phonetic + POS filtering using the `.pkl` lookup files (zero API cost, runs offline)
2. **EmbeddingLayer** — semantic similarity filtering using `all-MiniLM-L6-v2` to ensure substitutions preserve meaning
3. **HybridEngine** — orchestrates both layers + Gemini for re-ranking and rephrase suggestions
4. **GrammarGuard** — post-substitution checker with 5 layers:
   - Fact anchor detection (named entities, publications, numbers)
   - Tense consistency check
   - Subject-verb agreement check
   - LanguageTool grammar engine (optional)
   - Embedding semantic similarity

### Frontend

Single-page React app. Paste or type text → the system analyses it in one pass → risky tokens are highlighted → click any token to see synonym options or rephrase suggestions → run Grammar Check to validate the modified text.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Your Google Gemini API key |

The backend degrades gracefully without it (local-only mode) but quality is significantly reduced.

---

## Running Both Servers (Summary)

**Terminal 1 — Backend:**
```bash
cd speech-backend
export GEMINI_API_KEY=your_key_here      # or set on Windows
uvicorn main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd speech-app
npm run dev
```

Then open **http://localhost:5173**.

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'google.genai'`**
```bash
pip install google-genai
```

**`ModuleNotFoundError: No module named 'sentence_transformers'`**
```bash
pip install sentence-transformers
```
The first run downloads the `all-MiniLM-L6-v2` model (~90 MB). Subsequent runs use the cached version.

**CORS errors in the browser**
Make sure the backend is running on port 8000. The frontend's Vite dev server proxies `/api` calls to `http://localhost:8000` by default. If your backend is on a different port, update `vite.config.js`.

**`GEMINI_API_KEY not set` warning in backend logs**
The app still runs but Gemini re-ranking is disabled. Set the env var as shown above.

**Grammar Check button is greyed out**
Click "Analyse" first to run the transform pass, then Grammar Check activates.

---

## PKL Files

The `.pkl` files in `speech-backend/` are pre-computed lookup tables (phoneme index, synonym map, frequency ranks, POS map, cluster cache). They are committed to the repo because they are static data files, not trained models — no GPU or training pipeline required to use them.

---

## License

MIT
