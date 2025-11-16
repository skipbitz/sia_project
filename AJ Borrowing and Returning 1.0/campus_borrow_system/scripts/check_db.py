"""Quick DB connectivity and latency check.

Usage:
  python .\scripts\check_db.py

This script reads `backend/db_config.json` via backend.database.load_config()
and attempts a simple connection and `SELECT 1` to measure response time.
"""
import time
import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.database import load_config

def main():
    cfg = load_config()
    try:
        import mysql.connector
    except Exception as e:
        print('mysql.connector not available:', e)
        return 2

    print('DB config:', {k: v for k, v in cfg.items() if k != 'password'})
    start = time.time()
    try:
        conn = mysql.connector.connect(connect_timeout=5, **cfg)
    except Exception as e:
        print('Failed to connect to DB:', e)
        return 2
    conn_time = time.time() - start
    print(f'Connected to DB in {conn_time:.3f}s')
    try:
        cur = conn.cursor()
        t0 = time.time()
        cur.execute('SELECT 1')
        cur.fetchone()
        qtime = time.time() - t0
        print(f'Query SELECT 1 took {qtime:.3f}s')
    except Exception as e:
        print('Query failed:', e)
        return 2
    finally:
        try:
            cur.close()
        except: pass
        try:
            conn.close()
        except: pass
    print('DB check OK')
    return 0

if __name__ == '__main__':
    sys.exit(main())
