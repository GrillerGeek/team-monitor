"""Stop/SubagentStop hook for team-monitor plugin.

Handles agent lifecycle stop events.
For SubagentStop, also parses the agent's transcript to backfill
all tool calls made by that subagent (since PostToolUse hooks
only fire in the parent session, not in subagent sessions).

Always prints {} to stdout and exits 0.
"""

import sys
import os
import json
import traceback
from datetime import datetime, timezone

try:
    PLUGIN_ROOT = os.environ.get('CLAUDE_PLUGIN_ROOT') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.environ['CLAUDE_PLUGIN_ROOT'] = PLUGIN_ROOT
    sys.path.insert(0, PLUGIN_ROOT)

    from core.event_parser import parse_event
    from core.db import init_db, insert_event
    from core.sse_bridge import notify_sse
    from core.transcript_parser import parse_transcript

    raw = sys.stdin.read()
    hook_data = json.loads(raw) if raw.strip() else {}

    init_db()

    # Log the stop event itself
    event_dict = parse_event(hook_data)
    event_id = insert_event(event_dict)
    event_dict['id'] = event_id
    notify_sse(event_dict)

    # For SubagentStop: parse the transcript to backfill tool calls
    hook_event = hook_data.get('hook_event_name', '')
    if hook_event == 'SubagentStop':
        transcript_path = hook_data.get('agent_transcript_path', '')
        # Also check tool_input and tool_result for transcript path
        if not transcript_path:
            transcript_path = hook_data.get('tool_input', {}).get('agent_transcript_path', '')
        if not transcript_path:
            transcript_path = hook_data.get('transcript_path', '')

        # Extract agent info for attribution
        agent_name = hook_data.get('agent_name', '') or hook_data.get('tool_input', {}).get('name', '')
        session_id = hook_data.get('session_id', '')
        team_name = hook_data.get('team_name', '') or hook_data.get('tool_input', {}).get('team_name', '')

        # Also try to find the agent name from the stop event's tool_input
        tool_input = hook_data.get('tool_input', {}) or {}
        if not agent_name:
            agent_name = tool_input.get('name', '') or tool_input.get('description', '').split()[0] if tool_input.get('description') else ''

        if transcript_path and os.path.exists(transcript_path):
            transcript_events = parse_transcript(
                transcript_path,
                agent_name=agent_name or 'unknown',
                session_id=session_id,
                team_name=team_name,
            )

            now = datetime.now(timezone.utc)
            for i, tevt in enumerate(transcript_events):
                # Spread timestamps slightly so they sort correctly
                ts = now.strftime('%Y-%m-%dT%H:%M:%S.') + f'{i:03d}Z'
                tevt['timestamp'] = ts
                eid = insert_event(tevt)
                tevt['id'] = eid
                notify_sse(tevt)

except Exception:
    try:
        log_path = os.path.join(
            os.environ.get('CLAUDE_PLUGIN_ROOT') or os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'data', 'hook_errors.log'
        )
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"=== stop_hook ===\n")
            f.write(f"PLUGIN_ROOT={os.environ.get('CLAUDE_PLUGIN_ROOT', 'NOT SET')}\n")
            f.write(f"__file__={os.path.abspath(__file__)}\n")
            traceback.print_exc(file=f)
            f.write("\n")
    except Exception:
        pass

print("{}")
sys.exit(0)
