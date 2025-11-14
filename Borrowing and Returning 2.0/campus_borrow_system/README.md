Campus Borrowing & Returning System (Vanilla Python + MySQL)

Overview
--------
This is a minimal campus equipment borrowing and returning system built with:
- Backend: Vanilla Python using http.server, urllib, json, mysql.connector
- Frontend: Plain HTML/CSS/JS (fetch API)
- Database: MySQL (schema provided)

Quick start (Windows PowerShell)
--------------------------------
1. Install Python (3.8+ recommended) and pip.
2. Install MySQL and create a user with privileges.
3. Install the MySQL connector for Python:

```powershell
pip install mysql-connector-python
```

4. Edit `backend/db_config.json` and set your DB credentials (host, user, password). The default database name is `campus_borrow_system`.
5. Initialize the database schema (from the project root):

```powershell
python -c "from backend.database import init_db; init_db()"
```

This will create the database and tables and insert sample equipment rows.

6. Run the server:

```powershell
python backend/server.py
```

7. Open a browser to http://127.0.0.1:8000

Usage notes
-----------
- Create users via the Register flow on the site (it hashes passwords).
- To create an admin: register a user, then update their role directly in the DB:

```sql
UPDATE user_login SET role='admin' WHERE username='your_admin_username';
```

API endpoints
-------------
The server exposes REST-like endpoints under `/api/` for equipment, borrow, return, login, logout, register, and session checks.

Files added/changed
- backend/: server.py, database.py, auth.py, equipment.py, borrow.py, return_mod.py, utils.py, db_config.json
- frontend/: index.html, login.html, dashboard_user.html, dashboard_admin.html, css/style.css, js/*.js
- database/schema.sql

Limitations & next steps
------------------------
- Sessions are stored in memory; for production use a persistent store (Redis) or signed cookies.
- Input validation is minimal; sanitize/validate more strictly for production.
- Consider adding CSRF protection and HTTPS.
