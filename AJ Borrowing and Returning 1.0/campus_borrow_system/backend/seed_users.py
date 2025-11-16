"""Seed a few users into the database using the project's create_user helper.

This ensures passwords are hashed the same way the application expects.

Usage (from project root):
  python -m backend.seed_users
"""
from backend.auth import create_user

USERS = [
    {'username': 'student1@college.edu', 'password': 'StudentPass123', 'role': 'user'},
    {'username': 'student2@college.edu', 'password': 'StudentPass123', 'role': 'user'},
    {'username': 'staff1@college.edu', 'password': 'StaffPass123', 'role': 'user'},
    {'username': 'admin', 'password': 'AdminPass123', 'role': 'admin'},
]

def seed():
    for u in USERS:
        uid = create_user(u['username'], u['password'], role=u.get('role', 'user'))
        print(f"Created or found user: {u['username']} (id={uid})")

if __name__ == '__main__':
    seed()
