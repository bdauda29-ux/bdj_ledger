# PHP Login/Signup System

This is a PHP OOP implementation of a user authentication system (Login, Signup, Dashboard) with MySQL.

## Setup Instructions

1. **Database Setup**
   - Create a MySQL database (e.g., `ledger_db`).
   - Import the `database.sql` file to create the `users` table.
   ```sql
   source database.sql;
   ```

2. **Configuration**
   - Edit `config/database.php` with your database credentials.
   ```php
   return [
       'host' => 'localhost',
       'dbname' => 'ledger_db',
       'username' => 'root', // Change this
       'password' => '',     // Change this
       'charset' => 'utf8mb4'
   ];
   ```

3. **Running the Application**
   - You can use the built-in PHP server for testing:
   ```bash
   cd public
   php -S localhost:8000
   ```
   - Open your browser and go to `http://localhost:8000`.

## Features
- **MVC Architecture**: Models (`src/User.php`), Controllers (`src/AuthController.php`), Views (`views/`).
- **Security**: Password hashing (`password_hash`), PDO prepared statements (SQL injection prevention).
- **Styling**: Jetstream-inspired UI with Inter font and modern CSS.
