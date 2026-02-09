"""Event classification and parsing for team-monitor plugin."""

import json
from datetime import datetime, timezone

# Maximum size for tool_result in stored payload (50 KB)
MAX_TOOL_RESULT_SIZE = 50 * 1024


def parse_event(hook_data):
    """Parse raw hook stdin JSON into a classified event dict.

    Args:
        hook_data: dict from hook stdin JSON

    Returns:
        dict with keys: timestamp, session_id, team_name, agent_name,
        hook_event, tool_name, event_category, summary, payload_json
    """
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    session_id = hook_data.get('session_id', '')
    hook_event = hook_data.get('hook_event_name', '')
    tool_name = hook_data.get('tool_name', '') or ''
    tool_input = hook_data.get('tool_input', {}) or {}
    tool_result = hook_data.get('tool_result', '')

    # Extract agent_name from various sources
    agent_name = _extract_agent_name(hook_data, tool_input, session_id)

    # Extract team_name
    team_name = _extract_team_name(hook_data, tool_input)

    # Classify the event
    event_category, summary = _classify(tool_name, hook_event, tool_input, tool_result)

    # Truncate tool_result in payload to keep storage reasonable
    payload = dict(hook_data)
    if 'tool_result' in payload:
        result_str = str(payload['tool_result'])
        if len(result_str) > MAX_TOOL_RESULT_SIZE:
            payload['tool_result'] = result_str[:MAX_TOOL_RESULT_SIZE] + '...[truncated]'

    return {
        'timestamp': timestamp,
        'session_id': session_id,
        'team_name': team_name,
        'agent_name': agent_name,
        'hook_event': hook_event,
        'tool_name': tool_name,
        'event_category': event_category,
        'summary': summary,
        'payload_json': json.dumps(payload, default=str),
    }


def _extract_agent_name(hook_data, tool_input, session_id):
    """Extract agent name from available context."""
    # Try tool_input.name (used in Task-related tools)
    name = tool_input.get('name', '')
    if name:
        return name

    # Try agent_name from top-level hook data
    name = hook_data.get('agent_name', '')
    if name:
        return name

    # Try recipient from SendMessage
    # (for messages, the sender is more useful - but we may not have it)
    # Fallback to session_id prefix if it contains agent info
    if session_id:
        return session_id.split('-')[0] if '-' in session_id else session_id

    return 'unknown'


def _extract_team_name(hook_data, tool_input):
    """Extract team name from available context."""
    # TeamCreate has it directly
    team = tool_input.get('team_name', '')
    if team:
        return team

    # Top-level hook data
    team = hook_data.get('team_name', '')
    if team:
        return team

    return 'unknown'


def _classify(tool_name, hook_event, tool_input, tool_result):
    """Classify event into category and generate summary.

    Returns:
        (event_category, summary)
    """
    # Lifecycle events (by hook_event_name)
    if hook_event == 'Stop':
        return 'lifecycle', 'Agent stopped'
    if hook_event == 'SubagentStart':
        agent = tool_input.get('name', '') or tool_input.get('description', '')[:40] if tool_input.get('description') else ''
        return 'lifecycle', f'Subagent started: {agent}' if agent else 'Subagent started'
    if hook_event == 'SubagentStop':
        return 'lifecycle', 'Subagent stopped'
    if hook_event == 'Notification':
        msg = str(tool_input.get('message', '') or tool_result or '')[:60]
        return 'lifecycle', f'Notification: {msg}'

    # SendMessage variants
    if tool_name == 'SendMessage':
        return _classify_send_message(tool_input)

    # Task management tools
    if tool_name == 'TaskCreate':
        subject = tool_input.get('subject', '')
        return 'task_management', f'Created task: {subject}'

    if tool_name == 'TaskUpdate':
        return _classify_task_update(tool_input)

    if tool_name == 'TeamCreate':
        team = tool_input.get('team_name', '')
        return 'task_management', f'Created team: {team}'

    if tool_name == 'TaskList':
        return 'task_management', 'Listed tasks'

    if tool_name == 'TaskGet':
        task_id = tool_input.get('taskId', '')
        return 'task_management', f'Got task #{task_id}'

    # Tool use
    if tool_name == 'Bash':
        cmd = str(tool_input.get('command', ''))[:60]
        return 'tool_use', f'Bash: {cmd}'

    if tool_name == 'Edit':
        path = tool_input.get('file_path', '')
        return 'tool_use', f'Edit: {path}'

    if tool_name == 'Write':
        path = tool_input.get('file_path', '')
        return 'tool_use', f'Write: {path}'

    if tool_name == 'Read':
        path = tool_input.get('file_path', '')
        return 'tool_use', f'Read: {path}'

    if tool_name == 'Glob':
        pattern = tool_input.get('pattern', '')
        return 'tool_use', f'Glob: {pattern}'

    if tool_name == 'Grep':
        pattern = tool_input.get('pattern', '')
        return 'tool_use', f'Grep: {pattern}'

    if tool_name == 'WebFetch':
        url = str(tool_input.get('url', ''))[:60]
        return 'tool_use', f'WebFetch: {url}'

    if tool_name == 'WebSearch':
        query = tool_input.get('query', '')
        return 'tool_use', f'WebSearch: {query}'

    # Default: any other tool
    if tool_name:
        return 'tool_use', tool_name

    return 'lifecycle', hook_event or 'unknown event'


def _classify_send_message(tool_input):
    """Classify SendMessage events by message type."""
    msg_type = tool_input.get('type', 'message')
    summary_text = tool_input.get('summary', '') or tool_input.get('content', '')[:60] if tool_input.get('content') else ''

    if msg_type == 'broadcast':
        return 'communication', f'Broadcast: {summary_text}'

    if msg_type == 'shutdown_request':
        recipient = tool_input.get('recipient', '')
        return 'communication', f'Shutdown request to {recipient}'

    if msg_type == 'shutdown_response':
        approved = 'approved' if tool_input.get('approve') else 'rejected'
        return 'communication', f'Shutdown response: {approved}'

    # Default: type=message (DM)
    recipient = tool_input.get('recipient', '')
    return 'communication', f'DM to {recipient}: {summary_text}'


def _classify_task_update(tool_input):
    """Classify TaskUpdate events by what changed."""
    task_id = tool_input.get('taskId', '')

    # Check for owner change
    owner = tool_input.get('owner', '')
    if owner:
        return 'task_management', f'Assigned task #{task_id} to {owner}'

    # Check for status change
    status = tool_input.get('status', '')
    if status:
        return 'task_management', f'Updated task #{task_id}: {status}'

    return 'task_management', f'Updated task #{task_id}'
