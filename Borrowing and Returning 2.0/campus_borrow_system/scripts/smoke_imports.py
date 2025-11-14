"""Quick smoke-test that imports backend modules without starting the HTTP server.

Run this when starting the full server is slow or 'too long to load' — it verifies imports and common errors quickly.
"""
import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

MODULES = [
    'backend.database',
    'backend.utils',
    'backend.auth',
    'backend.equipment',
    'backend.borrow',
    'backend.return_mod',
    'backend.server',
]

def main():
    ok = True
    for m in MODULES:
        try:
            __import__(m)
            print(f"OK: imported {m}")
        except Exception as e:
            print(f"FAIL: importing {m}: {e}")
            ok = False
    if ok:
        print("\nSmoke test passed: imports OK. This does NOT start the HTTP server.")
        return 0
    else:
        print("\nSmoke test failed: fix import errors above.")
        return 2

if __name__ == '__main__':
    sys.exit(main())
