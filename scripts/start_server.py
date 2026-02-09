"""Start the Team Monitor dashboard server."""

import argparse
import os
import subprocess
import sys

PLUGIN_ROOT = os.environ.get('CLAUDE_PLUGIN_ROOT') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PID_FILE = os.path.join(PLUGIN_ROOT, 'data', 'server.pid')


def ensure_dependencies():
    """Install Flask if it's not available."""
    try:
        import flask  # noqa: F401
    except ImportError:
        print('Flask not found. Installing...')
        req_file = os.path.join(PLUGIN_ROOT, 'requirements.txt')
        subprocess.check_call(
            [sys.executable, '-m', 'pip', 'install', '-r', req_file],
            stdout=subprocess.DEVNULL,
        )
        print('Flask installed successfully.')


def is_process_alive(pid):
    """Check if a process with the given PID is still running."""
    try:
        if sys.platform == 'win32':
            result = subprocess.run(
                ['tasklist', '/FI', f'PID eq {pid}', '/NH'],
                capture_output=True, text=True
            )
            return str(pid) in result.stdout
        else:
            os.kill(pid, 0)
            return True
    except (OSError, ProcessLookupError):
        return False


def show_status():
    """Print whether the server is currently running."""
    if not os.path.exists(PID_FILE):
        print('Team Monitor is not running.')
        return

    with open(PID_FILE, 'r') as f:
        pid = int(f.read().strip())

    if is_process_alive(pid):
        print(f'Team Monitor is running (PID {pid}).')
    else:
        print('Team Monitor is not running (stale PID file).')
        os.remove(PID_FILE)


def start_server(port):
    """Launch the Flask server as a detached background process."""
    if os.path.exists(PID_FILE):
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        if is_process_alive(pid):
            print(f'Team Monitor is already running (PID {pid}).')
            return

    app_path = os.path.join(PLUGIN_ROOT, 'server', 'app.py')
    if not os.path.exists(app_path):
        print(f'Error: server/app.py not found at {app_path}')
        sys.exit(1)

    os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)

    cmd = [sys.executable, app_path, '--port', str(port)]

    if sys.platform == 'win32':
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        DETACHED_PROCESS = 0x00000008
        proc = subprocess.Popen(
            cmd,
            creationflags=CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )
    else:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )

    with open(PID_FILE, 'w') as f:
        f.write(str(proc.pid))

    print(f'Team Monitor started on http://localhost:{port}')


def main():
    parser = argparse.ArgumentParser(description='Start the Team Monitor dashboard server')
    parser.add_argument('--port', type=int, default=5111, help='Port to run the server on')
    parser.add_argument('--status', action='store_true', help='Show server status instead of starting')
    args = parser.parse_args()

    if args.status:
        show_status()
    else:
        ensure_dependencies()
        start_server(args.port)


if __name__ == '__main__':
    main()
