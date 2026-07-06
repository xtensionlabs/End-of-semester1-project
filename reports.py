"""
reports.py
==========
Member: Maina, Njeri
Handles downloading data (reports/backups) and preparing basic summary numbers.
Uses strictly live data from the SQLite database.
"""

import csv
import json
from database import fetch_all, fetch_one


def generate_summary_data():
    """
    Gets the total numbers directly from the live database to show on the dashboard.
    Returns a dictionary of statistics.
    """
    stats = {
        "total_listings": 0,
        "total_transactions": 0,
        "food_saved_kg": 0.0,
        "total_donations_ksh": 0.0,
        "meals_provided": 0
    }

    # 1. Count live listings
    listings_result = fetch_one("SELECT COUNT(*) as count FROM listings")
    if listings_result and listings_result["count"]:
        stats["total_listings"] = listings_result["count"]

    # 2. Sum up live transaction data
    tx_query = """
        SELECT 
            COUNT(*) as count, 
            SUM(quantity) as total_qty, 
            SUM(donation_amount) as total_donations 
        FROM transactions
    """
    tx_result = fetch_one(tx_query)

    if tx_result and tx_result["count"]:
        stats["total_transactions"] = tx_result["count"]
        stats["food_saved_kg"] = tx_result["total_qty"] or 0.0
        stats["total_donations_ksh"] = tx_result["total_donations"] or 0.0

        # Matches Haggai's logic from donations.py exactly
        stats["meals_provided"] = int(stats["food_saved_kg"] * 3)

    return stats


def export_transactions_to_csv(filepath="sales_report.csv"):
    """
    Downloads real transaction history into a CSV spreadsheet file.
    """
    query = """
        SELECT 
            t.transaction_id,
            b.username AS buyer_name,
            f.username AS farmer_name,
            l.crop_name,
            t.quantity,
            t.total_price,
            t.donation_amount,
            t.transaction_date
        FROM transactions t
        JOIN users b ON t.buyer_id = b.user_id
        JOIN listings l ON t.listing_id = l.listing_id
        JOIN users f ON l.farmer_id = f.user_id
        ORDER BY t.transaction_date DESC
    """
    rows = fetch_all(query)

    if not rows:
        return False, "[yellow]No sales found in the database to download yet.[/yellow]"

    try:
        with open(filepath, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([
                "Transaction ID", "Buyer Name", "Farmer Name", "Crop Name",
                "Quantity (kg)", "Total Price (KSH)", "Donation (KSH)", "Date"
            ])

            for row in rows:
                writer.writerow([
                    row["transaction_id"], row["buyer_name"], row["farmer_name"],
                    row["crop_name"], row["quantity"], row["total_price"],
                    row["donation_amount"], row["transaction_date"]
                ])

        return True, f"[bold green]✓ Successfully downloaded sales report to {filepath}[/bold green]"
    except Exception as e:
        return False, f"[bold red]Error saving file: {str(e)}[/bold red]"


def export_listings_to_json(filepath="listings_backup.json"):
    """
    Downloads live crop listings into a JSON backup file.
    """
    query = """
        SELECT 
            l.listing_id,
            u.username AS farmer_name,
            l.crop_name,
            l.quantity_kg,
            l.min_price,
            l.location,
            l.status
        FROM listings l
        JOIN users u ON l.farmer_id = u.user_id
    """
    rows = fetch_all(query)

    if not rows:
        return False, "[yellow]No listings found in the database to download yet.[/yellow]"

    listings_data = []
    for row in rows:
        listings_data.append(dict(row))

    try:
        with open(filepath, mode="w", encoding="utf-8") as file:
            json.dump(listings_data, file, indent=4)

        return True, f"[bold green]✓ Successfully downloaded listings backup to {filepath}[/bold green]"
    except Exception as e:
        return False, f"[bold red]Error saving file: {str(e)}[/bold red]"