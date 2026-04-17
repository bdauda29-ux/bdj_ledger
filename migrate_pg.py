import os
import sqlite3
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
SQLITE_DB = 'ledger.db'
POSTGRES_URL = os.getenv('POSTGRES_URL')

def get_sqlite_connection():
    conn = sqlite3.connect(SQLITE_DB)
    conn.row_factory = sqlite3.Row
    return conn

def get_postgres_connection():
    if not POSTGRES_URL:
        print("Error: POSTGRES_URL not found in .env")
        return None
    try:
        conn = psycopg2.connect(POSTGRES_URL)
        conn.autocommit = True
        return conn
    except Exception as e:
        print(f"Error connecting to Postgres: {e}")
        return None

def init_schema(pg_conn):
    print("Initializing schema in Postgres...")
    cur = pg_conn.cursor()
    
    # Enable UUID extension if needed (not strictly needed here as we use SERIAL/INTEGER)
    
    # Drop tables to ensure clean state (optional, commented out for safety)
    # tables = ['balance_history', 'deleted_transactions', 'transactions', 'clients', 'countries', 'users', 'models', 'wallet']
    # for t in tables:
    #     cur.execute(f"DROP TABLE IF EXISTS {t} CASCADE")

    # 1. Models
    cur.execute('''
        CREATE TABLE IF NOT EXISTS models (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 2. Clients
    cur.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id SERIAL PRIMARY KEY,
            client_name TEXT NOT NULL,
            phone_number TEXT NOT NULL,
            balance REAL NOT NULL DEFAULT 0.0,
            model_id INTEGER
        )
    ''')
    cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_clients_unique ON clients(client_name, model_id)')

    # 3. Countries
    cur.execute('''
        CREATE TABLE IF NOT EXISTS countries (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            model_id INTEGER,
            continent TEXT
        )
    ''')
    cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_countries_unique ON countries(name, model_id)')

    # 4. Users
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            email TEXT,
            can_edit_client INTEGER DEFAULT 1,
            can_delete_client INTEGER DEFAULT 1,
            can_add_transaction INTEGER DEFAULT 1,
            can_edit_transaction INTEGER DEFAULT 1,
            can_delete_transaction INTEGER DEFAULT 1,
            can_view_clients INTEGER DEFAULT 1,
            is_admin INTEGER DEFAULT 1
        )
    ''')

    # 5. Transactions
    cur.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            client_name TEXT NOT NULL,
            email TEXT,
            service_type TEXT DEFAULT 'eVisa',
            applicant_name TEXT,
            app_id BIGINT NOT NULL,
            country_name TEXT NOT NULL,
            country_price REAL,
            rate REAL,
            addition REAL,
            amount REAL NOT NULL,
            amount_n REAL,
            transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted INTEGER DEFAULT 0,
            is_paid INTEGER DEFAULT 0,
            model_id INTEGER,
            email_link TEXT,
            created_by TEXT
        )
    ''')
    cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_transactions_app_unique ON transactions(app_id, model_id)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_transactions_client ON transactions(client_name)')

    # 6. Balance History
    cur.execute('''
        CREATE TABLE IF NOT EXISTS balance_history (
            id SERIAL PRIMARY KEY,
            client_id INTEGER NOT NULL,
            transaction_id INTEGER,
            amount REAL NOT NULL,
            type TEXT NOT NULL,
            balance_before REAL NOT NULL,
            balance_after REAL NOT NULL,
            description TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            model_id INTEGER
        )
    ''')

    # 7. Deleted Transactions
    cur.execute('''
        CREATE TABLE IF NOT EXISTS deleted_transactions (
            id SERIAL PRIMARY KEY,
            original_id INTEGER,
            client_name TEXT,
            email TEXT,
            service_type TEXT,
            applicant_name TEXT,
            app_id BIGINT,
            country_name TEXT,
            country_price REAL,
            rate REAL,
            addition REAL,
            amount REAL,
            amount_n REAL,
            is_paid INTEGER DEFAULT 0,
            transaction_date TIMESTAMP,
            deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            model_id INTEGER,
            email_link TEXT,
            created_by TEXT
        )
    ''')

    # 8. Wallet
    cur.execute('''
        CREATE TABLE IF NOT EXISTS wallet (
            id SERIAL PRIMARY KEY,
            dollars REAL DEFAULT 0,
            providus_dollars REAL DEFAULT 0,
            bybit_dollars REAL DEFAULT 0,
            naira REAL DEFAULT 0,
            naira_1 REAL DEFAULT 0,
            taj_naira REAL DEFAULT 0,
            debt REAL DEFAULT 0,
            rate REAL DEFAULT 0,
            model_id INTEGER
        )
    ''')
    cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_wallet_model ON wallet(model_id)')

    # 9. Assets
    cur.execute('''
        CREATE TABLE IF NOT EXISTS assets (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            amount REAL NOT NULL DEFAULT 0.0,
            type TEXT NOT NULL,
            currency TEXT NOT NULL,
            model_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS asset_history (
            id SERIAL PRIMARY KEY,
            asset_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            type TEXT NOT NULL,
            balance_before REAL NOT NULL,
            balance_after REAL NOT NULL,
            description TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            model_id INTEGER
        )
    ''')

    print("Schema initialized.")

def migrate_data():
    if not os.path.exists(SQLITE_DB):
        print(f"Error: {SQLITE_DB} not found.")
        return

    sqlite_conn = get_sqlite_connection()
    pg_conn = get_postgres_connection()

    if not pg_conn:
        return

    init_schema(pg_conn)

    tables = [
        'models',
        'users',
        'countries',
        'clients',
        'transactions',
        'balance_history',
        'deleted_transactions',
        'wallet',
        'assets'
    ]

    cur = pg_conn.cursor()

    for table in tables:
        print(f"Migrating {table}...")
        
        # Get data from SQLite
        try:
            rows = sqlite_conn.execute(f"SELECT * FROM {table}").fetchall()
        except sqlite3.OperationalError:
            print(f"Skipping {table} (not found in SQLite)")
            continue

        if not rows:
            continue

        # Get column names
        columns = rows[0].keys()
        placeholders = ','.join(['%s'] * len(columns))
        col_names = ','.join(columns)

        # Prepare data
        data = []
        for row in rows:
            data.append(tuple(row))

        # Insert into Postgres
        # We use ON CONFLICT DO NOTHING to avoid duplicates if running multiple times
        # For tables with unique constraints, this helps. For others, we might duplicate if not careful.
        # But for migration, assuming empty target is best.
        
        conflict_clause = ""
        if table == 'models':
            conflict_clause = "ON CONFLICT (name) DO NOTHING"
        elif table == 'users':
            conflict_clause = "ON CONFLICT (username) DO NOTHING"
        elif table == 'clients':
            conflict_clause = "ON CONFLICT (client_name, model_id) DO NOTHING"
        elif table == 'countries':
            conflict_clause = "ON CONFLICT (name, model_id) DO NOTHING"
        elif table == 'transactions':
            conflict_clause = "ON CONFLICT (app_id, model_id) DO NOTHING"
        elif table == 'wallet':
            conflict_clause = "ON CONFLICT (model_id) DO NOTHING"

        query = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders}) {conflict_clause}"
        
        try:
            psycopg2.extras.execute_batch(cur, query, data)
            print(f"Migrated {len(data)} rows to {table}.")
        except Exception as e:
            print(f"Error migrating {table}: {e}")

    pg_conn.commit()
    print("Migration completed successfully.")

if __name__ == '__main__':
    migrate_data()
