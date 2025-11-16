import sys
sys.path.insert(0, r'c:/Users/Pee Jay/Documents/1 PROJECT/pj/campus_borrow_system')
from backend import borrow
print('Testing borrow functions...')
print('current borrows:')
try:
    rows = borrow.list_current_borrows()
    print(rows)
except Exception as e:
    print('ERROR', e)
print('\nborrow history:')
try:
    rows = borrow.list_borrow_history()
    print(rows[:10])
except Exception as e:
    print('ERROR', e)
