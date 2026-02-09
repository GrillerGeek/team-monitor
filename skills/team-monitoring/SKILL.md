---
trigger: monitor team|watch team activity|team dashboard|observe agents|team monitor|monitor agents
---

# Team Monitoring Dashboard

Start the Team Monitor real-time dashboard so the user can observe agent team activity.

## Steps

1. Register hooks if not already installed (safe to run repeatedly):

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/install_hooks.py"
```

If that fails, try with `python` instead of `python3`.

2. Check if the server is already running:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/start_server.py" --status
```

3. If the server is not running, start it:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/start_server.py" --port 5111
```

4. Tell the user:
   - The dashboard is available at http://localhost:5111
   - If hooks were just installed for the first time, they need to **restart Claude Code** for hooks to take effect
