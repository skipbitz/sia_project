"""Generate SQL INSERT statements for seed users with correctly hashed passwords.

This script does not require a DB connection. It uses the same hashing
scheme as `backend/auth.py` (salt$sha256(salt+password)).

Usage (from project root):
  python .\scripts\generate_seed_sql.py > seed_users.sql

Then review `seed_users.sql` and apply it with your MySQL client.
"""
import os
import hashlib

def hash_password(password, salt=None):
    if salt is None:
        salt = os.urandom(16).hex()
    h = hashlib.sha256((salt + password).encode('utf-8')).hexdigest()
    return f"{salt}${h}"

SEED_USERS = [
    {'username': 'student1@college.edu', 'password': 'StudentPass123', 'role': 'user'},
    {'username': 'student2@college.edu', 'password': 'StudentPass123', 'role': 'user'},
    {'username': 'staff1@college.edu', 'password': 'StaffPass123', 'role': 'user'},
    {'username': 'admin', 'password': 'AdminPass123', 'role': 'admin'},
]

def main():
    print('-- Generated INSERT statements for user_login')
    for u in SEED_USERS:
        pw_hash = hash_password(u['password'])
        # escape single quotes in username
        username = u['username'].replace("'", "''")
        role = u['role']
        print(f"INSERT INTO user_login (username, password, role) VALUES ('{username}', '{pw_hash}', '{role}');")

if __name__ == '__main__':
    main()
