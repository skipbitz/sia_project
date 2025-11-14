import json
from urllib.parse import parse_qs


def parse_json_body(rfile, content_length):
    try:
        length = int(content_length)
    except Exception:
        return {}
    if length <= 0:
        return {}
    raw = rfile.read(length).decode('utf-8')
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        # Fallback for form-encoded body
        return {k: v[0] for k, v in parse_qs(raw).items()}


def json_response(handler, obj, status=200):
    data = json.dumps(obj, default=str).encode('utf-8')
    handler.send_response(status)
    handler.send_header('Content-Type', 'application/json; charset=utf-8')
    handler.send_header('Content-Length', str(len(data)))
    # Echo Origin header for CORS during development (safer than wildcard when credentials used)
    origin = handler.headers.get('Origin')
    if origin:
        handler.send_header('Access-Control-Allow-Origin', origin)
        handler.send_header('Access-Control-Allow-Credentials', 'true')
        handler.send_header('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
        handler.send_header('Access-Control-Allow-Headers', 'Content-Type')
    else:
        handler.send_header('Access-Control-Allow-Origin', '*')
    handler.end_headers()
    handler.wfile.write(data)
