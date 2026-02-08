"""Stop the Team Monitor dashboard server."""

import os
import signal
import subprocess
import sys

PLUGIN_ROOT = os.environ.get('CLAUDE_PLUGIN_ROOT') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PID_FILE = os.path.join(PLUGIN_ROOT, 'data', 'server.pid')


def stop_server():
    """Stop the running server by PID."""
    if not os.path.exists(PID_FILE):
        print('Team Monitor is not running.')
        return

    with open(PID_FILE, 'r') as f:
        pid = int(f.read().strip())

    try:
        if sys.platform == 'win32':
            subprocess.run(['taskkill', '/F', '/PID', str(pid)], capture_output=True)
        else:
            os.kill(pid, signal.SIGTERM)
        print('Team Monitor stopped.')
    except (OSError, ProcessLookupError):
        print('Team Monitor was not running (process already exited).')

    os.remove(PID_FILE)


if __name__ == '__main__':
    stop_server()
