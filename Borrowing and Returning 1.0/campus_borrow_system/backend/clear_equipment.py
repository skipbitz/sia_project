"""Clear equipment_inventory table.

Usage: from project root
  python -m backend.clear_equipment

This will DELETE all rows from equipment_inventory. Use with care.
"""
from backend.database import get_connection

def clear_equipment():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute('DELETE FROM equipment_inventory')
        conn.commit()
        print('Cleared equipment_inventory table')
    finally:
        cur.close()
        conn.close()

if __name__ == '__main__':
    clear_equipment()
