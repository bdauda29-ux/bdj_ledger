# Debit & Credit Ledger System

A web-based ledger management system built with Python Flask and SQLite database. This application allows you to manage clients, countries, and transactions with automatic calculation of amounts.

## Features

- **Client Management**: Add, edit, and delete clients with name and phone number
- **Country Management**: Add, edit, and delete countries with name and price
- **Transaction Management**: Create transactions with automatic calculation of:
  - Amount = Country Price + Addition
  - Amount N = Amount × Rate
- **Modern UI**: Clean, responsive web interface
- **Data Validation**: Prevents duplicate entries and validates data integrity

## Database Schema

### Clients Table
- `id` (Primary Key)
- `client_name` (Unique)
- `phone_number`

### Countries Table
- `id` (Primary Key)
- `name` (Unique)
- `price`

### Transactions Table
- `id` (Primary Key)
- `client_name` (Foreign Key to Clients)
- `applicant_name`
- `app_id`
- `country_name` (Foreign Key to Countries)
- `country_price` (copied from Countries table)
- `rate`
- `addition`
- `amount` (calculated: country_price + addition)
- `amount_n` (calculated: amount × rate)
- `transaction_date` (auto-generated timestamp)

## Installation

1. **Install Python** (if not already installed)
   - Download from https://www.python.org/downloads/
   - Make sure to check "Add Python to PATH" during installation

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

1. **Start the Flask server**
   ```bash
   python app.py
   ```

2. **Open your browser**
   - Navigate to: http://localhost:5000
   - The application will automatically create the database file (`ledger.db`) on first run

## Usage

### Setting Up Data

1. **Add Clients**
   - Click on "Clients" in the navigation
   - Click "Add New Client"
   - Enter client name and phone number
   - Save

2. **Add Countries**
   - Click on "Countries" in the navigation
   - Click "Add New Country"
   - Enter country name and price
   - Save

3. **Create Transactions**
   - Click on "Transactions" or "Home"
   - Click "Add New Transaction"
   - Select a client and country
   - Enter applicant name, app ID, rate, and addition
   - The Amount and Amount N will be calculated automatically
   - Save

### Viewing Data

- **Home**: Shows recent transactions
- **Transactions**: View all transactions in detail
- **Clients**: View and manage all clients
- **Countries**: View and manage all countries

## Project Structure

```
.
├── app.py                 # Main Flask application
├── ledger.db             # SQLite database (created automatically)
├── requirements.txt      # Python dependencies
├── README.md            # This file
├── templates/           # HTML templates
│   ├── base.html
│   ├── index.html
│   ├── transactions.html
│   ├── add_transaction.html
│   ├── clients.html
│   ├── add_client.html
│   ├── edit_client.html
│   ├── countries.html
│   ├── add_country.html
│   └── edit_country.html
└── static/              # CSS and static files
    └── style.css
```

## API Endpoints

- `GET /` - Home page with transactions
- `GET /transactions` - View all transactions
- `GET /transactions/add` - Add transaction form
- `POST /transactions/add` - Create new transaction
- `POST /transactions/<id>/delete` - Delete transaction
- `GET /clients` - View all clients
- `GET /clients/add` - Add client form
- `POST /clients/add` - Create new client
- `GET /clients/<id>/edit` - Edit client form
- `POST /clients/<id>/edit` - Update client
- `POST /clients/<id>/delete` - Delete client
- `GET /countries` - View all countries
- `GET /countries/add` - Add country form
- `POST /countries/add` - Create new country
- `GET /countries/<id>/edit` - Edit country form
- `POST /countries/<id>/edit` - Update country
- `POST /countries/<id>/delete` - Delete country
- `GET /api/countries/<name>/price` - Get country price (API)

## Notes

- The database file (`ledger.db`) will be created automatically in the project root directory
- All calculations (Amount and Amount N) are performed automatically
- Country prices are stored with transactions for historical accuracy
- Foreign key constraints ensure data integrity

## Troubleshooting

- **Port already in use**: Change the port in `app.py` (last line) from 5000 to another port
- **Database errors**: Delete `ledger.db` and restart the application to recreate the database
- **Module not found**: Make sure all dependencies are installed using `pip install -r requirements.txt`

## License

This project is provided as-is for educational and business purposes.

