import os
import json
import urllib
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from backend.utils import parse_json_body, json_response
from backend.auth import create_user, authenticate, create_session, get_session, clear_session
import backend.equipment as equipment_mod
import backend.borrow as borrow_mod
import backend.return_mod as return_mod

STATIC_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend')


class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith('/api/'):
            return self.handle_api_get(path, parsed)
        else:
            return self.serve_static(path)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith('/api/'):
            return self.handle_api_post(path)
        else:
            self.send_response(404)
            self.end_headers()

    def do_PUT(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith('/api/'):
            return self.handle_api_put(path)
        else:
            self.send_response(404)
            self.end_headers()

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path.startswith('/api/'):
            return self.handle_api_delete(path)
        else:
            self.send_response(404)
            self.end_headers()

    # --- static file serving ---
    def serve_static(self, path):
        if path == '/' or path == '':
            path = '/index.html'
        full = os.path.abspath(os.path.normpath(os.path.join(STATIC_DIR, path.lstrip('/'))))
        # special-case assets folder which lives at project root (outside frontend)
        if path.startswith('/assets/'):
            full = os.path.abspath(os.path.normpath(os.path.join(os.path.dirname(__file__), '..', path.lstrip('/'))))
        # prevent path traversal
        if not full.startswith(os.path.abspath(STATIC_DIR)):
            self.send_response(403)
            self.end_headers()
            return
        if not os.path.exists(full) or os.path.isdir(full):
            self.send_response(404)
            self.end_headers()
            return
        with open(full, 'rb') as f:
            data = f.read()
        self.send_response(200)
        ctype = 'text/html'
        if full.endswith('.css'):
            ctype = 'text/css'
        elif full.endswith('.js'):
            ctype = 'application/javascript'
        elif full.endswith('.json'):
            ctype = 'application/json'
        elif full.endswith('.png'):
            ctype = 'image/png'
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        # CORS headers for browser previews (will echo Origin if present)
        origin = self.headers.get('Origin')
        if origin:
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Access-Control-Allow-Credentials', 'true')
        else:
            self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(data)

    # --- API handlers ---
    def handle_api_get(self, path, parsed):
        if path == '/api/equipment':
            qs = parse_qs(parsed.query)
            cat = qs.get('category', [None])[0]
            rows = equipment_mod.list_equipment(cat)
            return json_response(self, rows)

        if path == '/api/borrow':
            sess = get_session(self)
            if not sess:
                return json_response(self, {'error': 'not authenticated'}, status=401)
            if sess['role'] == 'admin':
                rows = borrow_mod.list_borrow_requests()
            else:
                rows = borrow_mod.list_borrow_requests(sess['user_id'])
            return json_response(self, rows)

        if path == '/api/return':
            sess = get_session(self)
            if not sess:
                return json_response(self, {'error': 'not authenticated'}, status=401)
            if sess['role'] == 'admin':
                rows = return_mod.list_return_requests()
            else:
                rows = return_mod.list_return_requests(sess['user_id'])
            return json_response(self, rows)

        if path == '/api/session':
            sess = get_session(self)
            return json_response(self, {'session': sess})

        return json_response(self, {'error': 'not found'}, status=404)

    def handle_api_post(self, path):
        if path == '/api/register':
            length = int(self.headers.get('Content-Length', 0))
            body = parse_json_body(self.rfile, length)
            username = body.get('username')
            password = body.get('password')
            role = body.get('role', 'user')
            if not username or not password:
                return json_response(self, {'error': 'username and password required'}, status=400)
            uid = create_user(username, password, role)
            return json_response(self, {'user_id': uid})

        if path == '/api/login':
            length = int(self.headers.get('Content-Length', 0))
            body = parse_json_body(self.rfile, length)
            username = body.get('username')
            password = body.get('password')
            user = authenticate(username, password)
            if not user:
                return json_response(self, {'error': 'invalid credentials'}, status=401)
            sid = create_session(user)
            # set cookie
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Set-Cookie', f'session_id={sid}; Path=/; HttpOnly')
            self.end_headers()
            self.wfile.write(json.dumps({'message': 'ok', 'user': user}).encode('utf-8'))
            return

        if path == '/api/logout':
            clear_session(self)
            # clear cookie
            self.send_response(200)
            self.send_header('Set-Cookie', 'session_id=; Path=/; Max-Age=0')
            self.end_headers()
            self.wfile.write(b'{}')
            return

        if path == '/api/equipment':
            # add equipment (admin)
            sess = get_session(self)
            if not sess or sess['role'] != 'admin':
                return json_response(self, {'error': 'forbidden'}, status=403)
            length = int(self.headers.get('Content-Length', 0))
            body = parse_json_body(self.rfile, length)
            eid = equipment_mod.add_equipment(body.get('equipment_name'), body.get('category'), int(body.get('quantity_available', 0)), body.get('status', 'available'))
            return json_response(self, {'equipment_id': eid})

        if path == '/api/borrow':
            sess = get_session(self)
            if not sess:
                return json_response(self, {'error': 'not authenticated'}, status=401)
            length = int(self.headers.get('Content-Length', 0))
            body = parse_json_body(self.rfile, length)
            eid = int(body.get('equipment_id'))
            bid = borrow_mod.create_borrow_request(sess['user_id'], eid)
            return json_response(self, {'request_id': bid})

        if path == '/api/return':
            sess = get_session(self)
            if not sess:
                return json_response(self, {'error': 'not authenticated'}, status=401)
            length = int(self.headers.get('Content-Length', 0))
            body = parse_json_body(self.rfile, length)
            borrow_id = int(body.get('borrow_id'))
            rid = return_mod.create_return_request(borrow_id)
            return json_response(self, {'return_id': rid})

        return json_response(self, {'error': 'not found'}, status=404)

    def handle_api_put(self, path):
        # admin actions: approve/deny borrow, approve return, update equipment
        sess = get_session(self)
        if not sess or sess['role'] != 'admin':
            return json_response(self, {'error': 'forbidden'}, status=403)
        length = int(self.headers.get('Content-Length', 0))
        body = parse_json_body(self.rfile, length)
        if path.startswith('/api/equipment/'):
            equipment_id = int(path.split('/')[-1])
            equipment_mod.update_equipment(equipment_id, **body)
            return json_response(self, {'ok': True})

        if path.startswith('/api/borrow/'):
            request_id = int(path.split('/')[-1])
            status = body.get('status')
            borrow_mod.update_borrow_status(request_id, status)
            return json_response(self, {'ok': True})

        if path.startswith('/api/return/'):
            return_id = int(path.split('/')[-1])
            return_mod.approve_return(return_id)
            return json_response(self, {'ok': True})

        return json_response(self, {'error': 'not found'}, status=404)

    def handle_api_delete(self, path):
        sess = get_session(self)
        if not sess or sess['role'] != 'admin':
            return json_response(self, {'error': 'forbidden'}, status=403)
        if path.startswith('/api/equipment/'):
            equipment_id = int(path.split('/')[-1])
            equipment_mod.delete_equipment(equipment_id)
            return json_response(self, {'ok': True})
        return json_response(self, {'error': 'not found'}, status=404)


def run(host='127.0.0.1', port=8000):
    server = HTTPServer((host, port), Handler)
    print(f"Server running at http://{host}:{port}")
    server.serve_forever()


if __name__ == '__main__':
    run()
