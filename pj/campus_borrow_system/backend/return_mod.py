from backend.database import get_connection
import datetime


def create_return_request(borrow_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        now = datetime.datetime.now()
        cursor.execute("INSERT INTO return_request (borrow_id, return_date, status) VALUES (%s,%s,%s)",
                       (borrow_id, now, 'pending'))
        conn.commit()
        rid = cursor.lastrowid
    finally:
        cursor.close()
        conn.close()
    return rid


def list_return_requests(user_id=None):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if user_id:
            # return richer rows joined with borrow_request, user and equipment
            cursor.execute("""
                SELECT rr.return_id, rr.borrow_id, rr.return_date, rr.status,
                       br.user_id, u.username, br.equipment_id, ei.equipment_name
                FROM return_request rr
                JOIN borrow_request br ON rr.borrow_id = br.request_id
                JOIN user_login u ON br.user_id = u.user_id
                JOIN equipment_inventory ei ON br.equipment_id = ei.equipment_id
                WHERE br.user_id = %s
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT rr.return_id, rr.borrow_id, rr.return_date, rr.status,
                       br.user_id, u.username, br.equipment_id, ei.equipment_name
                FROM return_request rr
                JOIN borrow_request br ON rr.borrow_id = br.request_id
                JOIN user_login u ON br.user_id = u.user_id
                JOIN equipment_inventory ei ON br.equipment_id = ei.equipment_id
            """)
        rows = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
    return rows


def approve_return(return_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # find borrow_id
        cursor.execute("SELECT borrow_id FROM return_request WHERE return_id=%s", (return_id,))
        row = cursor.fetchone()
        if not row:
            return False
        borrow_id = row[0]
        # find equipment_id from borrow_request
        cursor.execute("SELECT equipment_id FROM borrow_request WHERE request_id=%s", (borrow_id,))
        row2 = cursor.fetchone()
        if not row2:
            return False
        eid = row2[0]
        # increase equipment quantity
        cursor.execute("UPDATE equipment_inventory SET quantity_available = quantity_available + 1 WHERE equipment_id=%s", (eid,))
        # mark return approved
        cursor.execute("UPDATE return_request SET status='approved' WHERE return_id=%s", (return_id,))
        # also mark borrow_request as returned/approved (optional)
        cursor.execute("UPDATE borrow_request SET status='approved' WHERE request_id=%s", (borrow_id,))
        conn.commit()
    finally:
        cursor.close()
        conn.close()
    return True
