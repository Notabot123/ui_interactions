import csv
import io
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Dict, List, Optional

from models import InteractionEvent, Prediction

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("INTERACTION_DB_PATH", BASE_DIR / "interaction_events.db"))


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(_connect()) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp REAL NOT NULL,
                event_type TEXT NOT NULL,
                element_id TEXT NOT NULL,
                element_label TEXT,
                page TEXT,
                component_id TEXT,
                x REAL,
                y REAL,
                value TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_interactions_session ON interactions(session_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_interactions_timestamp ON interactions(timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_interactions_event_type ON interactions(event_type)")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp REAL NOT NULL,
                action TEXT NOT NULL,
                confidence REAL NOT NULL,
                reason TEXT,
                actual_action TEXT,
                actual_event_type TEXT,
                actual_element_id TEXT,
                is_correct INTEGER,
                matched_within_window INTEGER,
                matched_after_events INTEGER,
                matched_actual_action TEXT
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_predictions_session ON predictions(session_id)")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                summary TEXT NOT NULL,
                model TEXT NOT NULL,
                event_count INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_summaries_session ON summaries(session_id)")
        conn.commit()


def _row_to_event(row: sqlite3.Row) -> InteractionEvent:
    return InteractionEvent(
        session_id=row["session_id"],
        timestamp=row["timestamp"],
        event_type=row["event_type"],
        element_id=row["element_id"],
        element_label=row["element_label"],
        page=row["page"],
        component_id=row["component_id"],
        x=row["x"],
        y=row["y"],
        value=row["value"],
        metadata=json.loads(row["metadata_json"] or "{}"),
    )


def add_event(event: InteractionEvent) -> None:
    init_db()
    #update_previous_prediction_with_actual(event) # newly added, for predictions
    update_recent_predictions_with_actual(event)
    
    with closing(_connect()) as conn:
        conn.execute(
            """
            INSERT INTO interactions (
                session_id, timestamp, event_type, element_id, element_label,
                page, component_id, x, y, value, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.session_id,
                event.timestamp,
                event.event_type,
                event.element_id,
                event.element_label,
                event.page,
                event.component_id,
                event.x,
                event.y,
                event.value,
                json.dumps(event.metadata or {}),
            ),
        )
        conn.commit()


def add_prediction(session_id: str, timestamp: float, prediction: Prediction) -> None:
    init_db()
    with closing(_connect()) as conn:
        conn.execute(
            """
            INSERT INTO predictions (session_id, timestamp, action, confidence, reason)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, timestamp, prediction.action, prediction.confidence, prediction.reason),
        )
        conn.commit()


def add_summary(session_id: str, summary: str, model: str, event_count: int) -> None:
    init_db()
    with closing(_connect()) as conn:
        conn.execute(
            """
            INSERT INTO summaries (session_id, summary, model, event_count)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, summary, model, event_count),
        )
        conn.commit()


def get_events(session_id: str) -> List[InteractionEvent]:
    init_db()
    with closing(_connect()) as conn:
        rows = conn.execute(
            """
            SELECT * FROM interactions
            WHERE session_id = ?
            ORDER BY timestamp ASC, id ASC
            """,
            (session_id,),
        ).fetchall()
    return [_row_to_event(row) for row in rows]


def clear_session(session_id: str) -> None:
    init_db()
    with closing(_connect()) as conn:
        conn.execute("DELETE FROM interactions WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM predictions WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM summaries WHERE session_id = ?", (session_id,))
        conn.commit()


def list_sessions() -> List[str]:
    init_db()
    with closing(_connect()) as conn:
        rows = conn.execute(
            """
            SELECT session_id, MIN(timestamp) AS first_event, MAX(timestamp) AS last_event, COUNT(*) AS event_count
            FROM interactions
            GROUP BY session_id
            ORDER BY last_event DESC
            """
        ).fetchall()
    return [row["session_id"] for row in rows]


def analytics_summary() -> Dict[str, object]:
    init_db()
    with closing(_connect()) as conn:
        total_events = conn.execute("SELECT COUNT(*) AS c FROM interactions").fetchone()["c"]
        total_sessions = conn.execute("SELECT COUNT(DISTINCT session_id) AS c FROM interactions").fetchone()["c"]
        event_types = conn.execute(
            "SELECT event_type, COUNT(*) AS count FROM interactions GROUP BY event_type ORDER BY count DESC"
        ).fetchall()
        top_elements = conn.execute(
            """
            SELECT COALESCE(element_label, element_id) AS element, COUNT(*) AS count
            FROM interactions
            GROUP BY COALESCE(element_label, element_id)
            ORDER BY count DESC
            LIMIT 10
            """
        ).fetchall()
        top_components = conn.execute(
            """
            SELECT component_id, COUNT(*) AS count
            FROM interactions
            WHERE component_id IS NOT NULL AND component_id != ''
            GROUP BY component_id
            ORDER BY count DESC
            LIMIT 10
            """
        ).fetchall()
        prediction_rows = conn.execute(
            """
            SELECT action, COUNT(*) AS count, AVG(confidence) AS avg_confidence
            FROM predictions
            GROUP BY action
            ORDER BY count DESC
            LIMIT 10
            """
        ).fetchall()
    return {
        "database": str(DB_PATH),
        "total_events": total_events,
        "total_sessions": total_sessions,
        "event_types": [dict(row) for row in event_types],
        "top_elements": [dict(row) for row in top_elements],
        "top_components": [dict(row) for row in top_components],
        "top_predictions": [dict(row) for row in prediction_rows],
    }


def events_as_csv(session_id: Optional[str] = None) -> str:
    init_db()
    query = "SELECT * FROM interactions"
    params: tuple = ()
    if session_id:
        query += " WHERE session_id = ?"
        params = (session_id,)
    query += " ORDER BY timestamp ASC, id ASC"

    with closing(_connect()) as conn:
        rows = conn.execute(query, params).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    headers = [
        "id", "session_id", "timestamp", "event_type", "element_id", "element_label",
        "page", "component_id", "x", "y", "value", "metadata_json", "created_at"
    ]
    writer.writerow(headers)
    for row in rows:
        writer.writerow([row[h] for h in headers])
    return output.getvalue()

def get_dashboard_metrics():

    with closing(_connect()) as conn:
        total_events = conn.execute(
            "SELECT COUNT(*) AS c FROM interactions"
        ).fetchone()["c"]

        total_sessions = conn.execute(
            "SELECT COUNT(DISTINCT session_id) AS c FROM interactions"
        ).fetchone()["c"]

        total_clicks = conn.execute(
            "SELECT COUNT(*) AS c FROM interactions WHERE event_type = 'click'"
        ).fetchone()["c"]

        total_searches = conn.execute(
            "SELECT COUNT(*) AS c FROM interactions WHERE event_type = 'search'"
        ).fetchone()["c"]

        total_predictions = conn.execute(
            "SELECT COUNT(*) AS c FROM predictions"
        ).fetchone()["c"]

        top_elements = conn.execute("""
            SELECT COALESCE(element_label, element_id) AS element, COUNT(*) AS count
            FROM interactions
            WHERE element_id IS NOT NULL
            GROUP BY COALESCE(element_label, element_id)
            ORDER BY count DESC
            LIMIT 5
        """).fetchall()

        event_types = conn.execute("""
            SELECT event_type, COUNT(*) AS count
            FROM interactions
            GROUP BY event_type
            ORDER BY count DESC
        """).fetchall()

    return {
        "total_events": total_events,
        "total_sessions": total_sessions,
        "total_clicks": total_clicks,
        "total_searches": total_searches,
        "total_predictions": total_predictions,
        "top_elements": [dict(row) for row in top_elements],
        "event_types": [dict(row) for row in event_types],
    }

# for checking prediction accuracy
def update_previous_prediction_with_actual(event: InteractionEvent) -> None:
    actual_action = normalise_actual_action(event)

    with closing(_connect()) as conn:
        previous = conn.execute(
            """
            SELECT id, action
            FROM predictions
            WHERE session_id = ?
              AND actual_action IS NULL
              AND timestamp < ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (event.session_id, event.timestamp),
        ).fetchone()

        if not previous:
            return

        #is_correct = 1 if previous["action"] == actual_action else 0
        is_correct = 1 if prediction_matches_actual(previous["action"], actual_action) else 0

        conn.execute(
            """
            UPDATE predictions
            SET actual_action = ?,
                actual_event_type = ?,
                actual_element_id = ?,
                is_correct = ?
            WHERE id = ?
            """,
            (
                actual_action,
                event.event_type,
                event.element_id,
                is_correct,
                previous["id"],
            ),
        )

        conn.commit()


# normalising to assist pred vs actual
# in future, make frontend send both element name and simplified action description
def normalise_actual_action(event: InteractionEvent) -> str:
    element_id = (event.element_id or "").lower()
    element_label = (event.element_label or "").lower()
    event_type = (event.event_type or "").lower()
    text = f"{element_id} {element_label}"

    if "search-result" in text or "search result" in text:
        return "Open top search result"

    if "tree-search" in text or "component search" in text:
        return "Search for a component"

    if "btn-open-diagram" in text or "open diagram" in text:
        return "Open Diagram"

    if "btn-maintenance" in text or "maintenance" in text:
        return "Open Maintenance History"

    if "btn-inspect" in text or "inspect" in text:
        return "Inspect Component"

    if "tab-specs" in text or "specifications" in text:
        return "View Specifications"

    if "tab-docs" in text or "documentation" in text:
        return "View Documentation"

    if "input-notes" in text or "notes" in text:
        return "Add Notes"

    if "select-priority" in text or "priority" in text:
        return "Set Priority"

    if "tree-item" in element_id:
        return "Use tree navigation"

    if event_type == "input" and "search" in text:
        return "Search for a component"

    return event.element_label or event.element_id or event_type.title()

def prediction_matches_actual(predicted: str, actual: str) -> bool:
    predicted_l = (predicted or "").lower()
    actual_l = (actual or "").lower()

    if predicted_l == actual_l:
        return True

    acceptable_matches = {
        "use search result instead of expanding tree": {
            "open top search result",
            "search for a component",
        },
        "open top search result": {
            "open top search result",
        },
        "use tree navigation": {
            "use tree navigation",
            "select component",
        },
    }

    return actual_l in acceptable_matches.get(predicted_l, set())

LOOKAHEAD_WINDOW = 5


def update_recent_predictions_with_actual(event: InteractionEvent) -> None:
    actual_action = normalise_actual_action(event)

    with closing(_connect()) as conn:
        recent_predictions = conn.execute(
            """
            SELECT id, action, timestamp
            FROM predictions
            WHERE session_id = ?
              AND matched_within_window IS NULL
              AND timestamp < ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (event.session_id, event.timestamp, LOOKAHEAD_WINDOW),
        ).fetchall()

        for offset, prediction in enumerate(recent_predictions, start=1):
            matched = prediction_matches_actual(
                prediction["action"],
                actual_action,
            )

            if matched:
                conn.execute(
                    """
                    UPDATE predictions
                    SET actual_action = ?,
                        actual_event_type = ?,
                        actual_element_id = ?,
                        is_correct = CASE
                            WHEN ? = 1 THEN 1
                            ELSE is_correct
                        END,
                        matched_within_window = 1,
                        matched_after_events = ?,
                        matched_actual_action = ?
                    WHERE id = ?
                    """,
                    (
                        actual_action,
                        event.event_type,
                        event.element_id,
                        offset,
                        offset,
                        actual_action,
                        prediction["id"],
                    ),
                )
            elif offset == LOOKAHEAD_WINDOW:
                conn.execute(
                    """
                    UPDATE predictions
                    SET matched_within_window = 0
                    WHERE id = ?
                    """,
                    (prediction["id"],),
                )

        conn.commit()