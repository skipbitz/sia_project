import hashlib
import os
import time
import http.cookies
import uuid
from backend.database import get_connection

# Simple in-memory session store: {session_id: {'user_id':..., 'username':..., 'role':..., 'expiry':...}}
SESSIONS = {}
SESSION_TTL = 60 * 60 * 2  # 2 hours


def hash_password(password, salt=None):
    if salt is None:
        salt = os.urandom(16).hex()
    h = hashlib.sha256((salt + password).encode('utf-8')).hexdigest()
    return f"{salt}${h}"


def verify_password(stored, password):
    try:
        salt, h = stored.split('$', 1)
    except Exception:
        return False
    return hash_password(password, salt) == stored


def create_user(username, password, role='user'):
    # If user already exists, return existing id (idempotent)
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT user_id FROM user_login WHERE username=%s", (username,))
        existing = cursor.fetchone()
        if existing:
            return existing[0]
        pw = hash_password(password)
        cursor.execute("INSERT INTO user_login (username, password, role) VALUES (%s, %s, %s)",
                       (username, pw, role))
        conn.commit()
        uid = cursor.lastrowid
    finally:
        cursor.close()
        conn.close()
    return uid


def authenticate(username, password):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT user_id, username, password, role FROM user_login WHERE username=%s", (username,))
        row = cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

    if not row:
        return None
    if verify_password(row['password'], password):
        return {'user_id': row['user_id'], 'username': row['username'], 'role': row['role']}
    return None


def create_session(user):
    sid = uuid.uuid4().hex
    expiry = time.time() + SESSION_TTL
    SESSIONS[sid] = {'user_id': user['user_id'], 'username': user['username'], 'role': user['role'], 'expiry': expiry}
    return sid


def get_session(handler):
    cookie_header = handler.headers.get('Cookie')
    if not cookie_header:
        return None
    cookie = http.cookies.SimpleCookie()
    cookie.load(cookie_header)
    sid = None
    if 'session_id' in cookie:
        sid = cookie['session_id'].value
    if not sid:
        return None
    sess = SESSIONS.get(sid)
    if not sess:
        return None
    if sess['expiry'] < time.time():
        del SESSIONS[sid]
        return None
    # refresh expiry
    sess['expiry'] = time.time() + SESSION_TTL
    return {'session_id': sid, **sess}


def clear_session(handler):
    cookie_header = handler.headers.get('Cookie')
    if not cookie_header:
        return
    cookie = http.cookies.SimpleCookie()
    cookie.load(cookie_header)
    if 'session_id' in cookie:
        sid = cookie['session_id'].value
        if sid in SESSIONS:
            del SESSIONS[sid]
