Start the Team Monitor real-time dashboard.

**Step 1: Register hooks** (safe to run multiple times — skips if already installed):

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/install_hooks.py"
```

If that fails, try with `python` instead of `python3`.

After installing hooks, tell the user they need to **restart Claude Code** for hooks to take effect (if this is the first time installing hooks). Hooks only need to be installed once.

**Step 2: Start the dashboard server:**

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/start_server.py" --port 5111
```

If that fails, try with `python` instead of `python3`.

After starting, inform the user the dashboard is available at http://localhost:5111 and they can open it in their browser to see real-time team activity.
