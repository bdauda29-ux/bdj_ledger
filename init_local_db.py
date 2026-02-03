
import app
import os

print("Initializing local database...")
if os.path.exists("ledger.db"):
    print("Warning: ledger.db already exists.")
else:
    print("ledger.db not found. Creating new one.")

try:
    # Ensure MYSQL_URL is not set so it defaults to SQLite
    if app.MYSQL_URL:
        print(f"Warning: MYSQL_URL is set to {app.MYSQL_URL}. Temporarily unsetting for local init.")
        app.MYSQL_URL = None
    
    app.init_db()
    print("Database initialized successfully.")
except Exception as e:
    print(f"Error initializing database: {e}")
