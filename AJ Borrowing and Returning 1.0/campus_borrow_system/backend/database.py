import os
import json
import mysql.connector
from mysql.connector import errorcode

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'db_config.json')


def load_config():
    # Load DB config from file or use defaults
    # Priority: environment variables > file config > defaults
    env_host = os.environ.get('DB_HOST')
    env_user = os.environ.get('DB_USER')
    env_password = os.environ.get('DB_PASSWORD')
    env_database = os.environ.get('DB_NAME') or os.environ.get('DB_DATABASE')

    if env_host or env_user or env_password or env_database:
        return {
            'host': env_host or '127.0.0.1',
            'user': env_user or 'root',
            'password': env_password or '',
            'database': env_database or 'campus_borrowing_system',
            'raise_on_warnings': True,
        }

    if os.path.exists(CONFIG_PATH):
        # read with utf-8-sig to tolerate a BOM written by some editors/powershell
        with open(CONFIG_PATH, 'r', encoding='utf-8-sig') as f:
            return json.load(f)

    # Defaults - expect the user to edit or provide env-specific config
    return {
        'host': '127.0.0.1',
        'user': 'root',
        'password': '',
        'database': 'campus_borrowing_system',
        'raise_on_warnings': True,
    }


def get_connection():
    cfg = load_config()
    conn = mysql.connector.connect(**cfg)
    return conn


def init_db(schema_sql_path=None):
    """Creates the database and tables from a schema SQL file.
    Use with care — this will attempt to create the configured database.
    """
    cfg = load_config()
    host = cfg.get('host', '127.0.0.1')
    user = cfg.get('user', 'root')
    password = cfg.get('password', '')
    dbname = cfg.get('database', 'campus_borrow_system')

    conn = mysql.connector.connect(host=host, user=user, password=password)
    cursor = conn.cursor()
    try:
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{dbname}` DEFAULT CHARACTER SET 'utf8mb4'")
        conn.database = dbname
    except mysql.connector.Error as err:
        print('Failed creating database:', err)
        raise

    if schema_sql_path is None:
        schema_sql_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'schema.sql')
    schema_sql_path = os.path.abspath(schema_sql_path)
    if not os.path.exists(schema_sql_path):
        print('schema.sql not found at', schema_sql_path)
        return

    with open(schema_sql_path, 'r', encoding='utf-8-sig') as f:
        sql = f.read()

    # Split by ; to run statements. This is simplistic but okay for initial setup.
    statements = [s.strip() for s in sql.split(';') if s.strip()]
    for stmt in statements:
        try:
            cursor.execute(stmt)
        except mysql.connector.Error as err:
            print('Error executing statement:', err)

    conn.commit()
    cursor.close()
    conn.close()
