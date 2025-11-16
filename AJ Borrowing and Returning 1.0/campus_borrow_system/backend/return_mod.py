from backend.database import get_connection
import datetime


def create_return_request(borrow_id):
    return create_return_request_with_condition(borrow_id, condition=None)


def create_return_request_with_condition(borrow_id, condition=None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        now = datetime.datetime.now()
        # If the return_request table has a 'condition' column, include it
        try:
            cursor.execute("SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = DATABASE() AND table_name='return_request' AND column_name='condition'")
            has_condition = cursor.fetchone()[0] > 0
        except Exception:
            has_condition = False

        if has_condition:
            cursor.execute("INSERT INTO return_request (borrow_id, return_date, status, `condition`) VALUES (%s,%s,%s,%s)",
                           (borrow_id, now, 'pending', condition))
        else:
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
                SELECT rr.return_id, rr.borrow_id, rr.return_date, rr.status, rr.`condition`,
                       br.user_id, u.username, br.equipment_id, ei.equipment_name
                FROM return_request rr
                JOIN borrow_request br ON rr.borrow_id = br.request_id
                JOIN user_login u ON br.user_id = u.user_id
                JOIN equipment_inventory ei ON br.equipment_id = ei.equipment_id
                WHERE br.user_id = %s
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT rr.return_id, rr.borrow_id, rr.return_date, rr.status, rr.`condition`,
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
        cursor.execute("SELECT return_id, borrow_id, status, `condition` FROM return_request WHERE return_id=%s", (return_id,))
        rr = cursor.fetchone()
        if not rr:
            return False
        # rr may be a tuple; unpack safely
        try:
            _rid, borrow_id, r_status, r_condition = rr
        except Exception:
            # fallback: no condition available
            _rid, borrow_id, r_status = rr[0], rr[1], rr[2]
            r_condition = None

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

        # increase equipment quantity only if returned item is in good condition
        inc_ok = True
        if r_condition is not None:
            cand = str(r_condition).lower()
            if cand not in ('good', 'ok', 'excellent', 'usable'):
                inc_ok = False
        if inc_ok:
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


def ensure_return_request_columns():
    """Add optional columns to return_request if they don't exist (idempotent)."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        try:
            cursor.execute("ALTER TABLE return_request ADD COLUMN `condition` VARCHAR(50) NULL")
        except Exception:
            pass
        conn.commit()
    finally:
        cursor.close()
        conn.close()
