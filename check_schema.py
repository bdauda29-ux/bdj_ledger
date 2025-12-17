import sqlite3
import os
from app import app, init_db, get_db_connection

# Force init_db to run to make sure migrations are applied
with app.app_context():
    print("Running init_db()...")
    init_db()
    
    conn = get_db_connection()
    print("Checking transactions table schema...")
    try:
        # For SQLite
        cursor = conn.execute("PRAGMA table_info(transactions)")
        columns = [row['name'] for row in cursor.fetchall()]
        print("Columns:", columns)
        
        if 'email_link' in columns:
            print("SUCCESS: email_link column exists.")
        else:
            print("FAILURE: email_link column MISSING.")
            
        print("Checking special countries...")
        specials = ['TWP', '32pgs', '32pgs COD', '64pgs', '64pgs COD']
        found_all = True
        for name in specials:
            row = conn.execute("SELECT name FROM countries WHERE name = ?", (name,)).fetchone()
            if row:
                print(f"Found: {name}")
            else:
                print(f"MISSING: {name}")
                found_all = False
                
        if found_all:
            print("SUCCESS: All special countries found.")
        else:
            print("FAILURE: Some special countries are missing.")
            
    except Exception as e:
        print(f"Error checking schema: {e}")
