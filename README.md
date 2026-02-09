# Team Monitor

Real-time dashboard for monitoring Claude Code agent team activity. When multiple agents collaborate — sending messages, creating tasks, editing files — this plugin captures everything and streams it to a live dashboard at `localhost:5111`.

![Dark themed dashboard with agent cards, live event feed, and stats sidebar](https://img.shields.io/badge/dashboard-localhost%3A5111-blue)

## What It Does

- **Hooks into every tool call** via Claude Code's PostToolUse event
- **Classifies events** into categories: communication, task management, tool use, lifecycle
- **Stores everything** in a local SQLite database (WAL mode for concurrent access)
- **Streams live updates** to a dark-themed browser dashboard via SSE

## Install

### From GitHub

```
/plugin marketplace add GrillerGeek/team-monitor
/plugin install team-monitor@GrillerGeek/team-monitor
```

Restart Claude Code after installing so hooks are loaded.

### For Development

```bash
claude --plugin-dir /path/to/team-monitor
```

### Dependencies

The plugin requires Flask. Install it if you don't have it:

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
Claude Code Hooks (PostToolUse, Stop, Notification)
    │  stdin: JSON with tool_name, tool_input, session_id
    ▼
Hook Scripts (Python) ──► SQLite DB (WAL mode)  ◄── Flask Server
                          data/team_monitor.db        │
    │                                                 ▼
    └── SSE Bridge (file-based) ──────────────► Browser Dashboard
        data/sse_events/*.json                  localhost:5111
```

1. Claude Code fires a hook after every tool call
2. The hook script classifies the event and writes it to SQLite
3. A small JSON notification file is written for the SSE bridge
4. The Flask server picks up notifications and streams them to the browser
5. The dashboard updates in real time — no refresh needed

## File Structure

```
team-monitor/
├── .claude-plugin/
│   ├── plugin.json          # Plugin manifest
│   └── marketplace.json     # Marketplace config for installation
├── core/
│   ├── db.py                # SQLite schema and queries
│   ├── event_parser.py      # Event classification
│   └── sse_bridge.py        # File-based SSE notifications
├── hooks/
│   ├── hooks.json           # Hook registrations
│   ├── posttooluse_hook.py  # Captures all tool calls
│   ├── stop_hook.py         # Captures agent stops
│   └── notification_hook.py # Captures notifications
├── server/
│   ├── app.py               # Flask routes + SSE endpoint
│   ├── templates/           # Dashboard HTML
│   └── static/              # CSS + JavaScript
├── commands/                # Slash commands
├── skills/                  # Natural language triggers
├── scripts/                 # Server start/stop scripts
└── data/                    # Runtime data (gitignored)
```

## Troubleshooting

**Dashboard shows no data:**
- Make sure you restarted Claude Code after installing the plugin
- Run `/hooks` to verify the team-monitor hooks appear
- Check `data/hook_errors.log` inside the plugin directory for errors

**Server won't start:**
- Make sure Flask is installed: `pip install flask`
- Check if port 5111 is already in use

**Events not appearing in real time:**
- Check the connection status dot in the dashboard header (green = connected)
- The SSE connection auto-reconnects after 3 seconds if disconnected
