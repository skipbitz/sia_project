import sys
sys.path.insert(0, r'c:/Users/Pee Jay/Documents/1 PROJECT/pj/campus_borrow_system')
from backend.database import get_connection
conn = get_connection()
cur = conn.cursor()
print('borrow_request:')
cur.execute('SELECT request_id, user_id, equipment_id, borrow_date, status FROM borrow_request')
for r in cur.fetchall():
    print(r)
print('\nreturn_request:')
cur.execute('SELECT return_id, borrow_id, return_date, status FROM return_request')
for r in cur.fetchall():
    print(r)
print('\nborrow_history:')
try:
    cur.execute('SELECT history_id, request_id, user_id, equipment_id, borrow_date, return_date FROM borrow_history')
    for r in cur.fetchall():
        print(r)
except Exception as e:
    print('history error', e)
cur.close(); conn.close()
