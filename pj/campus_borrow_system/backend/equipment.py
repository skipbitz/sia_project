from backend.database import get_connection


def list_equipment(category=None):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        if category:
            cursor.execute("SELECT * FROM equipment_inventory WHERE category=%s", (category,))
        else:
            cursor.execute("SELECT * FROM equipment_inventory")
        rows = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
    return rows


def add_equipment(name, category, quantity, status='available'):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO equipment_inventory (equipment_name, category, quantity_available, status) VALUES (%s,%s,%s,%s)",
                       (name, category, quantity, status))
        conn.commit()
        eid = cursor.lastrowid
    finally:
        cursor.close()
        conn.close()
    return eid


def update_equipment(equipment_id, **fields):
    allowed = ['equipment_name', 'category', 'quantity_available', 'status']
    set_parts = []
    values = []
    for k, v in fields.items():
        if k in allowed:
            set_parts.append(f"{k}=%s")
            values.append(v)
    if not set_parts:
        return False
    values.append(equipment_id)
    sql = f"UPDATE equipment_inventory SET {', '.join(set_parts)} WHERE equipment_id=%s"
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(sql, tuple(values))
        conn.commit()
    finally:
        cursor.close()
        conn.close()
    return True


def delete_equipment(equipment_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM equipment_inventory WHERE equipment_id=%s", (equipment_id,))
        conn.commit()
    finally:
        cursor.close()
        conn.close()
    return True
