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
    with get_connection() as conn:
        cursor = conn.cursor()

        total_events = cursor.execute(
            "SELECT COUNT(*) FROM events"
        ).fetchone()[0]

        total_sessions = cursor.execute(
            "SELECT COUNT(DISTINCT session_id) FROM events"
        ).fetchone()[0]

        total_clicks = cursor.execute(
            "SELECT COUNT(*) FROM events WHERE event_type = 'click'"
        ).fetchone()[0]

        total_searches = cursor.execute(
            "SELECT COUNT(*) FROM events WHERE event_type = 'search'"
        ).fetchone()[0]

        total_predictions = cursor.execute(
            "SELECT COUNT(*) FROM predictions"
        ).fetchone()[0]

        top_elements = cursor.execute("""
            SELECT element_id, COUNT(*) as count
            FROM events
            WHERE element_id IS NOT NULL
            GROUP BY element_id
            ORDER BY count DESC
            LIMIT 5
        """).fetchall()

        event_types = cursor.execute("""
            SELECT event_type, COUNT(*) as count
            FROM events
            GROUP BY event_type
            ORDER BY count DESC
        """).fetchall()

        return {
            "total_events": total_events,
            "total_sessions": total_sessions,
            "total_clicks": total_clicks,
            "total_searches": total_searches,
            "total_predictions": total_predictions,
            "top_elements": [
                {"element_id": row[0], "count": row[1]}
                for row in top_elements
            ],
            "event_types": [
                {"event_type": row[0], "count": row[1]}
                for row in event_types
            ],
        }