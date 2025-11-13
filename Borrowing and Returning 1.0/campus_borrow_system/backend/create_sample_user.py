from backend.auth import create_user

def create_sample():
    username = 'student1@college.edu'
    password = 'StudentPass123'
    uid = create_user(username, password, role='user')
    print(f'Created sample user: {username} (id={uid})')

if __name__ == '__main__':
    create_sample()
