from backend.database import get_connection

conn = get_connection()
cur = conn.cursor()
try:
    cur.execute("SELECT COLUMN_NAME FROM information_schema.columns WHERE table_schema = DATABASE() AND table_name='borrow_request' AND column_name IN ('expected_return_date','quantity_requested')")
    rows = cur.fetchall()
    found = {r[0] for r in rows}
    print('found_columns:', found)
    # Also list sample approved borrow rows
    cur.execute("SELECT request_id, borrow_date, expected_return_date, quantity_requested FROM borrow_request WHERE status='approved' ORDER BY borrow_date DESC LIMIT 10")
    samples = cur.fetchall()
    print('approved samples:')
    for s in samples:
        print(s)
finally:
    cur.close()
    conn.close()
