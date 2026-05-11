from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class InteractionEvent(BaseModel):
    session_id: str = Field(..., min_length=1)
    timestamp: float
    event_type: str
    element_id: str
    element_label: Optional[str] = None
    page: Optional[str] = None
    component_id: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None
    value: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Prediction(BaseModel):
    action: str
    confidence: float
    reason: str


class SummaryRequest(BaseModel):
    session_id: str


class SessionSummary(BaseModel):
    summary: str
    model: str
    event_count: int
