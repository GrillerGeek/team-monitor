"""SubagentStart hook for team-monitor plugin.

Logs when a subagent is spawned so the dashboard shows agents
appearing in real time rather than only when they finish.

Always prints {} to stdout and exits 0.
"""

import sys
import os
import json
import traceback

try:
    PLUGIN_ROOT = os.environ.get('CLAUDE_PLUGIN_ROOT') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.environ['CLAUDE_PLUGIN_ROOT'] = PLUGIN_ROOT
    sys.path.insert(0, PLUGIN_ROOT)

    from core.event_parser import parse_event
    from core.db import init_db, insert_event
    from core.sse_bridge import notify_sse

    raw = sys.stdin.read()
    hook_data = json.loads(raw) if raw.strip() else {}

    # Ensure this is classified as a lifecycle start event
    if not hook_data.get('hook_event_name'):
        hook_data['hook_event_name'] = 'SubagentStart'

    event_dict = parse_event(hook_data)

    init_db()
    event_id = insert_event(event_dict)
    event_dict['id'] = event_id

    notify_sse(event_dict)

except Exception:
    try:
        log_path = os.path.join(
            os.environ.get('CLAUDE_PLUGIN_ROOT') or os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'data', 'hook_errors.log'
        )
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"=== subagentstart_hook ===\n")
            f.write(f"PLUGIN_ROOT={os.environ.get('CLAUDE_PLUGIN_ROOT', 'NOT SET')}\n")
            f.write(f"__file__={os.path.abspath(__file__)}\n")
            traceback.print_exc(file=f)
            f.write("\n")
    except Exception:
        pass

print("{}")
sys.exit(0)
