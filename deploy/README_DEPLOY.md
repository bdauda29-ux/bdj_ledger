# Deployment Guide

## Windows (Waitress)
1. Install dependencies: `pip install -r requirements.txt` and `pip install waitress`
2. Set env: `set SECRET_KEY=your-secret` and optionally `set DATABASE=ledger.db`
3. Run: `waitress-serve --host=0.0.0.0 --port=8000 wsgi:application`
3. Optional: front with IIS or Nginx reverse proxy to `127.0.0.1:8000`

## Linux (Gunicorn + Nginx)
1. Install: `pip install -r requirements.txt` and `pip install gunicorn`
2. Set env: `export SECRET_KEY=your-secret` and optionally `export DATABASE=/var/www/app/ledger.db`
3. Run: `gunicorn -w 4 -b 0.0.0.0:8000 app:app`
4. Configure Nginx with `deploy/nginx.conf` and enable HTTPS via Let's Encrypt

## Environment
- Set `SECRET_KEY` in environment and assign to `app.secret_key`
- Back up `ledger.db` or switch to Postgres for multi-user scale
- Use a process manager (systemd, supervisor, or Windows service)

## Procfile
- For platforms supporting Procfile (e.g., Render, Fly), use: `web: gunicorn -w 4 -b 0.0.0.0:8000 app:app`

## Docker
1. Build: `docker build -t ledger-app .`
2. Run: `docker run -p 8000:8000 -e SECRET_KEY=your-secret -v %cd%/data:/app/data ledger-app`
   - On Linux/Mac: `-v $(pwd)/data:/app/data`
3. Compose: `docker compose up -d` (sets env via `docker-compose.yml`)
4. Open: `http://localhost:8000`

## Notes
- Environment:
  - `SECRET_KEY` is required in production
  - `DATABASE` defaults to `ledger.db`; override to a persistent path
- Backups:
  - If using SQLite, back up the `.db` file regularly
  - For multi-user scale, consider switching to Postgres

## Systemd Service
1. Copy code to `/var/www/app`
2. Install: `pip install -r requirements.txt && pip install gunicorn`
3. Place service file: `/etc/systemd/system/ledger.service` from `deploy/systemd/ledger.service`
4. Set env inside service or via `/etc/default/ledger`
5. Enable and start: `sudo systemctl daemon-reload && sudo systemctl enable --now ledger`
6. Check status: `systemctl status ledger`

## Nginx with SSL
1. Install Nginx and Certbot
2. Place config: `/etc/nginx/sites-available/ledger.conf` from `deploy/nginx-ssl.conf`
3. Update `server_name` and certificate paths
4. Enable site: `ln -s /etc/nginx/sites-available/ledger.conf /etc/nginx/sites-enabled/`
5. Test and reload: `nginx -t && sudo systemctl reload nginx`
6. Issue certificates: `sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com`

## Render
1. Push repository to Git
2. Add `deploy/render.yaml` to the repo
3. Create new Web Service in Render with “Use Blueprint”
4. Set `SECRET_KEY` and any SMTP env vars
