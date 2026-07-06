# listings.py
# Member 3: Mwangi, Wendy – Product & Listing Management

import csv
import os
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt

# Group Integrations
import database
import auth
import products

console = Console()

# ---------------------------------------------------------------------------
# DATA VALIDATION HELPERS
# ---------------------------------------------------------------------------
def validate_positive_number(value, field_name):
    """Ensures input strings are valid positive float calculations."""
    try:
        num = float(value)
        if num <= 0:
            raise ValueError(f"{field_name} must be strictly greater than 0.")
        return num
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be a valid numeric quantity.")

def validate_date(date_str):
    """Ensures dates match the YYYY-MM-DD format requirement."""
    try:
        datetime.strptime(date_str.strip(), "%Y-%m-%d")
        return date_str.strip()
    except ValueError:
        raise ValueError("Date format must strictly follow YYYY-MM-DD.")


# ---------------------------------------------------------------------------
# MODULE FUNCTIONS
# ---------------------------------------------------------------------------
def add_new_listing():
    """Requirement: Add New Listing (Farmer only)"""
    user = auth.get_current_user()
    
    # 1. Role Verification Enforcement
    if not user or not auth.is_farmer():
        console.print("[bold red]Access Denied: Only authenticated Farmers can add crop listings.[/bold red]")
        return

    console.print(Panel("[bold green]Create New Crop Market Listing[/bold green]"))
    
    # Let the user see what valid options are available from your products.py file
    products.display_crops()
    
    crop_input = Prompt.ask("\nEnter Crop Name").strip()
    
    # 2. Check compatibility against Wendy's product specification list
    if not products.crop_exists(crop_input):
        console.print(f"[bold red]Validation Error:[/] '{crop_input}' is not an authorized marketplace commodity.")
        return
        
    try:
        raw_qty = Prompt.ask("Quantity in kilograms (KG)")
        quantity_kg = validate_positive_number(raw_qty, "Quantity")
        
        raw_price = Prompt.ask("Minimum acceptable price per KG ($)")
        min_price = validate_positive_number(raw_price, "Minimum Price")
        
        location = Prompt.ask("Current storage location", default=user.get("location", "")).strip()
        if not location:
            raise ValueError("Location string information is mandatory.")
            
        raw_date = Prompt.ask("Harvest Date (YYYY-MM-DD)")
        harvest_date = validate_date(raw_date)
        
        # 3. Assemble parameters mapped strictly to David's DB schemas
        listing_data = {
            "farmer_id": user["user_id"],
            "crop_name": crop_input.title(),
            "quantity_kg": quantity_kg,
            "min_price": min_price,
            "location": location,
            "harvest_date": harvest_date,
            "status": "Available"  # Specified status default rule
        }
        
        database.insert_data("listings", listing_data)
        console.print(f"[bold green]✓ Success: Listing for {crop_input.title()} uploaded to market repository![/bold green]")
        
    except ValueError as e:
        console.print(f"[bold red]Validation Error:[/] {e}")


def view_my_listings():
    """Requirement: View My Listings (Farmer)"""
    user = auth.get_current_user()
    if not user:
        console.print("[bold red]Access Error: Please log into your profile session first.[/bold red]")
        return
        
    # Query matching farmer rows securely via bound placeholder indices
    query = "SELECT * FROM listings WHERE farmer_id = ?"
    rows = database.fetch_all(query, (user["user_id"],))
    
    table = Table(title=f"🌾 Dynamic Inventory Ledger — User: {user['username']}", show_header=True, header_style="bold green")
    table.add_column("Listing ID", justify="center")
    table.add_column("Crop Commodity", justify="left")
    table.add_column("Weight volume", justify="right")
    table.add_column("Floor Bid/KG", justify="right")
    table.add_column("Regional Base", justify="left")
    table.add_column("Harvest Date", justify="center")
    table.add_column("Status Condition", justify="center")
    
    for row in rows:
        table.add_row(
            str(row["listing_id"]),
            row["crop_name"],
            f"{row['quantity_kg']:,} KG",
            f"${row['min_price']:.2f}",
            row["location"],
            row["harvest_date"],
            row["status"]
        )
    console.print(table)


def view_all_active_listings():
    """Requirement: View All Active Listings (For buyers)"""
    query = "SELECT * FROM listings WHERE status = 'Available'"
    rows = database.fetch_all(query)
    
    table = Table(title="🛒 Active Spot Market Board (Open Exchange Bids)", show_header=True, header_style="bold blue")
    table.add_column("ID", justify="center")
    table.add_column("Crop", justify="left")
    table.add_column("Available Yield", justify="right")
    table.add_column("Unit Ask Price", justify="right")
    table.add_column("Sourced Location", justify="left")
    table.add_column("Freshness Index", justify="center")
    
    for row in rows:
        table.add_row(
            str(row["listing_id"]),
            row["crop_name"],
            f"{row['quantity_kg']:,} KG",
            f"${row['min_price']:.2f}",
            row["location"],
            row["harvest_date"]
        )
    console.print(table)


def bulk_import_from_csv():
    """Requirement: Bulk Import from CSV (File I/O)"""
    user = auth.get_current_user()
    if not user or not auth.is_farmer():
        console.print("[bold red]Access Denied: Only active Farmers can trigger batch CSV pipelines.[/bold red]")
        return
        
    filepath = Prompt.ask("Provide path directory pointer toward target CSV registry source").strip()
    
    if not os.path.exists(filepath):
        console.print(f"[bold red]File System Fault: Path pointer configuration reference '{filepath}' yields broken link.[/bold red]")
        return
        
    success_items = 0
    with open(filepath, mode="r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            try:
                crop_name = row["crop_name"].strip().title()
                
                # Check cross-reference catalog validation from Wendy's product list
                if not products.crop_exists(crop_name):
                    continue
                    
                qty = validate_positive_number(row["quantity_kg"], "CSV Row Quantities")
                price = validate_positive_number(row["min_price"], "CSV Row Unit Valuation")
                loc = row["location"].strip()
                h_date = validate_date(row["harvest_date"])
                
                listing_data = {
                    "farmer_id": user["user_id"],
                    "crop_name": crop_name,
                    "quantity_kg": qty,
                    "min_price": price,
                    "location": loc,
                    "harvest_date": h_date,
                    "status": "Available"
                }
                database.insert_data("listings", listing_data)
                success_items += 1
            except Exception:
                # Silently bypass malformed rows to preserve processing run-state consistency
                continue
                
    console.print(f"[bold green]✓ Ingestion pipeline run complete. Processed {success_items} rows into SQLite tables successfully.[/bold green]")


def edit_or_delete_listing():
    """Requirement: Edit / Delete Listing"""
    user = auth.get_current_user()
    if not user:
        console.print("[bold red]Authentication Error: Log in to proceed.[/bold red]")
        return
        
    view_my_listings()
    listing_id = Prompt.ask("\nEnter target Listing ID for record modification processing").strip()
    
    # Ownership Validation Check before calling write mutations
    record = database.fetch_one("SELECT * FROM listings WHERE listing_id = ?", (listing_id,))
    if not record:
        console.print("[bold red]Index Error: Specified listing pointer does not exist inside current indices.[/bold red]")
        return
        
    # Permit edit actions only if caller matches the record's creator or holds Admin tokens
    if record["farmer_id"] != user["user_id"] and not auth.is_admin():
        console.print("[bold red]Permission Violation Check Failed: Context operational lock enforced.[/bold red]")
        return
        
    choice = Prompt.ask("Select Target Record Strategy", choices=["Edit", "Delete", "Cancel"], default="Cancel")
    
    if choice == "Edit":
        try:
            new_qty_str = Prompt.ask("Target modified weight capacity (Leave blank to preserve state value)")
            new_price_str = Prompt.ask("Target modified pricing scale (Leave blank to preserve state value)")
            
            changes = {}
            if new_qty_str.strip():
                changes["quantity_kg"] = validate_positive_number(new_qty_str, "Revised Weight Metrics")
            if new_price_str.strip():
                changes["min_price"] = validate_positive_number(new_price_str, "Revised Target Valuation Pricing")
                
            if changes:
                database.update_data("listings", changes, "listing_id = ?", (listing_id,))
                console.print("[bold green]✓ Database transaction update metrics complete.[/bold green]")
            else:
                console.print("[yellow]Change request payload read empty. No write committed.[/yellow]")
        except ValueError as err:
            console.print(f"[bold red]Transaction rolled back:[/] {err}")
            
    elif choice == "Delete":
        confirm_intent = Prompt.ask(f"Confirm irreversible destruction sequence layout for entry listing index {listing_id}?", choices=["y", "n"], default="n")
        if confirm_intent == "y":
            database.delete_data("listings", "listing_id = ?", (listing_id,))
            console.print("[bold green]✓ Record cleared from active live schema arrays permanently.[/bold green]")


# --- MODULE DEPLOYMENT SANDBOX FRAME ---
if __name__ == "__main__":
    database.init_db()
    try:
        import users
        if not users.username_exists("Wendy"):
            database.insert_data("users", {
                "username": "Wendy",
                "password": users.hash_password("password123"),
                "role": "Farmer",
                "location": "Nairobi",
                "phone": "0700000000"
            })
    except Exception:
        pass 
        
    auth.login_user("Wendy", "password123")
    
    while True:
        console.print("\n[bold]Listings Module Standalone Interface Options:[/bold]")
        console.print("1. Add Listing | 2. View My Listings | 3. View Global Spot Market | 4. Bulk CSV Import | 5. Update/Drop Record | 6. Exit Module")
        selection = Prompt.ask("Trigger operational matrix choice", choices=["1", "2", "3", "4", "5", "6"])
        
        if selection == "1": add_new_listing()
        elif selection == "2": view_my_listings()
        elif selection == "3": view_all_active_listings()
        elif selection == "4": bulk_import_from_csv()
        elif selection == "5": edit_or_delete_listing()
        elif selection == "6": 
            console.print("[cyan]Exiting Listing Engine.[/cyan]")
            break
    