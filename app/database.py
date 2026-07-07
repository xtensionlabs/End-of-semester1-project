"""
database.py — Core Data Layer
================================
Member  : Otieno, David Abel
Module  : Core Infrastructure & Database
Team    : Lab 2, Group 5 

Purpose
-------
Every piece of data in the Agri-Tech Marketplace lives in a SQLite database
file called market.db.  This module is the ONLY place in the entire project
that talks directly to that file — every other module imports and calls these
functions instead of writing raw SQL themselves.

This "single responsibility" design means:
  - If we ever swap SQLite for another database, we only change this one file.
  - Every SQL injection risk is contained here and neutralised with
    parameterized queries.
  - Error handling for database failures lives in one place.

Database Tables (defined inside init_db)
-----------------------------------------
  users        — farmers, buyers, admins; stores hashed passwords and roles
  food_bank    — registry of partner food banks and their cumulative totals
  listings     — crop batches posted by farmers (crop, qty, price, location)
  transactions — completed purchase records (buyer, listing, qty, price, donation)
  donations    — itemised donation ledger linking transactions to food banks

Technical Concepts Demonstrated
---------------------------------
  FUNCTIONS        — five named CRUD helper functions, each with clear
                     parameters and a documented return value.
  DATA STORAGE     — insert_data() constructs and executes a parameterized
                     INSERT statement; update_data() does the same for UPDATE.
  DATA RETRIEVAL   — fetch_one() and fetch_all() execute SELECT queries and
                     return results as Python dicts (not raw sqlite3.Row objects).
  ITERATIVE        — for loops in insert_data, update_data, delete_data build
                     dynamic SQL clauses by iterating over dict keys.
  SELECTION        — if/else guards in fetch functions handle the case where
                     a query returns no rows.
  ERROR HANDLING   — every function wraps its SQL execution in try/except
                     sqlite3.Error so a database failure returns None or []
                     instead of crashing the application.
  VARIABLE DECL.   — columns, placeholders, query, combined_params are all
                     clearly named intermediate variables that show each step
                     of the dynamic SQL construction.
  TYPE CASTING     — dict(row) converts a sqlite3.Row object to a plain
                     Python dict so callers can access columns by key name.
"""

import sqlite3   # Python's built-in SQLite interface — no external install needed

# ---------------------------------------------------------------------------
# DATABASE FILE NAME
# Using a module-level constant makes it easy to change the path in one place.
# The file is created in the current working directory (wherever main.py runs).
# ---------------------------------------------------------------------------
DB_NAME = "market.db"   # str — relative path to the SQLite database file


# ===========================================================================
# SECTION 1 — CONNECTION HELPER
# ===========================================================================

def get_db_connection():
    """
    Open and return a connection to the SQLite database.

    Configuration applied to every connection
    -------------------------------------------
    foreign_keys = ON   — SQLite does NOT enforce foreign keys by default.
                          We enable it so that deleting a user also cascades
                          to their listings (as specified in the schema).
    row_factory         — Tells sqlite3 to return rows as sqlite3.Row objects,
                          which behave like dicts (access by column name, not
                          by numeric index).

    Returns
    -------
    sqlite3.Connection

    This function is called at the start of every CRUD function below.
    Using a fresh connection per operation keeps the code simple and avoids
    stale connection bugs in a long-running application.
    """
    conn = sqlite3.connect(DB_NAME)   # open (or create) the .db file

    # Enforce foreign key constraints — must be done once per connection.
    conn.execute("PRAGMA foreign_keys = ON;")

    # row_factory: makes cursor.fetchone() / fetchall() return sqlite3.Row
    # objects instead of plain tuples so we can do row['username'] instead
    # of row[0].
    conn.row_factory = sqlite3.Row

    return conn


# ===========================================================================
# SECTION 2 — DATABASE INITIALISATION
# ===========================================================================

def init_db():
    """
    Create all application tables and indexes if they don't already exist.

    Uses CREATE TABLE IF NOT EXISTS so this function is safe to call on
    every application startup — it only creates tables on the very first run.

    Table schemas
    -------------
    users
      user_id       : INTEGER PRIMARY KEY AUTOINCREMENT
      username      : TEXT UNIQUE NOT NULL
      password      : TEXT NOT NULL          (SHA-256 hash, never plain text)
      role          : TEXT CHECK (role IN ('farmer','buyer','food_bank','admin'))
      location      : TEXT
      phone         : TEXT
      date_joined   : TEXT DEFAULT CURRENT_TIMESTAMP

    food_bank
      food_bank_id       : INTEGER PRIMARY KEY AUTOINCREMENT
      user_id            : INTEGER REFERENCES users  (optional — for web login later)
      name               : TEXT NOT NULL
      location           : TEXT
      total_food_saved_kg: REAL DEFAULT 0.00  CHECK >= 0

    listings
      listing_id  : INTEGER PRIMARY KEY AUTOINCREMENT
      farmer_id   : INTEGER REFERENCES users ON DELETE CASCADE
      crop_name   : TEXT NOT NULL
      quantity_kg : REAL  CHECK >= 0
      min_price   : REAL  CHECK >= 0
      location    : TEXT
      harvest_date: TEXT
      status      : TEXT CHECK (status IN ('available','pending','sold','donated','expired'))

    transactions
      transaction_id : INTEGER PRIMARY KEY AUTOINCREMENT
      buyer_id       : INTEGER REFERENCES users
      listing_id     : INTEGER REFERENCES listings
      quantity       : REAL  CHECK > 0
      total_price    : REAL  CHECK >= 0
      donation_amount: REAL  DEFAULT 0.00  CHECK >= 0
      transaction_date: TEXT DEFAULT CURRENT_TIMESTAMP

    donations
      donation_id    : INTEGER PRIMARY KEY AUTOINCREMENT
      transaction_id : INTEGER REFERENCES transactions (nullable)
      food_bank_id   : INTEGER REFERENCES food_bank
      amount         : REAL  CHECK >= 0
      date           : TEXT  DEFAULT CURRENT_TIMESTAMP
    """
    # The entire schema is a single string passed to executescript().
    # executescript() runs multiple SQL statements separated by semicolons.
    schema = """
    CREATE TABLE IF NOT EXISTS users (
        user_id     INTEGER PRIMARY KEY AUTOINCREMENT,
        username    TEXT    UNIQUE NOT NULL,
        password    TEXT    NOT NULL,
        role        TEXT    NOT NULL
                    CHECK (role IN ('farmer', 'buyer', 'food_bank', 'admin')),
        location    TEXT,
        phone       TEXT,
        date_joined TEXT    DEFAULT CURRENT_TIMESTAMP NOT NULL
    );

    CREATE TABLE IF NOT EXISTS food_bank (
        food_bank_id        INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id             INTEGER UNIQUE REFERENCES users(user_id)
                            ON DELETE SET NULL,
        name                TEXT    NOT NULL,
        location            TEXT,
        total_food_saved_kg REAL    DEFAULT 0.00 NOT NULL
                            CHECK (total_food_saved_kg >= 0)
    );

    CREATE TABLE IF NOT EXISTS listings (
        listing_id  INTEGER PRIMARY KEY AUTOINCREMENT,
        farmer_id   INTEGER NOT NULL
                    REFERENCES users(user_id) ON DELETE CASCADE,
        crop_name   TEXT    NOT NULL,
        quantity_kg REAL    NOT NULL CHECK (quantity_kg >= 0),
        min_price   REAL    NOT NULL CHECK (min_price   >= 0),
        location    TEXT,
        harvest_date TEXT,
        status      TEXT    DEFAULT 'available' NOT NULL
                    CHECK (status IN
                           ('available','pending','sold','donated','expired'))
    );

    CREATE TABLE IF NOT EXISTS transactions (
        transaction_id  INTEGER PRIMARY KEY AUTOINCREMENT,
        buyer_id        INTEGER NOT NULL
                        REFERENCES users(user_id)    ON DELETE RESTRICT,
        listing_id      INTEGER NOT NULL
                        REFERENCES listings(listing_id) ON DELETE RESTRICT,
        quantity        REAL    NOT NULL CHECK (quantity       > 0),
        total_price     REAL    NOT NULL CHECK (total_price    >= 0),
        donation_amount REAL    DEFAULT 0.00 NOT NULL
                        CHECK (donation_amount >= 0),
        transaction_date TEXT   DEFAULT CURRENT_TIMESTAMP NOT NULL
    );

    CREATE TABLE IF NOT EXISTS donations (
        donation_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_id INTEGER REFERENCES transactions(transaction_id)
                       ON DELETE SET NULL,
        food_bank_id   INTEGER NOT NULL
                       REFERENCES food_bank(food_bank_id) ON DELETE RESTRICT,
        amount         REAL    NOT NULL CHECK (amount >= 0),
        date           TEXT    DEFAULT CURRENT_TIMESTAMP NOT NULL
    );

    -- INDEXES: speed up the most frequent lookup patterns.
    CREATE INDEX IF NOT EXISTS idx_users_role      ON users(role);
    CREATE INDEX IF NOT EXISTS idx_listings_status ON listings(status);
    """

    # Execute the schema inside a connection context manager.
    # The `with` statement auto-commits on success and auto-rolls-back on error.
    with get_db_connection() as conn:
        conn.executescript(schema)
        conn.commit()

    print("Database initiated successfully.")


# ===========================================================================
# SECTION 3 — CRUD HELPER FUNCTIONS
# CRUD = Create, Read, Update, Delete — the four fundamental data operations.
# Each function builds a parameterized SQL statement DYNAMICALLY from a dict,
# so we never have to write a new SQL string when adding a new table column.
# ===========================================================================

def insert_data(table, data_dict):
    """
    Insert one row into `table` using the column-value pairs in `data_dict`.

    How it works — step by step
    ----------------------------
    1. Extract the column names from data_dict.keys().
    2. Build the VALUES clause as a string of "?" placeholders — one per column.
    3. Combine into a full INSERT statement string.
    4. Execute with the dict's values as the parameter tuple.
    5. Return the auto-assigned primary key of the new row (lastrowid).

    Parameters
    ----------
    table     : str   — name of the target table, e.g. "users"
    data_dict : dict  — column names mapped to their values,
                        e.g. {'username': 'alice', 'role': 'farmer', ...}

    Returns
    -------
    int | None — the new row's primary key on success, None on failure

    Variable declarations demonstrated
    ------------------------------------
    columns      : str  — "username, role, location"
    placeholders : str  — "?, ?, ?"
    query        : str  — the complete INSERT SQL statement

    Iterative structure demonstrated
    ---------------------------------
    ", ".join([...]) and ", ".join(["?"] * n) are both list-based iterations
    that build comma-separated strings from sequences.

    Error handling demonstrated
    ----------------------------
    sqlite3.Error covers all database errors (constraint violations, locked
    database, etc.).  Returning None instead of raising lets the caller
    decide how to handle the failure.
    """
    # VARIABLE DECLARATION: build the column list string.
    # data_dict.keys() might be ['username', 'role', 'location']
    # ", ".join() turns that into "username, role, location"
    columns = ", ".join(data_dict.keys())   # str

    # VARIABLE DECLARATION: build the VALUES placeholder string.
    # ["?"] * len(data_dict) creates ["?", "?", "?"] — one per column.
    # ", ".join() turns that into "?, ?, ?"
    placeholders = ", ".join(["?"] * len(data_dict))   # str

    # VARIABLE DECLARATION: assemble the complete SQL statement.
    # Using f-string for table/column names (safe — they come from our code,
    # not from user input).  Values are always passed as parameters (?).
    query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders});"

    try:
        # Use a context manager — auto-commits if no exception is raised.
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Execute with a tuple of values — the ? placeholders prevent
            # SQL injection by treating the values as data, not SQL code.
            cursor.execute(query, tuple(data_dict.values()))
            conn.commit()
            # lastrowid is the integer primary key assigned to the new row.
            return cursor.lastrowid   # int

    except sqlite3.Error as e:
        # ERROR HANDLING: print the error but do not crash the app.
        # Return None so the caller can check `if result is None`.
        print(f"Error executing dynamic insert on {table}: {e}")
        return None


def fetch_one(query, params=()):
    """
    Execute a SELECT query and return exactly one matching row as a dict.

    Parameters
    ----------
    query  : str   — SQL query with ? placeholders,
                     e.g. "SELECT * FROM users WHERE username = ?"
    params : tuple — values to bind to the placeholders,
                     e.g. ("alice",)

    Returns
    -------
    dict | None — the first matching row as a column→value dict,
                  or None if no rows matched.

    Type casting demonstrated
    --------------------------
    cursor.fetchone() returns a sqlite3.Row object (which behaves like a
    tuple by default).  dict(row) converts it to a genuine Python dict so
    callers can do result['username'] and result.get('location', '').

    Selection structure demonstrated
    ----------------------------------
    `return dict(row) if row else None` is a conditional expression:
    - If fetchone() found a row, convert it to dict and return it.
    - If fetchone() returned None (no match), return None explicitly.

    Error handling demonstrated
    ----------------------------
    Returns None on any sqlite3.Error so the caller gets a predictable
    "nothing found" response rather than an unhandled exception.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Parameterized execution: ? placeholders are filled by sqlite3,
            # never by string concatenation, blocking SQL injection.
            cursor.execute(query, params)
            row = cursor.fetchone()   # sqlite3.Row | None

            # SELECTION + TYPE CAST: convert to dict if a row was found.
            return dict(row) if row else None

    except sqlite3.Error as e:
        print(f"Error fetching record: {e}")
        return None   # caller checks for None to detect failure


def fetch_all(query, params=()):
    """
    Execute a SELECT query and return ALL matching rows as a list of dicts.

    Parameters
    ----------
    query  : str   — SQL SELECT query with ? placeholders
    params : tuple — values to bind to the placeholders

    Returns
    -------
    list of dict — every matching row converted to a column→value dict.
                   Returns an empty list [] if no rows match or on error.

    Iterative structure demonstrated
    ---------------------------------
    The list comprehension `[dict(row) for row in cursor.fetchall()]` is a
    compact for-loop that iterates over every sqlite3.Row object returned
    by fetchall() and converts each one to a plain Python dict.

    Type casting demonstrated
    --------------------------
    Same dict(row) conversion as fetch_one() — every row is cast from
    sqlite3.Row to dict so callers use column names, not numeric indexes.

    Error handling demonstrated
    ----------------------------
    Returns an empty list on sqlite3.Error so callers can safely do
    `for row in fetch_all(...)` even when the query fails — they just get
    zero iterations instead of an unhandled exception.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)   # parameterized — safe from injection

            # ITERATIVE + TYPE CAST: list comprehension converts each row.
            # fetchall() returns a list of sqlite3.Row objects.
            # dict(row) converts each one to a Python dict.
            return [dict(row) for row in cursor.fetchall()]

    except sqlite3.Error as e:
        print(f"Error fetching records: {e}")
        return []   # empty list — safe for callers to iterate over


def update_data(table, updates, condition):
    """
    Execute a parameterized UPDATE statement on `table`.

    Parameters
    ----------
    table     : str   — table to update, e.g. "listings"
    updates   : dict  — columns to change and their new values,
                        e.g. {'status': 'sold', 'quantity_kg': 0}
    condition : dict  — WHERE clause columns and values (AND logic),
                        e.g. {'listing_id': 7}

    Returns
    -------
    int — the number of rows modified (0 if nothing matched the condition)

    How the SQL is built
    ---------------------
    updates   = {'status': 'sold'}    → set_clause   = "status = ?"
    condition = {'listing_id': 7}     → where_clause = "listing_id = ?"
    Full query: "UPDATE listings SET status = ? WHERE listing_id = ?;"
    Params:     ('sold', 7)

    Variable declarations demonstrated
    ------------------------------------
    set_clause      : str  — the SET portion of the UPDATE statement
    where_clause    : str  — the WHERE portion
    query           : str  — the complete UPDATE SQL statement
    combined_params : tuple — updates values followed by condition values

    Iterative structure demonstrated
    ---------------------------------
    Both ", ".join() calls iterate over dict keys to build the clause strings.

    Error handling demonstrated
    ----------------------------
    Returns 0 on sqlite3.Error (0 rows modified) — a safe, checkable value.
    """
    # VARIABLE DECLARATION: build "col1 = ?, col2 = ?" from updates keys.
    # This is an f-string inside a list comprehension inside join() —
    # it iterates over updates.keys() to produce one "col = ?" per column.
    set_clause = ", ".join([f"{col} = ?" for col in updates.keys()])   # str

    # VARIABLE DECLARATION: build "col = ?" for the WHERE clause similarly.
    where_clause = " AND ".join([f"{col} = ?" for col in condition.keys()])   # str

    # VARIABLE DECLARATION: assemble the full UPDATE statement.
    query = f"UPDATE {table} SET {set_clause} WHERE {where_clause};"   # str

    # VARIABLE DECLARATION: combine both value tuples into one.
    # sqlite3 fills ? placeholders left-to-right, so SET values come first,
    # then WHERE values.
    combined_params = tuple(updates.values()) + tuple(condition.values())

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, combined_params)
            conn.commit()
            # rowcount is the number of rows that matched the WHERE clause.
            return cursor.rowcount   # int

    except sqlite3.Error as e:
        print(f"Error executing dynamic update on {table}: {e}")
        return 0   # 0 rows modified — safe for callers to check


def delete_data(table, condition):
    """
    Execute a parameterized DELETE statement on `table`.

    Parameters
    ----------
    table     : str   — table to delete from, e.g. "listings"
    condition : dict  — WHERE clause columns and values,
                        e.g. {'listing_id': 3}

    Returns
    -------
    int — the number of rows deleted (0 if nothing matched the condition)

    How the SQL is built
    ---------------------
    condition = {'listing_id': 3}
    where_clause = "listing_id = ?"
    Full query: "DELETE FROM listings WHERE listing_id = ?;"
    Params:     (3,)

    Error handling demonstrated
    ----------------------------
    Returns 0 on sqlite3.Error — callers can check `if result == 0` to
    detect that the deletion did not succeed.
    """
    # Build the WHERE clause from the condition dict keys.
    where_clause = " AND ".join([f"{col} = ?" for col in condition.keys()])
    query = f"DELETE FROM {table} WHERE {where_clause};"

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(condition.values()))
            conn.commit()
            return cursor.rowcount   # int: rows deleted

    except sqlite3.Error as e:
        print(f"Error executing dynamic delete on {table}: {e}")
        return 0


# ===========================================================================
# SECTION 4 — SAMPLE DATA SEEDER
# Populates the database with realistic demo data on the very first run.
# This means the grader/presenter can log in and use the app immediately
# without having to register accounts or create listings manually.
# ===========================================================================

def seed_sample_data():
    """
    Insert demo farmers, buyers, listings, and a food bank on first run.

    Idempotency
    -----------
    Before inserting anything, we COUNT(*) the users table.  If any users
    already exist, we return immediately — this makes the function safe to
    call on every startup without creating duplicates.

    Demo accounts created
    ----------------------
    Admin   : username="admin"             password="admin123"
    Farmers : john_kamau, grace_wanjiku, peter_ochieng, mary_atieno, samuel_kimani
              All farmer passwords: "farmer123"
    Buyers  : nairobi_wholesale, coast_traders, rift_valley_market,
              western_buyers_co, highland_grocers
              All buyer passwords: "buyer123"
    Listings: 10 crop listings spread across all 5 farmers
    Food bank: "Agri-Tech Food Bank" based in Nairobi

    Iterative structure demonstrated
    ---------------------------------
    Two for loops iterate over the farmers_data and buyers_data lists to
    insert each account with a single insert_data() call per iteration.
    A third for loop inserts the 10 sample listings.

    Functions demonstrated
    -----------------------
    _h() is a nested helper function (defined inside seed_sample_data)
    that hashes a password string.  Defining it locally keeps the hashing
    logic close to where it is used without polluting the module namespace.
    """
    # DATA RETRIEVAL: check if we've already seeded.
    existing = fetch_one("SELECT COUNT(*) AS cnt FROM users")
    if existing and existing['cnt'] > 0:
        return   # Data already exists — skip seeding to avoid duplicates

    # IMPORT: hashlib is only needed here, so import it locally.
    import hashlib

    def _h(password):
        """
        Hash a plain-text password with SHA-256 and return the hex digest.

        Parameters
        ----------
        password : str — plain text password to hash

        Returns
        -------
        str — 64-character hexadecimal hash string

        This is a nested function — it is only accessible inside
        seed_sample_data() and cannot be called from outside this function.
        Passwords are NEVER stored in plain text; only the hash is saved.
        """
        return hashlib.sha256(password.encode()).hexdigest()

    # ── Food bank ──────────────────────────────────────────────────────────
    # The food bank record must exist before any donations can reference it
    # (foreign key constraint: donations.food_bank_id → food_bank.food_bank_id).
    insert_data("food_bank", {
        "name":                "Agri-Tech Food Bank",
        "location":            "Nairobi",
        "total_food_saved_kg": 0,   # starts at zero; increments with each sale
    })

    # ── Admin account ──────────────────────────────────────────────────────
    insert_data("users", {
        "username": "admin",
        "password": _h("admin123"),  # stored as hash, never as plain text
        "role":     "admin",
        "location": "Nairobi",
        "phone":    "+254700000000",
    })

    # ── Sample farmers ─────────────────────────────────────────────────────
    # Data type: list of tuples — each tuple holds (username, location, phone).
    farmers_data = [
        ("john_kamau",    "Nakuru",  "+254711000001"),
        ("grace_wanjiku", "Nyeri",   "+254711000002"),
        ("peter_ochieng", "Kisumu",  "+254711000003"),
        ("mary_atieno",   "Eldoret", "+254711000004"),
        ("samuel_kimani", "Meru",    "+254711000005"),
    ]

    # ITERATIVE STRUCTURE — for loop:
    # Insert each farmer and collect the auto-assigned primary keys so we
    # can link listings to the correct farmer_id.
    farmer_ids = []   # list of int primary keys
    for username, loc, phone in farmers_data:
        fid = insert_data("users", {
            "username": username,
            "password": _h("farmer123"),   # same demo password for all farmers
            "role":     "farmer",          # lowercase to match schema CHECK constraint
            "location": loc,
            "phone":    phone,
        })
        farmer_ids.append(fid)   # int — the new user_id assigned by SQLite

    # ── Sample buyers ──────────────────────────────────────────────────────
    buyers_data = [
        ("nairobi_wholesale",  "Nairobi", "+254722000001"),
        ("coast_traders",      "Mombasa", "+254722000002"),
        ("rift_valley_market", "Nakuru",  "+254722000003"),
        ("western_buyers_co",  "Kisumu",  "+254722000004"),
        ("highland_grocers",   "Nyeri",   "+254722000005"),
    ]

    # ITERATIVE STRUCTURE — for loop: insert each buyer.
    for username, loc, phone in buyers_data:
        insert_data("users", {
            "username": username,
            "password": _h("buyer123"),
            "role":     "buyer",
            "location": loc,
            "phone":    phone,
        })

    # ── Sample listings ────────────────────────────────────────────────────
    # Each tuple: (farmer_id, crop_name, quantity_kg, min_price, location, harvest_date)
    # Data types: int, str, float, float, str, str
    listings_data = [
        (farmer_ids[0], "Maize",      500.0,  35.0,  "Nakuru",  "2026-06-20"),
        (farmer_ids[0], "Potatoes",   300.0,  25.0,  "Nakuru",  "2026-06-25"),
        (farmer_ids[1], "Tomatoes",   150.0,  60.0,  "Nyeri",   "2026-07-01"),
        (farmer_ids[1], "Cabbage",    200.0,  20.0,  "Nyeri",   "2026-06-28"),
        (farmer_ids[2], "Beans",      400.0,  80.0,  "Kisumu",  "2026-07-05"),
        (farmer_ids[2], "Sorghum",    350.0,  30.0,  "Kisumu",  "2026-06-30"),
        (farmer_ids[3], "Wheat",      600.0,  45.0,  "Eldoret", "2026-06-15"),
        (farmer_ids[3], "Sunflower",  250.0,  90.0,  "Eldoret", "2026-07-10"),
        (farmer_ids[4], "Tea Leaves", 100.0, 200.0,  "Meru",    "2026-07-03"),
        (farmer_ids[4], "Avocado",    180.0,  50.0,  "Meru",    "2026-07-08"),
    ]

    # ITERATIVE STRUCTURE — for loop: insert each listing.
    for farmer_id, crop, qty, price, loc, harvest in listings_data:
        insert_data("listings", {
            "farmer_id":    farmer_id,   # int — links listing to its owner
            "crop_name":    crop,        # str
            "quantity_kg":  qty,         # float
            "min_price":    price,       # float — KSH per kg
            "location":     loc,         # str
            "harvest_date": harvest,     # str — ISO 8601 date format
            "status":       "available", # str — must match schema CHECK constraint
        })

    print("Sample data seeded: 1 admin, 5 farmers, 5 buyers, 10 listings, 1 food bank.")


# ===========================================================================
# SECTION 5 — DIRECT EXECUTION TEST
# Running `python database.py` directly exercises all CRUD helpers so you
# can verify the database layer in isolation without starting the full app.
# ===========================================================================
if __name__ == "__main__":
    init_db()

    print("\n--- Testing insert_data ---")
    new_user = {
        "username": "organic_agri",
        "password": "hashed_password_abc",
        "role":     "farmer",
        "location": "Nairobi North",
        "phone":    "+254700000000",
    }
    farmer_id = insert_data("users", new_user)
    print(f"Inserted test farmer. Assigned ID: {farmer_id}")

    print("\n--- Testing fetch_all ---")
    all_farmers = fetch_all("SELECT * FROM users WHERE role = ?;", ("farmer",))
    print(f"Farmers found: {len(all_farmers)}")

    if farmer_id:
        print("\n--- Testing update_data ---")
        rows_changed = update_data(
            table="users",
            updates={"location": "Nairobi West-Central"},
            condition={"user_id": farmer_id},
        )
        print(f"Rows updated: {rows_changed}")

        print("\n--- Testing fetch_one ---")
        updated = fetch_one(
            "SELECT username, location FROM users WHERE user_id = ?;",
            (farmer_id,)
        )
        print(f"Updated record: {updated}")

        print("\n--- Testing delete_data ---")
        rows_deleted = delete_data("users", {"user_id": farmer_id})
        print(f"Rows deleted: {rows_deleted}")
