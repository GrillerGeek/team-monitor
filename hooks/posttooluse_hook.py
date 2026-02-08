"""PostToolUse hook for team-monitor plugin.

Reads hook JSON from stdin, classifies the event, stores it in the DB,
and notifies the SSE bridge for live dashboard updates.
Always prints {} to stdout and exits 0.
"""

import sys
import os
import json
import traceback

try:
    # Resolve plugin root
    PLUGIN_ROOT = os.environ.get('CLAUDE_PLUGIN_ROOT') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.environ['CLAUDE_PLUGIN_ROOT'] = PLUGIN_ROOT
    sys.path.insert(0, PLUGIN_ROOT)

    from core.event_parser import parse_event
    from core.db import init_db, insert_event
    from core.sse_bridge import notify_sse

    # Read hook data from stdin
    raw = sys.stdin.read()
    hook_data = json.loads(raw) if raw.strip() else {}

    # Classify the event
    event_dict = parse_event(hook_data)

    # Store in database
    init_db()
    event_id = insert_event(event_dict)
    event_dict['id'] = event_id

    # Notify SSE bridge
    notify_sse(event_dict)

except Exception:
    # Log errors to file for debugging — never block Claude
    try:
        log_path = os.path.join(
            os.environ.get('CLAUDE_PLUGIN_ROOT') or os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'data', 'hook_errors.log'
        )
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"=== posttooluse_hook ===\n")
            f.write(f"PLUGIN_ROOT={os.environ.get('CLAUDE_PLUGIN_ROOT', 'NOT SET')}\n")
            f.write(f"__file__={os.path.abspath(__file__)}\n")
            traceback.print_exc(file=f)
            f.write("\n")
    except Exception:
        pass

# Always output valid JSON and exit cleanly
print("{}")
sys.exit(0)
