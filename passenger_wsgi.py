import os
import sys
import secrets

# Activate virtualenv if present (Opalstack/Passenger does not always auto-activate)
env_activate = os.path.join(os.path.dirname(__file__), 'env', 'bin', 'activate_this.py')
if os.path.exists(env_activate):
    with open(env_activate) as f:
        code = compile(f.read(), env_activate, 'exec')
        exec(code, {'__file__': env_activate})

# Set required environment variables if not already set
app_dir = os.path.dirname(__file__)
data_dir = os.path.join(app_dir, 'data')
os.makedirs(data_dir, exist_ok=True)

if not os.environ.get('SECRET_KEY'):
    sk_path = os.path.join(data_dir, 'secret_key.txt')
    try:
        with open(sk_path, 'r') as f:
            secret = f.read().strip()
    except Exception:
        secret = secrets.token_hex(32)
        with open(sk_path, 'w') as f:
            f.write(secret)
    os.environ['SECRET_KEY'] = secret
os.environ.setdefault('DATABASE', os.path.join(data_dir, 'ledger.db'))

# Optional SMTP settings (set your provider credentials in Opalstack or here)
# os.environ.setdefault('SMTP_HOST', '')
# os.environ.setdefault('SMTP_PORT', '587')
# os.environ.setdefault('SMTP_USER', '')
# os.environ.setdefault('SMTP_PASS', '')
# os.environ.setdefault('SMTP_USE_TLS', '1')
# os.environ.setdefault('SMTP_FROM', '')

# Import the WSGI application exposed by your app
from wsgi import application
