from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import InteractionEvent, Prediction, SessionSummary, SummaryRequest
from predictor import predict_next
from store import add_event, clear_session, get_events, list_sessions
from summariser import summarise_with_openai

app = FastAPI(title="Interaction Intelligence POC")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/events", response_model=Prediction)
def ingest_event(event: InteractionEvent):
    add_event(event)
    return predict_next(get_events(event.session_id))


@app.get("/sessions/{session_id}/events")
def session_events(session_id: str):
    return get_events(session_id)


@app.get("/sessions")
def sessions():
    return {"sessions": list_sessions()}


@app.delete("/sessions/{session_id}")
def reset_session(session_id: str):
    clear_session(session_id)
    return {"status": "cleared"}


@app.post("/summarise", response_model=SessionSummary)
def summarise(req: SummaryRequest):
    events = get_events(req.session_id)
    if not events:
        raise HTTPException(status_code=404, detail="No events found for session")
    summary, model = summarise_with_openai(events)
    return SessionSummary(summary=summary, model=model, event_count=len(events))
