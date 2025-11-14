import sys
sys.path.insert(0, r'c:/Users/Pee Jay/Documents/1 PROJECT/pj/campus_borrow_system')
from backend.database import get_connection
from backend.return_mod import approve_return

conn = get_connection()
cur = conn.cursor()
cur.execute("SELECT return_id FROM return_request WHERE status='approved'")
rows = cur.fetchall()
print('approved return_ids:', rows)
processed = 0
for r in rows:
    rid = r[0]
    ok = approve_return(rid)
    print('processed', rid, ok)
    processed += 1
cur.close(); conn.close()
print('done')
