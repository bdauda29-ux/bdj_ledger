import os
import sys

# Add the project root to sys.path so we can import wsgi
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Vercel serverless functions have ephemeral storage; write to /tmp
os.environ.setdefault('DATABASE', '/tmp/ledger.db')
os.environ.setdefault('DISABLE_AUTH', '1')

try:
    from wsgi import application as app
    
    # Auto-initialize DB if needed (Postgres or SQLite)
    # This ensures tables exist on Vercel cold start
    with app.app_context():
        try:
            from app import init_db
            init_db()
        except Exception as e:
            print(f"DB Initialization failed: {e}", file=sys.stderr)

                
except Exception as e:
    # Fallback app to show import errors
    from flask import Flask
    app = Flask(__name__)
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def catch_all(path):
        import traceback
        return f"<h1>Startup Error</h1><pre>{traceback.format_exc()}</pre>", 500
