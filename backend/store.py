from collections import defaultdict
from typing import Dict, List
from models import InteractionEvent

_sessions: Dict[str, List[InteractionEvent]] = defaultdict(list)


def add_event(event: InteractionEvent) -> None:
    _sessions[event.session_id].append(event)


def get_events(session_id: str) -> List[InteractionEvent]:
    return list(_sessions.get(session_id, []))


def clear_session(session_id: str) -> None:
    _sessions.pop(session_id, None)


def list_sessions() -> List[str]:
    return sorted(_sessions.keys())
