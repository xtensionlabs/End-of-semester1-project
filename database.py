import sqlite3

DB_NAME = "market.db"

def get_db_connection():
    """
    Establishes and returns a connection to 'market.db'.
    Enforces foreign key constraint checks and configures rows to be 
    accessed as dictionaries for seamless data manipulation.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row  # Enables column fetching by name (e.g., row['username'])
    return conn


def init_db():
    """
    Creates all core application tables and optimization indexes 
    if they do not already exist in market.db.
    """
    schema = """
    -- 1. USERS TABLE
    -- Registers farmers, buyers, and food banks alongside authentication hashes.
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK (role IN ('farmer', 'buyer', 'food_bank', 'admin')),
        location TEXT,
        phone TEXT,
        date_joined TEXT DEFAULT CURRENT_TIMESTAMP NOT NULL
    );

    -- 2. FOOD BANK REGISTRY TABLE
    -- A ledger tracking specific regional food banks and aggregate salvaged food mass.
    CREATE TABLE IF NOT EXISTS food_bank (
        food_bank_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE REFERENCES users(user_id) ON DELETE SET NULL,
        name TEXT NOT NULL,
        location TEXT,
        total_food_saved_kg REAL DEFAULT 0.00 NOT NULL CHECK (total_food_saved_kg >= 0)
    );

    -- 3. LISTINGS TABLE
    -- Tracks batches of produce posted for public matching or surplus diversion.
    CREATE TABLE IF NOT EXISTS listings (
        listing_id INTEGER PRIMARY KEY AUTOINCREMENT,
        farmer_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
        crop_name TEXT NOT NULL,
        quantity_kg REAL NOT NULL CHECK (quantity_kg >= 0),
        min_price REAL NOT NULL CHECK (min_price >= 0),
        location TEXT,
        harvest_date TEXT,
        status TEXT DEFAULT 'available' NOT NULL CHECK (status IN ('available', 'pending', 'sold', 'donated', 'expired'))
    );

    -- 4. TRANSACTIONS TABLE
    -- Captures execution quantities, gross costs, and structural cross-subsidies.
    CREATE TABLE IF NOT EXISTS transactions (
        transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        buyer_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
        listing_id INTEGER NOT NULL REFERENCES listings(listing_id) ON DELETE RESTRICT,
        quantity REAL NOT NULL CHECK (quantity > 0),
        total_price REAL NOT NULL CHECK (total_price >= 0),
        donation_amount REAL DEFAULT 0.00 NOT NULL CHECK (donation_amount >= 0),
        transaction_date TEXT DEFAULT CURRENT_TIMESTAMP NOT NULL
    );

    -- 5. DONATIONS TABLE
    -- Direct logging linking individual transactions or independent collections to food banks.
    CREATE TABLE IF NOT EXISTS donations (
        donation_id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_id INTEGER REFERENCES transactions(transaction_id) ON DELETE SET NULL,
        food_bank_id INTEGER NOT NULL REFERENCES food_bank(food_bank_id) ON DELETE RESTRICT,
        amount REAL NOT NULL CHECK (amount >= 0),
        date TEXT DEFAULT CURRENT_TIMESTAMP NOT NULL
    );

    -- PERFORMANCE OPTIMIZATION INDEXES
    CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
    CREATE INDEX IF NOT EXISTS idx_listings_status ON listings(status);
    """
    with get_db_connection() as conn:
        conn.executescript(schema)
        conn.commit()
    print("Database initiated successfully.")


# ==========================================
# REUSABLE PARAMETERIZED CRUD HELPERS
# ==========================================

def insert_data(table, data_dict):
    """
    Dynamically generates a secure parameterized INSERT statement.
    - table: Target table name (string)
    - data_dict: Dictionary containing column-value pairs (e.g., {'username': 'johndoe', ...})
    """
    columns = ", ".join(data_dict.keys())
    placeholders = ", ".join(["?"] * len(data_dict))
    query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders});"
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(data_dict.values()))
            conn.commit()
            return cursor.lastrowid
    except sqlite3.Error as e:
        print(f"Error executing dynamic insert on {table}: {e}")
        return None


def fetch_one(query, params=()):
    """
    Executes an explicit lookup query and fetches exactly one matching record.
    - query: SQL query string containing '?' placeholders
    - params: Tuple containing user data to safely bind to the parameters
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Error fetching record: {e}")
        return None


def fetch_all(query, params=()):
    """
    Executes an explicit lookup query and returns all matching records.
    - query: SQL query string containing '?' placeholders
    - params: Tuple containing user data to safely bind to the parameters
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Error fetching records: {e}")
        return []


def update_data(table, updates, condition):
    """
    Dynamically builds a secure parameterized UPDATE declaration.
    - table: Target table name (string)
    - updates: Dictionary containing column-value pairs to set (e.g., {'status': 'sold'})
    - condition: Dictionary specifying the matching WHERE criteria (e.g., {'listing_id': 1})
    """
    set_clause = ", ".join([f"{col} = ?" for col in updates.keys()])
    where_clause = " AND ".join([f"{col} = ?" for col in condition.keys()])
    query = f"UPDATE {table} SET {set_clause} WHERE {where_clause};"
    
    # Combined positional parameter passing order: values to change first, conditional values second
    combined_params = tuple(updates.values()) + tuple(condition.values())
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, combined_params)
            conn.commit()
            return cursor.rowcount  # Returns the total amount of altered records
    except sqlite3.Error as e:
        print(f"Error executing dynamic update on {table}: {e}")
        return 0


def delete_data(table, condition):
    """
    Dynamically builds a secure parameterized DELETE configuration.
    - table: Target table name (string)
    - condition: Dictionary specifying structural target parameters (e.g., {'user_id': 4})
    """
    where_clause = " AND ".join([f"{col} = ?" for col in condition.keys()])
    query = f"DELETE FROM {table} WHERE {where_clause};"
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(condition.values()))
            conn.commit()
            return cursor.rowcount
    except sqlite3.Error as e:
        print(f"Error executing dynamic delete on {table}: {e}")
        return 0


# ==========================================
# SANITY CHECK / DEMONSTRATION WORKFLOW
# ==========================================
if __name__ == "__main__":
    init_db()

    print("\n--- Testing Safe Dynamic Insert Helper ---")
    new_user = {
        "username": "organic_agri",
        "password": "hashed_password_abc",
        "role": "farmer",
        "location": "Nairobi North",
        "phone": "+254700000000"
    }
    farmer_id = insert_data("users", new_user)
    print(f"Inserted Farmer. Assigned ID: {farmer_id}")

    print("\n--- Testing Safe Query Fetch Multi-Row Helper ---")
    all_farmers = fetch_all("SELECT * FROM users WHERE role = ?;", ("farmer",))
    print(f"Farmers query result: {all_farmers}")

    if farmer_id:
        print("\n--- Testing Safe Dynamic Update Helper ---")
        updates_applied = update_data(
            table="users", 
            updates={"location": "Nairobi West-Central"}, 
            condition={"user_id": farmer_id}
        )
        print(f"Rows modified by update query: {updates_applied}")

        print("\n--- Testing Single Row Lookup ---")
        updated_profile = fetch_one("SELECT username, location FROM users WHERE user_id = ?;", (farmer_id,))
        print(f"Updated User Info: {updated_profile}")

        print("\n--- Testing Safe Dynamic Delete Helper ---")
        deleted_count = delete_data("users", {"user_id": farmer_id})
        print(f"Rows removed by delete query: {deleted_count}")