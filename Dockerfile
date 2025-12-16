FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

# Defaults; override in runtime
ENV PORT=8000
ENV SECRET_KEY=change-this-secret-key
ENV DATABASE=/app/data/ledger.db

# Create data dir for SQLite
RUN mkdir -p /app/data
VOLUME ["/app/data"]

EXPOSE 8000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app:app"]
