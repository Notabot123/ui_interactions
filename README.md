# Interaction Intelligence POC

A proof-of-concept showing how telemetry from a complex engineering-style UI can be captured, analysed live, and summarised with an LLM.

## What it demonstrates

- React engineering workspace with a dense collapsible component tree
- Search with top-five approximate matches
- Component viewer with buttons, tabs, forms and placeholder 3D/model content
- DOM-level interaction capture: clicks, hovers, search input, textarea input, select changes
- Live heatmap pulses for user interaction points
- FastAPI ingestion endpoint
- Heuristic live next-action prediction layer
- Post-session UX summary using OpenAI when `OPENAI_API_KEY` is set
- Deterministic mock summary fallback when no API key is present

## Architecture

```text
frontend/ React + Vite UI
backend/  FastAPI API, in-memory session store, predictor, summariser
```

## Quick start with Docker

```bash
cd interaction-intelligence-poc
export OPENAI_API_KEY="your-key-here" # optional

docker compose up --build
```

Then open:

- Frontend: http://localhost:5173
- Backend health: http://localhost:8000/health

## Quick start without Docker

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # optional; add OPENAI_API_KEY if desired
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

## Demo script

1. Expand several tree categories.
2. Search for `pump`, `valve`, or `sensor`.
3. Click a result or tree item.
4. Hover over `Open Diagram`, `Inspect`, and `Maintenance History`.
5. Add text in the Notes field and change Priority.
6. Watch the live interaction feed and next-action prediction update.
7. Click `Generate UX Insights`.

## Notes on the ML strategy

The live predictor is deliberately heuristic for this MVP. It uses recent interactions, element IDs, hover intent, and simple transition rules. This makes the demo stable and explainable.

A later LSTM/Transformer model could consume the same event schema:

```json
{
  "timestamp": 171234567,
  "event_type": "click",
  "element_id": "btn-open-diagram",
  "component_id": "hydraulics-22",
  "x": 522,
  "y": 310,
  "metadata": {}
}
```

Once real sessions are collected, train a sequence model to predict the next element/action from event windows.
