# Team Monitor

Real-time dashboard for monitoring Claude Code agent team activity. When multiple agents collaborate — sending messages, creating tasks, editing files — this plugin captures everything and streams it to a live dashboard at `localhost:5111`.

![Dark themed dashboard with agent cards, live event feed, and stats sidebar](https://img.shields.io/badge/dashboard-localhost%3A5111-blue)

## What It Does

- **Hooks into every tool call** via Claude Code's PostToolUse event
- **Classifies events** into categories: communication, task management, tool use, lifecycle
- **Stores everything** in a local SQLite database (WAL mode for concurrent access)
- **Streams live updates** to a dark-themed browser dashboard via SSE
- **Captures subagent activity** by parsing transcripts when agents finish

## Install

### From GitHub

```
/plugin marketplace add GrillerGeek/team-monitor
/plugin install team-monitor@GrillerGeek/team-monitor
```

### Register Hooks

The plugin requires hooks to be registered in your Claude Code settings. The first time you start the dashboard, this happens automatically. Or run it manually:

**macOS / Linux:**
```bash
python3 ~/.claude/plugins/cache/team-monitor-marketplace/team-monitor/1.0.0/scripts/install_hooks.py
```

**Windows:**
```bash
python %USERPROFILE%\.claude\plugins\cache\team-monitor-marketplace\team-monitor\1.0.0\scripts\install_hooks.py
```

**Restart Claude Code after installing hooks.**

### For Development

```bash
claude --plugin-dir /path/to/team-monitor
python3 /path/to/team-monitor/scripts/install_hooks.py
```

### Dependencies

Flask is auto-installed when you first start the dashboard. To install manually:

```bash
pip install flask
```

## Usage

### Start the Dashboard

```
/team-monitor
```

Then open http://localhost:5111 in your browser.

### Stop the Dashboard

```
/team-monitor-stop
```

### Check Status

```
/team-monitor-status
```

### Natural Language

You can also just say "monitor my team" or "open the team dashboard" and the skill will trigger automatically.

## Uninstall

To remove the hooks from your Claude Code settings:

**macOS / Linux:**
```bash
python3 /path/to/team-monitor/scripts/uninstall_hooks.py
```

**Windows:**
```bash
python /path/to/team-monitor/scripts/uninstall_hooks.py
```

## Dashboard Features

- **Agent Cards** — one card per agent showing name, team, last activity, and event count
- **Live Event Feed** — reverse-chronological stream with color-coded category badges
  - Blue = communication (DMs, broadcasts, shutdown requests)
  - Green = task management (create, update, assign)
  - Orange = tool use (Bash, Edit, Write, Read, Grep, etc.)
  - Gray = lifecycle (agent stop, notifications)
- **Event Detail** — click any event to expand and see the full JSON payload
- **Filters** — filter by category, agent, or tool
- **Stats Sidebar** — total events, events/minute rate, category breakdown, most active agent

## How It Works

```
Claude Code Hooks (PostToolUse, SubagentStart/Stop, Notification)
    │  stdin: JSON with tool_name, tool_input, session_id
    ▼
Hook Scripts (Python) ──► SQLite DB (WAL mode)  ◄── Flask Server
    │                      data/team_monitor.db        │
    ▼                                                  ▼
SSE Bridge (file-based) ────────────────────► Browser Dashboard
    data/sse_events/*.json                   localhost:5111
```

1. Claude Code fires a hook after every tool call in the lead session
2. The hook script classifies the event and writes it to SQLite
3. A small JSON notification file is written for the SSE bridge
4. When subagents finish, their transcripts are parsed to backfill all tool calls
5. The Flask server streams events to the browser via SSE
6. The dashboard updates in real time — no refresh needed

## File Structure

```
team-monitor/
├── .claude-plugin/
│   ├── plugin.json            # Plugin manifest
│   └── marketplace.json       # Marketplace config for installation
├── core/
│   ├── db.py                  # SQLite schema and queries
│   ├── event_parser.py        # Event classification
│   ├── sse_bridge.py          # File-based SSE notifications
│   └── transcript_parser.py   # Parse subagent JSONL transcripts
├── hooks/
│   ├── hooks.json             # Hook registrations (reference)
│   ├── posttooluse_hook.py    # Captures all tool calls
│   ├── subagentstart_hook.py  # Captures agent spawns
│   ├── stop_hook.py           # Captures stops + parses transcripts
│   └── notification_hook.py   # Captures notifications
├── server/
│   ├── app.py                 # Flask routes + SSE endpoint
│   ├── templates/             # Dashboard HTML
│   └── static/                # CSS + JavaScript
├── commands/                  # Slash commands
├── skills/                    # Natural language triggers
├── scripts/
│   ├── start_server.py        # Launch dashboard (auto-installs deps + hooks)
│   ├── stop_server.py         # Stop dashboard
│   ├── install_hooks.py       # Register hooks in ~/.claude/settings.json
│   └── uninstall_hooks.py     # Remove hooks from settings
└── data/                      # Runtime data (gitignored)
```

## Troubleshooting

**Dashboard shows no data:**
- Run `python3 scripts/install_hooks.py` to register hooks (or `python` on Windows)
- Restart Claude Code after installing hooks
- Run `/hooks` to verify the team-monitor hooks appear
- Check `data/hook_errors.log` inside the plugin directory for errors

**Server won't start:**
- Flask is auto-installed, but if it fails: `pip install flask`
- Check if port 5111 is already in use

**Events not appearing in real time:**
- Lead session tool calls appear in real time
- Subagent tool calls appear when the agent finishes (transcript is parsed on SubagentStop)
- Check the connection status dot in the dashboard header (green = connected)
- The SSE connection auto-reconnects after 3 seconds if disconnected

**Hooks not firing:**
- Hooks must be in `~/.claude/settings.json`, not just in the plugin's hooks.json
- Run `install_hooks.py` to register them, then restart Claude Code
- On macOS use `python3`, on Windows use `python`
