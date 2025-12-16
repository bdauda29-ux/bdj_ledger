from app import app, init_db

# Initialize database on startup for WSGI servers
try:
    init_db()
except Exception as e:
    print(f"Error initializing database: {e}")
    app.config['STARTUP_ERROR'] = str(e)

# Expose WSGI application object
application = app
