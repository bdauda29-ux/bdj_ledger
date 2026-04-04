import os
import sys

# Add the project root to sys.path
root_dir = os.path.join(os.path.dirname(__file__), '..')
sys.path.append(root_dir)

# Vercel serverless functions have ephemeral storage; write to /tmp
os.environ.setdefault('DATABASE', '/tmp/ledger.db')
os.environ.setdefault('DISABLE_AUTH', '1')

# Import the application directly from app.py
# Vercel's @vercel/python runtime looks for 'app', 'application', or 'handler'
try:
    from app import app
    
    # Auto-initialize SQLite DB if it doesn't exist (for serverless cold starts)
    if not os.environ.get('POSTGRES_URL'):
        db_path = os.environ.get('DATABASE')
        if db_path and not os.path.exists(db_path):
            print(f"Initializing ephemeral SQLite database at {db_path}...", file=sys.stderr)
            with app.app_context():
                from app import init_db
                init_db()
                
except Exception as e:
    # If import fails, create a fallback app to show the error
    from flask import Flask
    app = Flask(__name__)
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def catch_all(path):
        import traceback
        return f"<h1>Startup Error</h1><pre>{traceback.format_exc()}</pre>", 500

# Explicitly expose common handler names for Vercel
application = app
handler = app
