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
        # fetch the return_request row
        cursor.execute("SELECT return_id, borrow_id, status FROM return_request WHERE return_id=%s", (return_id,))
        rr = cursor.fetchone()
        if not rr:
            return False
        _rid, borrow_id, r_status = rr

        # If history already contains this borrow (idempotent), nothing to do
        try:
            cursor.execute("SELECT 1 FROM borrow_history WHERE request_id=%s LIMIT 1", (borrow_id,))
            if cursor.fetchone():
                # ensure return_request is marked approved
                if r_status != 'approved':
                    cursor.execute("UPDATE return_request SET status='approved' WHERE return_id=%s", (return_id,))
                    conn.commit()
                return True
        except Exception:
            # maybe borrow_history doesn't exist yet; ignore and continue
            pass

        # fetch the borrow_request row
        cursor.execute("SELECT request_id, user_id, equipment_id, borrow_date, status FROM borrow_request WHERE request_id=%s", (borrow_id,))
        row2 = cursor.fetchone()
        if not row2:
            # borrow row missing; still mark return as approved and return
            cursor.execute("UPDATE return_request SET status='approved' WHERE return_id=%s", (return_id,))
            conn.commit()
            return True

        req_id, user_id, eid, borrow_date, br_status = row2

        # increase equipment quantity
        cursor.execute("UPDATE equipment_inventory SET quantity_available = quantity_available + 1 WHERE equipment_id=%s", (eid,))

        # mark return approved
        cursor.execute("UPDATE return_request SET status='approved' WHERE return_id=%s", (return_id,))

        # ensure history table exists (use safe creation)
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
            # ignore DDL races
            pass

        now = datetime.datetime.now()
        cursor.execute("INSERT INTO borrow_history (request_id, user_id, equipment_id, borrow_date, return_date) VALUES (%s,%s,%s,%s,%s)",
                       (req_id, user_id, eid, borrow_date, now))

        # delete the borrow_request row
        cursor.execute("DELETE FROM borrow_request WHERE request_id=%s", (borrow_id,))

        conn.commit()
        return True
    except Exception:
        # log and return False on unexpected errors
        try:
            import traceback
            print('[error] approve_return exception:', traceback.format_exc())
        except Exception:
            pass
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        cursor.close()
        conn.close()
