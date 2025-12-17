import os
import sys

# Add the project root to sys.path so we can import wsgi
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Vercel serverless functions have ephemeral storage; write to /tmp
# Note: For persistent data, use POSTGRES_URL environment variable
os.environ.setdefault('DATABASE', '/tmp/ledger.db')

try:
    from wsgi import application as app
except Exception as e:
    # Fallback app to show import errors
    from flask import Flask
    app = Flask(__name__)
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def catch_all(path):
        import traceback
        return f"<h1>Startup Error</h1><pre>{traceback.format_exc()}</pre>", 500
