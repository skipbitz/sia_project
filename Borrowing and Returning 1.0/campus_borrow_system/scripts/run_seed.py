"""Run the repository's seed_users.seed() function to insert users into the DB.

This is a convenience wrapper so you don't need to run SQL manually.
Usage:
  python .\scripts\run_seed.py
"""
import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend import seed_users

def main():
    print('Running backend.seed_users.seed()...')
    try:
        seed_users.seed()
        print('Seeding complete.')
    except Exception as e:
        print('Error while seeding:', e)
        raise

if __name__ == '__main__':
    main()
