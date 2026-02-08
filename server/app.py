"""Flask web server for team-monitor dashboard."""

import os
import sys
import json
import time

PLUGIN_ROOT = os.environ.get('CLAUDE_PLUGIN_ROOT') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PLUGIN_ROOT)

from flask import Flask, Response, jsonify, render_template, request
from core.db import init_db, get_events, get_event_by_id, get_agents, get_stats
from core.sse_bridge import get_pending_events

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
    static_folder=os.path.join(os.path.dirname(__file__), 'static'),
)

_db_initialized = False


@app.before_request
def _ensure_db():
    global _db_initialized
    if not _db_initialized:
        init_db()
        _db_initialized = True


@app.after_request
def _add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response


# ---- Pages ----

@app.route('/')
def index():
    return render_template('dashboard.html')


# ---- API ----

@app.route('/api/events')
def api_events():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    category = request.args.get('category', None)
    agent = request.args.get('agent', None)
    tool = request.args.get('tool', None)
    result = get_events(page=page, per_page=per_page, category=category, agent=agent, tool=tool)
    return jsonify(result)


@app.route('/api/events/<int:event_id>')
def api_event_detail(event_id):
    event = get_event_by_id(event_id)
    if event is None:
        return jsonify({'error': 'not found'}), 404
    # Parse payload_json into a proper object for the response
    if event.get('payload_json'):
        try:
            event['payload'] = json.loads(event['payload_json'])
        except (json.JSONDecodeError, TypeError):
            event['payload'] = event['payload_json']
    return jsonify(event)


@app.route('/api/agents')
def api_agents():
    agents = get_agents()
    return jsonify({'agents': agents})


@app.route('/api/stats')
def api_stats():
    stats = get_stats()
    return jsonify(stats)


@app.route('/api/stream')
def api_stream():
    def generate():
        last_id = 0
        last_heartbeat = time.time()

        while True:
            # Poll SSE bridge files
            pending = get_pending_events()
            for ev in pending:
                ev_id = ev.get('id', 0)
                if ev_id > last_id:
                    last_id = ev_id
                yield f"data: {json.dumps(ev)}\n\n"

            # Fallback: poll DB for events newer than last_id
            if last_id > 0:
                try:
                    result = get_events(page=1, per_page=20)
                    for ev in reversed(result.get('events', [])):
                        ev_id = ev.get('id', 0)
                        if ev_id > last_id:
                            last_id = ev_id
                            yield f"data: {json.dumps(ev)}\n\n"
                except Exception:
                    pass

            # Heartbeat every 15 seconds
            now = time.time()
            if now - last_heartbeat >= 15:
                yield ": heartbeat\n\n"
                last_heartbeat = now

            time.sleep(0.5)

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
        },
    )


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5111)
    args = parser.parse_args()
    init_db()
    app.run(host='127.0.0.1', port=args.port, debug=False, threaded=True)
