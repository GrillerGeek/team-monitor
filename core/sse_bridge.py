"""SSE notification file bridge for team-monitor plugin.

Hooks write small JSON files to data/sse_events/.
The Flask server reads and deletes them to stream as SSE to browsers.
"""

import os
import json
import glob

PLUGIN_ROOT = os.environ.get('CLAUDE_PLUGIN_ROOT') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SSE_DIR = os.path.join(PLUGIN_ROOT, 'data', 'sse_events')


def ensure_sse_dir():
    """Create the data/sse_events/ directory if it doesn't exist."""
    os.makedirs(SSE_DIR, exist_ok=True)


def notify_sse(event_dict):
    """Write a small JSON notification file for the SSE bridge.

    Args:
        event_dict: dict with at least id, event_category, summary,
                    agent_name, timestamp, tool_name
    """
    ensure_sse_dir()

    # Build filename from timestamp ms and event id for natural sort order
    ts = event_dict.get('timestamp', '')
    event_id = event_dict.get('id', 0)
    # Convert ISO timestamp to ms for filename uniqueness
    ts_safe = ts.replace(':', '').replace('-', '').replace('.', '').replace('Z', '')
    filename = f"{ts_safe}_{event_id}.json"
    filepath = os.path.join(SSE_DIR, filename)

    notification = {
        'id': event_id,
        'category': event_dict.get('event_category', ''),
        'summary': event_dict.get('summary', ''),
        'agent_name': event_dict.get('agent_name', ''),
        'timestamp': ts,
        'tool_name': event_dict.get('tool_name', ''),
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(notification, f)


def get_pending_events():
    """Read all pending SSE event files, return sorted list, delete consumed files.

    Returns:
        list of dicts sorted by filename (chronological order)
    """
    ensure_sse_dir()
    pattern = os.path.join(SSE_DIR, '*.json')
    files = sorted(glob.glob(pattern))
    events = []

    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            events.append(data)
            os.remove(filepath)
        except (json.JSONDecodeError, OSError):
            # If file is corrupt or locked, try to remove and skip
            try:
                os.remove(filepath)
            except OSError:
                pass

    return events
