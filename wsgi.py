from app import app, init_db

# Initialize database on startup for WSGI servers
init_db()

# Expose WSGI application object
application = app
