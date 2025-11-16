from backend.database import get_connection
import datetime


def create_borrow_request(user_id, equipment_id, borrow_date=None, quantity_requested=1, expected_return_date=None, reason=None):
    """
    Create a borrow request. If borrow_date is provided (string or datetime), use it,
    otherwise use current datetime. Additional fields such as quantity or expected
    return_date are currently accepted by the frontend but not stored in the current
    schema; they can be added later if desired.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if borrow_date:
            if isinstance(borrow_date, str):
                try:
                    borrow_dt = datetime.datetime.fromisoformat(borrow_date)
                except Exception:
                    borrow_dt = datetime.datetime.now()
            elif isinstance(borrow_date, datetime.datetime):
                borrow_dt = borrow_date
            else:
                borrow_dt = datetime.datetime.now()
        else:
            borrow_dt = datetime.datetime.now()

        # Try to include optional fields if the columns exist
        try:
            # check for expected_return_date and quantity_requested columns
            cursor.execute("SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = DATABASE() AND table_name='borrow_request' AND column_name='expected_return_date'")
            has_return = cursor.fetchone()[0] > 0
            cursor.execute("SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = DATABASE() AND table_name='borrow_request' AND column_name='quantity_requested'")
            has_qty = cursor.fetchone()[0] > 0
        except Exception:
            has_return = False
            has_qty = False

        if has_return or has_qty:
            # Also check for optional 'reason' column so users can describe why they borrow
            cursor.execute("SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = DATABASE() AND table_name='borrow_request' AND column_name='reason'")
            has_reason = cursor.fetchone()[0] > 0

            cols = ['user_id','equipment_id','borrow_date','status']
            vals = [user_id, equipment_id, borrow_dt, 'pending']
            if has_qty:
                cols.append('quantity_requested')
                vals.append(int(quantity_requested or 1))
            if has_return:
                # parse expected_return_date if provided
                ert = None
                if expected_return_date:
                    if isinstance(expected_return_date, str):
                        try:
                            ert = datetime.datetime.fromisoformat(expected_return_date)
                        except Exception:
                            # try replacing T with space
                            try:
                                ert = datetime.datetime.fromisoformat(expected_return_date.replace('T', ' '))
                            except Exception:
                                ert = None
                    elif isinstance(expected_return_date, datetime.datetime):
                        ert = expected_return_date
                cols.append('expected_return_date')
                vals.append(ert)
            # If caller provided a reason and the column exists, include it.
            # We'll accept a value passed via a keyword argument 'reason' from the API layer.
            # The function signature doesn't include reason to preserve back-compat, so
            # attempt to read it from locals() or kwargs via a fallback on the caller.
            try:
                reason_val = locals().get('reason')
            except Exception:
                reason_val = None
            if has_reason and reason_val is not None:
                cols.append('reason')
                vals.append(reason_val)

            sql = f"INSERT INTO borrow_request ({', '.join(cols)}) VALUES ({', '.join(['%s']*len(vals))})"
            cursor.execute(sql, tuple(vals))
        else:
            # fallback simple insert — include reason if column exists
            try:
                cursor.execute("SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = DATABASE() AND table_name='borrow_request' AND column_name='reason'")
                has_reason_simple = cursor.fetchone()[0] > 0
            except Exception:
                has_reason_simple = False
            if has_reason_simple:
                try:
                    reason_val = locals().get('reason')
                except Exception:
                    reason_val = None
                cursor.execute("INSERT INTO borrow_request (user_id, equipment_id, borrow_date, status, reason) VALUES (%s,%s,%s,%s,%s)",
                               (user_id, equipment_id, borrow_dt, 'pending', reason_val))
            else:
                cursor.execute("INSERT INTO borrow_request (user_id, equipment_id, borrow_date, status) VALUES (%s,%s,%s,%s)",
                               (user_id, equipment_id, borrow_dt, 'pending'))

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
                SELECT br.request_id, br.user_id, u.username, br.equipment_id, ei.equipment_name, br.borrow_date, br.status, br.reason
                FROM borrow_request br
                JOIN user_login u ON br.user_id = u.user_id
                JOIN equipment_inventory ei ON br.equipment_id = ei.equipment_id
                WHERE br.user_id = %s
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT br.request_id, br.user_id, u.username, br.equipment_id, ei.equipment_name, br.borrow_date, br.status, br.reason
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
        # Read current status and related info so we can adjust inventory when status changes
        prev_status = None
        eid = None
        qty = 1
        try:
            # Try to include quantity_requested if available
            cursor.execute("SELECT br.status, br.equipment_id, COALESCE(br.quantity_requested,1) FROM borrow_request br WHERE br.request_id=%s", (request_id,))
            row = cursor.fetchone()
            if row:
                prev_status, eid, qty = row[0], row[1], int(row[2] or 1)
        except Exception:
            # Fallback to selecting without quantity_requested
            try:
                cursor.execute("SELECT status, equipment_id FROM borrow_request WHERE request_id=%s", (request_id,))
                row = cursor.fetchone()
                if row:
                    prev_status, eid = row[0], row[1]
                    qty = 1
            except Exception:
                prev_status, eid, qty = None, None, 1

        # Update the status
        cursor.execute("UPDATE borrow_request SET status=%s WHERE request_id=%s", (status, request_id))

        # If moving from approved -> not-approved, restore inventory
        if prev_status == 'approved' and status != 'approved' and eid is not None and qty > 0:
            cursor.execute("UPDATE equipment_inventory SET quantity_available = quantity_available + %s WHERE equipment_id=%s", (qty, eid))

        # If moving from not-approved -> approved, reduce inventory
        if prev_status != 'approved' and status == 'approved' and eid is not None and qty > 0:
            cursor.execute("UPDATE equipment_inventory SET quantity_available = quantity_available - %s WHERE equipment_id=%s AND quantity_available>0", (qty, eid))
        conn.commit()
    finally:
        cursor.close()
        conn.close()
    return True


def list_current_borrows():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Prefer to return the expected_return_date when possible. Try the richer SELECT
        # first and fall back to a narrower SELECT if the column does not exist or the
        # query fails for any reason. This makes the API more robust across schema
        # versions and avoids relying solely on information_schema checks which may
        # behave differently across environments.
        try:
            cursor.execute("""
                SELECT br.request_id, br.user_id, u.username, br.equipment_id, ei.equipment_name, br.borrow_date, br.expected_return_date, br.reason
                FROM borrow_request br
                JOIN user_login u ON br.user_id = u.user_id
                JOIN equipment_inventory ei ON br.equipment_id = ei.equipment_id
                WHERE br.status = 'approved'
            """)
        except Exception:
            # Fallback when expected_return_date column is missing or inaccessible
            cursor.execute("""
                SELECT br.request_id, br.user_id, u.username, br.equipment_id, ei.equipment_name, br.borrow_date, br.reason
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


def list_recent_borrows(limit=5, user_id=None):
    """Return the most recent borrow requests (any status), joined with user and equipment names.
    If user_id is provided, only return rows for that user."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if user_id is not None:
            cursor.execute("""
                SELECT br.request_id, br.user_id, u.username, br.equipment_id, ei.equipment_name, br.borrow_date, br.status, br.reason
                FROM borrow_request br
                LEFT JOIN user_login u ON br.user_id = u.user_id
                LEFT JOIN equipment_inventory ei ON br.equipment_id = ei.equipment_id
                WHERE br.user_id = %s
                ORDER BY br.borrow_date DESC
                LIMIT %s
            """, (user_id, limit))
        else:
            cursor.execute("""
                SELECT br.request_id, br.user_id, u.username, br.equipment_id, ei.equipment_name, br.borrow_date, br.status, br.reason
                FROM borrow_request br
                LEFT JOIN user_login u ON br.user_id = u.user_id
                LEFT JOIN equipment_inventory ei ON br.equipment_id = ei.equipment_id
                ORDER BY br.borrow_date DESC
                LIMIT %s
            """, (limit,))
        rows = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
    return rows


def get_most_borrowed(limit=1):
    """Return equipment items ordered by number of borrow requests (most borrowed first)."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        # Count borrow_request rows grouped by equipment
        cursor.execute("""
            SELECT ei.equipment_id, ei.equipment_name, COUNT(*) AS borrow_count
            FROM borrow_request br
            JOIN equipment_inventory ei ON br.equipment_id = ei.equipment_id
            GROUP BY ei.equipment_id, ei.equipment_name
            ORDER BY borrow_count DESC
            LIMIT %s
        """, (limit,))
        rows = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
    return rows


def ensure_borrow_request_columns():
    """Add optional columns to borrow_request if they don't exist (idempotent)."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        try:
            cursor.execute("ALTER TABLE borrow_request ADD COLUMN quantity_requested INT DEFAULT 1")
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE borrow_request ADD COLUMN expected_return_date DATETIME NULL")
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE borrow_request ADD COLUMN reason TEXT NULL")
        except Exception:
            pass
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def delete_borrow_request(request_id):
    """Delete a borrow_request row by id. Returns True on success."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM borrow_request WHERE request_id=%s", (request_id,))
        conn.commit()
    finally:
        cursor.close()
        conn.close()
    return True


def update_borrow_request(request_id, borrow_date=None, expected_return_date=None, quantity_requested=None):
    """Update borrow_request fields (non-status fields)."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        updates = []
        vals = []
        if borrow_date is not None:
            bd = None
            if isinstance(borrow_date, str):
                try:
                    bd = datetime.datetime.fromisoformat(borrow_date)
                except Exception:
                    try:
                        bd = datetime.datetime.fromisoformat(borrow_date.replace('T', ' '))
                    except Exception:
                        bd = None
            elif isinstance(borrow_date, datetime.datetime):
                bd = borrow_date
            if bd is not None:
                updates.append('borrow_date=%s')
                vals.append(bd)
        if expected_return_date is not None:
            ert = None
            if isinstance(expected_return_date, str):
                try:
                    ert = datetime.datetime.fromisoformat(expected_return_date)
                except Exception:
                    try:
                        ert = datetime.datetime.fromisoformat(expected_return_date.replace('T', ' '))
                    except Exception:
                        ert = None
            elif isinstance(expected_return_date, datetime.datetime):
                ert = expected_return_date
            updates.append('expected_return_date=%s')
            vals.append(ert)
        if quantity_requested is not None:
            try:
                q = int(quantity_requested)
            except Exception:
                q = None
            if q is not None:
                updates.append('quantity_requested=%s')
                vals.append(q)

        if not updates:
            return False

        sql = f"UPDATE borrow_request SET {', '.join(updates)} WHERE request_id=%s"
        vals.append(request_id)
        cursor.execute(sql, tuple(vals))
        conn.commit()
    finally:
        cursor.close()
        conn.close()
    return True
