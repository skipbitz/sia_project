import os
import json
import urllib
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from backend.utils import parse_json_body, json_response
from backend.database import get_connection
from backend.auth import create_user, authenticate, create_session, get_session, clear_session, update_user, delete_user
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
        # (removed friendly alias for /forgot - feature disabled)
        full = os.path.abspath(os.path.normpath(os.path.join(STATIC_DIR, path.lstrip('/'))))
        # special-case assets folder which lives at project root (outside frontend)
        assets_dir = os.path.abspath(os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'assets')))
        if path.startswith('/assets/'):
            full = os.path.abspath(os.path.normpath(os.path.join(os.path.dirname(__file__), '..', path.lstrip('/'))))
        # prevent path traversal: allow files under STATIC_DIR or the assets_dir
        static_abs = os.path.abspath(STATIC_DIR)
        if not (full.startswith(static_abs) or full.startswith(assets_dir)):
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
        # --- user listing for admin UI ---
        if path == '/api/users':
            # Debugging: print cookie and session info to help diagnose frontend failures
            try:
                print(f"[api/users] Cookie header: {self.headers.get('Cookie')}")
            except Exception:
                pass
            sess = get_session(self)
            try:
                print(f"[api/users] session: {sess}")
            except Exception:
                pass
            if not sess or sess.get('role') != 'admin':
                print(f"[api/users] access denied: sess={sess}")
                return json_response(self, {'error': 'forbidden'}, status=403)
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute("SELECT user_id, username, role FROM user_login")
                rows = cursor.fetchall()
            finally:
                cursor.close()
                conn.close()
            return json_response(self, rows)
        if path == '/api/current_borrows':
            # list currently borrowed equipment (approved borrow_request)
            sess = get_session(self)
            if not sess or sess.get('role') != 'admin':
                return json_response(self, {'error': 'forbidden'}, status=403)
            rows = borrow_mod.list_current_borrows()
            return json_response(self, rows)

        if path == '/api/recent_borrows':
            sess = get_session(self)
            if not sess:
                return json_response(self, {'error': 'not authenticated'}, status=401)
            # optional limit parameter
            qs = parse_qs(parsed.query)
            try:
                limit = int(qs.get('limit', [5])[0])
            except Exception:
                limit = 5
            # Admins can see all recent borrows; users only their own
            if sess.get('role') == 'admin':
                rows = borrow_mod.list_recent_borrows(limit=limit)
            else:
                rows = borrow_mod.list_recent_borrows(limit=limit, user_id=sess.get('user_id'))
            return json_response(self, rows)

        if path == '/api/most_borrowed':
            sess = get_session(self)
            if not sess or sess.get('role') != 'admin':
                return json_response(self, {'error': 'forbidden'}, status=403)
            qs = parse_qs(parsed.query)
            try:
                limit = int(qs.get('limit', [1])[0])
            except Exception:
                limit = 1
            rows = borrow_mod.get_most_borrowed(limit=limit)
            return json_response(self, rows)

        if path == '/api/borrow_history':
            # Allow a local debug bypass when called with ?debug=1 from localhost
            qs = parse_qs(parsed.query)
            debug_mode = qs.get('debug', [None])[0]
            client_ip = None
            try:
                client_ip = self.client_address[0]
            except Exception:
                client_ip = None
            if debug_mode == '1' and client_ip in ('127.0.0.1', '::1'):
                rows = borrow_mod.list_borrow_history()
                return json_response(self, rows)

            sess = get_session(self)
            if not sess or sess.get('role') != 'admin':
                return json_response(self, {'error': 'forbidden'}, status=403)
            rows = borrow_mod.list_borrow_history()
            return json_response(self, rows)
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
            # debug: log cookie + session for troubleshooting
            try:
                print(f"[api/return GET] Cookie: {self.headers.get('Cookie')}")
            except Exception:
                pass
            sess = get_session(self)
            try:
                print(f"[api/return GET] session: {sess}")
            except Exception:
                pass
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
            # debug: log login attempt (do NOT log passwords in production)
            try:
                print(f"[login] attempt username={username}")
            except Exception:
                pass
            user = authenticate(username, password)
            try:
                print(f"[login] result username={username} -> {'OK' if user else 'FAIL'}")
            except Exception:
                pass
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
            # optional fields from frontend: quantity, borrow_date, return_date
            quantity = int(body.get('quantity') or 1)
            borrow_date = body.get('borrow_date')
            return_date = body.get('return_date')

            # validate requested quantity and availability
            try:
                equip = equipment_mod.get_equipment(eid)
            except Exception:
                equip = None
            if not equip:
                return json_response(self, {'error': 'equipment not found'}, status=404)
            available = int(equip.get('quantity_available', 0) or 0)
            if quantity <= 0:
                return json_response(self, {'error': 'invalid quantity'}, status=400)
            if available < quantity:
                return json_response(self, {'error': 'Item not available'}, status=400)

            try:
                # pass optional quantity and return date to be stored when supported
                bid = borrow_mod.create_borrow_request(sess['user_id'], eid, borrow_date=borrow_date, quantity_requested=quantity, expected_return_date=return_date)
            except Exception as e:
                # Log and return error
                try:
                    import traceback
                    print('[api/borrow] error creating request:', traceback.format_exc())
                except Exception:
                    pass
                return json_response(self, {'error': 'failed to create borrow request', 'details': str(e)}, status=500)
            except Exception as e:
                # Log and return error
                try:
                    import traceback
                    print('[api/borrow] error creating request:', traceback.format_exc())
                except Exception:
                    pass
                return json_response(self, {'error': 'failed to create borrow request', 'details': str(e)}, status=500)
            return json_response(self, {'request_id': bid})

        if path == '/api/return':
            # debug: log incoming body and session
            try:
                print(f"[api/return POST] Cookie: {self.headers.get('Cookie')}")
            except Exception:
                pass
            sess = get_session(self)
            try:
                print(f"[api/return POST] session: {sess}")
            except Exception:
                pass
            if not sess:
                return json_response(self, {'error': 'not authenticated'}, status=401)
            length = int(self.headers.get('Content-Length', 0))
            body = parse_json_body(self.rfile, length)
            try:
                print(f"[api/return POST] body: {body}")
            except Exception:
                pass
            borrow_id = int(body.get('borrow_id'))
            rid = return_mod.create_return_request(borrow_id)
            return json_response(self, {'return_id': rid})

        return json_response(self, {'error': 'not found'}, status=404)

    def handle_api_put(self, path):
        # admin actions: approve/deny borrow, approve return, update equipment
        try:
            sess = get_session(self)
            if not sess or sess['role'] != 'admin':
                return json_response(self, {'error': 'forbidden'}, status=403)
            length = int(self.headers.get('Content-Length', 0))
            body = parse_json_body(self.rfile, length)
            if path.startswith('/api/equipment/'):
                equipment_id = int(path.split('/')[-1])
                equipment_mod.update_equipment(equipment_id, **body)
                return json_response(self, {'ok': True})

            if path.startswith('/api/users/'):
                # update user (admin only)
                try:
                    user_id = int(path.split('/')[-1])
                except Exception:
                    return json_response(self, {'error': 'invalid user id'}, status=400)
                username = body.get('username')
                role = body.get('role')
                password = body.get('password')
                # prevent changing own role to non-admin accidentally? allow but be careful
                ok = update_user(user_id, username=username, role=role, password=password)
                if not ok:
                    return json_response(self, {'error': 'no fields to update'}, status=400)
                return json_response(self, {'ok': True})

            if path.startswith('/api/borrow/'):
                request_id = int(path.split('/')[-1])
                # If the body contains fields other than status, treat as an edit
                if any(k in body for k in ('borrow_date', 'return_date', 'expected_return_date', 'quantity', 'quantity_requested')):
                    # map frontend names to backend parameter names
                    borrow_date = body.get('borrow_date')
                    expected_return_date = body.get('expected_return_date') or body.get('return_date')
                    quantity = body.get('quantity') or body.get('quantity_requested')
                    ok = borrow_mod.update_borrow_request(request_id, borrow_date=borrow_date, expected_return_date=expected_return_date, quantity_requested=quantity)
                    if not ok:
                        return json_response(self, {'error': 'failed to update borrow request'}, status=500)
                    return json_response(self, {'ok': True})
                else:
                    status = body.get('status')
                    borrow_mod.update_borrow_status(request_id, status)
                    return json_response(self, {'ok': True})

            if path.startswith('/api/return/'):
                return_id = int(path.split('/')[-1])
                # call approve_return and return a JSON response; catch internal errors
                ok = return_mod.approve_return(return_id)
                if not ok:
                    return json_response(self, {'error': 'failed to approve return'}, status=500)
                return json_response(self, {'ok': True})

            return json_response(self, {'error': 'not found'}, status=404)
        except Exception as e:
            # log traceback and return 500 JSON instead of letting the connection drop
            import traceback
            tb = traceback.format_exc()
            try:
                print('[error] exception in handle_api_put:', tb)
            except Exception:
                pass
            return json_response(self, {'error': 'internal server error', 'details': str(e)}, status=500)

    def handle_api_delete(self, path):
        try:
            print(f"[api/DELETE] path={path} Cookie={self.headers.get('Cookie')}")
        except Exception:
            pass
        sess = get_session(self)
        if not sess or sess['role'] != 'admin':
            return json_response(self, {'error': 'forbidden'}, status=403)
        if path.startswith('/api/equipment/'):
            equipment_id = int(path.split('/')[-1])
            equipment_mod.delete_equipment(equipment_id)
            return json_response(self, {'ok': True})
        if path.startswith('/api/borrow/'):
            # allow admins to remove denied/invalid borrow requests
            try:
                request_id = int(path.split('/')[-1])
            except Exception:
                return json_response(self, {'error': 'invalid id'}, status=400)
            try:
                borrow_mod.delete_borrow_request(request_id)
            except Exception as e:
                try:
                    print('[api/delete borrow] error:', e)
                except Exception:
                    pass
                return json_response(self, {'error': 'failed to delete borrow request'}, status=500)
            return json_response(self, {'ok': True})
        if path.startswith('/api/users/'):
            try:
                user_id = int(path.split('/')[-1])
            except Exception:
                return json_response(self, {'error': 'invalid id'}, status=400)
            # prevent deleting self
            sess = get_session(self)
            if sess and sess.get('user_id') == user_id:
                return json_response(self, {'error': 'cannot delete yourself'}, status=400)
            try:
                delete_user(user_id)
            except Exception as e:
                try:
                    print('[api/delete user] error:', e)
                except Exception:
                    pass
                return json_response(self, {'error': 'failed to delete user'}, status=500)
            return json_response(self, {'ok': True})
        return json_response(self, {'error': 'not found'}, status=404)


def run(host='127.0.0.1', port=8000):
    import time
    t0 = time.perf_counter()
    print(f"[startup] beginning server bind at {time.strftime('%H:%M:%S')}")
    # ensure optional columns exist so frontend return dates and quantities are persisted
    try:
        borrow_mod.ensure_borrow_request_columns()
    except Exception:
        pass
    server = HTTPServer((host, port), Handler)
    t1 = time.perf_counter()
    print(f"[startup] server bound at {time.strftime('%H:%M:%S')} (bind took {t1-t0:.3f}s)")
    print(f"Server running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n[shutdown] server stopped by KeyboardInterrupt')
    finally:
        server.server_close()
        t2 = time.perf_counter()
        print(f"[shutdown] server closed at {time.strftime('%H:%M:%S')} (uptime {t2-t1:.3f}s)")


if __name__ == '__main__':
    run()
