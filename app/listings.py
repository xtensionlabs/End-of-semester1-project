"""
listings.py
Member 3: Mwangi, Wendy — Product & Listing Management
Allows farmers to add, view, edit, and delete crop listings.
"""

import csv
import os
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from rich import box

import database
import auth
import products

console = Console()


# ---------------------------------------------------------------------------
# INPUT VALIDATION HELPERS
# ---------------------------------------------------------------------------

def validate_positive_number(value, field_name):
    """Ensure value is a valid positive float."""
    try:
        num = float(value)
        if num <= 0:
            raise ValueError(f"{field_name} must be greater than 0.")
        return num
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be a valid number.")


def validate_date(date_str):
    """Ensure date string matches YYYY-MM-DD format."""
    try:
        datetime.strptime(date_str.strip(), "%Y-%m-%d")
        return date_str.strip()
    except ValueError:
        raise ValueError("Date must be in YYYY-MM-DD format (e.g. 2026-08-15).")


# ---------------------------------------------------------------------------
# LISTING MANAGER CLASS
# ---------------------------------------------------------------------------

class ListingManager:

    def add_listing(self):
        """Add a new crop listing. Farmers only."""
        user = auth.get_current_user()
        if not user or not auth.is_farmer():
            console.print("[bold red]Access Denied: Only Farmers can add listings.[/bold red]")
            return

        console.print(Panel("[bold green]Create New Crop Listing[/bold green]", border_style="green"))
        products.display_crops()

        crop_input = Prompt.ask("\nCrop name").strip()
        if not products.crop_exists(crop_input):
            console.print(f"[bold red]'{crop_input}' is not a registered commodity.[/bold red]")
            console.print("[dim]Choose from the list above, or ask an admin to add a new crop.[/dim]")
            return

        try:
            quantity_kg = validate_positive_number(
                Prompt.ask("Quantity (kg)"), "Quantity"
            )
            min_price = validate_positive_number(
                Prompt.ask("Minimum price per kg (KSH)"), "Min Price"
            )
            location = Prompt.ask(
                "Storage location", default=user.get("location", "")
            ).strip()
            if not location:
                raise ValueError("Location is required.")
            harvest_date = validate_date(Prompt.ask("Harvest date (YYYY-MM-DD)"))
        except ValueError as e:
            console.print(f"[bold red]Validation Error:[/bold red] {e}")
            return

        database.insert_data("listings", {
            "farmer_id":    user["user_id"],
            "crop_name":    crop_input.strip().title(),
            "quantity_kg":  quantity_kg,
            "min_price":    min_price,
            "location":     location,
            "harvest_date": harvest_date,
            "status":       "available",
        })
        console.print(f"[bold green]Listing for {crop_input.title()} created successfully![/bold green]")

    def view_my_listings(self):
        """Show all listings belonging to the logged-in farmer."""
        user = auth.get_current_user()
        if not user:
            console.print("[bold red]Please log in first.[/bold red]")
            return

        rows = database.fetch_all(
            "SELECT * FROM listings WHERE farmer_id = ? ORDER BY listing_id DESC",
            (user["user_id"],)
        )
        if not rows:
            console.print("[yellow]You have no listings yet.[/yellow]")
            return

        table = Table(
            title=f"My Listings — {user['username']}",
            box=box.ROUNDED, border_style="green", show_lines=True
        )
        table.add_column("ID",       style="cyan",  justify="right")
        table.add_column("Crop",     style="bold green")
        table.add_column("Qty (kg)", style="white", justify="right")
        table.add_column("KSH/kg",   style="blue",  justify="right")
        table.add_column("Location", style="yellow")
        table.add_column("Harvest",  style="dim")
        table.add_column("Status",   justify="center")

        for row in rows:
            status = row["status"]
            if status == "available":
                status_cell = f"[green]{status}[/green]"
            elif status == "sold":
                status_cell = f"[red]{status}[/red]"
            else:
                status_cell = f"[yellow]{status}[/yellow]"

            table.add_row(
                str(row["listing_id"]),
                row["crop_name"],
                f"{row['quantity_kg']:,.1f}",
                f"{row['min_price']:.2f}",
                row["location"] or "—",
                row["harvest_date"] or "—",
                status_cell,
            )
        console.print(table)

    def view_all_active_listings(self):
        """Show every available listing with farmer info. For buyers and all users."""
        rows = database.fetch_all(
            """SELECT l.listing_id, l.crop_name, l.quantity_kg, l.min_price,
                      l.location, l.harvest_date, u.username AS farmer_name
               FROM listings l
               JOIN users u ON l.farmer_id = u.user_id
               WHERE l.status = 'available'
               ORDER BY l.crop_name ASC, l.min_price ASC"""
        )
        if not rows:
            console.print("[yellow]No active listings on the market right now.[/yellow]")
            return

        table = Table(
            title="Active Market Listings",
            box=box.ROUNDED, border_style="cyan", show_lines=True
        )
        table.add_column("ID",       style="cyan",  justify="right")
        table.add_column("Crop",     style="bold green")
        table.add_column("Qty (kg)", style="white", justify="right")
        table.add_column("KSH/kg",   style="blue",  justify="right")
        table.add_column("Location", style="yellow")
        table.add_column("Farmer",   style="magenta")
        table.add_column("Harvest",  style="dim")

        for row in rows:
            table.add_row(
                str(row["listing_id"]),
                row["crop_name"],
                f"{row['quantity_kg']:,.1f}",
                f"{row['min_price']:.2f}",
                row["location"] or "—",
                row["farmer_name"],
                row["harvest_date"] or "—",
            )
        console.print(table)
        console.print(f"[dim]  {len(rows)} active listing(s).[/dim]")

    def display_all_listings(self):
        """Alias used by TransactionManager.process_purchase."""
        self.view_all_active_listings()

    def bulk_import_from_csv(self):
        """Import multiple listings from a CSV file. Farmers only."""
        user = auth.get_current_user()
        if not user or not auth.is_farmer():
            console.print("[bold red]Access Denied: Only Farmers can bulk-import listings.[/bold red]")
            return

        filepath = Prompt.ask("Path to CSV file", default="data/sample_listings.csv").strip()
        if not os.path.exists(filepath):
            console.print(f"[bold red]File not found: '{filepath}'[/bold red]")
            console.print("[dim]Required columns: crop_name, quantity_kg, min_price, location, harvest_date[/dim]")
            console.print("[dim]Sample file: data/sample_listings.csv[/dim]")
            return

        success = skipped = 0
        errors = []

        try:
            with open(filepath, mode="r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                required = {"crop_name", "quantity_kg", "min_price", "location", "harvest_date"}
                actual   = set(reader.fieldnames or [])
                if not required.issubset(actual):
                    console.print(f"[bold red]CSV missing required columns: {required - actual}[/bold red]")
                    return

                for line_no, row in enumerate(reader, 2):
                    try:
                        crop = row["crop_name"].strip().title()
                        if not products.crop_exists(crop):
                            skipped += 1
                            continue

                        qty   = validate_positive_number(row["quantity_kg"], "Quantity")
                        price = validate_positive_number(row["min_price"],   "Price")
                        loc   = row["location"].strip()
                        date  = validate_date(row["harvest_date"])

                        database.insert_data("listings", {
                            "farmer_id":    user["user_id"],
                            "crop_name":    crop,
                            "quantity_kg":  qty,
                            "min_price":    price,
                            "location":     loc,
                            "harvest_date": date,
                            "status":       "available",
                        })
                        success += 1
                    except Exception as e:
                        errors.append(f"Line {line_no}: {e}")

        except Exception as e:
            console.print(f"[bold red]Could not read file: {e}[/bold red]")
            return

        console.print(
            f"[bold green]Import complete.[/bold green]  "
            f"Imported: [green]{success}[/green]   "
            f"Skipped (unknown crop): [yellow]{skipped}[/yellow]   "
            f"Errors: [red]{len(errors)}[/red]"
        )
        for err in errors[:5]:
            console.print(f"  [red]{err}[/red]")
        if len(errors) > 5:
            console.print(f"  [dim]...and {len(errors) - 5} more.[/dim]")

    def edit_or_delete_listing(self):
        """Interactively edit or delete a listing. Owner or admin only."""
        user = auth.get_current_user()
        if not user:
            console.print("[bold red]Please log in first.[/bold red]")
            return

        self.view_my_listings()

        raw_id = Prompt.ask("\nEnter Listing ID").strip()
        try:
            listing_id = int(raw_id)
        except ValueError:
            console.print("[red]Listing ID must be a number.[/red]")
            return

        record = database.fetch_one(
            "SELECT * FROM listings WHERE listing_id = ?", (listing_id,)
        )
        if not record:
            console.print("[bold red]Listing not found.[/bold red]")
            return

        if record["farmer_id"] != user["user_id"] and not auth.is_admin():
            console.print("[bold red]Permission denied: you don't own this listing.[/bold red]")
            return

        choice = Prompt.ask("Action", choices=["edit", "delete", "cancel"], default="cancel")

        if choice == "edit":
            try:
                changes = {}
                new_qty   = Prompt.ask("New quantity kg  (blank = keep current)").strip()
                new_price = Prompt.ask("New min price KSH/kg  (blank = keep current)").strip()
                new_loc   = Prompt.ask("New location  (blank = keep current)").strip()

                if new_qty:
                    changes["quantity_kg"] = validate_positive_number(new_qty,   "Quantity")
                if new_price:
                    changes["min_price"]   = validate_positive_number(new_price, "Price")
                if new_loc:
                    changes["location"]    = new_loc

                if changes:
                    database.update_data("listings", changes, {"listing_id": listing_id})
                    console.print("[bold green]Listing updated successfully.[/bold green]")
                else:
                    console.print("[yellow]No changes entered — listing unchanged.[/yellow]")
            except ValueError as e:
                console.print(f"[bold red]Validation Error:[/bold red] {e}")

        elif choice == "delete":
            confirm = Prompt.ask(
                f"Permanently delete listing #{listing_id}? [y/n]",
                choices=["y", "n"], default="n"
            )
            if confirm == "y":
                database.delete_data("listings", {"listing_id": listing_id})
                console.print("[bold green]Listing deleted.[/bold green]")
            else:
                console.print("[yellow]Deletion cancelled.[/yellow]")


# ---------------------------------------------------------------------------
# Module-level convenience wrappers
# Preserves the original standalone function API for the main menu.
# ---------------------------------------------------------------------------

_manager = ListingManager()


def add_new_listing():
    _manager.add_listing()


def view_my_listings():
    _manager.view_my_listings()


def view_all_active_listings():
    _manager.view_all_active_listings()


def bulk_import_from_csv():
    _manager.bulk_import_from_csv()


def edit_or_delete_listing():
    _manager.edit_or_delete_listing()


# ---------------------------------------------------------------------------
# Standalone demo — run `python listings.py` to test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    database.init_db()
    database.seed_sample_data()

    if auth.login_user("john_kamau", "farmer123"):
        while True:
            console.print("\n[bold]Listings Module:[/bold]")
            console.print("  1. Add listing")
            console.print("  2. View my listings")
            console.print("  3. View all market listings")
            console.print("  4. Bulk CSV import")
            console.print("  5. Edit / Delete listing")
            console.print("  6. Exit")
            sel = Prompt.ask("Choice", choices=["1", "2", "3", "4", "5", "6"])
            if sel == "1":
                add_new_listing()
            elif sel == "2":
                view_my_listings()
            elif sel == "3":
                view_all_active_listings()
            elif sel == "4":
                bulk_import_from_csv()
            elif sel == "5":
                edit_or_delete_listing()
            elif sel == "6":
                console.print("[cyan]Bye.[/cyan]")
                break
