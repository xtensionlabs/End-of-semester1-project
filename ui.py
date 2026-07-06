"""
ui.py
=====
Member: Maina, Njeri — UI/UX + Reporting & Dashboard
The primary user interface shell for the Agri-Tech Digital Marketplace.
Directly answers the project brief by connecting all modules to facilitate
direct farmer-to-buyer sales, automated micro-donations, and market analytics.
"""

import os
import sys
import time
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TaskProgressColumn

# --- INTEGRATING ALL TEAM MODULES WITH EXACT MATCHES ---
import database
import auth
import listings
import search
import matching
import transactions
import donations
import dashboard
import reports

console = Console()


def display_header():
    """Renders a clean, professional top header."""
    console.print("[bold white on green]   AGRI-TECH DIGITAL MARKETPLACE v1.0   [/bold white on green]", justify="center")
    console.print()


def display_footer(user_info=None):
    """Renders a clear bottom status bar with navigation hints instead of jargon."""
    console.print()
    if user_info:
        status = f"Logged in as: {user_info['username']} ({user_info['role'].capitalize()})"
    else:
        status = "Not logged in"

    console.print(f"[bold white on blue] {status} | Use menu numbers to navigate [/bold white on blue]", justify="center")


def simulate_loading_bar(action_text):
    """Displays a smooth progress bar for better User Experience (UX)."""
    console.print()
    with Progress(
        SpinnerColumn(),
        TextColumn("[cyan]{task.description}[/cyan]"),
        BarColumn(bar_width=40, complete_style="green", finished_style="bold green"),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task(action_text, total=100)
        while not progress.finished:
            time.sleep(0.04)
            progress.update(task, advance=5)
    time.sleep(0.5)


def show_welcome_screen():
    """Displays the welcome banner highlighting the project's core mission."""
    welcome_text = (
        "[bold green]Welcome to the Agri-Tech Digital Marketplace[/bold green]\n"
        "[italic cyan]Empowering Farmers, Eliminating Middlemen, and Feeding Communities.[/italic cyan]"
    )
    console.print(Panel(welcome_text, border_style="green", padding=(1, 4), title="[bold white]Home[/bold white]"))
    console.print()


def _render_menu(title, style, options):
    """Builds and prints a beautifully formatted table menu."""
    table = Table(title=title, title_style=f"bold {style}", show_header=True, header_style=f"bold {style}", expand=True)
    table.add_column("Option", style=style, width=8, justify="center")
    table.add_column("What would you like to do?")

    for number, label in options:
        table.add_row(number, label)

    console.print(table)
    return Prompt.ask(
        "\nType the number of your choice",
        choices=[num for num, _ in options],
        show_choices=False,
    )


def handle_visitor_menu():
    """Menu shown before a user logs in."""
    options = [
        ("1", "Register a new account"),
        ("2", "Log in to existing account"),
        ("3", "View total platform social impact (Donations & Meals)"),
        ("4", "Exit Application"),
    ]
    choice = _render_menu("MAIN MENU", "green", options)

    if choice == "1":
        auth.register()
        Prompt.ask("\nPress [Enter] to continue...")
    elif choice == "2":
        auth.login()
        if auth.get_current_user():
            simulate_loading_bar("Signing in securely...")
    elif choice == "3":
        # Verified function name in donations.py
        donations.DonationManager().display_global_impact()
        Prompt.ask("\nPress [Enter] to continue...")
    elif choice == "4":
        console.print("\n[bold green]Thank you for using the Agri-Tech Marketplace. Goodbye![/bold green]")
        sys.exit(0)


def handle_farmer_menu(user):
    """Integrates Farmer actions to Wendy's product listings & the dashboard."""
    options = [
        ("1", "Add a new crop to sell"),
        ("2", "View the crops I am currently selling"),
        ("3", "Edit or remove a crop listing"),
        ("4", "View market prices and alerts (Prevent Undercutting)"),
        ("5", "Update my farm location"),
        ("6", "Log out"),
    ]
    choice = _render_menu("FARMER MENU", "green", options)

    if choice == "1":
        listings.add_new_listing()
    elif choice == "2":
        listings.view_my_listings()
    elif choice == "3":
        listings.edit_or_delete_listing()
    elif choice == "4":
        dashboard.display_dashboard_view()
    elif choice == "5":
        auth.change_location()
    elif choice == "6":
        simulate_loading_bar("Signing out securely...")
        auth.logout_user()

    if choice != "6":
        Prompt.ask("\nPress [Enter] to return to menu...")


def handle_buyer_menu(user):
    """Integrates Buyer actions matching your teammates' precise signatures."""
    options = [
        ("1", "Browse all available crops directly from farmers"),
        ("2", "Search and filter crops by price or type"),
        ("3", "Find crops being sold near my location"),
        ("4", "Buy crops (Includes a 2% micro-donation to the Food Bank)"),
        ("5", "View my personal donation impact"),
        ("6", "Update my delivery location"),
        ("7", "Log out"),
    ]
    choice = _render_menu("BUYER MENU", "blue", options)

    if choice == "1":
        listings.view_all_active_listings()
    elif choice == "2":
        search.SearchEngine().search_interactive()
    elif choice == "3":
        matching.MatchingEngine().match_interactive()
    elif choice == "4":
        transactions.TransactionManager().process_purchase(user["user_id"])
    elif choice == "5":
        donations.DonationManager().display_personal_impact(user["user_id"])
    elif choice == "6":
        auth.change_location()
    elif choice == "7":
        simulate_loading_bar("Signing out securely...")
        auth.logout_user()

    if choice != "7":
        Prompt.ask("\nPress [Enter] to return to menu...")

def handle_admin_menu(user):
    """Integrates Admin actions to your Dashboard and Reports modules."""
    options = [
        ("1", "View overall system dashboard and statistics"),
        ("2", "View food bank donations ledger"),
        ("3", "Download a spreadsheet report of all sales"),
        ("4", "Download a system backup of all listings"),
        ("5", "Log out"),
    ]
    choice = _render_menu("ADMIN MENU", "red", options)

    if choice == "1":
        dashboard.display_dashboard_view()
    elif choice == "2":
        # Verified from donations.py
        donations.DonationManager().display_donations()
    elif choice == "3":
        success, msg = reports.export_transactions_to_csv()
        console.print(msg)
    elif choice == "4":
        success, msg = reports.export_listings_to_json()
        console.print(msg)
    elif choice == "5":
        simulate_loading_bar("Signing out securely...")
        auth.logout_user()

    if choice != "5":
        Prompt.ask("\nPress [Enter] to return to menu...")


def run_application():
    """Main execution loop that keeps the application running smoothly."""
    database.init_db()

    while True:
        os.system("cls" if os.name == "nt" else "clear")
        display_header()

        current_user = auth.get_current_user()

        if not current_user:
            show_welcome_screen()
            display_footer(None)
            handle_visitor_menu()
        else:
            role = current_user["role"].lower()
            display_footer(current_user)

            if role == "farmer":
                handle_farmer_menu(current_user)
            elif role == "buyer":
                handle_buyer_menu(current_user)
            elif role == "admin":
                handle_admin_menu(current_user)
            else:
                console.print("[red]System error: Invalid role detected. Logging out.[/red]")
                auth.logout_user()


if __name__ == "__main__":
    try:
        run_application()
    except KeyboardInterrupt:
        console.print("\n\n[bold green]Application closed safely. Goodbye![/bold green]")
        sys.exit(0)