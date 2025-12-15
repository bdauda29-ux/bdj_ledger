import sqlite3
from datetime import datetime

DB = 'ledger.db'
conn = sqlite3.connect(DB)
c = conn.cursor()

# Ensure tables exist (init_db in app.py should have created them, but be safe)
try:
    c.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL UNIQUE,
            phone_number TEXT NOT NULL,
            balance REAL NOT NULL DEFAULT 0.0
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS countries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            price REAL NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            applicant_name TEXT,
            app_id INTEGER NOT NULL,
            country_name TEXT NOT NULL,
            country_price REAL NOT NULL,
            rate REAL NOT NULL,
            addition REAL,
            amount REAL NOT NULL,
            amount_n REAL NOT NULL,
            transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
except Exception:
    pass

# Insert client and country if not exists
c.execute('INSERT OR IGNORE INTO clients (client_name, phone_number) VALUES (?, ?)', ('SmokeClient', '000111222'))
c.execute('INSERT OR IGNORE INTO countries (name, price) VALUES (?, ?)', ('SmokeLand', 100.50))

# Get country price
country = c.execute('SELECT price FROM countries WHERE name = ?', ('SmokeLand',)).fetchone()
if country:
    country_price = country[0]
else:
    country_price = 100.50

amount = country_price + 10.00
amount_n = amount * 1.5
transaction_date = '2025-12-01 00:00:00'

c.execute('''
    INSERT INTO transactions (client_name, applicant_name, app_id, country_name, country_price, rate, addition, amount, amount_n, transaction_date)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', ('SmokeClient', 'John Doe', 42, 'SmokeLand', country_price, 1.5, 10.00, amount, amount_n, transaction_date))

conn.commit()
conn.close()
print('Inserted smoke transaction')
