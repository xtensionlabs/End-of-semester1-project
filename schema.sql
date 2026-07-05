-- Enable Foreign Keygit
PRAGMA foreign_keys = ON;

-- 1. USERS TABLE
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('farmer', 'buyer', 'food_bank', 'admin')),
    location TEXT,
    phone TEXT,
    date_joined TEXT DEFAULT CURRENT_TIMESTAMP NOT NULL -- SQLite stores dates/times as TEXT, ISO8601 strings
);

-- 2. FOOD BANK REGISTRY TABLE
CREATE TABLE food_bank (
    food_bank_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE REFERENCES users(user_id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    location TEXT,
    total_food_saved_kg REAL DEFAULT 0.00 NOT NULL CHECK (total_food_saved_kg >= 0) -- SQLite uses REAL/NUMERIC for decimals
);

-- 3. LISTINGS TABLE
CREATE TABLE listings (
    listing_id INTEGER PRIMARY KEY AUTOINCREMENT,
    farmer_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    crop_name TEXT NOT NULL,
    quantity_kg REAL NOT NULL CHECK (quantity_kg >= 0),
    min_price REAL NOT NULL CHECK (min_price >= 0),
    location TEXT,
    harvest_date TEXT, -- Stored as ISO8601 string (YYYY-MM-DD)
    status TEXT DEFAULT 'available' NOT NULL CHECK (status IN ('available', 'pending', 'sold', 'donated', 'expired'))
);

-- 4. TRANSACTIONS TABLE
CREATE TABLE transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    buyer_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
    listing_id INTEGER NOT NULL REFERENCES listings(listing_id) ON DELETE RESTRICT,
    quantity REAL NOT NULL CHECK (quantity > 0),
    total_price REAL NOT NULL CHECK (total_price >= 0),
    donation_amount REAL DEFAULT 0.00 NOT NULL CHECK (donation_amount >= 0),
    transaction_date TEXT DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- 5. DONATIONS TABLE
CREATE TABLE donations (
    donation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id INTEGER REFERENCES transactions(transaction_id) ON DELETE SET NULL,
    food_bank_id INTEGER NOT NULL REFERENCES food_bank(food_bank_id) ON DELETE RESTRICT,
    amount REAL NOT NULL CHECK (amount >= 0),
    date TEXT DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- CREATE INDEXES FOR PERFORMANCE OPTIMIZATION
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_listings_farmer ON listings(farmer_id);
CREATE INDEX idx_listings_status ON listings(status);
CREATE INDEX idx_transactions_buyer ON transactions(buyer_id);
CREATE INDEX idx_transactions_listing ON transactions(listing_id);
CREATE INDEX idx_donations_food_bank ON donations(food_bank_id);