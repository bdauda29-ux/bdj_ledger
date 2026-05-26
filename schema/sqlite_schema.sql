CREATE TABLE IF NOT EXISTS models (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  email TEXT,
  surname TEXT,
  passport_number TEXT,
  passport_expiry TEXT,
  nationality TEXT,
  can_edit_client INTEGER DEFAULT 1,
  can_delete_client INTEGER DEFAULT 1,
  can_add_transaction INTEGER DEFAULT 1,
  can_edit_transaction INTEGER DEFAULT 1,
  can_delete_transaction INTEGER DEFAULT 1,
  can_view_clients INTEGER DEFAULT 1,
  is_admin INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS clients (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  client_name TEXT NOT NULL,
  phone_number TEXT NOT NULL,
  balance REAL NOT NULL DEFAULT 0.0,
  model_id INTEGER
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_clients_unique ON clients(client_name, model_id);

CREATE TABLE IF NOT EXISTS countries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  price REAL NOT NULL,
  model_id INTEGER,
  continent TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_countries_unique ON countries(name, model_id);

CREATE TABLE IF NOT EXISTS transactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
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
  email_link TEXT,
  created_by TEXT,
  model_id INTEGER
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_transactions_app_unique ON transactions(app_id, model_id);

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
  model_id INTEGER
);

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
  is_paid INTEGER DEFAULT 0,
  email_link TEXT,
  transaction_date TIMESTAMP,
  deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  model_id INTEGER
);

CREATE TABLE IF NOT EXISTS wallet (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  dollars REAL DEFAULT 0,
  providus_dollars REAL DEFAULT 0,
  bybit_dollars REAL DEFAULT 0,
  naira REAL DEFAULT 0,
  naira_1 REAL DEFAULT 0,
  taj_naira REAL DEFAULT 0,
  rate REAL DEFAULT 0,
  debt REAL DEFAULT 0,
  model_id INTEGER
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_wallet_model ON wallet(model_id);

CREATE TABLE IF NOT EXISTS assets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  description TEXT,
  amount REAL NOT NULL DEFAULT 0.0,
  type TEXT NOT NULL,
  currency TEXT NOT NULL,
  model_id INTEGER,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS asset_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  asset_id INTEGER NOT NULL,
  amount REAL NOT NULL,
  type TEXT NOT NULL,
  balance_before REAL NOT NULL,
  balance_after REAL NOT NULL,
  description TEXT,
  timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  model_id INTEGER
);

CREATE TABLE IF NOT EXISTS password_resets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  token TEXT NOT NULL UNIQUE,
  expires_at TIMESTAMP NOT NULL,
  used INTEGER DEFAULT 0
);
