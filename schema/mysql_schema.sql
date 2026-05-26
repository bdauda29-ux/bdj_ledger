CREATE TABLE IF NOT EXISTS models (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  name VARCHAR(255) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY idx_models_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS users (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  username VARCHAR(255) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  email VARCHAR(255) NULL,
  surname VARCHAR(255) NULL,
  passport_number VARCHAR(255) NULL,
  passport_expiry VARCHAR(255) NULL,
  nationality VARCHAR(255) NULL,
  can_edit_client TINYINT(1) DEFAULT 1,
  can_delete_client TINYINT(1) DEFAULT 1,
  can_add_transaction TINYINT(1) DEFAULT 1,
  can_edit_transaction TINYINT(1) DEFAULT 1,
  can_delete_transaction TINYINT(1) DEFAULT 1,
  can_view_clients TINYINT(1) DEFAULT 1,
  is_admin TINYINT(1) DEFAULT 1,
  PRIMARY KEY (id),
  UNIQUE KEY idx_users_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS clients (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  client_name VARCHAR(255) NOT NULL,
  phone_number VARCHAR(64) NOT NULL,
  balance DOUBLE NOT NULL DEFAULT 0.0,
  model_id BIGINT UNSIGNED NULL,
  PRIMARY KEY (id),
  UNIQUE KEY idx_clients_unique (client_name, model_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS countries (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  name VARCHAR(255) NOT NULL,
  price DOUBLE NOT NULL,
  model_id BIGINT UNSIGNED NULL,
  continent VARCHAR(64) NULL,
  PRIMARY KEY (id),
  UNIQUE KEY idx_countries_unique (name, model_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS transactions (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  client_name VARCHAR(255) NOT NULL,
  email VARCHAR(255) NULL,
  service_type VARCHAR(64) DEFAULT 'eVisa',
  applicant_name VARCHAR(255) NULL,
  app_id BIGINT NOT NULL,
  country_name VARCHAR(255) NOT NULL,
  country_price DOUBLE NULL,
  rate DOUBLE NULL,
  addition DOUBLE NULL,
  amount DOUBLE NOT NULL,
  amount_n DOUBLE NULL,
  transaction_date DATETIME DEFAULT CURRENT_TIMESTAMP,
  deleted TINYINT(1) DEFAULT 0,
  is_paid TINYINT(1) DEFAULT 0,
  email_link TEXT NULL,
  created_by VARCHAR(255) NULL,
  model_id BIGINT UNSIGNED NULL,
  PRIMARY KEY (id),
  UNIQUE KEY idx_transactions_app_unique (app_id, model_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS balance_history (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  client_id BIGINT UNSIGNED NOT NULL,
  transaction_id BIGINT UNSIGNED NULL,
  amount DOUBLE NOT NULL,
  type VARCHAR(64) NOT NULL,
  balance_before DOUBLE NOT NULL,
  balance_after DOUBLE NOT NULL,
  description TEXT NULL,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  model_id BIGINT UNSIGNED NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS deleted_transactions (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  original_id BIGINT UNSIGNED NULL,
  client_name VARCHAR(255) NULL,
  email VARCHAR(255) NULL,
  service_type VARCHAR(64) NULL,
  applicant_name VARCHAR(255) NULL,
  app_id BIGINT NULL,
  country_name VARCHAR(255) NULL,
  country_price DOUBLE NULL,
  rate DOUBLE NULL,
  addition DOUBLE NULL,
  amount DOUBLE NULL,
  amount_n DOUBLE NULL,
  is_paid TINYINT(1) DEFAULT 0,
  email_link TEXT NULL,
  transaction_date DATETIME NULL,
  deleted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  model_id BIGINT UNSIGNED NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS wallet (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  dollars DOUBLE DEFAULT 0,
  providus_dollars DOUBLE DEFAULT 0,
  bybit_dollars DOUBLE DEFAULT 0,
  naira DOUBLE DEFAULT 0,
  naira_1 DOUBLE DEFAULT 0,
  taj_naira DOUBLE DEFAULT 0,
  rate DOUBLE DEFAULT 0,
  debt DOUBLE DEFAULT 0,
  model_id BIGINT UNSIGNED NULL,
  PRIMARY KEY (id),
  UNIQUE KEY idx_wallet_model (model_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS assets (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  name VARCHAR(255) NOT NULL,
  description TEXT NULL,
  amount DOUBLE NOT NULL DEFAULT 0.0,
  type VARCHAR(64) NOT NULL,
  currency VARCHAR(16) NOT NULL,
  model_id BIGINT UNSIGNED NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS asset_history (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  asset_id BIGINT UNSIGNED NOT NULL,
  amount DOUBLE NOT NULL,
  type VARCHAR(64) NOT NULL,
  balance_before DOUBLE NOT NULL,
  balance_after DOUBLE NOT NULL,
  description TEXT NULL,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  model_id BIGINT UNSIGNED NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS password_resets (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id BIGINT UNSIGNED NOT NULL,
  token VARCHAR(255) NOT NULL,
  expires_at DATETIME NOT NULL,
  used TINYINT(1) DEFAULT 0,
  PRIMARY KEY (id),
  UNIQUE KEY idx_password_resets_token (token)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
