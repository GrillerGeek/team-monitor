---
trigger: monitor team|watch team activity|team dashboard|observe agents|team monitor|monitor agents
---

# Team Monitoring Dashboard

Start the Team Monitor real-time dashboard so the user can observe agent team activity.

## Steps

1. Check if the server is already running:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/start_server.py" --status
```

2. If the server is not running, start it:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/start_server.py" --port 5111
```

3. Tell the user the dashboard is available at http://localhost:5111 and they can open it in their browser to watch real-time agent activity, messages, and task progress.
