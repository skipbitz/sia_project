from backend.database import get_connection
import datetime


def create_borrow_request(user_id, equipment_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        now = datetime.datetime.now()
        cursor.execute("INSERT INTO borrow_request (user_id, equipment_id, borrow_date, status) VALUES (%s,%s,%s,%s)",
                       (user_id, equipment_id, now, 'pending'))
        conn.commit()
        bid = cursor.lastrowid
    finally:
        cursor.close()
        conn.close()
    return bid


def list_borrow_requests(user_id=None):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # return richer rows joining username and equipment name
        if user_id:
            cursor.execute("""
                SELECT br.request_id, br.user_id, u.username, br.equipment_id, ei.equipment_name, br.borrow_date, br.status
                FROM borrow_request br
                JOIN user_login u ON br.user_id = u.user_id
                JOIN equipment_inventory ei ON br.equipment_id = ei.equipment_id
                WHERE br.user_id = %s
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT br.request_id, br.user_id, u.username, br.equipment_id, ei.equipment_name, br.borrow_date, br.status
                FROM borrow_request br
                JOIN user_login u ON br.user_id = u.user_id
                JOIN equipment_inventory ei ON br.equipment_id = ei.equipment_id
            """)
        rows = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
    return rows


def update_borrow_status(request_id, status):
    # status: approved or denied
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE borrow_request SET status=%s WHERE request_id=%s", (status, request_id))
        # If approved, decrease equipment quantity
        if status == 'approved':
            cursor.execute("SELECT equipment_id FROM borrow_request WHERE request_id=%s", (request_id,))
            eid = cursor.fetchone()[0]
            cursor.execute("UPDATE equipment_inventory SET quantity_available = quantity_available - 1 WHERE equipment_id=%s AND quantity_available>0", (eid,))
        conn.commit()
    finally:
        cursor.close()
        conn.close()
    return True


def list_current_borrows():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT br.request_id, br.user_id, u.username, br.equipment_id, ei.equipment_name, br.borrow_date
            FROM borrow_request br
            JOIN user_login u ON br.user_id = u.user_id
            JOIN equipment_inventory ei ON br.equipment_id = ei.equipment_id
            WHERE br.status = 'approved'
        """)
        rows = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
    return rows


def ensure_borrow_history_table():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS borrow_history (
                    history_id INT AUTO_INCREMENT PRIMARY KEY,
                    request_id INT,
                    user_id INT,
                    equipment_id INT,
                    borrow_date DATETIME,
                    return_date DATETIME
                )
            ''')
        except Exception:
            # Ignore any race condition where the table was created concurrently
            # (CREATE TABLE IF NOT EXISTS should be safe, but older servers or
            # concurrent DDL can still surface errors). If the table exists, continue.
            pass
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def insert_into_history(request_id, user_id, equipment_id, borrow_date, return_date):
    ensure_borrow_history_table()
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO borrow_history (request_id, user_id, equipment_id, borrow_date, return_date) VALUES (%s,%s,%s,%s,%s)",
                       (request_id, user_id, equipment_id, borrow_date, return_date))
        conn.commit()
        hid = cursor.lastrowid
    finally:
        cursor.close()
        conn.close()
    return hid


def list_borrow_history():
    # return richer rows joined with user and equipment names
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT bh.history_id, bh.request_id, bh.user_id, u.username, bh.equipment_id, ei.equipment_name, bh.borrow_date, bh.return_date
            FROM borrow_history bh
            LEFT JOIN user_login u ON bh.user_id = u.user_id
            LEFT JOIN equipment_inventory ei ON bh.equipment_id = ei.equipment_id
            ORDER BY bh.return_date DESC
        """)
        rows = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
    return rows
