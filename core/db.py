"""SQLite database schema and operations for team-monitor plugin."""

import os
import sqlite3
import json
from datetime import datetime, timezone

PLUGIN_ROOT = os.environ.get('CLAUDE_PLUGIN_ROOT') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_db_path():
    """Return absolute path to the SQLite database file."""
    return os.path.join(PLUGIN_ROOT, 'data', 'team_monitor.db')


def _get_connection():
    """Create a new database connection with WAL mode enabled."""
    db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables and indexes if they don't exist."""
    conn = _get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                session_id TEXT,
                team_name TEXT,
                agent_name TEXT,
                hook_event TEXT,
                tool_name TEXT,
                event_category TEXT,
                summary TEXT,
                payload_json TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp DESC);
            CREATE INDEX IF NOT EXISTS idx_events_session_id ON events(session_id);
            CREATE INDEX IF NOT EXISTS idx_events_agent_name ON events(agent_name);
            CREATE INDEX IF NOT EXISTS idx_events_event_category ON events(event_category);
            CREATE INDEX IF NOT EXISTS idx_events_tool_name ON events(tool_name);

            CREATE TABLE IF NOT EXISTS agents (
                agent_name TEXT UNIQUE NOT NULL,
                team_name TEXT,
                first_seen TEXT,
                last_seen TEXT,
                event_count INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT UNIQUE NOT NULL,
                team_name TEXT,
                started_at TEXT,
                ended_at TEXT,
                event_count INTEGER DEFAULT 0
            );
        """)
        conn.commit()
    finally:
        conn.close()


def insert_event(event_dict):
    """Insert an event row and upsert agent/session records. Returns event id."""
    conn = _get_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO events
               (timestamp, session_id, team_name, agent_name, hook_event,
                tool_name, event_category, summary, payload_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event_dict.get('timestamp'),
                event_dict.get('session_id'),
                event_dict.get('team_name'),
                event_dict.get('agent_name'),
                event_dict.get('hook_event'),
                event_dict.get('tool_name'),
                event_dict.get('event_category'),
                event_dict.get('summary'),
                event_dict.get('payload_json'),
            )
        )
        event_id = cursor.lastrowid
        ts = event_dict.get('timestamp')

        # Upsert agent record
        agent_name = event_dict.get('agent_name')
        if agent_name:
            conn.execute(
                """INSERT INTO agents (agent_name, team_name, first_seen, last_seen, event_count)
                   VALUES (?, ?, ?, ?, 1)
                   ON CONFLICT(agent_name) DO UPDATE SET
                     team_name = COALESCE(excluded.team_name, agents.team_name),
                     last_seen = excluded.last_seen,
                     event_count = agents.event_count + 1""",
                (agent_name, event_dict.get('team_name'), ts, ts)
            )

        # Upsert session record
        session_id = event_dict.get('session_id')
        if session_id:
            conn.execute(
                """INSERT INTO sessions (session_id, team_name, started_at, ended_at, event_count)
                   VALUES (?, ?, ?, ?, 1)
                   ON CONFLICT(session_id) DO UPDATE SET
                     team_name = COALESCE(excluded.team_name, sessions.team_name),
                     ended_at = excluded.ended_at,
                     event_count = sessions.event_count + 1""",
                (session_id, event_dict.get('team_name'), ts, ts)
            )

        conn.commit()
        return event_id
    finally:
        conn.close()


def get_events(page=1, per_page=50, category=None, agent=None, tool=None):
    """Paginated event query with optional filters. Returns list of dicts."""
    conn = _get_connection()
    try:
        conditions = []
        params = []
        if category:
            conditions.append("event_category = ?")
            params.append(category)
        if agent:
            conditions.append("agent_name = ?")
            params.append(agent)
        if tool:
            conditions.append("tool_name = ?")
            params.append(tool)

        where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
        offset = (page - 1) * per_page
        params.extend([per_page, offset])

        rows = conn.execute(
            f"SELECT id, timestamp, session_id, team_name, agent_name, hook_event, "
            f"tool_name, event_category, summary "
            f"FROM events{where} ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            params
        ).fetchall()

        # Get total count for pagination
        count_params = params[:-2]  # exclude limit/offset
        total = conn.execute(
            f"SELECT COUNT(*) FROM events{where}",
            count_params
        ).fetchone()[0]

        return {
            'events': [dict(row) for row in rows],
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page if per_page else 0,
        }
    finally:
        conn.close()


def get_event_by_id(event_id):
    """Return a single event with full payload, or None."""
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM events WHERE id = ?", (event_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_agents():
    """Return all agents with stats."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM agents ORDER BY last_seen DESC"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_stats():
    """Aggregate stats: total events, per-category counts, most active agent, recent activity."""
    conn = _get_connection()
    try:
        total = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]

        cat_rows = conn.execute(
            "SELECT event_category, COUNT(*) as cnt FROM events GROUP BY event_category"
        ).fetchall()
        by_category = {row['event_category']: row['cnt'] for row in cat_rows}

        most_active_row = conn.execute(
            "SELECT agent_name, event_count FROM agents ORDER BY event_count DESC LIMIT 1"
        ).fetchone()
        most_active = dict(most_active_row) if most_active_row else None

        now = datetime.now(timezone.utc).isoformat()
        # Events in last 60 seconds
        recent = conn.execute(
            "SELECT COUNT(*) FROM events WHERE timestamp >= datetime(?, '-60 seconds')",
            (now,)
        ).fetchone()[0]

        return {
            'total_events': total,
            'by_category': by_category,
            'most_active_agent': most_active,
            'events_last_minute': recent,
        }
    finally:
        conn.close()
