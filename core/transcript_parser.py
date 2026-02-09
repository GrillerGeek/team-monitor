"""Parse subagent transcript JSONL files to extract tool call events."""

import json
import os

MAX_TOOL_RESULT_SIZE = 50 * 1024


def parse_transcript(transcript_path, agent_name=None, session_id=None, team_name=None):
    """Parse a JSONL transcript file and extract tool use events.

    Args:
        transcript_path: Path to the .jsonl transcript file
        agent_name: Name to attribute events to
        session_id: Session ID for the subagent
        team_name: Team name if known

    Returns:
        list of event dicts ready for insert_event()
    """
    if not transcript_path or not os.path.exists(transcript_path):
        return []

    events = []
    for line in _read_jsonl(transcript_path):
        extracted = _extract_tool_events(line, agent_name, session_id, team_name)
        events.extend(extracted)

    return events


def _read_jsonl(path):
    """Read a JSONL file, yielding parsed dicts. Skip malformed lines."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
    except (OSError, IOError):
        return


def _extract_tool_events(entry, agent_name, session_id, team_name):
    """Extract tool use events from a single transcript entry.

    Transcript entries can be in various formats depending on the Claude Code version.
    We look for tool_use blocks in assistant messages and their corresponding tool_result blocks.
    """
    events = []

    # Handle assistant messages with tool_use content blocks
    if entry.get('role') == 'assistant':
        content = entry.get('content', [])
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get('type') == 'tool_use':
                    event = _tool_use_to_event(block, agent_name, session_id, team_name)
                    if event:
                        events.append(event)

    # Handle tool_result messages (contains the result of a tool call)
    # We skip these since we capture enough from tool_use blocks
    # and including results would double the events

    return events


def _tool_use_to_event(block, agent_name, session_id, team_name):
    """Convert a tool_use content block into an event dict."""
    from core.event_parser import _classify, _extract_team_name

    tool_name = block.get('name', '')
    tool_input = block.get('input', {}) or {}

    if not tool_name:
        return None

    # Classify using the same logic as live events
    event_category, summary = _classify(tool_name, 'PostToolUse', tool_input, '')

    # Try to extract better agent/team info from the tool_input
    if not agent_name:
        agent_name = tool_input.get('name', '') or 'unknown'
    if not team_name or team_name == 'unknown':
        team_name = _extract_team_name({'tool_input': tool_input}, tool_input)

    # Build truncated payload
    payload = {
        'tool_name': tool_name,
        'tool_input': tool_input,
        'hook_event_name': 'PostToolUse',
        '_source': 'transcript',
    }

    return {
        'session_id': session_id or '',
        'team_name': team_name or 'unknown',
        'agent_name': agent_name or 'unknown',
        'hook_event': 'PostToolUse',
        'tool_name': tool_name,
        'event_category': event_category,
        'summary': summary,
        'payload_json': json.dumps(payload, default=str)[:MAX_TOOL_RESULT_SIZE],
    }
