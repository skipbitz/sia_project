from backend.database import get_connection
from backend.auth import create_user

def ensure_admin(username='admin', password='AdminPass123'):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute('SELECT user_id FROM user_login WHERE username=%s', (username,))
        if cur.fetchone():
            print('admin user already exists')
            return
        create_user(username, password, 'admin')
        print('admin user created with username="admin" and password="AdminPass123"')
    finally:
        cur.close()
        conn.close()


if __name__ == '__main__':
    ensure_admin()
