Show the current status of the Team Monitor dashboard.

First, check if the server is running:

```
python "${CLAUDE_PLUGIN_ROOT}/scripts/start_server.py" --status
```

If the server is running, query the stats API for a summary:

```
curl -s http://localhost:5111/api/stats
```

Display the status to the user, including whether the server is running, the number of active agents, and recent message counts.
