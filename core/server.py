"""
Tokyo AI — Flask Server with SSE streaming and PWA support.
Serves the web interface and handles commands from browser/mobile.
"""
import sys
import os
import json
import time
from flask import Flask, render_template, request, jsonify, Response, send_from_directory
from flask_cors import CORS
import threading
import queue

# Handle PyInstaller path
if getattr(sys, 'frozen', False):
    template_dir = os.path.join(sys._MEIPASS, 'core', 'templates')
else:
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))

app = Flask(__name__, template_folder=template_dir)
CORS(app)

# ── Queues ─────────────────────────────────────────────────────
input_queue = None          # Commands from web → main loop
_sse_clients = []           # SSE subscriber queues
_sse_lock = threading.Lock()

# ── SSE Helpers ────────────────────────────────────────────────
def broadcast_sse(event_data: dict):
    """Send an event to all connected SSE clients."""
    msg = f"data: {json.dumps(event_data)}\n\n"
    with _sse_lock:
        dead = []
        for q in _sse_clients:
            try:
                q.put_nowait(msg)
            except:
                dead.append(q)
        for q in dead:
            _sse_clients.remove(q)

def push_response(text: str):
    """Push an AI response to all web clients."""
    broadcast_sse({"type": "response", "text": text})

def push_status(state: str, label: str):
    """Push a status change to all web clients."""
    broadcast_sse({"type": "status", "state": state, "label": label})

def push_log(text: str):
    """Push a log/system message to all web clients."""
    broadcast_sse({"type": "log", "text": text})

# ── Routes ─────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/mobile')
def mobile():
    return render_template('mobile.html')

@app.route('/command', methods=['POST'])
def receive_command():
    data = request.json
    text = data.get('text', '').strip()
    
    if text and input_queue:
        print(f"📱 Web Command: {text}")
        input_queue.put(text)
        return jsonify({"status": "queued", "message": f"Processing: {text}"})
    
    return jsonify({"status": "error", "message": "Empty command"}), 400

@app.route('/stream')
def stream():
    """Server-Sent Events endpoint for real-time updates."""
    def event_stream():
        q = queue.Queue(maxsize=100)
        with _sse_lock:
            _sse_clients.append(q)
        try:
            # Send initial heartbeat
            yield f"data: {json.dumps({'type': 'status', 'state': 'online', 'label': '● ONLINE'})}\n\n"
            while True:
                try:
                    msg = q.get(timeout=30)
                    yield msg
                except queue.Empty:
                    # Heartbeat to keep connection alive
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
        except GeneratorExit:
            pass
        finally:
            with _sse_lock:
                if q in _sse_clients:
                    _sse_clients.remove(q)
    
    return Response(event_stream(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

@app.route('/status')
def status():
    return jsonify({"status": "online", "message": "Tokyo AI is ready."})

# ── PWA Routes ─────────────────────────────────────────────────
@app.route('/manifest.webmanifest')
def manifest():
    m = {
        "name": "Tokyo AI",
        "short_name": "Tokyo",
        "description": "Your personal AI assistant",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#050510",
        "theme_color": "#050510",
        "orientation": "portrait",
        "icons": [
            {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"}
        ]
    }
    return Response(json.dumps(m), mimetype='application/manifest+json')

@app.route('/sw.js')
def service_worker():
    sw = """
self.addEventListener('install', e => { self.skipWaiting(); });
self.addEventListener('activate', e => { e.waitUntil(clients.claim()); });
self.addEventListener('fetch', e => {
    if (e.request.url.includes('/stream')) return;
    e.respondWith(fetch(e.request).catch(() => new Response('Offline', {status: 503})));
});
"""
    return Response(sw, mimetype='application/javascript')

@app.route('/icon-192.png')
@app.route('/icon-512.png')
def icon():
    """Generate a simple icon on the fly."""
    # Return a 1x1 transparent PNG as fallback
    import base64
    png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==')
    return Response(png, mimetype='image/png')

# ── Server Start ───────────────────────────────────────────────
def run_flask(q, host='0.0.0.0', port=5000):
    global input_queue
    input_queue = q
    app.run(host=host, port=port, debug=False, use_reloader=False, threaded=True)

def start_server(q):
    """Starts the Flask server in a separate thread."""
    t = threading.Thread(target=run_flask, args=(q,), daemon=True)
    t.start()
    return t
