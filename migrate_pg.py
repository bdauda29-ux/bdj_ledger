
import os
import sqlite3
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Prefer non-pooling URL for migration/DDL if available
POSTGRES_URL = os.getenv('POSTGRES_URL_NON_POOLING') or os.getenv('POSTGRES_URL')
SQLITE_DB = 'ledger.db'

def migrate_data():
    if not POSTGRES_URL:
        print("Error: POSTGRES_URL not found in .env")
        return

    if not os.path.exists(SQLITE_DB):
        print(f"Error: {SQLITE_DB} not found.")
        return

    print("Connecting to PostgreSQL...")
    try:
        pg_conn = psycopg2.connect(POSTGRES_URL)
        pg_conn.autocommit = True
    except Exception as e:
        print(f"Failed to connect to PostgreSQL: {e}")
        return

    print("Initializing schema in PostgreSQL...")
    try:
        # Import app to use its init_db logic
        # We need to mock the environment variable so app.py picks up the Postgres URL
        # But app.py reads os.environ at module level, so we might need to reload or set env before import
        # However, we can just manually run the init_db logic or assume app.py works if we set the var
        
        # Better approach: Just use app.init_db if possible, but app.py initializes variables at top level.
        # Let's set the env var in os.environ before importing app
        os.environ['POSTGRES_URL'] = POSTGRES_URL
        
        # We also need to handle the case where app is already imported (unlikely in script)
        import app
        # Force re-check
        app.POSTGRES_URL = POSTGRES_URL
        app.init_db()
        print("Schema initialized.")
    except Exception as e:
        print(f"Error initializing schema: {e}")
        # Continue anyway? No, schema is needed.
        return

    print("Connecting to SQLite...")
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()
    
    pg_cur = pg_conn.cursor()

    # Table order respecting FKs
    tables = [
        'models', 
        'clients', 
        'countries', 
        'users', 
        'transactions', 
        'balance_history', 
        'deleted_transactions', 
        'wallet'
    ]

    try:
        for table in tables:
            print(f"Migrating table: {table}...")
            
            try:
                sqlite_cur.execute(f"SELECT * FROM {table}")
            except sqlite3.OperationalError:
                print(f"  Skipping {table} (not found in SQLite)")
                continue
                
            rows = sqlite_cur.fetchall()
            if not rows:
                print(f"  No data in {table}")
                continue
                
            columns = list(rows[0].keys())
            col_str = ", ".join(columns)
            
            # Prepare data
            data_to_insert = []
            for row in rows:
                data_to_insert.append(tuple(row))
            
            # TRUNCATE with CASCADE to handle FKs
            print(f"  Truncating {table} in PostgreSQL...")
            try:
                pg_cur.execute(f"TRUNCATE TABLE {table} CASCADE")
            except Exception as e:
                print(f"  Warning: Could not truncate {table}: {e}")

            print(f"  Inserting {len(data_to_insert)} rows...")
            
            # Use execute_values for efficient batch insert
            insert_sql = f"INSERT INTO {table} ({col_str}) VALUES %s"
            
            try:
                psycopg2.extras.execute_values(
                    pg_cur, 
                    insert_sql, 
                    data_to_insert,
                    page_size=1000
                )
            except Exception as e:
                print(f"  Error inserting into {table}: {e}")
                
            # Reset sequence
            try:
                # Assuming standard serial naming convention: tablename_id_seq
                # We need to check if the table has an 'id' column first
                if 'id' in columns:
                    pg_cur.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), coalesce(max(id)+1, 1), false) FROM {table}")
                    print(f"  Sequence reset for {table}")
            except Exception as e:
                # Might fail if no sequence or different name
                print(f"  Warning: Could not reset sequence for {table}: {e}")

        print("Migration completed successfully!")

    except Exception as e:
        print(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if sqlite_conn: sqlite_conn.close()
        if pg_conn: pg_conn.close()

if __name__ == "__main__":
    migrate_data()
