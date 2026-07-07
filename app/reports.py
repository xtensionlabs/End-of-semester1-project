"""
reports.py
==========
Member  : Maina, Njeri
Module  : Reporting & Data Exports

Responsibilities
----------------
1. generate_summary_data()        — aggregate KPIs used by dashboard.py
2. export_transactions_to_csv()   — download sales history as a spreadsheet
3. export_listings_to_json()      — backup all listings as a JSON file
4. generate_text_report()         — write a human-readable .txt summary file

Technical concepts demonstrated
--------------------------------
  - File I/O      : csv.writer, json.dump, open() in write mode
  - Error handling: try/except around all file writes
  - Functions     : each export is its own named function
  - Data types    : int/float casts, f-strings, .strftime() for dates
  - Selection     : guard clauses when no data exists in the database
"""

import csv
import json
import os
from datetime import datetime
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


def _ensure_exports_dir():
    """Create the exports/ folder relative to CWD if it doesn't exist yet."""
    os.makedirs("exports", exist_ok=True)


def export_transactions_to_csv(filepath="exports/sales_report.csv"):
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

    _ensure_exports_dir()
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

        return True, f"[bold green]Successfully downloaded sales report to {filepath}[/bold green]"
    except Exception as e:
        return False, f"[bold red]Error saving file: {str(e)}[/bold red]"


def export_listings_to_json(filepath="exports/listings_backup.json"):
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

    _ensure_exports_dir()
    try:
        with open(filepath, mode="w", encoding="utf-8") as file:
            json.dump(listings_data, file, indent=4)

        return True, f"[bold green]Successfully downloaded listings backup to {filepath}[/bold green]"
    except Exception as e:
        return False, f"[bold red]Error saving file: {str(e)}[/bold red]"


def generate_text_report(filepath="exports/summary_report.txt"):
    """
    Write a full platform summary as a human-readable plain text file.

    The report includes:
      - Generation timestamp
      - Platform-wide KPI totals (listings, sales, food saved, donations)
      - Top 5 best-selling crops by transaction volume
      - Top 5 most active farmers by number of sales
      - Top 5 most active buyers by number of purchases
      - Food bank aggregate stats

    Returns
    -------
    tuple (bool, str)
        (True,  success message) on success
        (False, error message)   on failure
    """
    # Collect platform-wide KPIs
    stats = generate_summary_data()

    # ── Top 5 crops by total kg sold ─────────────────────────────────────
    top_crops = fetch_all("""
        SELECT l.crop_name, SUM(t.quantity) AS total_kg, COUNT(*) AS sales
        FROM transactions t
        JOIN listings l ON t.listing_id = l.listing_id
        GROUP BY l.crop_name
        ORDER BY total_kg DESC
        LIMIT 5
    """)

    # ── Top 5 farmers by number of completed sales ────────────────────────
    top_farmers = fetch_all("""
        SELECT u.username, COUNT(*) AS sales, SUM(t.total_price) AS revenue
        FROM transactions t
        JOIN listings l ON t.listing_id = l.listing_id
        JOIN users u ON l.farmer_id = u.user_id
        GROUP BY u.username
        ORDER BY sales DESC
        LIMIT 5
    """)

    # ── Top 5 buyers by number of purchases ──────────────────────────────
    top_buyers = fetch_all("""
        SELECT u.username, COUNT(*) AS purchases, SUM(t.total_price) AS spent
        FROM transactions t
        JOIN users u ON t.buyer_id = u.user_id
        GROUP BY u.username
        ORDER BY purchases DESC
        LIMIT 5
    """)

    # ── Food bank totals ──────────────────────────────────────────────────
    food_bank = fetch_one("SELECT * FROM food_bank WHERE food_bank_id = 1")

    # ── Build the text lines ──────────────────────────────────────────────
    # Use datetime.now() to timestamp the report
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sep = "=" * 64  # Reusable separator line

    lines = [
        sep,
        "   AGRI-TECH DIGITAL MARKETPLACE — SUMMARY REPORT",
        sep,
        f"  Generated : {generated_at}",
        f"  Team      : Lab 2, Group 5 — Moringa School",
        "",
        sep,
        "  SECTION 1 — PLATFORM KEY PERFORMANCE INDICATORS",
        sep,
        f"  Total active listings : {stats['total_listings']}",
        f"  Total completed sales : {stats['total_transactions']}",
        f"  Total food saved (kg) : {stats['food_saved_kg']:.2f} kg",
        f"  Total donations (KSH) : KSH {stats['total_donations_ksh']:.2f}",
        f"  Estimated meals given : {stats['meals_provided']} meals",
        "",
        sep,
        "  SECTION 2 — TOP 5 CROPS BY VOLUME SOLD",
        sep,
    ]

    # Iterative structure: append one row per crop
    if top_crops:
        for i, row in enumerate(top_crops, start=1):
            # Type casting: row values from SQLite are returned as int/float
            lines.append(
                f"  {i}. {row['crop_name']:<20}  {float(row['total_kg']):.1f} kg"
                f"  ({int(row['sales'])} sales)"
            )
    else:
        lines.append("  No sales recorded yet.")

    lines += [
        "",
        sep,
        "  SECTION 3 — TOP 5 FARMERS BY SALES COUNT",
        sep,
    ]

    if top_farmers:
        for i, row in enumerate(top_farmers, start=1):
            lines.append(
                f"  {i}. {row['username']:<20}  {int(row['sales'])} sales"
                f"  (KSH {float(row['revenue']):.2f} revenue)"
            )
    else:
        lines.append("  No farmer sales recorded yet.")

    lines += [
        "",
        sep,
        "  SECTION 4 — TOP 5 BUYERS BY PURCHASE COUNT",
        sep,
    ]

    if top_buyers:
        for i, row in enumerate(top_buyers, start=1):
            lines.append(
                f"  {i}. {row['username']:<20}  {int(row['purchases'])} purchases"
                f"  (KSH {float(row['spent']):.2f} spent)"
            )
    else:
        lines.append("  No buyer purchases recorded yet.")

    lines += [
        "",
        sep,
        "  SECTION 5 — FOOD BANK IMPACT",
        sep,
    ]

    if food_bank:
        lines += [
            f"  Food bank name           : {food_bank.get('name', 'Nairobi Food Bank')}",
            f"  Total food received (kg) : {float(food_bank.get('total_food_saved_kg', 0)):.2f} kg",
            f"  Total cash donated (KSH) : KSH {float(food_bank.get('total_donations', 0)):.2f}",
        ]
    else:
        lines.append("  Food bank data unavailable.")

    lines += [
        "",
        sep,
        "  SDG ALIGNMENT",
        sep,
        "  SDG 1  — No Poverty             : Fair farm-gate prices",
        "  SDG 2  — Zero Hunger            : 2% micro-donation per sale",
        "  SDG 8  — Decent Work & Growth   : Direct market access for farmers",
        "  SDG 12 — Responsible Consumption: Demand-matched supply cuts waste",
        "",
        sep,
        "  END OF REPORT",
        sep,
        "",
    ]

    # ── Write to disk ─────────────────────────────────────────────────────
    _ensure_exports_dir()
    try:
        with open(filepath, mode="w", encoding="utf-8") as fh:
            # Join each line with a newline and write the full document
            fh.write("\n".join(lines))

        # Resolve the absolute path so the admin knows exactly where it landed
        abs_path = os.path.abspath(filepath)
        return True, (
            f"[bold green]Summary report saved to:[/bold green] {abs_path}"
        )

    except Exception as err:
        return False, f"[bold red]Failed to write report:[/bold red] {err}"