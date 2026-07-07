"""
ui.py — Interactive Terminal Interface
========================================
Member  : Maina, Njeri
Module  : UI/UX + Reporting & Dashboard
Team    : Lab 2, Group 5 —

Purpose
-------
This file is the single "shell" that ties every team module together into one
cohesive, role-based terminal application.  It owns three responsibilities:
  1. Presenting menus and collecting user input (Interactive I/O)
  2. Deciding which features to show based on who is logged in (Selection)
  3. Keeping the application alive between actions (Iteration)

Technical Concepts Demonstrated
---------------------------------
  INTERACTIVE I/O      — Prompt.ask() collects validated keyboard input;
                         console.print() renders rich, coloured output.
  ITERATIVE STRUCTURES — `while True` in run_application() is the main event
                         loop.  A second `while` drives the loading-bar
                         animation.  A `for` loop builds every menu table.
  SELECTION STRUCTURES — Nested if/elif chains route each menu choice AND
                         route each user role to the correct sub-menu.
  FUNCTIONS            — Every menu is its own named function; shared logic
                         (_render_menu, _run_safely, _wait) is factored out
                         so it is written once and reused everywhere.
  ERROR HANDLING       — _run_safely() wraps every action in try/except so a
                         single crash in one feature never kills the whole app.
  DATA TYPES & CASTING — role is read as str; user_id is cast to int before
                         being forwarded to module functions that expect an int.
"""

import os       # os.system("cls") — clear screen between menu renders
import sys      # sys.exit()       — clean application shutdown
import time     # time.sleep()     — pacing for the loading-bar animation

from rich.console import Console
from rich.panel   import Panel
from rich.table   import Table
from rich.prompt  import Prompt
from rich.progress import (
    Progress, SpinnerColumn, BarColumn, TextColumn, TaskProgressColumn
)

# ── Team module imports ────────────────────────────────────────────────────
# Each import gives this file access to all public functions in that module.
import database       # Member 1 — SQLite layer (init, seed, CRUD helpers)
import auth           # Member 2 — authentication (login, logout, roles)
import listings       # Member 3 — crop listing management
import products       # Member 3 — commodity catalogue
import search         # Member 4 — keyword / filter search engine
import matching       # Member 4 — smart location-based matching algorithm
import transactions   # Member 5 — purchase flow and transaction history
import donations      # Member 5 — food bank tracking and impact stats
import dashboard      # Member 6 — analytics dashboard and price alerts
import reports        # Member 6 — CSV / JSON / plain-text report exports

# Shared console instance — every print() in this file goes through Rich
# so colours, tables, and panels render consistently.
console = Console()


# ===========================================================================
# SECTION 1 — SCREEN CHROME
# Helpers that draw the persistent header, footer, and loading animation.
# These are called at the top of every loop iteration so the brand and
# session status are always visible regardless of which menu is active.
# ===========================================================================

def display_header():
    """
    Print the application title banner.

    Uses Rich markup ([bold white on green]) to produce a full-width
    colour bar.  Called once per loop iteration so the banner reappears
    after every action.
    """
    # Interactive output: console.print sends formatted text to the terminal.
    console.print(
        "[bold white on green]   AGRI-TECH DIGITAL MARKETPLACE v1.0   [/bold white on green]",
        justify="center",
    )
    console.print()   # blank line for visual breathing room


def display_footer(user_info=None):
    """
    Print a status bar showing who is logged in and their role.

    Parameters
    ----------
    user_info : dict | None
        The dict returned by auth.get_current_user().
        Pass None when no user is logged in.

    Data types demonstrated
    -----------------------
    user_info is either a dict (logged-in state) or None (logged-out state).
    We use a selection structure (if/else) to produce a different string
    for each case.
    """
    console.print()  # blank line above the footer bar

    # SELECTION: choose which status text to build based on login state.
    if user_info:
        # .capitalize() converts 'farmer' → 'Farmer' for display purposes
        # (the database stores roles in lowercase; we capitalise for the UI).
        status = (
            f"Logged in: {user_info['username']}"
            f"  |  Role: {user_info['role'].capitalize()}"
        )
    else:
        # No active session — prompt the visitor to register or log in.
        status = "Not logged in — Register or Log In to continue"

    # Interactive output: print the status bar in a blue background band.
    console.print(
        f"[bold white on blue]  {status}"
        f"  |  Use menu numbers to navigate  [/bold white on blue]",
        justify="center",
    )


def simulate_loading_bar(action_text):
    """
    Display a short animated progress bar during login / logout transitions.

    This is purely cosmetic — it gives the user visual feedback that
    something is happening rather than jumping straight to the next screen.

    Parameters
    ----------
    action_text : str
        Label shown beside the spinner, e.g. 'Signing in securely...'

    Iterative structure demonstrated
    ---------------------------------
    The `while not progress.finished` loop advances the bar by 5% every
    40 ms until it reaches 100%, then the Progress context manager exits.
    """
    console.print()

    # Rich Progress context manager — handles the live-updating display.
    with Progress(
        SpinnerColumn(),                            # animated spinner icon
        TextColumn("[cyan]{task.description}[/cyan]"),  # action label
        BarColumn(bar_width=40,
                  complete_style="green",
                  finished_style="bold green"),     # the fill bar itself
        TaskProgressColumn(),                       # percentage readout
        console=console,
    ) as progress:

        # Add a task with a total of 100 "units" (percent steps).
        task = progress.add_task(action_text, total=100)

        # ITERATIVE STRUCTURE — while loop:
        # Keep advancing the bar until the task reaches 100%.
        # Each iteration sleeps 40 ms then adds 5 percentage points.
        # Total duration ≈ 20 iterations × 40 ms = ~0.8 seconds.
        while not progress.finished:
            time.sleep(0.04)            # pause 40 milliseconds
            progress.update(task, advance=5)  # add 5% to the bar

    time.sleep(0.3)   # brief pause so the user can see the completed bar


def show_welcome_screen():
    """
    Render the public landing panel with the SDG mission statement.

    Shown on every iteration where no user is logged in, so the platform's
    purpose is immediately visible to anyone who opens the app.
    """
    # Interactive output: a Rich Panel acts as a styled text box with a border.
    console.print(Panel(
        "[bold green]Welcome to the Agri-Tech Digital Marketplace[/bold green]\n\n"
        "[italic cyan]Empowering Farmers.  "
        "Eliminating Middlemen.  Feeding Communities.[/italic cyan]\n\n"
        "[dim]Supporting:\n"
        "  SDG 1  — No Poverty              (fair farm-gate prices)\n"
        "  SDG 2  — Zero Hunger             (2% micro-donation to food banks)\n"
        "  SDG 8  — Decent Work & Growth    (direct digital market access)\n"
        "  SDG 12 — Responsible Consumption (reducing food waste)[/dim]",
        border_style="green",
        padding=(1, 4),
        title="[bold white]Home[/bold white]",
    ))
    console.print()


# ===========================================================================
# SECTION 2 — GENERIC UI HELPERS
# Reusable utilities used by all four menus (visitor, farmer, buyer, admin).
# Factoring these out means the logic is written once and never duplicated.
# ===========================================================================

def _render_menu(title, style, options):
    """
    Build a numbered menu table, print it, then prompt for a valid choice.

    Parameters
    ----------
    title   : str   — heading text rendered above the table
    style   : str   — Rich colour name for the option-number column
    options : list  — list of (number_str, description_str) tuples,
                      e.g. [("1", "Add listing"), ("2", "View listings")]

    Returns
    -------
    str  — the option number the user typed (always a member of valid_choices)

    Functions demonstrated
    ----------------------
    _render_menu() is a reusable function that accepts parameters and
    returns a value.  Every menu in this file calls it instead of
    re-implementing table construction and input validation each time.

    Iterative structure demonstrated
    ---------------------------------
    The `for` loop on line ~163 iterates over the `options` list.
    Each iteration unpacks one (number, label) pair and adds a row to
    the Rich table.  Without this loop we would need one table.add_row()
    call per option — duplicated code for every menu change.

    Interactive I/O demonstrated
    -----------------------------
    Prompt.ask() is Rich's validated input function.  Passing `choices`
    means it will ONLY accept strings that are in that list — any other
    input is rejected and the prompt repeats automatically, preventing
    invalid menu selections from reaching the if/elif routing logic.
    """
    # Build a Rich Table to display the numbered options in a styled box.
    table = Table(
        title=title,
        title_style=f"bold {style}",
        show_header=True,
        header_style=f"bold {style}",
        expand=True,          # stretch to the full terminal width
    )
    table.add_column("Option", style=style, width=8, justify="center")
    table.add_column("What would you like to do?")

    # ITERATIVE STRUCTURE — for loop:
    # Each pass through the loop handles one menu option.
    # `number` is a str like "1"; `label` is the description string.
    for number, label in options:
        table.add_row(number, label)   # add one row per option

    # Interactive output: print the completed table to the terminal.
    console.print(table)

    # Build the list of valid responses from the same options list.
    # This is a list comprehension — a compact for-loop that builds a list.
    # e.g. [("1","Add"), ("2","View")] → valid_choices = ["1", "2"]
    valid_choices = [num for num, _ in options]

    # INTERACTIVE INPUT — Prompt.ask():
    # Displays the question and blocks until the user types a valid choice.
    # `choices=valid_choices` makes Rich automatically re-prompt on bad input.
    # `show_choices=False` keeps the prompt clean (the table already shows them).
    return Prompt.ask(
        "\nType the number of your choice",
        choices=valid_choices,
        show_choices=False,
    )


def _run_safely(fn, *args, **kwargs):
    """
    Call a function and absorb any exception it raises.

    This is the application's primary defence against runtime crashes.
    Every menu action is wrapped here so that if a module has a bug,
    the user sees a friendly message and returns to the menu — the app
    never terminates unexpectedly.

    Parameters
    ----------
    fn       : callable — the function to call
    *args    : positional arguments forwarded to fn
    **kwargs : keyword arguments forwarded to fn

    Error handling demonstrated
    ----------------------------
    Two except clauses cover different failure categories:
      KeyboardInterrupt — user pressed Ctrl+C mid-flow (soft cancel)
      Exception         — any other runtime error (bug, DB failure, etc.)
    Both cases are handled gracefully; neither propagates up to crash the app.
    """
    try:
        # Attempt to call the function with whatever arguments were passed.
        fn(*args, **kwargs)

    except KeyboardInterrupt:
        # The user pressed Ctrl+C during input — treat as a voluntary cancel.
        # We do NOT re-raise, so the main while-loop continues normally.
        console.print("\n[yellow]Action cancelled.[/yellow]")

    except Exception as err:
        # Catch-all for any other runtime error (TypeError, ValueError,
        # sqlite3.Error, etc.).  Print a human-readable message and let
        # the loop bring the user back to the menu.
        console.print(
            f"\n[bold red]An unexpected error occurred:[/bold red] {err}"
        )
        console.print(
            "[dim]Please try again or contact your administrator.[/dim]"
        )


def _wait():
    """
    Pause the UI and wait for the user to press Enter.

    Called after every action (except logout) so the user has time to
    read the output before the screen is cleared and the menu redraws.

    Interactive I/O demonstrated
    -----------------------------
    Prompt.ask with default="" returns immediately when the user presses
    Enter without typing anything, making it a clean "press any key" pause.
    """
    Prompt.ask(
        "\n[dim]Press Enter to return to the menu[/dim]",
        default=""   # accept an empty response — user just presses Enter
    )


# ===========================================================================
# SECTION 3 — VISITOR MENU  (shown when no user is logged in)
# ===========================================================================

def handle_visitor_menu():
    """
    Present the public-facing menu to unauthenticated visitors.

    Options
    -------
    1. Register — create a new farmer or buyer account
    2. Log in   — authenticate an existing account
    3. Impact   — view global food bank stats (public, no login needed)
    4. Exit     — close the application

    Selection structure demonstrated
    ----------------------------------
    The if/elif chain below maps each numeric choice to a specific action.
    This is equivalent to a switch/case in other languages.  Only one
    branch executes per iteration because the conditions are mutually
    exclusive (a string can only equal one value at a time).
    """
    options = [
        ("1", "Register a new account"),
        ("2", "Log in to an existing account"),
        ("3", "View global food bank & donation impact"),
        ("4", "Exit the application"),
    ]
    # _render_menu prints the table and returns the validated choice string.
    choice = _render_menu("MAIN MENU", "green", options)

    # SELECTION STRUCTURE — if/elif chain:
    # Route the validated choice to the correct module function.
    if choice == "1":
        # auth.register() prompts for username, password, role, location, phone.
        _run_safely(auth.register)
        _wait()

    elif choice == "2":
        # auth.login() returns True on success, False on bad credentials.
        success = auth.login()
        if success:
            # Only animate if login succeeded — no point animating a failure.
            simulate_loading_bar("Signing in securely...")
        # If login failed, auth.login() already printed the error; loop continues.

    elif choice == "3":
        # The global impact view is intentionally public — even visitors can
        # see how much the platform has donated, which builds trust.
        _run_safely(donations.DonationManager().display_global_impact)
        _wait()

    elif choice == "4":
        # sys.exit(0) signals a clean shutdown (exit code 0 = success).
        console.print(
            "\n[bold green]"
            "Thank you for using the Agri-Tech Marketplace. Goodbye!"
            "[/bold green]"
        )
        sys.exit(0)


# ===========================================================================
# SECTION 4 — FARMER MENU
# ===========================================================================

def handle_farmer_menu(user):
    """
    Present the role-restricted menu for authenticated farmers.

    A farmer can manage their own listings, view the full market board,
    track their sales, analyse pricing trends, and bulk-import via CSV.

    Parameters
    ----------
    user : dict
        The session dict returned by auth.get_current_user().
        Relevant keys used here: user["user_id"] (int), user["role"] (str).

    Data types & casting demonstrated
    -----------------------------------
    user["user_id"] comes from SQLite as an int, but we pass it explicitly
    as int() to make the type contract clear to anyone reading this code.
    user["role"] is a str; we never compare it here — role checking happened
    in run_application() before this function was called.
    """
    options = [
        ("1", "Add a new crop listing to sell"),
        ("2", "View my current listings"),
        ("3", "Edit or delete one of my listings"),
        ("4", "View the full market board (all active listings)"),
        ("5", "View my sales history"),
        ("6", "Market analytics dashboard & price alerts"),
        ("7", "Bulk import listings from a CSV file"),
        ("8", "Update my farm location"),
        ("9", "Log out"),
    ]
    choice = _render_menu("FARMER MENU", "green", options)

    # SELECTION STRUCTURE — nested if/elif:
    # Each branch maps to a specific feature in a team-mate's module.
    # _run_safely() wraps every call so a bug in one feature can't crash
    # the whole menu system.

    if choice == "1":
        # listings.add_new_listing() prompts for crop name, quantity (kg),
        # price (KSH/kg), location, and harvest date — all validated inside.
        _run_safely(listings.add_new_listing)

    elif choice == "2":
        # view_my_listings() queries the DB for listings WHERE farmer_id
        # matches the currently logged-in user, so farmers only see their own.
        _run_safely(listings.view_my_listings)

    elif choice == "3":
        # edit_or_delete_listing() checks ownership before allowing changes —
        # a farmer cannot edit another farmer's listing.
        _run_safely(listings.edit_or_delete_listing)

    elif choice == "4":
        # All active listings are public — farmers use this to benchmark
        # their prices against competitors in the same crop category.
        _run_safely(listings.view_all_active_listings)

    elif choice == "5":
        # DATA TYPE: user["user_id"] is an int primary key.
        # "farmer" (str) tells TransactionManager which SQL JOIN branch to use
        # — the farmer sees sales of their own listings, not purchases.
        _run_safely(
            transactions.TransactionManager().display_transactions,
            user["user_id"],   # int — filters transactions by this farmer
            "farmer",          # str — selects the farmer-perspective query
        )

    elif choice == "6":
        # Aggregates platform stats and highlights listings priced >30% below
        # the market average for that crop (price undercutting alerts).
        _run_safely(dashboard.display_dashboard_view)

    elif choice == "7":
        # FILE INPUT: reads a .csv file and bulk-inserts multiple listings.
        # Required columns: crop_name, quantity_kg, min_price, location, harvest_date.
        # Invalid rows (unknown crop, bad number) are skipped with a warning.
        # Sample file available at: data/sample_listings.csv
        _run_safely(listings.bulk_import_from_csv)

    elif choice == "8":
        # Updates the location column for this user_id in the users table.
        _run_safely(auth.change_location)

    elif choice == "9":
        # Logout: animate the transition, then clear the session variable.
        # `return` here skips the _wait() call at the bottom — the screen
        # will clear and show the visitor menu on the next loop iteration.
        simulate_loading_bar("Signing out securely...")
        auth.logout_user()
        return   # exit this function; do NOT call _wait()

    # Pause after every action except logout so the user can read the output.
    _wait()


# ===========================================================================
# SECTION 5 — BUYER MENU
# ===========================================================================

def handle_buyer_menu(user):
    """
    Present the role-restricted menu for authenticated buyers.

    A buyer can browse listings, run filtered searches, use the smart
    location-matching algorithm, purchase crops (with the 2% donation),
    review their purchase history, and check their personal donation impact.

    Parameters
    ----------
    user : dict
        Session dict from auth.get_current_user().

    Data types & casting demonstrated
    -----------------------------------
    int(user["user_id"]) — explicit cast before forwarding to module
    functions that store the value in the database as an INTEGER column.
    Although SQLite is flexible about types, being explicit makes the
    intent clear and prevents subtle bugs if the value arrives as a string.
    """
    options = [
        ("1", "Browse all available crops"),
        ("2", "Search and filter crops by type, location, or price"),
        ("3", "Find crops near me  (Smart Location Matching)"),
        ("4", "Buy crops  [2% micro-donation goes to the Food Bank]"),
        ("5", "View my purchase history"),
        ("6", "View my personal donation impact"),
        ("7", "Update my delivery location"),
        ("8", "Log out"),
    ]
    choice = _render_menu("BUYER MENU", "blue", options)

    # SELECTION STRUCTURE — if/elif chain for buyer-specific actions.

    if choice == "1":
        # Shows all listings where status = 'available', joined with the
        # farmer's username so the buyer knows who they're buying from.
        _run_safely(listings.view_all_active_listings)

    elif choice == "2":
        # SearchEngine.search_interactive() prompts for optional filters
        # (crop name, location, min/max price, sort order) then runs a
        # parameterized SQL query and displays matching listings.
        _run_safely(search.SearchEngine().search_interactive)

    elif choice == "3":
        # DATA TYPE CAST: user["user_id"] → int, forwarded so the matcher
        # can look up the buyer's stored location from the users table and
        # pre-fill the location prompt.
        _run_safely(
            matching.MatchingEngine().match_interactive,
            int(user["user_id"])   # int — used to fetch buyer's saved location
        )

    elif choice == "4":
        # process_purchase() shows all available listings, asks which one
        # and what quantity, calculates total_price and donation_amount
        # (2% of total_price), then writes both to the transactions table.
        _run_safely(
            transactions.TransactionManager().process_purchase,
            int(user["user_id"]),   # int — stored as buyer_id in transactions
        )

    elif choice == "5":
        # "buyer" tells TransactionManager to join on buyer_id = this user,
        # showing only purchases made by this buyer (not their non-existent sales).
        _run_safely(
            transactions.TransactionManager().display_transactions,
            int(user["user_id"]),
            "buyer",   # str — selects the buyer-perspective SQL query
        )

    elif choice == "6":
        # Totals: number of purchases, kg of food bought (= food saved from waste),
        # KSH donated, and estimated meals that donation could provide.
        _run_safely(
            donations.DonationManager().display_personal_impact,
            int(user["user_id"]),
        )

    elif choice == "7":
        # Lets the buyer update their delivery location stored in the DB —
        # the matching algorithm uses this as the default buyer location.
        _run_safely(auth.change_location)

    elif choice == "8":
        simulate_loading_bar("Signing out securely...")
        auth.logout_user()
        return   # skip _wait(); return to visitor menu on next loop iteration

    _wait()


# ===========================================================================
# SECTION 6 — ADMIN MENU
# ===========================================================================

def handle_admin_menu(user):
    """
    Present the role-restricted menu for platform administrators.

    An admin has full read visibility across all users, transactions, and
    donations, plus the ability to manage the crop catalogue and export data.

    Parameters
    ----------
    user : dict
        Session dict from auth.get_current_user().  The `user` parameter
        is accepted here for consistency with the other menu functions even
        though admin queries don't filter by a specific user_id.
    """
    options = [
        ("1", "System analytics dashboard"),
        ("2", "View all platform transactions"),
        ("3", "View food bank donations ledger"),
        ("4", "Manage crop commodity catalogue"),
        ("5", "Export sales report to CSV"),
        ("6", "Export listings backup to JSON"),
        ("7", "Generate & save full text summary report"),
        ("8", "Log out"),
    ]
    choice = _render_menu("ADMIN MENU", "red", options)

    # SELECTION STRUCTURE — if/elif for admin-only features.

    if choice == "1":
        # Aggregated platform statistics + price-alert panel.
        _run_safely(dashboard.display_dashboard_view)

    elif choice == "2":
        # Passing None as user_id and "admin" as role tells
        # TransactionManager to skip the user_id filter and return ALL rows,
        # showing both the buyer name and the farmer name in the output.
        _run_safely(
            transactions.TransactionManager().display_transactions,
            None,      # no user_id filter — admin sees every transaction
            "admin",   # str — selects the admin-perspective SQL query
        )

    elif choice == "3":
        # Full donation ledger: every entry with donor name, amount, date,
        # and the food bank it was attributed to.
        _run_safely(donations.DonationManager().display_donations)

    elif choice == "4":
        # Calls the sub-function below — separated to keep this function short.
        _run_safely(_admin_manage_crops)

    elif choice == "5":
        # FILE OUTPUT: export_transactions_to_csv() writes exports/sales_report.csv
        # and returns a (bool, message) tuple.  We unpack it and print the message.
        ok, msg = reports.export_transactions_to_csv()
        console.print(msg)   # msg is a Rich markup string (green = success, red = error)

    elif choice == "6":
        # FILE OUTPUT: exports/listings_backup.json — a JSON array of all listings.
        ok, msg = reports.export_listings_to_json()
        console.print(msg)

    elif choice == "7":
        # FILE OUTPUT: exports/summary_report.txt — human-readable 5-section report
        # covering KPIs, top crops, top farmers, top buyers, and food bank impact.
        ok, msg = reports.generate_text_report()
        console.print(msg)

    elif choice == "8":
        simulate_loading_bar("Signing out securely...")
        auth.logout_user()
        return   # skip _wait(); return to visitor menu on next loop iteration

    _wait()


def _admin_manage_crops():
    """
    Sub-flow for admin crop catalogue management.

    Displays the full crop list, then optionally lets the admin add a new
    commodity.  Extracted from handle_admin_menu() to keep each function
    focused on a single responsibility (a core principle of clean code).
    """
    # Print the current catalogue as a numbered table (from products.py).
    products.display_crops()

    # INTERACTIVE INPUT: ask for a yes/no decision before proceeding.
    action = Prompt.ask(
        "\nAdd a new crop to the catalogue? [y/n]",
        choices=["y", "n"],
        default="n"   # pressing Enter without typing defaults to 'n'
    )

    # SELECTION: only attempt to add if the admin confirmed 'y'.
    if action == "y":
        new_crop = Prompt.ask("New crop name").strip()
        # Guard: don't insert an empty string if the admin just pressed Enter.
        if new_crop:
            products.add_crop(new_crop)


# ===========================================================================
# SECTION 7 — MAIN APPLICATION LOOP
# This is the top-level entry point called by main.py.
# ===========================================================================

def run_application():
    """
    Initialise the database and enter the application's main event loop.

    Execution flow
    --------------
    1. database.init_db()         — CREATE TABLE IF NOT EXISTS for all tables.
    2. database.seed_sample_data()— Insert demo data on first run (idempotent).
    3. while True                 — The app runs indefinitely until the user
                                    chooses 'Exit' or presses Ctrl+C.
    4. auth.get_current_user()    — Check session state on every iteration.
    5. Role routing               — if/elif directs each role to its sub-menu.

    Iterative structure demonstrated
    ---------------------------------
    `while True` on line ~507 is an infinite loop — the only way out is:
      a) The user selects 'Exit' → sys.exit(0)
      b) The user presses Ctrl+C → caught by the try/except in __main__
    Every other action (menu selection, login, logout) returns from the
    sub-menu function and the loop simply starts its next iteration,
    clearing the screen and re-drawing the appropriate menu.

    Selection structure demonstrated
    ----------------------------------
    After reading the current user's role string, an if/elif chain decides
    which of the three sub-menus to show.  This is the outermost "router"
    of the entire application — one branch per role.
    """
    # ── One-time initialisation ────────────────────────────────────────────
    # init_db() is safe to call every startup — it uses CREATE TABLE IF NOT
    # EXISTS, so it only creates tables the very first time.
    database.init_db()

    # seed_sample_data() checks whether any users exist before inserting,
    # so it silently skips on every run after the first.
    database.seed_sample_data()

    # ── Main event loop ────────────────────────────────────────────────────
    # ITERATIVE STRUCTURE — while True (infinite loop):
    # The application stays alive across unlimited menu interactions.
    # Each iteration represents one complete "screen" — clear, draw, respond.
    while True:

        # Clear the terminal before drawing the next screen.
        # "cls" on Windows, "clear" on Mac/Linux — os.name detects which.
        os.system("cls" if os.name == "nt" else "clear")

        # Always draw the header banner at the top of every screen.
        display_header()

        # Check who is currently logged in (returns None if no session).
        current_user = auth.get_current_user()

        # SELECTION STRUCTURE — outer if/else: logged in vs. not logged in.
        if not current_user:
            # No active session: show the public welcome panel and
            # the visitor menu (Register / Login / Impact / Exit).
            show_welcome_screen()
            display_footer(None)
            handle_visitor_menu()

        else:
            # Active session: read the user's role and route to their menu.

            # DATA TYPE: role is a str stored as lowercase in the database
            # ('farmer', 'buyer', 'admin').  .lower() guards against any
            # legacy data that might have been stored with a capital letter.
            role = current_user["role"].lower()

            # Print the status bar showing username and role.
            display_footer(current_user)

            # SELECTION STRUCTURE — nested if/elif (role-based routing):
            # Each branch calls the matching sub-menu function and passes
            # the full user dict so it can access user_id, location, etc.
            if role == "farmer":
                handle_farmer_menu(current_user)

            elif role == "buyer":
                handle_buyer_menu(current_user)

            elif role == "admin":
                handle_admin_menu(current_user)

            else:
                # Defensive branch: an unrecognised role should never occur
                # because the DB enforces a CHECK constraint on the role column,
                # but we handle it gracefully rather than crashing.
                console.print(
                    "[bold red]Error: Unrecognised role. Logging out.[/bold red]"
                )
                auth.logout_user()
        # End of one loop iteration — control returns to `while True` and
        # the screen is cleared again at the top of the next iteration.


# ---------------------------------------------------------------------------
# Direct execution guard
# Allows both `python main.py` (via main.py) and `python ui.py` (direct).
# The try/except catches Ctrl+C at the top level for a clean shutdown message.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    try:
        run_application()
    except KeyboardInterrupt:
        # User pressed Ctrl+C at the top level — print goodbye and exit cleanly.
        console.print(
            "\n\n[bold green]Application closed safely. Goodbye![/bold green]"
        )
        sys.exit(0)
