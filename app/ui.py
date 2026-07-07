"""
ui.py — Interactive Terminal Interface
========================================
Member : Maina, Njeri
Module : UI/UX + Reporting & Dashboard

Objective
---------
Serve as the single shell that ties every team module together into one
cohesive, role-based terminal application.  A farmer, buyer, or admin each
sees only the actions relevant to their role.

Technical concepts demonstrated here
--------------------------------------
  - Selection structures  : role-based if/elif routing in run_application()
  - Iterative structures  : while True main event loop, for loop in menu builder
  - Functions             : each menu is its own function; helpers are factored out
  - Error handling        : _run_safely() wraps every action; top-level try/except
  - Interactive I/O       : rich Prompt throughout; progress-bar UX feedback
  - Data types & casting  : role stored as str, user_id as int passed to modules
"""

import os
import sys
import time

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich.progress import (
    Progress, SpinnerColumn, BarColumn, TextColumn, TaskProgressColumn
)

# ── Team module imports ────────────────────────────────────────────────────
import database       # Member 1: SQLite layer
import auth           # Member 2: sessions & roles
import listings       # Member 3: crop listings
import products       # Member 3: commodity catalogue
import search         # Member 4: search engine
import matching       # Member 4: smart matcher
import transactions   # Member 5: purchase flow
import donations      # Member 5: food bank tracking
import dashboard      # Member 6: statistics dashboard
import reports        # Member 6: CSV / JSON / text exports

console = Console()


# ===========================================================================
# SECTION 1 — SCREEN CHROME (header, footer, loading bar)
# ===========================================================================

def display_header():
    """
    Render the application title banner at the top of every screen.
    Called at the start of each loop iteration so the brand is always visible.
    """
    console.print(
        "[bold white on green]   AGRI-TECH DIGITAL MARKETPLACE v1.0   [/bold white on green]",
        justify="center",
    )
    console.print()


def display_footer(user_info=None):
    """
    Render a status bar at the bottom of the screen.

    Parameters
    ----------
    user_info : dict or None
        The currently logged-in user dict (from auth.get_current_user()),
        or None when no session is active.
    """
    console.print()
    # Type check: show session info when a user dict is present
    if user_info:
        status = f"Logged in: {user_info['username']}  |  Role: {user_info['role'].capitalize()}"
    else:
        status = "Not logged in — Register or Log In to continue"

    console.print(
        f"[bold white on blue]  {status}  |  Use menu numbers to navigate  [/bold white on blue]",
        justify="center",
    )


def simulate_loading_bar(action_text):
    """
    Display an animated progress bar for state transitions (login, logout).
    Purely cosmetic — improves the perceived responsiveness of the app.

    Parameters
    ----------
    action_text : str  Text shown beside the spinner, e.g. 'Signing in...'
    """
    console.print()
    with Progress(
        SpinnerColumn(),
        TextColumn("[cyan]{task.description}[/cyan]"),
        BarColumn(bar_width=40, complete_style="green", finished_style="bold green"),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(action_text, total=100)
        # Iterative structure: advance the bar in small steps until complete
        while not progress.finished:
            time.sleep(0.04)
            progress.update(task, advance=5)
    time.sleep(0.3)


def show_welcome_screen():
    """
    Render the public landing panel with the project's SDG mission statement.
    Shown every time the app is at the login/register screen.
    """
    console.print(Panel(
        "[bold green]Welcome to the Agri-Tech Digital Marketplace[/bold green]\n\n"
        "[italic cyan]Empowering Farmers.  Eliminating Middlemen.  Feeding Communities.[/italic cyan]\n\n"
        "[dim]Supporting:\n"
        "  SDG 1  — No Poverty             (fair farm-gate prices)\n"
        "  SDG 2  — Zero Hunger            (2% micro-donation to food banks)\n"
        "  SDG 8  — Decent Work & Growth   (direct digital market access)\n"
        "  SDG 12 — Responsible Consumption (reducing food waste)[/dim]",
        border_style="green",
        padding=(1, 4),
        title="[bold white]Home[/bold white]",
    ))
    console.print()


# ===========================================================================
# SECTION 2 — GENERIC UI HELPERS
# ===========================================================================

def _render_menu(title, style, options):
    """
    Build and print a numbered menu table, then return the user's selection.

    Parameters
    ----------
    title   : str   Heading text for the table.
    style   : str   Rich colour name applied to option numbers (e.g. 'green').
    options : list  List of (number_str, description_str) tuples.

    Returns
    -------
    str  The number string the user selected.
    """
    table = Table(
        title=title,
        title_style=f"bold {style}",
        show_header=True,
        header_style=f"bold {style}",
        expand=True,
    )
    table.add_column("Option", style=style, width=8, justify="center")
    table.add_column("What would you like to do?")

    # Iterative structure: populate each row of the menu table
    for number, label in options:
        table.add_row(number, label)

    console.print(table)

    # Collect valid choice strings for the Prompt validator
    valid_choices = [num for num, _ in options]
    return Prompt.ask(
        "\nType the number of your choice",
        choices=valid_choices,
        show_choices=False,
    )


def _run_safely(fn, *args, **kwargs):
    """
    Execute a callable with error handling so one broken feature cannot
    crash the whole application.

    Parameters
    ----------
    fn      : callable  The function to call.
    *args   : positional arguments forwarded to fn.
    **kwargs: keyword arguments forwarded to fn.
    """
    try:
        fn(*args, **kwargs)
    except KeyboardInterrupt:
        # User pressed Ctrl+C mid-action — treat as a soft cancel
        console.print("\n[yellow]Action cancelled.[/yellow]")
    except Exception as err:
        # Catch all other runtime errors and show a friendly message
        console.print(f"\n[bold red]An unexpected error occurred:[/bold red] {err}")
        console.print("[dim]Please try again or contact your administrator.[/dim]")


def _wait():
    """
    Pause and wait for the user to press Enter before returning to the menu.
    Gives the user time to read the output of the previous action.
    """
    Prompt.ask("\n[dim]Press Enter to return to the menu[/dim]", default="")


# ===========================================================================
# SECTION 3 — VISITOR MENU (before login)
# ===========================================================================

def handle_visitor_menu():
    """
    Menu shown to unauthenticated users.

    Options
    -------
    1. Register a new account
    2. Log in to an existing account
    3. View the platform's global donation impact (public)
    4. Exit the application
    """
    options = [
        ("1", "Register a new account"),
        ("2", "Log in to an existing account"),
        ("3", "View global food bank & donation impact"),
        ("4", "Exit the application"),
    ]
    choice = _render_menu("MAIN MENU", "green", options)

    # Selection structure: route each choice to the correct module function
    if choice == "1":
        _run_safely(auth.register)
        _wait()

    elif choice == "2":
        # login() returns True on success; animate the transition if successful
        success = auth.login()
        if success:
            simulate_loading_bar("Signing in securely...")

    elif choice == "3":
        # Public visibility: anyone can see how much the platform has donated
        _run_safely(donations.DonationManager().display_global_impact)
        _wait()

    elif choice == "4":
        console.print(
            "\n[bold green]Thank you for using the Agri-Tech Marketplace. Goodbye![/bold green]"
        )
        sys.exit(0)


# ===========================================================================
# SECTION 4 — FARMER MENU
# ===========================================================================

def handle_farmer_menu(user):
    """
    Role-based menu for authenticated farmers.

    Provides listing management, market visibility, sales tracking,
    and price-alert analytics.

    Parameters
    ----------
    user : dict  The current farmer's session dict from auth.get_current_user().
    """
    options = [
        ("1", "Add a new crop listing to sell"),
        ("2", "View my current listings"),
        ("3", "Edit or delete one of my listings"),
        ("4", "View the full market board (all active listings)"),
        ("5", "View my sales history"),
        ("6", "Market analytics dashboard & price alerts"),
        ("7", "Update my farm location"),
        ("8", "Log out"),
    ]
    choice = _render_menu("FARMER MENU", "green", options)

    if choice == "1":
        # Calls listings.py — validates crop name, quantity, price, date
        _run_safely(listings.add_new_listing)

    elif choice == "2":
        # Shows only this farmer's own listings (filtered by farmer_id)
        _run_safely(listings.view_my_listings)

    elif choice == "3":
        # Ownership check is performed inside edit_or_delete_listing()
        _run_safely(listings.edit_or_delete_listing)

    elif choice == "4":
        # Farmers can browse competitor prices to set fair listings
        _run_safely(listings.view_all_active_listings)

    elif choice == "5":
        # TransactionManager filters by farmer_id on the listings they own
        _run_safely(
            transactions.TransactionManager().display_transactions,
            user["user_id"],   # int: current farmer's primary key
            "farmer",          # str: controls which SQL JOIN branch is used
        )

    elif choice == "6":
        # Loads the stats + price-undercutting alerts from dashboard.py
        _run_safely(dashboard.display_dashboard_view)

    elif choice == "7":
        # Updates the 'location' column for this user in the database
        _run_safely(auth.change_location)

    elif choice == "8":
        simulate_loading_bar("Signing out securely...")
        auth.logout_user()
        return  # Skip _wait() — user is being sent to the login screen

    _wait()


# ===========================================================================
# SECTION 5 — BUYER MENU
# ===========================================================================

def handle_buyer_menu(user):
    """
    Role-based menu for authenticated buyers.

    Provides browsing, smart location-based matching, purchasing (with the
    automatic 2% food-bank donation), and personal impact tracking.

    Parameters
    ----------
    user : dict  The current buyer's session dict.
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

    if choice == "1":
        # Shows all listings with status = 'available', joined with farmer info
        _run_safely(listings.view_all_active_listings)

    elif choice == "2":
        # Interactive filter form: crop name, location, price range, sort order
        _run_safely(search.SearchEngine().search_interactive)

    elif choice == "3":
        # Pass user_id so the matcher pre-fills the buyer's stored location
        # Type: user["user_id"] is an int — cast explicitly for safety
        _run_safely(matching.MatchingEngine().match_interactive, int(user["user_id"]))

    elif choice == "4":
        # The buy flow auto-calculates and stores the 2% donation amount
        _run_safely(
            transactions.TransactionManager().process_purchase,
            int(user["user_id"]),
        )

    elif choice == "5":
        # Fetches all transactions where buyer_id = this user
        _run_safely(
            transactions.TransactionManager().display_transactions,
            int(user["user_id"]),
            "buyer",
        )

    elif choice == "6":
        # Shows totals: purchases made, food saved, KSH donated, meals provided
        _run_safely(
            donations.DonationManager().display_personal_impact,
            int(user["user_id"]),
        )

    elif choice == "7":
        _run_safely(auth.change_location)

    elif choice == "8":
        simulate_loading_bar("Signing out securely...")
        auth.logout_user()
        return

    _wait()


# ===========================================================================
# SECTION 6 — ADMIN MENU
# ===========================================================================

def handle_admin_menu(user):
    """
    Role-based menu for platform administrators.

    Provides full platform oversight: system analytics, all transaction
    history, donation records, crop catalogue management, and data exports.

    Parameters
    ----------
    user : dict  The current admin's session dict.
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

    if choice == "1":
        # Stats table + price-undercutting alerts (dashboard.py)
        _run_safely(dashboard.display_dashboard_view)

    elif choice == "2":
        # Admin role shows BOTH buyer name and farmer name columns
        _run_safely(
            transactions.TransactionManager().display_transactions,
            None,    # user_id not needed for admin — fetches all rows
            "admin",
        )

    elif choice == "3":
        # Full donation log with donor names and food bank info
        _run_safely(donations.DonationManager().display_donations)

    elif choice == "4":
        # View catalogue and optionally add a new commodity
        _run_safely(_admin_manage_crops)

    elif choice == "5":
        # Returns (bool, message) tuple — unpack and display the message
        ok, msg = reports.export_transactions_to_csv()
        console.print(msg)

    elif choice == "6":
        ok, msg = reports.export_listings_to_json()
        console.print(msg)

    elif choice == "7":
        # Writes a human-readable .txt summary to disk
        ok, msg = reports.generate_text_report()
        console.print(msg)

    elif choice == "8":
        simulate_loading_bar("Signing out securely...")
        auth.logout_user()
        return

    _wait()


def _admin_manage_crops():
    """
    Sub-flow: display the crop catalogue and let an admin add a new commodity.
    Separated from handle_admin_menu() to keep each function single-purpose.
    """
    products.display_crops()  # Shows the full numbered table from products.py
    action = Prompt.ask("\nAdd a new crop to the catalogue? [y/n]", choices=["y", "n"], default="n")
    if action == "y":
        new_crop = Prompt.ask("New crop name").strip()
        if new_crop:
            products.add_crop(new_crop)


# ===========================================================================
# SECTION 7 — MAIN APPLICATION LOOP
# ===========================================================================

def run_application():
    """
    Initialise the database and enter the main event loop.

    Execution Flow
    --------------
    1. init_db()         — Create tables if they don't already exist.
    2. seed_sample_data()— Populate demo farmers/buyers/listings on first run.
    3. while True        — The application runs until the user selects 'Exit'
                           or presses Ctrl+C.
    4. Role routing      — After each login the correct sub-menu is shown.

    The outer try/except in __main__ catches KeyboardInterrupt so Ctrl+C
    always exits cleanly rather than printing a traceback.
    """
    # ── One-time startup ──────────────────────────────────────────────────
    database.init_db()
    database.seed_sample_data()   # Idempotent: skips if data already exists

    # ── Main event loop ───────────────────────────────────────────────────
    # Iterative structure: keep the app alive between menu selections
    while True:
        # Clear the screen before each render for a clean terminal look
        os.system("cls" if os.name == "nt" else "clear")
        display_header()

        current_user = auth.get_current_user()

        if not current_user:
            # No active session — show the public landing page
            show_welcome_screen()
            display_footer(None)
            handle_visitor_menu()

        else:
            # Active session — read the role and route to the right menu.
            # .lower() normalises stored values like 'Farmer' → 'farmer'
            # in case of legacy data (selection structure)
            role = current_user["role"].lower()
            display_footer(current_user)

            if role == "farmer":
                handle_farmer_menu(current_user)
            elif role == "buyer":
                handle_buyer_menu(current_user)
            elif role == "admin":
                handle_admin_menu(current_user)
            else:
                # Defensive: guard against unexpected role values
                console.print("[red]Error: Unrecognised role detected. Logging out.[/red]")
                auth.logout_user()


# ---------------------------------------------------------------------------
# Allow running this file directly (python ui.py) as well as via main.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    try:
        run_application()
    except KeyboardInterrupt:
        console.print("\n\n[bold green]Application closed safely. Goodbye![/bold green]")
        sys.exit(0)
