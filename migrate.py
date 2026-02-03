import os
import sqlite3
import pymysql
import ssl
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

MYSQL_URL = os.getenv('MYSQL_URL')
SQLITE_DB = 'ledger.db'

def get_mysql_connection():
    if not MYSQL_URL:
        print("Error: MYSQL_URL not found in .env")
        return None
    
    try:
        p = urlparse(MYSQL_URL)
        qs = parse_qs(p.query)
        
        connect_args = {
            'host': p.hostname,
            'user': p.username,
            'password': p.password,
            'database': p.path.lstrip('/'),
            'port': p.port or 3306,
            'autocommit': True,
            'cursorclass': pymysql.cursors.DictCursor
        }
        
        if 'ssl-mode' in qs and qs['ssl-mode'][0].upper() == 'REQUIRED':
            connect_args['ssl'] = ssl.create_default_context()
            
        return pymysql.connect(**connect_args)
    except Exception as e:
        print(f"Failed to connect to MySQL: {e}")
        return None

def migrate_data():
    if not os.path.exists(SQLITE_DB):
        print(f"Error: {SQLITE_DB} not found.")
        return

    print("Connecting to MySQL...")
    mysql_conn = get_mysql_connection()
    if not mysql_conn:
        return

    print("Initializing schema in MySQL...")
    # Import here to avoid early side effects, assuming app.py handles init_db logic for MySQL
    try:
        from app import init_db
        # Ensure app thinks we are using MySQL
        import app as app_module
        app_module.MYSQL_URL = MYSQL_URL 
        init_db()
    except Exception as e:
        print(f"Error initializing schema: {e}")
        return

    print("Connecting to SQLite...")
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()
    
    mysql_cur = mysql_conn.cursor()

    # Tables to migrate in order (to respect foreign keys if we were checking them, 
    # but we will disable FK checks)
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
        # Disable FK checks
        mysql_cur.execute("SET FOREIGN_KEY_CHECKS = 0")
        
        for table in tables:
            print(f"Migrating table: {table}...")
            
            # Check if table exists in SQLite
            try:
                sqlite_cur.execute(f"SELECT * FROM {table}")
            except sqlite3.OperationalError:
                print(f"  Skipping {table} (not found in SQLite)")
                continue
                
            rows = sqlite_cur.fetchall()
            if not rows:
                print(f"  No data in {table}")
                continue
                
            # Get column names
            columns = rows[0].keys()
            col_str = ", ".join(columns)
            placeholders = ", ".join(["%s"] * len(columns))
            
            # Prepare INSERT query
            insert_sql = f"INSERT INTO {table} ({col_str}) VALUES ({placeholders})"
            
            # Insert data
            data_to_insert = [tuple(row) for row in rows]
            
            # Use REPLACE INTO or INSERT IGNORE to avoid duplicates if running multiple times?
            # Or just TRUNCATE first?
            # Let's TRUNCATE first to ensure clean state
            print(f"  Truncating {table} in MySQL...")
            try:
                mysql_cur.execute(f"TRUNCATE TABLE {table}")
            except Exception as e:
                print(f"  Warning: Could not truncate {table}: {e}")

            print(f"  Inserting {len(data_to_insert)} rows...")
            # Batch insert
            batch_size = 1000
            for i in range(0, len(data_to_insert), batch_size):
                batch = data_to_insert[i:i+batch_size]
                try:
                    mysql_cur.executemany(insert_sql, batch)
                    mysql_conn.commit()
                except Exception as e:
                    print(f"  Error inserting batch into {table}: {e}")
            
        # Re-enable FK checks
        mysql_cur.execute("SET FOREIGN_KEY_CHECKS = 1")
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        sqlite_conn.close()
        mysql_conn.close()

if __name__ == "__main__":
    migrate_data()
