import os

# Vercel serverless functions have ephemeral storage; write to /tmp
os.environ.setdefault('DATABASE', '/tmp/ledger.db')
os.environ.setdefault('DISABLE_AUTH', '1')

from wsgi import application as app
