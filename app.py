from flask import Flask, render_template, request, redirect, url_for, jsonify, g, send_file, session
import sqlite3
from datetime import datetime, timedelta
import secrets
import hashlib
import os
import smtplib
from email.message import EmailMessage
# Postgres (optional) support
try:
    import psycopg2
    import psycopg2.extras
    import psycopg2.extensions
except Exception:
    psycopg2 = None

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.secret_key = os.getenv('SECRET_KEY', 'change-this-secret-key')
DATABASE = os.getenv('DATABASE', 'ledger.db')
POSTGRES_URL = (
    os.getenv('POSTGRES_URL')
    or os.getenv('POSTGRES_URL_NON_POOLING')
    or os.getenv('DATABASE_URL_NON_POOLING')
    or os.getenv('DATABASE_URL')
)
if psycopg2 is None:
    POSTGRES_URL = None

if psycopg2 is not None:
    class PGConn:
        def __init__(self, dsn):
            self.conn = psycopg2.connect(dsn)
            self.conn.autocommit = False
        def _convert_sql(self, sql):
            sql = sql.replace('?', '%s')
            sql = sql.replace("date('now','localtime')", 'CURRENT_DATE')
            sql = sql.replace('date(', 'DATE(')
            return sql
        def execute(self, sql, params=None):
            try:
                if self.conn.get_transaction_status() == psycopg2.extensions.TRANSACTION_STATUS_INERROR:
                    self.conn.rollback()
                cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute(self._convert_sql(sql), params or [])
                return cur
            except Exception as e:
                try:
                    self.conn.rollback()
                except Exception:
                    pass
                raise e
        def commit(self):
            self.conn.commit()
        def close(self):
            self.conn.close()

def send_email(to_email, subject, body):
    host = os.getenv('SMTP_HOST')
    port = int(os.getenv('SMTP_PORT', '587'))
    username = os.getenv('SMTP_USER')
    password = os.getenv('SMTP_PASS')
    use_tls = os.getenv('SMTP_USE_TLS', '1') == '1'
    from_email = os.getenv('SMTP_FROM', username or 'no-reply@example.com')
    if not host or not username or not password:
        return False
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email
    msg.set_content(body)
    with smtplib.SMTP(host, port) as server:
        if use_tls:
            server.starttls()
        server.login(username, password)
        server.send_message(msg)
    return True

def init_db():
    """Initialize the database with required tables and columns"""
    if POSTGRES_URL:
        conn = psycopg2.connect(POSTGRES_URL)
        conn.autocommit = True
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clients (
                id SERIAL PRIMARY KEY,
                client_name TEXT NOT NULL,
                phone_number TEXT NOT NULL,
                balance REAL NOT NULL DEFAULT 0.0,
                model_id INTEGER
            )
        ''')
        cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_clients_unique ON clients(client_name, model_id)')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS countries (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                model_id INTEGER,
                continent TEXT
            )
        ''')
        cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_countries_unique ON countries(name, model_id)')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id SERIAL PRIMARY KEY,
                client_name TEXT NOT NULL,
                email TEXT,
                service_type TEXT DEFAULT 'eVisa',
                applicant_name TEXT,
                app_id INTEGER NOT NULL,
                country_name TEXT NOT NULL,
                country_price REAL,
                rate REAL,
                addition REAL,
                amount REAL NOT NULL,
                amount_n REAL,
                transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted INTEGER DEFAULT 0,
                is_paid INTEGER DEFAULT 0,
                model_id INTEGER,
                email_link TEXT
            )
        ''')
        cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_transactions_app_unique ON transactions(app_id, model_id)')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS balance_history (
                id SERIAL PRIMARY KEY,
                client_id INTEGER NOT NULL,
                transaction_id INTEGER,
                amount REAL NOT NULL,
                type TEXT NOT NULL,
                balance_before REAL NOT NULL,
                balance_after REAL NOT NULL,
                description TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                model_id INTEGER
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS deleted_transactions (
                id SERIAL PRIMARY KEY,
                original_id INTEGER,
                client_name TEXT,
                email TEXT,
                service_type TEXT,
                applicant_name TEXT,
                app_id INTEGER,
                country_name TEXT,
                country_price REAL,
                rate REAL,
                addition REAL,
                amount REAL,
                amount_n REAL,
                is_paid INTEGER DEFAULT 0,
                transaction_date TIMESTAMP,
                deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                model_id INTEGER,
                email_link TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                email TEXT,
                can_edit_client INTEGER DEFAULT 1,
                can_delete_client INTEGER DEFAULT 1,
                can_add_transaction INTEGER DEFAULT 1,
                can_edit_transaction INTEGER DEFAULT 1,
                can_delete_transaction INTEGER DEFAULT 1,
                is_admin INTEGER DEFAULT 1
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS models (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_models_name ON models(name)')
        
        # --- Postgres Migrations (Ensure columns exist) ---
        migrations = [
            'ALTER TABLE transactions ADD COLUMN IF NOT EXISTS applicant_name TEXT',
            'ALTER TABLE transactions ADD COLUMN IF NOT EXISTS email_link TEXT',
            'ALTER TABLE transactions ADD COLUMN IF NOT EXISTS service_type TEXT DEFAULT \'eVisa\'',
            'ALTER TABLE transactions ADD COLUMN IF NOT EXISTS country_price REAL',
            'ALTER TABLE transactions ADD COLUMN IF NOT EXISTS rate REAL',
            'ALTER TABLE transactions ADD COLUMN IF NOT EXISTS addition REAL',
            'ALTER TABLE transactions ADD COLUMN IF NOT EXISTS amount_n REAL',
            'ALTER TABLE transactions ADD COLUMN IF NOT EXISTS deleted INTEGER DEFAULT 0',
            'ALTER TABLE transactions ADD COLUMN IF NOT EXISTS is_paid INTEGER DEFAULT 0',
            'ALTER TABLE transactions ADD COLUMN IF NOT EXISTS model_id INTEGER',
            'ALTER TABLE balance_history ADD COLUMN IF NOT EXISTS model_id INTEGER',
            'ALTER TABLE clients ADD COLUMN IF NOT EXISTS model_id INTEGER',
            'ALTER TABLE countries ADD COLUMN IF NOT EXISTS model_id INTEGER',
            'ALTER TABLE countries ADD COLUMN IF NOT EXISTS continent TEXT',
            'ALTER TABLE deleted_transactions ADD COLUMN IF NOT EXISTS email_link TEXT'
        ]
        
        for sql in migrations:
            try:
                cursor.execute(sql)
                conn.commit()
            except Exception as e:
                # If IF NOT EXISTS is not supported or other error, rollback and ignore (assume exists)
                conn.rollback()

        conn.autocommit = False
        conn.commit()
        
        # Seed countries if empty
        country_names = [
            'TWP', '32pgs', '32pgs COD', '64pgs', '64pgs COD',
            'Afghanistan','Albania','Algeria','Andorra','Angola','Antigua and Barbuda','Argentina','Armenia','Australia','Austria','Azerbaijan',
            'Bahamas','Bahrain','Bangladesh','Barbados','Belarus','Belgium','Belize','Benin','Bhutan','Bolivia','Bosnia and Herzegovina','Botswana','Brazil','Brunei','Bulgaria','Burkina Faso','Burundi',
            'Cabo Verde','Cambodia','Cameroon','Canada','Central African Republic','Chad','Chile','China','Colombia','Comoros','Congo','Costa Rica','Côte d’Ivoire','Croatia','Cuba','Cyprus','Czechia',
            'Democratic Republic of the Congo','Denmark','Djibouti','Dominica','Dominican Republic','Ecuador','Egypt','El Salvador','Equatorial Guinea','Eritrea','Estonia','Eswatini','Ethiopia',
            'Fiji','Finland','France','Gabon','Gambia','Georgia','Germany','Ghana','Greece','Grenada','Guatemala','Guinea','Guinea-Bissau','Guyana',
            'Haiti','Honduras','Hungary','Iceland','India','Indonesia','Iran','Iraq','Ireland','Israel','Italy',
            'Jamaica','Japan','Jordan','Kazakhstan','Kenya','Kiribati','Kuwait','Kyrgyzstan','Laos','Latvia','Lebanon','Lesotho','Liberia','Libya','Liechtenstein','Lithuania','Luxembourg',
            'Madagascar','Malawi','Malaysia','Maldives','Mali','Malta','Marshall Islands','Mauritania','Mauritius','Mexico','Micronesia','Moldova','Monaco','Mongolia','Montenegro','Morocco','Mozambique','Myanmar',
            'Namibia','Nauru','Nepal','Netherlands','New Zealand','Nicaragua','Niger','Nigeria','North Korea','North Macedonia','Norway',
            'Oman','Pakistan','Palau','Panama','Papua New Guinea','Paraguay','Peru','Philippines','Poland','Portugal','Qatar',
            'Romania','Russia','Rwanda','Saint Kitts and Nevis','Saint Lucia','Saint Vincent and the Grenadines','Samoa','San Marino','Sao Tome and Principe','Saudi Arabia','Senegal','Serbia','Seychelles','Sierra Leone','Singapore','Slovakia','Slovenia','Solomon Islands','Somalia','South Africa','South Korea','South Sudan','Spain','Sri Lanka','Sudan','Suriname','Sweden','Switzerland','Syria',
            'Taiwan','Tajikistan','Tanzania','Thailand','Togo','Tonga','Trinidad and Tobago','Tunisia','Turkey','Turkmenistan','Tuvalu',
            'Uganda','Ukraine','United Arab Emirates','United Kingdom','United States','Uruguay','Uzbekistan','Vanuatu','Venezuela','Vietnam','Yemen','Zambia','Zimbabwe'
        ]
        # Check existing countries to avoid ON CONFLICT error if constraint is missing
        try:
            cursor.execute("SELECT name FROM countries")
            # RealDictCursor returns dicts, so use key access instead of index
            existing_countries = set(row['name'] for row in cursor.fetchall())
            new_countries = [n for n in country_names if n not in existing_countries]
            
            if new_countries:
                psycopg2.extras.execute_values(
                    cursor, 
                    "INSERT INTO countries (name, price, continent) VALUES %s", 
                    [(n, 0.0, None) for n in new_countries]
                )
                conn.commit() # Commit countries immediately
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error seeding countries: {e}")
            conn.rollback()
        
        continent_by_country = {
            'Afghanistan':'Asia','Albania':'Europe','Algeria':'Africa','Andorra':'Europe','Angola':'Africa','Antigua and Barbuda':'North America','Argentina':'South America','Armenia':'Asia','Australia':'Oceania','Austria':'Europe','Azerbaijan':'Asia',
            'Bahamas':'North America','Bahrain':'Asia','Bangladesh':'Asia','Barbados':'North America','Belarus':'Europe','Belgium':'Europe','Belize':'North America','Benin':'Africa','Bhutan':'Asia','Bolivia':'South America','Bosnia and Herzegovina':'Europe','Botswana':'Africa','Brazil':'South America','Brunei':'Asia','Bulgaria':'Europe','Burkina Faso':'Africa','Burundi':'Africa',
            'Cabo Verde':'Africa','Cambodia':'Asia','Cameroon':'Africa','Canada':'North America','Central African Republic':'Africa','Chad':'Africa','Chile':'South America','China':'Asia','Colombia':'South America','Comoros':'Africa','Congo':'Africa','Costa Rica':'North America','Côte d’Ivoire':'Africa','Croatia':'Europe','Cuba':'North America','Cyprus':'Asia','Czechia':'Europe',
            'Democratic Republic of the Congo':'Africa','Denmark':'Europe','Djibouti':'Africa','Dominica':'North America','Dominican Republic':'North America','Ecuador':'South America','Egypt':'Africa','El Salvador':'North America','Equatorial Guinea':'Africa','Eritrea':'Africa','Estonia':'Europe','Eswatini':'Africa','Ethiopia':'Africa',
            'Fiji':'Oceania','Finland':'Europe','France':'Europe','Gabon':'Africa','Gambia':'Africa','Georgia':'Asia','Germany':'Europe','Ghana':'Africa','Greece':'Europe','Grenada':'North America','Guatemala':'North America','Guinea':'Africa','Guinea-Bissau':'Africa','Guyana':'South America',
            'Haiti':'North America','Honduras':'North America','Hungary':'Europe','Iceland':'Europe','India':'Asia','Indonesia':'Asia','Iran':'Asia','Iraq':'Asia','Ireland':'Europe','Israel':'Asia','Italy':'Europe',
            'Jamaica':'North America','Japan':'Asia','Jordan':'Asia','Kazakhstan':'Asia','Kenya':'Africa','Kiribati':'Oceania','Kuwait':'Asia','Kyrgyzstan':'Asia','Laos':'Asia','Latvia':'Europe','Lebanon':'Asia','Lesotho':'Africa','Liberia':'Africa','Libya':'Africa','Liechtenstein':'Europe','Lithuania':'Europe','Luxembourg':'Europe',
            'Madagascar':'Africa','Malawi':'Africa','Malaysia':'Asia','Maldives':'Asia','Mali':'Africa','Malta':'Europe','Marshall Islands':'Oceania','Mauritania':'Africa','Mauritius':'Africa','Mexico':'North America','Micronesia':'Oceania','Moldova':'Europe','Monaco':'Europe','Mongolia':'Asia','Montenegro':'Europe','Morocco':'Africa','Mozambique':'Africa','Myanmar':'Asia',
            'Namibia':'Africa','Nauru':'Oceania','Nepal':'Asia','Netherlands':'Europe','New Zealand':'Oceania','Nicaragua':'North America','Niger':'Africa','Nigeria':'Africa','North Korea':'Asia','North Macedonia':'Europe','Norway':'Europe',
            'Oman':'Asia','Pakistan':'Asia','Palau':'Oceania','Panama':'North America','Papua New Guinea':'Oceania','Paraguay':'South America','Peru':'South America','Philippines':'Asia','Poland':'Europe','Portugal':'Europe','Qatar':'Asia',
            'Romania':'Europe','Russia':'Europe','Rwanda':'Africa','Saint Kitts and Nevis':'North America','Saint Lucia':'North America','Saint Vincent and the Grenadines':'North America','Samoa':'Oceania','San Marino':'Europe','Sao Tome and Principe':'Africa','Saudi Arabia':'Asia','Senegal':'Africa','Serbia':'Europe','Seychelles':'Africa','Sierra Leone':'Africa','Singapore':'Asia','Slovakia':'Europe','Slovenia':'Europe','Solomon Islands':'Oceania','Somalia':'Africa','South Africa':'Africa','South Korea':'Asia','South Sudan':'Africa','Spain':'Europe','Sri Lanka':'Asia','Sudan':'Africa','Suriname':'South America','Sweden':'Europe','Switzerland':'Europe','Syria':'Asia',
            'Taiwan':'Asia','Tajikistan':'Asia','Tanzania':'Africa','Thailand':'Asia','Togo':'Africa','Tonga':'Oceania','Trinidad and Tobago':'North America','Tunisia':'Africa','Turkey':'Asia','Turkmenistan':'Asia','Tuvalu':'Oceania',
            'Uganda':'Africa','Ukraine':'Europe','United Arab Emirates':'Asia','United Kingdom':'Europe','United States':'North America','Uruguay':'South America','Uzbekistan':'Asia','Vanuatu':'Oceania','Venezuela':'South America','Vietnam':'Asia','Yemen':'Asia','Zambia':'Africa','Zimbabwe':'Africa',
            'TWP':'Africa', '32pgs':'Africa', '32pgs COD':'Africa', '64pgs':'Africa', '64pgs COD':'Africa'
        }
        for n, cont in continent_by_country.items():
            cursor.execute('UPDATE countries SET continent = %s WHERE name = %s AND (continent IS NULL OR continent = %s)', (cont, n, ''))

        user = None
        try:
            cursor.execute('SELECT * FROM users WHERE username = %s', ('admin',))
            user = cursor.fetchone()
        except Exception:
            user = None
        if not user:
            default_hash = hashlib.sha256('admin'.encode()).hexdigest()
            cursor.execute('INSERT INTO users (username, password_hash, is_admin) VALUES (%s, %s, 1)', ('admin', default_hash))
        conn.commit()
        conn.close()
        return
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # --- Clients Table ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL UNIQUE,
            phone_number TEXT NOT NULL
        )
    ''')
    
    # Add balance column if it doesn't exist
    try:
        cursor.execute('ALTER TABLE clients ADD COLUMN balance REAL NOT NULL DEFAULT 0.0')
    except sqlite3.OperationalError:
        pass  # Column already exists
    # Add model_id to clients
    try:
        cursor.execute('ALTER TABLE clients ADD COLUMN model_id INTEGER')
    except sqlite3.OperationalError:
        pass
    # Migrate table-level unique(client_name) to per-model unique(client_name, model_id)
    try:
        idx_list = cursor.execute("PRAGMA index_list('clients')").fetchall()
        needs_migration = False
        for idx in idx_list:
            idx_name = idx[1]
            is_unique = bool(idx[2])
            if is_unique:
                cols = cursor.execute(f"PRAGMA index_info('{idx_name}')").fetchall()
                col_names = [c[2] for c in cols]
                if col_names == ['client_name']:
                    needs_migration = True
                    break
        if needs_migration:
            cursor.execute('''
                CREATE TABLE clients_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_name TEXT NOT NULL,
                    phone_number TEXT NOT NULL,
                    balance REAL NOT NULL DEFAULT 0.0,
                    model_id INTEGER
                )
            ''')
            cursor.execute('INSERT INTO clients_new (id, client_name, phone_number, balance, model_id) SELECT id, client_name, phone_number, balance, model_id FROM clients')
            cursor.execute('DROP TABLE clients')
            cursor.execute('ALTER TABLE clients_new RENAME TO clients')
    except sqlite3.OperationalError:
        pass
    # Ensure per-model uniqueness
    try:
        cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_clients_unique ON clients(client_name, model_id)')
    except sqlite3.OperationalError:
        pass

    # --- Countries Table ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS countries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            price REAL NOT NULL
        )
    ''')
    try:
        cursor.execute('ALTER TABLE countries ADD COLUMN model_id INTEGER')
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute('ALTER TABLE countries ADD COLUMN continent TEXT')
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_countries_unique ON countries(name, model_id)')
    except sqlite3.OperationalError:
        pass
    country_names = [
        'TWP', '32pgs', '32pgs COD', '64pgs', '64pgs COD',
        'Afghanistan','Albania','Algeria','Andorra','Angola','Antigua and Barbuda','Argentina','Armenia','Australia','Austria','Azerbaijan',
        'Bahamas','Bahrain','Bangladesh','Barbados','Belarus','Belgium','Belize','Benin','Bhutan','Bolivia','Bosnia and Herzegovina','Botswana','Brazil','Brunei','Bulgaria','Burkina Faso','Burundi',
        'Cabo Verde','Cambodia','Cameroon','Canada','Central African Republic','Chad','Chile','China','Colombia','Comoros','Congo','Costa Rica','Côte d’Ivoire','Croatia','Cuba','Cyprus','Czechia',
        'Democratic Republic of the Congo','Denmark','Djibouti','Dominica','Dominican Republic','Ecuador','Egypt','El Salvador','Equatorial Guinea','Eritrea','Estonia','Eswatini','Ethiopia',
        'Fiji','Finland','France','Gabon','Gambia','Georgia','Germany','Ghana','Greece','Grenada','Guatemala','Guinea','Guinea-Bissau','Guyana',
        'Haiti','Honduras','Hungary','Iceland','India','Indonesia','Iran','Iraq','Ireland','Israel','Italy',
        'Jamaica','Japan','Jordan','Kazakhstan','Kenya','Kiribati','Kuwait','Kyrgyzstan','Laos','Latvia','Lebanon','Lesotho','Liberia','Libya','Liechtenstein','Lithuania','Luxembourg',
        'Madagascar','Malawi','Malaysia','Maldives','Mali','Malta','Marshall Islands','Mauritania','Mauritius','Mexico','Micronesia','Moldova','Monaco','Mongolia','Montenegro','Morocco','Mozambique','Myanmar',
        'Namibia','Nauru','Nepal','Netherlands','New Zealand','Nicaragua','Niger','Nigeria','North Korea','North Macedonia','Norway',
        'Oman','Pakistan','Palau','Panama','Papua New Guinea','Paraguay','Peru','Philippines','Poland','Portugal','Qatar',
        'Romania','Russia','Rwanda','Saint Kitts and Nevis','Saint Lucia','Saint Vincent and the Grenadines','Samoa','San Marino','Sao Tome and Principe','Saudi Arabia','Senegal','Serbia','Seychelles','Sierra Leone','Singapore','Slovakia','Slovenia','Solomon Islands','Somalia','South Africa','South Korea','South Sudan','Spain','Sri Lanka','Sudan','Suriname','Sweden','Switzerland','Syria',
        'Taiwan','Tajikistan','Tanzania','Thailand','Togo','Tonga','Trinidad and Tobago','Tunisia','Turkey','Turkmenistan','Tuvalu',
        'Uganda','Ukraine','United Arab Emirates','United Kingdom','United States','Uruguay','Uzbekistan','Vanuatu','Venezuela','Vietnam','Yemen','Zambia','Zimbabwe'
    ]
    cursor.executemany('INSERT OR IGNORE INTO countries (name, price, continent) VALUES (?, ?, ?)', [(n, 0.0, None) for n in country_names])
    continent_by_country = {
        'Afghanistan':'Asia','Albania':'Europe','Algeria':'Africa','Andorra':'Europe','Angola':'Africa','Antigua and Barbuda':'North America','Argentina':'South America','Armenia':'Asia','Australia':'Oceania','Austria':'Europe','Azerbaijan':'Asia',
        'Bahamas':'North America','Bahrain':'Asia','Bangladesh':'Asia','Barbados':'North America','Belarus':'Europe','Belgium':'Europe','Belize':'North America','Benin':'Africa','Bhutan':'Asia','Bolivia':'South America','Bosnia and Herzegovina':'Europe','Botswana':'Africa','Brazil':'South America','Brunei':'Asia','Bulgaria':'Europe','Burkina Faso':'Africa','Burundi':'Africa',
        'Cabo Verde':'Africa','Cambodia':'Asia','Cameroon':'Africa','Canada':'North America','Central African Republic':'Africa','Chad':'Africa','Chile':'South America','China':'Asia','Colombia':'South America','Comoros':'Africa','Congo':'Africa','Costa Rica':'North America','Côte d’Ivoire':'Africa','Croatia':'Europe','Cuba':'North America','Cyprus':'Asia','Czechia':'Europe',
        'Democratic Republic of the Congo':'Africa','Denmark':'Europe','Djibouti':'Africa','Dominica':'North America','Dominican Republic':'North America','Ecuador':'South America','Egypt':'Africa','El Salvador':'North America','Equatorial Guinea':'Africa','Eritrea':'Africa','Estonia':'Europe','Eswatini':'Africa','Ethiopia':'Africa',
        'Fiji':'Oceania','Finland':'Europe','France':'Europe','Gabon':'Africa','Gambia':'Africa','Georgia':'Asia','Germany':'Europe','Ghana':'Africa','Greece':'Europe','Grenada':'North America','Guatemala':'North America','Guinea':'Africa','Guinea-Bissau':'Africa','Guyana':'South America',
        'Haiti':'North America','Honduras':'North America','Hungary':'Europe','Iceland':'Europe','India':'Asia','Indonesia':'Asia','Iran':'Asia','Iraq':'Asia','Ireland':'Europe','Israel':'Asia','Italy':'Europe',
        'Jamaica':'North America','Japan':'Asia','Jordan':'Asia','Kazakhstan':'Asia','Kenya':'Africa','Kiribati':'Oceania','Kuwait':'Asia','Kyrgyzstan':'Asia','Laos':'Asia','Latvia':'Europe','Lebanon':'Asia','Lesotho':'Africa','Liberia':'Africa','Libya':'Africa','Liechtenstein':'Europe','Lithuania':'Europe','Luxembourg':'Europe',
        'Madagascar':'Africa','Malawi':'Africa','Malaysia':'Asia','Maldives':'Asia','Mali':'Africa','Malta':'Europe','Marshall Islands':'Oceania','Mauritania':'Africa','Mauritius':'Africa','Mexico':'North America','Micronesia':'Oceania','Moldova':'Europe','Monaco':'Europe','Mongolia':'Asia','Montenegro':'Europe','Morocco':'Africa','Mozambique':'Africa','Myanmar':'Asia',
        'Namibia':'Africa','Nauru':'Oceania','Nepal':'Asia','Netherlands':'Europe','New Zealand':'Oceania','Nicaragua':'North America','Niger':'Africa','Nigeria':'Africa','North Korea':'Asia','North Macedonia':'Europe','Norway':'Europe',
        'Oman':'Asia','Pakistan':'Asia','Palau':'Oceania','Panama':'North America','Papua New Guinea':'Oceania','Paraguay':'South America','Peru':'South America','Philippines':'Asia','Poland':'Europe','Portugal':'Europe','Qatar':'Asia',
        'Romania':'Europe','Russia':'Europe','Rwanda':'Africa','Saint Kitts and Nevis':'North America','Saint Lucia':'North America','Saint Vincent and the Grenadines':'North America','Samoa':'Oceania','San Marino':'Europe','Sao Tome and Principe':'Africa','Saudi Arabia':'Asia','Senegal':'Africa','Serbia':'Europe','Seychelles':'Africa','Sierra Leone':'Africa','Singapore':'Asia','Slovakia':'Europe','Slovenia':'Europe','Solomon Islands':'Oceania','Somalia':'Africa','South Africa':'Africa','South Korea':'Asia','South Sudan':'Africa','Spain':'Europe','Sri Lanka':'Asia','Sudan':'Africa','Suriname':'South America','Sweden':'Europe','Switzerland':'Europe','Syria':'Asia',
        'Taiwan':'Asia','Tajikistan':'Asia','Tanzania':'Africa','Thailand':'Asia','Togo':'Africa','Tonga':'Oceania','Trinidad and Tobago':'North America','Tunisia':'Africa','Turkey':'Asia','Turkmenistan':'Asia','Tuvalu':'Oceania',
        'Uganda':'Africa','Ukraine':'Europe','United Arab Emirates':'Asia','United Kingdom':'Europe','United States':'North America','Uruguay':'South America','Uzbekistan':'Asia','Vanuatu':'Oceania','Venezuela':'South America','Vietnam':'Asia','Yemen':'Asia','Zambia':'Africa','Zimbabwe':'Africa',
        'TWP':'Africa', '32pgs':'Africa', '32pgs COD':'Africa', '64pgs':'Africa', '64pgs COD':'Africa'
    }
    for n, cont in continent_by_country.items():
        cursor.execute('INSERT OR IGNORE INTO countries (name, price, continent) VALUES (?, ?, ?)', (n, 0.0, cont))
        cursor.execute('UPDATE countries SET continent = ? WHERE name = ? AND (continent IS NULL OR continent = "")', (cont, n))

    # --- Transactions Table ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_name TEXT NOT NULL,
            email TEXT,
            service_type TEXT DEFAULT 'eVisa',
            app_id INTEGER NOT NULL,
            country_name TEXT NOT NULL,
            amount REAL NOT NULL,
            transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_name) REFERENCES clients(client_name),
            FOREIGN KEY (country_name) REFERENCES countries(name)
        )
    ''')
    
    # Add columns to transactions table if they don't exist
    try:
        cursor.execute('ALTER TABLE transactions ADD COLUMN applicant_name TEXT')
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute('ALTER TABLE transactions ADD COLUMN email TEXT')
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE transactions ADD COLUMN service_type TEXT DEFAULT 'eVisa'")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute('ALTER TABLE transactions ADD COLUMN country_price REAL')
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute('ALTER TABLE transactions ADD COLUMN rate REAL')
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute('ALTER TABLE transactions ADD COLUMN addition REAL')
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute('ALTER TABLE transactions ADD COLUMN amount_n REAL')
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute('ALTER TABLE transactions ADD COLUMN deleted INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute('ALTER TABLE transactions ADD COLUMN is_paid INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute('ALTER TABLE transactions ADD COLUMN email_link TEXT')
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute('ALTER TABLE transactions ADD COLUMN model_id INTEGER')
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_transactions_app_unique ON transactions(app_id, model_id)')
    except sqlite3.OperationalError:
        pass

    # --- Balance History Table ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS balance_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            transaction_id INTEGER,
            amount REAL NOT NULL,
            type TEXT NOT NULL,
            balance_before REAL NOT NULL,
            balance_after REAL NOT NULL,
            description TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients(id),
            FOREIGN KEY (transaction_id) REFERENCES transactions(id)
        )
    ''')
    try:
        cursor.execute('ALTER TABLE balance_history ADD COLUMN model_id INTEGER')
    except sqlite3.OperationalError:
        pass

    # --- Deleted transactions bin ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deleted_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_id INTEGER,
            client_name TEXT,
            email TEXT,
            service_type TEXT,
            applicant_name TEXT,
            app_id INTEGER,
            country_name TEXT,
            country_price REAL,
            rate REAL,
            addition REAL,
            amount REAL,
            amount_n REAL,
            transaction_date TIMESTAMP,
            deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    # Ensure all expected columns exist for backward compatibility
    for col_def in [
        ('email', 'TEXT'),
        ('service_type', 'TEXT'),
        ('applicant_name', 'TEXT'),
        ('app_id', 'INTEGER'),
        ('country_name', 'TEXT'),
        ('country_price', 'REAL'),
        ('rate', 'REAL'),
        ('addition', 'REAL'),
        ('amount', 'REAL'),
        ('amount_n', 'REAL'),
        ('is_paid', 'INTEGER DEFAULT 0'),
        ('email_link', 'TEXT'),
        ('transaction_date', 'TIMESTAMP'),
        ('deleted_at', "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ('model_id', 'INTEGER'),
    ]:
        try:
            cursor.execute(f'ALTER TABLE deleted_transactions ADD COLUMN {col_def[0]} {col_def[1]}')
        except sqlite3.OperationalError:
            pass

    # --- Users Table ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            email TEXT,
            can_edit_client INTEGER DEFAULT 1,
            can_delete_client INTEGER DEFAULT 1,
            can_add_transaction INTEGER DEFAULT 1,
            can_edit_transaction INTEGER DEFAULT 1,
            can_delete_transaction INTEGER DEFAULT 1,
            is_admin INTEGER DEFAULT 1
        )
    ''')
    try:
        cursor.execute('ALTER TABLE users ADD COLUMN email TEXT')
    except sqlite3.OperationalError:
        pass
    for col, default in [
        ('can_edit_client', 1),
        ('can_delete_client', 1),
        ('can_add_transaction', 1),
        ('can_edit_transaction', 1),
        ('can_delete_transaction', 1),
        ('is_admin', 1),
    ]:
        try:
            cursor.execute(f'ALTER TABLE users ADD COLUMN {col} INTEGER DEFAULT {default}')
        except sqlite3.OperationalError:
            pass
    # Create default admin if none
    user = cursor.execute('SELECT * FROM users WHERE username = ?', ('admin',)).fetchone()
    if not user:
        default_hash = hashlib.sha256('admin'.encode()).hexdigest()
        cursor.execute('INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, 1)', ('admin', default_hash))
    else:
        # Ensure admin has full permissions
        cursor.execute('UPDATE users SET is_admin = 1, can_edit_client = 1, can_delete_client = 1, can_add_transaction = 1, can_edit_transaction = 1, can_delete_transaction = 1 WHERE username = ?', ('admin',))
        # Ensure default admin password for local dev
        default_hash = hashlib.sha256('admin'.encode()).hexdigest()
        cursor.execute('UPDATE users SET password_hash = ? WHERE username = ?', (default_hash, 'admin'))

    # --- Models Table ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()

def get_db_connection():
    """Get database connection"""
    if 'db' not in g:
        if POSTGRES_URL:
            g.db = PGConn(POSTGRES_URL)
        else:
            g.db = sqlite3.connect(DATABASE, timeout=20)
            g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    """Close the database connection"""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def login_required():
    return bool(session.get('user_id'))

@app.before_request
def require_login():
    allowed = {'/login', '/logout'}
    path = request.path
    if path.startswith('/static/'):
        return
    if path in allowed or path.startswith('/models'):
        return
    # Allow disabling auth/model requirement for serverless testing environments
    if os.getenv('DISABLE_AUTH', '0') == '1':
        if not session.get('model_id'):
            conn = get_db_connection()
            m = conn.execute('SELECT id, name FROM models WHERE name = ?', ('Default',)).fetchone()
            if not m:
                conn.execute('INSERT INTO models (name) VALUES (?)', ('Default',))
                conn.commit()
                m = conn.execute('SELECT id, name FROM models WHERE name = ?', ('Default',)).fetchone()
            session['model_id'] = m['id']
            session['model_name'] = m['name']
        return
    if not login_required():
        return redirect(url_for('login'))
    # Require model selection for app routes
    if not session.get('model_id') and not path.startswith('/models'):
        return redirect(url_for('models'))

def current_model_id():
    return session.get('model_id')
def can(permission):
    perms = session.get('permissions', {})
    return bool(perms.get(permission)) or bool(perms.get('is_admin'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','')
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if user:
            if hashlib.sha256(password.encode()).hexdigest() == user['password_hash']:
                session['user_id'] = user['id']
                session['username'] = user['username']
                cols = user.keys()
                def pv(name, default):
                    return user[name] if name in cols and user[name] is not None else default
                session['permissions'] = {
                    'can_edit_client': bool(pv('can_edit_client', 1)),
                    'can_delete_client': bool(pv('can_delete_client', 1)),
                    'can_add_transaction': bool(pv('can_add_transaction', 1)),
                    'can_edit_transaction': bool(pv('can_edit_transaction', 1)),
                    'can_delete_transaction': bool(pv('can_delete_transaction', 1)),
                    'is_admin': bool(pv('is_admin', 0))
                }
                return redirect(url_for('models'))
        return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
@app.route('/account/password', methods=['GET','POST'])
def change_password():
    if not login_required():
        return redirect(url_for('login'))
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    if request.method == 'POST':
        current = request.form.get('current_password','')
        new = request.form.get('new_password','')
        confirm = request.form.get('confirm_password','')
        if hashlib.sha256(current.encode()).hexdigest() != user['password_hash']:
            return render_template('change_password.html', error='Current password is incorrect')
        if not new or new != confirm:
            return render_template('change_password.html', error='New passwords do not match')
        conn.execute('UPDATE users SET password_hash = ? WHERE id = ?', (hashlib.sha256(new.encode()).hexdigest(), user['id']))
        conn.commit()
        return redirect(url_for('index'))
    return render_template('change_password.html')
@app.route('/forgot', methods=['GET','POST'])
def forgot_password():
    conn = get_db_connection()
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if not user:
            return render_template('forgot_password.html', error='User not found')
        token = secrets.token_urlsafe(32)
        expires = (datetime.utcnow() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS password_resets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT NOT NULL UNIQUE,
                expires_at TIMESTAMP NOT NULL,
                used INTEGER DEFAULT 0
            )
        ''')
        conn.execute('INSERT INTO password_resets (user_id, token, expires_at) VALUES (?, ?, ?)', (user['id'], token, expires))
        conn.commit()
        reset_url = url_for('reset_password', token=token, _external=True)
        sent = False
        if user.get('email'):
            subject = 'Password Reset'
            body = f'Use the link below to reset your password (valid 1 hour):\n{reset_url}'
            try:
                sent = send_email(user['email'], subject, body)
            except Exception:
                sent = False
        if sent:
            return render_template('forgot_password.html', reset_url=None)
        return render_template('forgot_password.html', reset_url=reset_url)
    return render_template('forgot_password.html')
@app.route('/reset/<token>', methods=['GET','POST'])
def reset_password(token):
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM password_resets WHERE token = ?', (token,)).fetchone()
    if not row or row['used']:
        return redirect(url_for('login'))
    if datetime.utcnow() > datetime.strptime(row['expires_at'], '%Y-%m-%d %H:%M:%S'):
        return render_template('reset_password.html', error='Reset link expired', token=token)
    if request.method == 'POST':
        new = request.form.get('new_password','')
        confirm = request.form.get('confirm_password','')
        if not new or new != confirm:
            return render_template('reset_password.html', error='Passwords do not match', token=token)
        conn.execute('UPDATE users SET password_hash = ? WHERE id = ?', (hashlib.sha256(new.encode()).hexdigest(), row['user_id']))
        conn.execute('UPDATE password_resets SET used = 1 WHERE id = ?', (row['id'],))
        conn.commit()
        return redirect(url_for('login'))
    return render_template('reset_password.html', token=token)

@app.route('/models')
def models():
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM models ORDER BY created_at DESC').fetchall()
    try:
        edit_id = int(request.args.get('edit_id')) if request.args.get('edit_id') else None
    except ValueError:
        edit_id = None
    return render_template('models.html', models=rows, edit_id=edit_id, error=request.args.get('error'), message=request.args.get('message'))

@app.route('/models/add', methods=['GET', 'POST'])
def add_model():
    conn = get_db_connection()
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        if not name:
            return render_template('add_model.html', error='Name is required')
        try:
            conn.execute('INSERT INTO models (name) VALUES (?)', (name,))
            conn.commit()
            return redirect(url_for('models'))
        except sqlite3.IntegrityError:
            return render_template('add_model.html', error='Model name already exists')
    return render_template('add_model.html')

@app.route('/models/select/<int:model_id>')
def select_model(model_id):
    conn = get_db_connection()
    m = conn.execute('SELECT * FROM models WHERE id = ?', (model_id,)).fetchone()
    if not m:
        return redirect(url_for('models'))
    session['model_id'] = m['id']
    session['model_name'] = m['name']
    return redirect(url_for('index'))

@app.route('/models/clear', methods=['POST'])
def clear_current_model():
    """Clear all records for the current model"""
    if not can('is_admin'):
        return redirect(url_for('models'))
    conn = get_db_connection()
    mid = current_model_id()
    conn.execute('DELETE FROM balance_history WHERE model_id = ?', (mid,))
    conn.execute('DELETE FROM deleted_transactions WHERE model_id = ?', (mid,))
    conn.execute('DELETE FROM transactions WHERE model_id = ?', (mid,))
    conn.execute('DELETE FROM clients WHERE model_id = ?', (mid,))
    conn.commit()
    return redirect(url_for('models'))

@app.route('/models/<int:model_id>/edit', methods=['GET','POST'])
def edit_model(model_id):
    if not can('is_admin'):
        return redirect(url_for('models'))
    conn = get_db_connection()
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        if not name:
            return redirect(url_for('models', edit_id=model_id, error='Name is required'))
        try:
            conn.execute('UPDATE models SET name = ? WHERE id = ?', (name, model_id))
            conn.commit()
            if session.get('model_id') == model_id:
                session['model_name'] = name
            return redirect(url_for('models', message='Model updated'))
        except sqlite3.IntegrityError:
            return redirect(url_for('models', edit_id=model_id, error='Model name already exists'))
    return redirect(url_for('models', edit_id=model_id))

@app.route('/models/<int:model_id>/delete', methods=['POST'])
def delete_model(model_id):
    if not can('is_admin'):
        return redirect(url_for('models'))
    conn = get_db_connection()
    conn.execute('DELETE FROM balance_history WHERE model_id = ?', (model_id,))
    conn.execute('DELETE FROM deleted_transactions WHERE model_id = ?', (model_id,))
    conn.execute('DELETE FROM transactions WHERE model_id = ?', (model_id,))
    conn.execute('DELETE FROM clients WHERE model_id = ?', (model_id,))
    conn.execute('DELETE FROM models WHERE id = ?', (model_id,))
    conn.commit()
    if session.get('model_id') == model_id:
        session.pop('model_id', None)
        session.pop('model_name', None)
    return redirect(url_for('models'))
# ==================== USER MANAGEMENT ====================
@app.route('/users')
def list_users():
    if not can('is_admin'):
        return redirect(url_for('index'))
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users ORDER BY username').fetchall()
    return render_template('users.html', users=users, error=request.args.get('error'))

@app.route('/users/add', methods=['GET','POST'])
def add_user():
    if not can('is_admin'):
        return redirect(url_for('index'))
    conn = get_db_connection()
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','')
        if not username or not password:
            return render_template('add_user.html', error='Username and password required')
        flags = {
            'is_admin': 1 if request.form.get('is_admin') else 0,
            'can_edit_client': 1 if request.form.get('can_edit_client') else 0,
            'can_delete_client': 1 if request.form.get('can_delete_client') else 0,
            'can_add_transaction': 1 if request.form.get('can_add_transaction') else 0,
            'can_edit_transaction': 1 if request.form.get('can_edit_transaction') else 0,
            'can_delete_transaction': 1 if request.form.get('can_delete_transaction') else 0,
        }
        try:
            conn.execute('INSERT INTO users (username, password_hash, is_admin, can_edit_client, can_delete_client, can_add_transaction, can_edit_transaction, can_delete_transaction) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                         (username, hashlib.sha256(password.encode()).hexdigest(), flags['is_admin'], flags['can_edit_client'], flags['can_delete_client'], flags['can_add_transaction'], flags['can_edit_transaction'], flags['can_delete_transaction']))
            conn.commit()
            return redirect(url_for('list_users'))
        except sqlite3.IntegrityError:
            return render_template('add_user.html', error='Username already exists')
    return render_template('add_user.html')

@app.route('/users/<int:user_id>/edit', methods=['GET','POST'])
def edit_user(user_id):
    if not can('is_admin'):
        return redirect(url_for('index'))
    conn = get_db_connection()
    if request.method == 'POST':
        flags = {
            'is_admin': 1 if request.form.get('is_admin') else 0,
            'can_edit_client': 1 if request.form.get('can_edit_client') else 0,
            'can_delete_client': 1 if request.form.get('can_delete_client') else 0,
            'can_add_transaction': 1 if request.form.get('can_add_transaction') else 0,
            'can_edit_transaction': 1 if request.form.get('can_edit_transaction') else 0,
            'can_delete_transaction': 1 if request.form.get('can_delete_transaction') else 0,
        }
        conn.execute('UPDATE users SET is_admin = ?, can_edit_client = ?, can_delete_client = ?, can_add_transaction = ?, can_edit_transaction = ?, can_delete_transaction = ? WHERE id = ?',
                     (flags['is_admin'], flags['can_edit_client'], flags['can_delete_client'], flags['can_add_transaction'], flags['can_edit_transaction'], flags['can_delete_transaction'], user_id))
        conn.commit()
        return redirect(url_for('list_users'))
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    return render_template('edit_user.html', user=user)

@app.route('/users/<int:user_id>/delete', methods=['POST'])
def delete_user(user_id):
    if not can('is_admin'):
        return redirect(url_for('index'))
    conn = get_db_connection()
    # Prevent deleting your own account
    if session.get('user_id') == user_id:
        return redirect(url_for('list_users', error='Cannot delete your own account'))
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        return redirect(url_for('list_users'))
    # Prevent deleting the last admin
    if user['is_admin']:
        admin_count = conn.execute('SELECT COUNT(*) FROM users WHERE is_admin = 1').fetchone()[0]
        if admin_count <= 1:
            return redirect(url_for('list_users', error='Cannot delete the last admin'))
    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    return redirect(url_for('list_users'))

# ==================== CLIENT ROUTES ====================

@app.errorhandler(500)
def internal_error(error):
    import traceback
    return f"<pre>{traceback.format_exc()}</pre>", 500

@app.route('/')
def index():
    """Home page - shows dashboard"""
    try:
        conn = get_db_connection()
        mid = current_model_id()
        
        # Get total number of clients
        try:
            total_clients = conn.execute('SELECT COUNT(*) FROM clients WHERE model_id = %s', (mid,)).fetchone()['count']
        except (Exception, KeyError):
            # Fallback if key is different or query fails
            try:
                total_clients = conn.execute('SELECT COUNT(*) FROM clients WHERE model_id = ?', (mid,)).fetchone()[0]
            except:
                total_clients = 0
        
        # Get total number of transactions
        try:
            total_transactions = conn.execute('SELECT COUNT(*) FROM transactions WHERE model_id = %s', (mid,)).fetchone()['count']
        except:
             try:
                total_transactions = conn.execute('SELECT COUNT(*) FROM transactions WHERE model_id = ?', (mid,)).fetchone()[0]
             except:
                total_transactions = 0
        
        # Get total balance of all clients
        try:
            total_balance = conn.execute('SELECT SUM(balance) FROM clients WHERE model_id = %s', (mid,)).fetchone()['sum']
        except:
            try:
                total_balance = conn.execute('SELECT SUM(balance) FROM clients WHERE model_id = ?', (mid,)).fetchone()[0]
            except:
                total_balance = 0
            
        if total_balance is None: total_balance = 0.0
        
        # Get today's transactions
        # Safe query that works on both
        sql_trans = '''
            SELECT * FROM transactions 
            WHERE deleted = 0 AND model_id = ?
            ORDER BY transaction_date DESC
            LIMIT 50
        '''
        transactions = conn.execute(sql_trans, (mid,)).fetchall()
        
        # Today's totals (simplified to avoid complex date logic for now)
        today_sums = {'sum_amount': 0, 'sum_amount_n': 0}
        
        return render_template('index.html', 
                               total_clients=total_clients,
                               total_transactions=total_transactions,
                               total_balance=total_balance,
                               transactions=transactions,
                               today_sums=today_sums)
    except Exception as e:
        import traceback
        debug_info = []
        try:
            conn_debug = get_db_connection()
            if POSTGRES_URL:
                # Postgres checks
                tables = conn_debug.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'").fetchall()
                table_names = [t['table_name'] for t in tables]
                debug_info.append(f"Tables found: {table_names}")
                
                if 'countries' in table_names:
                    c_count = conn_debug.execute("SELECT count(*) FROM countries").fetchone()
                    debug_info.append(f"Countries count: {c_count}")
                else:
                    debug_info.append("CRITICAL: 'countries' table missing!")
            else:
                # SQLite checks
                tables = conn_debug.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                table_names = [t['name'] for t in tables]
                debug_info.append(f"Tables found: {table_names}")
                
                if 'countries' in table_names:
                    c_count = conn_debug.execute("SELECT count(*) FROM countries").fetchone()
                    debug_info.append(f"Countries count: {c_count[0]}")
        except Exception as db_e:
            debug_info.append(f"Debug check failed: {db_e}")
            
        debug_html = "<br>".join(str(x) for x in debug_info)
        return f"<h1>Dashboard Error</h1><pre>{traceback.format_exc()}</pre><h3>Debug Info</h3><pre>{debug_html}</pre>", 500

@app.route('/clients')
def clients():
    """View all clients"""
    conn = get_db_connection()
    clients_list = conn.execute('SELECT * FROM clients WHERE model_id = ? ORDER BY client_name', (current_model_id(),)).fetchall()
    return render_template('clients.html', clients=clients_list)

@app.route('/clients/add', methods=['GET', 'POST'])
def add_client():
    """Add a new client"""
    # Permission: add/edit clients requires can_edit_client
    perms = session.get('permissions', {})
    if not perms.get('can_edit_client') and not perms.get('is_admin'):
        return redirect(url_for('clients'))
    if request.method == 'POST':
        client_name = request.form['client_name']
        phone_number = request.form['phone_number']
        
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO clients (client_name, phone_number, model_id) VALUES (?, ?, ?)',
                        (client_name, phone_number, current_model_id()))
            conn.commit()
            return redirect(url_for('clients'))
        except sqlite3.IntegrityError:
            return render_template('add_client.html', error='Client name already exists')
    
    return render_template('add_client.html')

@app.route('/clients/<int:client_id>/edit', methods=['GET', 'POST'])
def edit_client(client_id):
    """Edit a client"""
    perms = session.get('permissions', {})
    if not perms.get('can_edit_client') and not perms.get('is_admin'):
        return redirect(url_for('clients'))
    conn = get_db_connection()
    
    if request.method == 'POST':
        client_name = request.form['client_name']
        phone_number = request.form['phone_number']
        
        try:
            conn.execute('UPDATE clients SET client_name = ?, phone_number = ? WHERE id = ? AND model_id = ?',
                        (client_name, phone_number, client_id, current_model_id()))
            conn.commit()
            return redirect(url_for('clients'))
        except sqlite3.IntegrityError:
            client = conn.execute('SELECT * FROM clients WHERE id = ? AND model_id = ?', (client_id, current_model_id())).fetchone()
            return render_template('edit_client.html', client=client, error='Client name already exists')
    
    client = conn.execute('SELECT * FROM clients WHERE id = ? AND model_id = ?', (client_id, current_model_id())).fetchone()
    return render_template('edit_client.html', client=client)

@app.route('/clients/<int:client_id>/delete', methods=['POST'])
def delete_client(client_id):
    """Delete a client"""
    perms = session.get('permissions', {})
    if not perms.get('can_delete_client') and not perms.get('is_admin'):
        return redirect(url_for('clients'))
    conn = get_db_connection()
    conn.execute('DELETE FROM clients WHERE id = ? AND model_id = ?', (client_id, current_model_id()))
    conn.commit()
    return redirect(url_for('clients'))

@app.route('/clients/<int:client_id>/update_balance', methods=['GET'])
def update_balance(client_id):
    """Update balance for a client"""
    amount = request.args.get('amount', type=float)
    type = request.args.get('type')

    if amount is None or amount <= 0 or type not in ['credit', 'debit']:
        return redirect(url_for('clients'))

    conn = get_db_connection()
    try:
        row = conn.execute('SELECT balance FROM clients WHERE id = ? AND model_id = ?', (client_id, current_model_id())).fetchone()
        if not row:
            return redirect(url_for('clients'))
        balance_before = row['balance']
        if type == 'credit':
            conn.execute('UPDATE clients SET balance = balance + ? WHERE id = ? AND model_id = ?', (amount, client_id, current_model_id()))
        else:
            conn.execute('UPDATE clients SET balance = balance - ? WHERE id = ? AND model_id = ?', (amount, client_id, current_model_id()))
        row2 = conn.execute('SELECT balance FROM clients WHERE id = ? AND model_id = ?', (client_id, current_model_id())).fetchone()
        balance_after = row2['balance'] if row2 else balance_before
        description = f'{type.capitalize()} of {amount} to client {client_id}'
        conn.execute('INSERT INTO balance_history (client_id, amount, type, balance_before, balance_after, description, model_id) VALUES (?, ?, ?, ?, ?, ?, ?)',
                     (client_id, amount, type, balance_before, balance_after, description, current_model_id()))
        conn.commit()
        return redirect(url_for('clients'))
    except Exception:
        import traceback
        with open('traceback.log', 'a') as f:
            f.write('\n\n=== EXCEPTION IN update_balance ===\n')
            f.write(traceback.format_exc())
        try:
            conn.rollback()
        except Exception:
            pass
        return redirect(url_for('clients'))

@app.route('/clients/<int:client_id>/transactions')
def client_transactions(client_id):
    """View all transactions for a specific client"""
    conn = get_db_connection()
    client = conn.execute('SELECT * FROM clients WHERE id = ? AND model_id = ?', (client_id, current_model_id())).fetchone()
    transactions = conn.execute('SELECT * FROM transactions WHERE client_name = ? AND model_id = ? AND deleted = 0 ORDER BY transaction_date DESC', (client['client_name'], current_model_id())).fetchall()
    return render_template('client_transactions.html', client=client, transactions=transactions)

@app.route('/clients/<int:client_id>/history')
def balance_history(client_id):
    """View balance history for a client"""
    conn = get_db_connection()
    client = conn.execute('SELECT * FROM clients WHERE id = ? AND model_id = ?', (client_id, current_model_id())).fetchone()
    history = conn.execute('SELECT * FROM balance_history WHERE client_id = ? AND model_id = ? ORDER BY timestamp DESC', (client_id, current_model_id())).fetchall()
    return render_template('balance_history.html', client=client, history=history)

# ==================== COUNTRY ROUTES ====================

@app.route('/countries')
def countries():
    """View all countries"""
    try:
        conn = get_db_connection()
        countries_list = conn.execute('SELECT id, name, COALESCE(price, 0.0) AS price, continent FROM countries ORDER BY name').fetchall()
        try:
            edit_id = int(request.args.get('edit_id')) if request.args.get('edit_id') else None
        except ValueError:
            edit_id = None
        return render_template('countries.html', countries=countries_list, edit_id=edit_id, error=request.args.get('error'), message=request.args.get('message'))
    except Exception as e:
        import traceback
        debug_info = []
        try:
            conn_debug = get_db_connection()
            if POSTGRES_URL:
                tables = conn_debug.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'").fetchall()
                table_names = [t['table_name'] for t in tables]
                debug_info.append(f"Tables found: {table_names}")
                if 'countries' in table_names:
                    c_count = conn_debug.execute("SELECT count(*) FROM countries").fetchone()
                    debug_info.append(f"Countries count: {c_count}")
            else:
                tables = conn_debug.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                table_names = [t['name'] for t in tables]
                debug_info.append(f"Tables found: {table_names}")
        except Exception as db_e:
            debug_info.append(f"Debug check failed: {db_e}")
        debug_html = "<br>".join(str(x) for x in debug_info)
        return f"<h1>Countries Error</h1><pre>{traceback.format_exc()}</pre><h3>Debug Info</h3><pre>{debug_html}</pre>", 500

@app.route('/countries/add', methods=['GET', 'POST'])
def add_country():
    """Add a new country"""
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        continent = request.form.get('continent') or None
        
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO countries (name, price, continent) VALUES (?, ?, ?)',
                        (name, price, continent))
            conn.commit()
            return redirect(url_for('countries'))
        except sqlite3.IntegrityError:
            return render_template('add_country.html', error='Country name already exists')
    
    return render_template('add_country.html')

@app.route('/countries/<int:country_id>/edit', methods=['GET', 'POST'])
def edit_country(country_id):
    """Edit a country"""
    conn = get_db_connection()
    
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        continent = request.form.get('continent') or None
        
        try:
            conn.execute('UPDATE countries SET name = ?, price = ?, continent = ? WHERE id = ?',
                        (name, price, continent, country_id))
            conn.commit()
            return redirect(url_for('countries', message='Country updated'))
        except sqlite3.IntegrityError:
            return redirect(url_for('countries', edit_id=country_id, error='Country name already exists'))
    return redirect(url_for('countries', edit_id=country_id))

@app.route('/countries/<int:country_id>/delete', methods=['POST'])
def delete_country(country_id):
    """Delete a country"""
    conn = get_db_connection()
    conn.execute('DELETE FROM countries WHERE id = ?', (country_id,))
    conn.commit()
    return redirect(url_for('countries'))

# ==================== TRANSACTION ROUTES ====================

@app.route('/transactions')
def transactions():
    """View all transactions with optional filters and sums"""
    conn = get_db_connection()
    # available filter options
    clients_list = conn.execute('SELECT client_name FROM clients WHERE model_id = ? ORDER BY client_name', (current_model_id(),)).fetchall()
    countries_list = conn.execute('SELECT name FROM countries ORDER BY name').fetchall()

    # collect filters from query params
    client = request.args.get('client_name')
    country = request.args.get('country_name')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    error = request.args.get('error')
    paid = request.args.get('paid')

    # Ensure country_price is populated for any legacy rows
    try:
        if POSTGRES_URL:
            conn.execute('''
                UPDATE transactions t
                SET country_price = c.price
                FROM countries c
                WHERE t.country_price IS NULL
                  AND t.country_name = c.name
                  AND t.model_id = ?
            ''', (current_model_id(),))
        else:
            conn.execute('''
                UPDATE transactions
                SET country_price = (
                    SELECT price FROM countries WHERE name = transactions.country_name
                )
                WHERE country_price IS NULL AND model_id = ?
            ''', (current_model_id(),))
        conn.commit()
    except Exception:
        pass

    where_clauses = []
    params = []
    if client:
        where_clauses.append('t.client_name = ?')
        params.append(client)
    if country:
        where_clauses.append('t.country_name = ?')
        params.append(country)
    if date_from:
        where_clauses.append("date(t.transaction_date) >= date(?)")
        params.append(date_from)
    if date_to:
        where_clauses.append("date(t.transaction_date) <= date(?)")
        params.append(date_to)

    if paid in ('0', '1'):
        where_clauses.append('t.is_paid = ?')
        params.append(int(paid))
    where_clauses = ['t.model_id = ?'] + where_clauses
    params = [current_model_id()] + params
    where_sql = ('WHERE ' + ' AND '.join(where_clauses)) if where_clauses else 'WHERE t.model_id = ?'

    transactions_list = conn.execute(f'''
        SELECT t.* FROM transactions t
        {where_sql}
        ORDER BY t.transaction_date DESC
    ''', params).fetchall()

    sums = conn.execute(f'''
        SELECT COALESCE(SUM(amount),0) AS sum_amount, COALESCE(SUM(amount_n),0) AS sum_amount_n
        FROM transactions t
        {where_sql}
    ''', params).fetchone()

    return render_template('transactions.html', transactions=transactions_list, clients=clients_list, countries=countries_list, filters={'client': client, 'country': country, 'date_from': date_from, 'date_to': date_to, 'paid': paid}, sums=sums, error=error)

@app.route('/transactions/add', methods=['GET', 'POST'])
def add_transaction():
    """Add a new transaction"""
    startup_error = app.config.get('STARTUP_ERROR')
    if startup_error:
        return render_template('base.html', error=f'Database Startup Error: {startup_error}'), 500

    perms = session.get('permissions', {})
    if not perms.get('can_add_transaction') and not perms.get('is_admin'):
        return redirect(url_for('transactions'))
    
    try:
        conn = get_db_connection()
        
        if request.method == 'POST':
            try:
                client_name = request.form['client_name']
                applicant_name = request.form.get('applicant_name', '')
                email = request.form.get('email', '')
                service_type = request.form.get('service_type', 'eVisa')
                try:
                    app_id = int(request.form['app_id'])
                except (ValueError, TypeError):
                     return render_template('add_transaction.html', 
                                         clients=conn.execute('SELECT client_name FROM clients ORDER BY client_name').fetchall(), 
                                         countries=conn.execute('SELECT name, price FROM countries ORDER BY name').fetchall(),
                                         error='Invalid App ID')

                country_name = request.form['country_name']
                
                try:
                    rate = float(request.form.get('rate') or 1.0)
                except ValueError:
                    rate = 1.0
                    
                try:
                    addition = float(request.form.get('add') or 0.0)
                except ValueError:
                    addition = 0.0

                transaction_date_str = request.form.get('transaction_date')
                transaction_date = None
                if transaction_date_str:
                    try:
                        dt = datetime.strptime(transaction_date_str, '%Y-%m-%d')
                        transaction_date = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        transaction_date = None
                
                # Get country price
                country = conn.execute('SELECT price FROM countries WHERE name = ?', (country_name,)).fetchone()
                if not country:
                    clients_list = conn.execute('SELECT client_name FROM clients').fetchall()
                    countries_list = conn.execute('SELECT name FROM countries').fetchall()
                    return render_template('add_transaction.html', 
                                         clients=clients_list, 
                                         countries=countries_list,
                                         error='Country not found')
                
                country_price = country['price']
                amount = country_price + addition
                amount_n = amount * rate
                email_link = request.form.get('email_link', '')
                
                exists = conn.execute('SELECT id FROM transactions WHERE app_id = ? AND model_id = ?', (app_id, current_model_id())).fetchone()
                if exists:
                    clients_list = conn.execute('SELECT client_name FROM clients ORDER BY client_name').fetchall()
                    countries_list = conn.execute('SELECT name, price FROM countries ORDER BY name').fetchall()
                    return render_template('add_transaction.html', clients=clients_list, countries=countries_list, error='App ID already exists')
                
                if transaction_date:
                    conn.execute('''
                        INSERT INTO transactions 
                        (client_name, email, service_type, applicant_name, app_id, country_name, country_price, rate, addition, amount, amount_n, transaction_date, model_id, email_link)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (client_name, email, service_type, applicant_name, app_id, country_name, country_price, rate, addition, amount, amount_n, transaction_date, current_model_id(), email_link))
                else:
                    conn.execute('''
                        INSERT INTO transactions 
                        (client_name, email, service_type, applicant_name, app_id, country_name, country_price, rate, addition, amount, amount_n, model_id, email_link)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (client_name, email, service_type, applicant_name, app_id, country_name, country_price, rate, addition, amount, amount_n, current_model_id(), email_link))
                
                transaction_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]

                conn.commit()
                return redirect(url_for('transactions'))
            except Exception as e:
                import traceback
                import sys
                print(f"ERROR in add_transaction: {e}", file=sys.stderr)
                traceback.print_exc()
                # Removed file logging for Vercel compatibility
                return render_template('base.html', error=f'Error processing transaction: {str(e)}'), 500
        
        clients_list = conn.execute('SELECT client_name FROM clients ORDER BY client_name').fetchall()
        countries_list = conn.execute('SELECT name, price FROM countries ORDER BY name').fetchall()
        return render_template('add_transaction.html', clients=clients_list, countries=countries_list)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return render_template('base.html', error=f'System Error (GET add_transaction): {str(e)}'), 500

@app.route('/transactions/<int:transaction_id>/edit', methods=['GET', 'POST'])
def edit_transaction(transaction_id):
    """Edit a transaction"""
    perms = session.get('permissions', {})
    if not perms.get('can_edit_transaction') and not perms.get('is_admin'):
        return redirect(url_for('transactions'))
    conn = get_db_connection()
    
    if request.method == 'POST':
        try:
            # Get original transaction
            original_transaction = conn.execute('SELECT client_name, amount_n, model_id FROM transactions WHERE id = ?', (transaction_id,)).fetchone()
            if not original_transaction or original_transaction['model_id'] != current_model_id():
                return redirect(url_for('transactions'))
            original_client_name = original_transaction['client_name']
            original_amount_n = original_transaction['amount_n']
        
            client_name = request.form['client_name']
            applicant_name = request.form.get('applicant_name', '')
            email = request.form.get('email', '')
            email_link = request.form.get('email_link', '')
            service_type = request.form.get('service_type', 'eVisa')
            try:
                app_id = int(request.form.get('app_id', '0'))
            except (TypeError, ValueError):
                app_id = 0
            country_name = request.form['country_name']
            try:
                rate = float(request.form.get('rate') or 1.0)
            except ValueError:
                rate = 1.0
            
            try:
                addition = float(request.form.get('add') or 0.0)
            except ValueError:
                addition = 0.0

            transaction_date_str = request.form.get('transaction_date')
            transaction_date = None
            if transaction_date_str:
                try:
                    dt = datetime.strptime(transaction_date_str, '%Y-%m-%d')
                    transaction_date = dt.strftime('%Y-%m-%d %H:%M:%S')
                except ValueError:
                    transaction_date = None
        
            # Get country price
            country = conn.execute('SELECT price FROM countries WHERE name = ?', (country_name,)).fetchone()
            if not country:
                transaction = conn.execute('SELECT * FROM transactions WHERE id = ?', (transaction_id,)).fetchone()
                clients_list = conn.execute('SELECT client_name FROM clients ORDER BY client_name').fetchall()
                countries_list = conn.execute('SELECT name, price FROM countries ORDER BY name').fetchall()
                return render_template('edit_transaction.html', 
                                     transaction=transaction,
                                     clients=clients_list, 
                                     countries=countries_list,
                                     error='Country not found')
        
            country_price = country['price']
            amount = country_price + addition
            amount_n = amount * rate
            dup = conn.execute('SELECT id FROM transactions WHERE app_id = ? AND model_id = ? AND id != ?', (app_id, current_model_id(), transaction_id)).fetchone()
            if dup:
                transaction = conn.execute('SELECT * FROM transactions WHERE id = ?', (transaction_id,)).fetchone()
                clients_list = conn.execute('SELECT client_name FROM clients WHERE model_id = ? ORDER BY client_name', (current_model_id(),)).fetchall()
                countries_list = conn.execute('SELECT name, price FROM countries ORDER BY name').fetchall()
                return render_template('edit_transaction.html', 
                                     transaction=transaction,
                                     clients=clients_list, 
                                     countries=countries_list,
                                     error='App ID already exists')
        
            if transaction_date:
                conn.execute('''
                    UPDATE transactions 
                    SET client_name = ?, email = ?, service_type = ?, applicant_name = ?, app_id = ?, country_name = ?, 
                        country_price = ?, rate = ?, addition = ?, amount = ?, amount_n = ?, transaction_date = ?, email_link = ?
                    WHERE id = ?
                ''', (client_name, email, service_type, applicant_name, app_id, country_name, country_price, rate, addition, amount, amount_n, transaction_date, email_link, transaction_id))
            else:
                conn.execute('''
                    UPDATE transactions 
                    SET client_name = ?, email = ?, service_type = ?, applicant_name = ?, app_id = ?, country_name = ?, 
                        country_price = ?, rate = ?, addition = ?, amount = ?, amount_n = ?, email_link = ?
                    WHERE id = ?
                ''', (client_name, email, service_type, applicant_name, app_id, country_name, country_price, rate, addition, amount, amount_n, email_link, transaction_id))
        
            original_client = conn.execute('SELECT id, balance FROM clients WHERE client_name = ? AND model_id = ?', (original_client_name, current_model_id())).fetchone()
            if original_client:
                balance_before_orig = original_client['balance']
                balance_after_orig = balance_before_orig + original_amount_n
                conn.execute('UPDATE clients SET balance = ? WHERE client_name = ? AND model_id = ?', (balance_after_orig, original_client_name, current_model_id()))
                description_orig = f'Reversal of transaction {transaction_id} for client {original_client_name}'
                conn.execute('INSERT INTO balance_history (client_id, transaction_id, amount, type, balance_before, balance_after, description, model_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                             (original_client['id'], transaction_id, original_amount_n, 'credit', balance_before_orig, balance_after_orig, description_orig, current_model_id()))

            new_client = conn.execute('SELECT id, balance FROM clients WHERE client_name = ? AND model_id = ?', (client_name, current_model_id())).fetchone()
            if new_client:
                balance_before_new = new_client['balance']
                balance_after_new = balance_before_new - amount_n
                conn.execute('UPDATE clients SET balance = ? WHERE client_name = ? AND model_id = ?', (balance_after_new, client_name, current_model_id()))
                description_new = f'Transaction {transaction_id} for client {client_name}'
                conn.execute('INSERT INTO balance_history (client_id, transaction_id, amount, type, balance_before, balance_after, description, model_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                             (new_client['id'], transaction_id, amount_n, 'debit', balance_before_new, balance_after_new, description_new, current_model_id()))
            else:
                transaction = conn.execute('SELECT * FROM transactions WHERE id = ?', (transaction_id,)).fetchone()
                clients_list = conn.execute('SELECT client_name FROM clients WHERE model_id = ? ORDER BY client_name', (current_model_id(),)).fetchall()
                countries_list = conn.execute('SELECT name, price FROM countries ORDER BY name').fetchall()
                conn.rollback()
                return render_template('edit_transaction.html', 
                                     transaction=transaction,
                                     clients=clients_list, 
                                     countries=countries_list,
                                     error='Selected client not found in current model')
        
            conn.commit()
            return redirect(url_for('transactions'))
        except Exception as e:
            import traceback
            import sys
            print(f"ERROR in edit_transaction: {e}", file=sys.stderr)
            traceback.print_exc()
            # Removed file logging for Vercel compatibility
            try:
                conn.rollback()
            except Exception:
                pass
            transaction = conn.execute('SELECT * FROM transactions WHERE id = ?', (transaction_id,)).fetchone()
            clients_list = conn.execute('SELECT client_name FROM clients WHERE model_id = ? ORDER BY client_name', (current_model_id(),)).fetchall()
            countries_list = conn.execute('SELECT name, price FROM countries ORDER BY name').fetchall()
            return render_template('edit_transaction.html', 
                                 transaction=transaction,
                                 clients=clients_list, 
                                 countries=countries_list,
                                 error=f'An unexpected error occurred: {str(e)}')
    
    transaction = conn.execute('SELECT * FROM transactions WHERE id = ? AND model_id = ?', (transaction_id, current_model_id())).fetchone()
    clients_list = conn.execute('SELECT client_name FROM clients WHERE model_id = ? ORDER BY client_name', (current_model_id(),)).fetchall()
    countries_list = conn.execute('SELECT name, price FROM countries ORDER BY name').fetchall()
    
    if not transaction:
        return redirect(url_for('transactions'))
    
    return render_template('edit_transaction.html', 
                         transaction=transaction, 
                         clients=clients_list, 
                         countries=countries_list)

@app.route('/health/db')
def health_db():
    # Check for startup errors first
    startup_error = app.config.get('STARTUP_ERROR')
    if startup_error:
        return jsonify({
            'status': 'error', 
            'source': 'startup_init', 
            'error': startup_error,
            'db_configured': 'postgres' if POSTGRES_URL else 'sqlite'
        }), 500

    try:
        conn = get_db_connection()
        row = conn.execute('SELECT 1 AS ok').fetchone()
        return jsonify({
            'status': 'ok', 
            'db': 'postgres' if POSTGRES_URL else 'sqlite', 
            'ok': (row['ok'] if row else None)
        })
    except Exception as e:
        return jsonify({
            'status': 'error', 
            'source': 'connection_check', 
            'error': str(e),
            'db_configured': 'postgres' if POSTGRES_URL else 'sqlite'
        }), 500

@app.route('/transactions/<int:transaction_id>/pay', methods=['POST'])
def pay_transaction(transaction_id):
    """Pay a transaction by deducting amount_n from client balance"""
    if not can('can_edit_transaction'):
        return redirect(url_for('transactions'))
    conn = get_db_connection()
    
    try:
        transaction = conn.execute('SELECT * FROM transactions WHERE id = ? AND model_id = ?', (transaction_id, current_model_id())).fetchone()
        if not transaction:
            return redirect(url_for('transactions'))
        if transaction['is_paid']:
            return redirect(url_for('transactions'))
        client = conn.execute('SELECT id, balance FROM clients WHERE client_name = ? AND model_id = ?', (transaction['client_name'], current_model_id())).fetchone()
        if not client:
            return redirect(url_for('transactions'))
        balance_before = client['balance']
        amount_to_deduct = transaction['amount_n']
        if amount_to_deduct > balance_before:
            return redirect(url_for('transactions', error='Insufficient balance to pay this transaction'))
        balance_after = balance_before - amount_to_deduct
        conn.execute('UPDATE clients SET balance = ? WHERE id = ? AND model_id = ?', (balance_after, client['id'], current_model_id()))
        conn.execute('UPDATE transactions SET is_paid = 1 WHERE id = ?', (transaction_id,))
        conn.execute('''
            INSERT INTO balance_history (client_id, transaction_id, amount, type, balance_before, balance_after, description, model_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            client['id'], transaction_id, amount_to_deduct, 'debit', balance_before, balance_after,
            f'Payment for transaction #{transaction_id}', current_model_id()
        ))
        conn.commit()
        return redirect(url_for('transactions'))
    except Exception:
        import traceback
        import sys
        traceback.print_exc()
        try:
            conn.rollback()
        except Exception:
            pass
        return redirect(url_for('transactions', error='Failed to mark transaction as paid'))

@app.route('/transactions/<int:transaction_id>/undo_pay', methods=['POST'])
def undo_pay_transaction(transaction_id):
    """Undo payment: revert is_paid and restore client balance"""
    if not can('can_edit_transaction'):
        return redirect(url_for('transactions'))
    conn = get_db_connection()
    try:
        transaction = conn.execute('SELECT * FROM transactions WHERE id = ? AND model_id = ?', (transaction_id, current_model_id())).fetchone()
        if not transaction:
            return redirect(url_for('transactions'))
        if not transaction['is_paid']:
            return redirect(url_for('transactions'))
        client = conn.execute('SELECT id, balance FROM clients WHERE client_name = ? AND model_id = ?', (transaction['client_name'], current_model_id())).fetchone()
        if not client:
            return redirect(url_for('transactions'))
        balance_before = client['balance']
        amount_to_add = transaction['amount_n']
        balance_after = balance_before + amount_to_add
        conn.execute('UPDATE clients SET balance = ? WHERE id = ? AND model_id = ?', (balance_after, client['id'], current_model_id()))
        conn.execute('UPDATE transactions SET is_paid = 0 WHERE id = ?', (transaction_id,))
        conn.execute('DELETE FROM balance_history WHERE transaction_id = ?', (transaction_id,))
        conn.commit()
        return redirect(url_for('transactions'))
    except Exception:
        import traceback
        import sys
        traceback.print_exc()
        try:
            conn.rollback()
        except Exception:
            pass
        return redirect(url_for('transactions', error='Failed to undo payment'))
@app.route('/transactions/<int:transaction_id>/delete', methods=['POST'])
def delete_transaction(transaction_id):
    """Delete a transaction"""
    perms = session.get('permissions', {})
    if not perms.get('can_delete_transaction') and not perms.get('is_admin'):
        return redirect(url_for('transactions'))
    conn = get_db_connection()
    try:
        transaction = conn.execute('SELECT * FROM transactions WHERE id = ? AND model_id = ?', (transaction_id, current_model_id())).fetchone()
        if not transaction:
            return redirect(url_for('transactions'))
        if transaction['is_paid']:
            client = conn.execute('SELECT id, balance FROM clients WHERE client_name = ? AND model_id = ?', (transaction['client_name'], current_model_id())).fetchone()
            if client:
                new_balance = client['balance'] + (transaction['amount_n'] or 0)
                conn.execute('UPDATE clients SET balance = ? WHERE id = ? AND model_id = ?', (new_balance, client['id'], current_model_id()))
        conn.execute('''
            INSERT INTO deleted_transactions (original_id, client_name, email, service_type, applicant_name, app_id, country_name, country_price, rate, addition, amount, amount_n, is_paid, transaction_date, model_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            transaction['id'], transaction['client_name'], transaction['email'], transaction['service_type'], transaction['applicant_name'], transaction['app_id'],
            transaction['country_name'], transaction['country_price'], transaction['rate'], transaction['addition'],
            transaction['amount'], transaction['amount_n'], transaction['is_paid'], transaction['transaction_date'], current_model_id()
        ))
        conn.execute('DELETE FROM transactions WHERE id = ? AND model_id = ?', (transaction_id, current_model_id()))
        conn.execute('DELETE FROM balance_history WHERE transaction_id = ?', (transaction_id,))
        conn.commit()
        return redirect(url_for('transactions'))
    except Exception:
        import traceback
        with open('traceback.log', 'a') as f:
            f.write('\n\n=== EXCEPTION IN delete_transaction ===\n')
            f.write(traceback.format_exc())
        try:
            conn.rollback()
        except Exception:
            pass
        return redirect(url_for('transactions', error='Failed to delete transaction'))


@app.route('/transactions/bin')
def transactions_bin():
    """View deleted transactions (bin)"""
    conn = get_db_connection()
    deleted = conn.execute('SELECT * FROM deleted_transactions WHERE model_id = ? ORDER BY deleted_at DESC', (current_model_id(),)).fetchall()
    return render_template('deleted_transactions.html', deleted=deleted)


@app.route('/transactions/bin/<int:deleted_id>/restore', methods=['POST'])
def restore_deleted_transaction(deleted_id):
    """Restore a deleted transaction back into transactions and apply balance effect"""
    conn = get_db_connection()
    try:
        row = conn.execute('SELECT * FROM deleted_transactions WHERE id = ? AND model_id = ?', (deleted_id, current_model_id())).fetchone()
        if not row:
            return redirect(url_for('transactions_bin'))
        conn.execute('''
            INSERT INTO transactions (client_name, email, service_type, applicant_name, app_id, country_name, country_price, rate, addition, amount, amount_n, is_paid, transaction_date, model_id, email_link)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (row['client_name'], row['email'], row['service_type'], row['applicant_name'], row['app_id'], row['country_name'], row['country_price'], row['rate'], row['addition'], row['amount'], row['amount_n'], int(row['is_paid'] or 0), row['transaction_date'], current_model_id(), row['email_link']))
        new_transaction_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        client = conn.execute('SELECT id, balance FROM clients WHERE client_name = ? AND model_id = ?', (row['client_name'], current_model_id())).fetchone()
        if client and int(row['is_paid'] or 0) == 1:
            balance_before = client['balance']
            balance_after = balance_before - (row['amount_n'] or 0)
            conn.execute('UPDATE clients SET balance = ? WHERE client_name = ? AND model_id = ?', (balance_after, row['client_name'], current_model_id()))
            description = f'Restore transaction {new_transaction_id} for client {row["client_name"]}'
            conn.execute('INSERT INTO balance_history (client_id, transaction_id, amount, type, balance_before, balance_after, description, model_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                         (client['id'], new_transaction_id, (row['amount_n'] or 0), 'debit', balance_before, balance_after, description, current_model_id()))
        conn.execute('DELETE FROM deleted_transactions WHERE id = ? AND model_id = ?', (deleted_id, current_model_id()))
        conn.commit()
        return redirect(url_for('transactions'))
    except Exception:
        import traceback
        with open('traceback.log', 'a') as f:
            f.write('\n\n=== EXCEPTION IN restore_deleted_transaction ===\n')
            f.write(traceback.format_exc())
        try:
            conn.rollback()
        except Exception:
            pass
        return redirect(url_for('transactions_bin', error='Failed to restore transaction'))


@app.route('/transactions/bin/<int:deleted_id>/delete', methods=['POST'])
def permanently_delete_transaction(deleted_id):
    """Permanently remove a transaction from the bin"""
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM deleted_transactions WHERE id = ? AND model_id = ?', (deleted_id, current_model_id()))
        conn.commit()
        return redirect(url_for('transactions_bin'))
    except Exception:
        import traceback
        with open('traceback.log', 'a') as f:
            f.write('\n\n=== EXCEPTION IN permanently_delete_transaction ===\n')
            f.write(traceback.format_exc())
        try:
            conn.rollback()
        except Exception:
            pass
        return redirect(url_for('transactions_bin', error='Failed to permanently delete'))

# ==================== EXPORT ROUTES ====================

@app.route('/transactions/export')
def export_transactions():
    """Export transactions as PDF or JPEG"""
    try:
        format_type = request.args.get('format', 'pdf')
        client = request.args.get('client_name', '').strip()
        country = request.args.get('country_name', '').strip()
        date_from = request.args.get('date_from', '').strip()
        date_to = request.args.get('date_to', '').strip()
        
        # Build WHERE clause
        where_clauses = ['model_id = ?']
        params = [current_model_id()]
        if client:
            where_clauses.append('client_name = ?')
            params.append(client)
        if country:
            where_clauses.append('country_name = ?')
            params.append(country)
        if date_from:
            where_clauses.append("date(transaction_date) >= date(?)")
            params.append(date_from)
        if date_to:
            where_clauses.append("date(transaction_date) <= date(?)")
            params.append(date_to)
        
        where_sql = ('WHERE ' + ' AND '.join(where_clauses)) if where_clauses else ''
        
        conn = get_db_connection()
        transactions_list = conn.execute(f'''
            SELECT * FROM transactions
            {where_sql}
            ORDER BY transaction_date DESC
        ''', params).fetchall()
        
        sums = conn.execute(f'''
            SELECT COALESCE(SUM(amount),0) AS sum_amount, COALESCE(SUM(amount_n),0) AS sum_amount_n
            FROM transactions
            {where_sql}
        ''', params).fetchone()
        
        if format_type == 'pdf':
            return export_pdf(transactions_list, sums)
        elif format_type == 'jpeg':
            return export_jpeg(transactions_list, sums)
        else:
            return 'Invalid format', 400
    except Exception as e:
        import traceback
        return f'Error exporting: {str(e)}<br><pre>{traceback.format_exc()}</pre>', 500

def export_pdf(transactions, sums):
    """Export transactions to PDF"""
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from io import BytesIO
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.black,
        spaceAfter=12,
        alignment=1
    )
    elements.append(Paragraph('Transaction Report', title_style))
    elements.append(Spacer(1, 0.2))
    
    # Create table data
    data = [['S.No', 'Applicant', 'App ID', 'Country', 'Service', 'Email', 'Amount ($)', 'Rate', 'Amount N (₦)', 'Date']]
    for idx, trans in enumerate(transactions, start=1):
        data.append([
            str(idx),
            trans['applicant_name'] or '',
            str(trans['app_id']),
            trans['country_name'],
            trans['service_type'] or '',
            trans['email'] or '',
            f"${trans['amount']:.2f}",
            f"{trans['rate']:.2f}",
            f"₦{trans['amount_n']:.2f}",
            trans['transaction_date'][:10]
        ])
    
    # Add sums row
    data.append(['', '', '', '', '', 'TOTAL:', f"${sums['sum_amount']:.2f}", '', f"₦{sums['sum_amount_n']:.2f}", ''])
    
    table = Table(data)
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.black),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
    ]
    for i, trans in enumerate(transactions, start=1):
        if trans['is_paid']:
            style_cmds.append(('BACKGROUND', (0, i), (-1, i), colors.lightgreen))
    table.setStyle(TableStyle(style_cmds))
    
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name='transactions.pdf'
    )

def export_jpeg(transactions, sums):
    """Export transactions to JPEG - creates a simple table image"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        from io import BytesIO
    except Exception:
        return export_pdf(transactions, sums)
    
    # Create image
    width, height = 1200, 100 + len(transactions) * 30 + 50
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # Try to use default font, fallback to basic font
    try:
        font = ImageFont.truetype("arial.ttf", 12)
        title_font = ImageFont.truetype("arial.ttf", 14)
    except:
        font = ImageFont.load_default()
        title_font = font
    
    y = 10
    draw.text((10, y), 'Transaction Report', fill='black', font=title_font)
    y += 30
    
    # Headers
    headers = ['S.No', 'Applicant', 'App ID', 'Country', 'Service', 'Email', 'Amount ($)', 'Rate', 'Amount N (₦)', 'Date']
    x_positions = [10, 80, 220, 320, 460, 560, 700, 780, 900, 1020]
    
    for i, header in enumerate(headers):
        draw.text((x_positions[i], y), header, fill='black', font=font)
    y += 25
    draw.line([(10, y), (width-10, y)], fill='black', width=1)
    y += 10
    
    # Data rows
    for idx, trans in enumerate(transactions, start=1):
        if trans['is_paid']:
            draw.rectangle([(10, y-3), (width-10, y+22)], fill=(230, 255, 237))
        row_data = [
            str(idx),
            (trans['applicant_name'] or '')[:15],
            str(trans['app_id']),
            trans['country_name'][:15],
            (trans['service_type'] or '')[:12],
            (trans['email'] or '')[:14],
            f"${trans['amount']:.2f}",
            f"{trans['rate']:.2f}",
            f"₦{trans['amount_n']:.2f}",
            trans['transaction_date'][:10]
        ]
        
        for i, text in enumerate(row_data):
            draw.text((x_positions[i], y), text, fill='black', font=font)
        y += 25
    
    # Total line
    y += 10
    draw.line([(10, y), (width-10, y)], fill='black', width=1)
    y += 10
    draw.text((x_positions[4], y), f'TOTAL:', fill='black', font=font)
    draw.text((x_positions[6], y), f'${sums["sum_amount"]:.2f}', fill='black', font=font)
    draw.text((x_positions[8], y), f'₦{sums["sum_amount_n"]:.2f}', fill='black', font=font)
    
    buffer = BytesIO()
    img.save(buffer, format='JPEG')
    buffer.seek(0)
    
    return send_file(
        buffer,
        mimetype='image/jpeg',
        as_attachment=True,
        download_name='transactions.jpeg'
    )

# ==================== API ROUTES ====================

@app.route('/api/countries/<country_name>/price')
def get_country_price(country_name):
    """API endpoint to get country price"""
    conn = get_db_connection()
    country = conn.execute('SELECT price FROM countries WHERE name = ?', (country_name,)).fetchone()
    
    if country:
        return jsonify({'price': country['price']})
    return jsonify({'error': 'Country not found'}), 404

@app.errorhandler(500)
def internal_server_error(error):
    return render_template('base.html', error='The server encountered an internal error and was unable to complete your request. Either the server is overloaded or there is an error in the application.'), 500

@app.route('/health/init')
def health_init():
    try:
        init_db()
        conn = get_db_connection()
        if POSTGRES_URL:
            rows = conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'").fetchall()
            names = [r['table_name'] for r in rows]
        else:
            rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            names = [r['name'] for r in rows]
        return jsonify({'status': 'ok', 'tables': names})
    except Exception as e:
        import traceback
        return jsonify({'status': 'error', 'error': str(e), 'traceback': traceback.format_exc()}), 500

if __name__ == '__main__':
    init_db()
    import os
    port = int(os.environ.get('PORT', '5000'))
    app.run(debug=True, host='127.0.0.1', port=port)
