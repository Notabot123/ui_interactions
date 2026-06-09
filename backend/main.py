from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from models import InteractionEvent, Prediction, SessionSummary, SummaryRequest
from predictor import predict_next
from store import (
    add_event,
    add_prediction,
    add_summary,
    analytics_summary,
    clear_session,
    events_as_csv,
    get_events,
    init_db,
    list_sessions,
    get_dashboard_metrics,
)
from summariser import summarise_with_openai

app = FastAPI(title="Interaction Intelligence POC")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    init_db()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/events", response_model=Prediction)
def ingest_event(event: InteractionEvent):
    add_event(event)
    prediction = predict_next(get_events(event.session_id))
    add_prediction(event.session_id, event.timestamp, prediction)
    return prediction

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
    add_summary(req.session_id, summary, model, len(events))
    return SessionSummary(summary=summary, model=model, event_count=len(events))


@app.post("/summarise", response_model=SessionSummary)
def summarise(req: SummaryRequest):
    events = get_events(req.session_id)
    if not events:
        raise HTTPException(status_code=404, detail="No events found for session")
    summary, model = summarise_with_openai(events)
    return SessionSummary(summary=summary, model=model, event_count=len(events))

@app.get("/analytics/summary")
def analytics():
    return analytics_summary()


@app.get("/analytics/events.csv")
def export_events_csv(session_id: str | None = None):
    csv_text = events_as_csv(session_id=session_id)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=interaction-events.csv"},
    )

@app.get("/analytics/dashboard")
def analytics_dashboard():
    return get_dashboard_metrics()