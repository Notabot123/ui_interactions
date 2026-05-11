from collections import Counter
from typing import List
from models import InteractionEvent, Prediction


TARGET_LABELS = {
    "btn-open-diagram": "Open Diagram",
    "btn-maintenance": "Open Maintenance History",
    "btn-inspect": "Inspect Component",
    "tab-specs": "View Specifications",
    "tab-docs": "View Documentation",
    "input-notes": "Add Notes",
    "select-priority": "Set Priority",
    "tree-search": "Search for a component",
}

TRANSITIONS = {
    "search": ["Open top search result", "Use tree navigation"],
    "tree-item": ["Open Diagram", "Inspect Component", "View Specifications"],
    "btn-inspect": ["Open Maintenance History", "Add Notes"],
    "btn-open-diagram": ["View Documentation", "Open Maintenance History"],
    "tab-specs": ["Open Diagram", "Set Priority"],
    "input-notes": ["Set Priority", "Open Maintenance History"],
}


def _base_id(element_id: str) -> str:
    for key in TRANSITIONS:
        if key in element_id:
            return key
    if element_id in TARGET_LABELS:
        return element_id
    return element_id


def predict_next(events: List[InteractionEvent]) -> Prediction:
    if not events:
        return Prediction(action="Start by searching or expanding the component tree", confidence=0.55, reason="No session activity yet.")

    recent = events[-12:]
    last = recent[-1]
    counts = Counter(e.element_id for e in recent)
    hover_events = [e for e in recent if e.event_type == "hover"]
    click_events = [e for e in recent if e.event_type == "click"]

    if last.event_type in {"input", "change"} and "tree-search" in last.element_id:
        return Prediction(action="Open top search result", confidence=0.82, reason="The user is actively searching for a component.")

    if hover_events and hover_events[-1].element_id in TARGET_LABELS:
        hovered = TARGET_LABELS[hover_events[-1].element_id]
        return Prediction(action=hovered, confidence=0.74, reason="Recent hover over a high-intent control.")

    if click_events:
        base = _base_id(click_events[-1].element_id)
        suggestions = TRANSITIONS.get(base)
        if suggestions:
            return Prediction(action=suggestions[0], confidence=0.68, reason=f"Common next step after interacting with {base}.")

    if counts["tree-search"] >= 2:
        return Prediction(action="Use search result instead of expanding tree", confidence=0.62, reason="Repeated search interactions suggest navigation intent.")

    if last.component_id:
        return Prediction(action="Open Diagram", confidence=0.6, reason="A component is selected; diagrams are a frequent next action.")

    return Prediction(action="Inspect Component", confidence=0.52, reason="Default action based on current session context.")
