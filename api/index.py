import os

# Vercel serverless functions have ephemeral storage; write to /tmp
os.environ.setdefault('DATABASE', '/tmp/ledger.db')

from wsgi import application as app
