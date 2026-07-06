"""
dashboard.py
============
Member: Maina, Njeri
Builds the visual dashboard using rich panels and tables.
Displays total system stats and warns if crop prices are suspiciously low
compared to the current market average.
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import reports
from database import fetch_all

# Shared console for rich printing
console = Console()


def check_price_alerts():
    """
    Checks all available listings and calculates the average price per crop.
    If a farmer is selling >30% below the real market average, it creates an alert.
    """
    # Fetch only active listings from the database
    query = "SELECT listing_id, crop_name, min_price, location FROM listings WHERE status = 'available'"
    active_listings = fetch_all(query)

    alerts = []

    if not active_listings:
        return alerts

    # 1. Group the prices to find the market average for each crop
    crop_totals = {}
    crop_counts = {}

    for item in active_listings:
        crop = item["crop_name"].lower()
        price = float(item["min_price"])

        crop_totals[crop] = crop_totals.get(crop, 0) + price
        crop_counts[crop] = crop_counts.get(crop, 0) + 1

    # 2. Calculate the averages
    crop_averages = {}
    for crop in crop_totals:
        crop_averages[crop] = crop_totals[crop] / crop_counts[crop]

    # 3. Check for severe undercutting (price is 30% or more below the average)
    for item in active_listings:
        crop = item["crop_name"].lower()
        price = float(item["min_price"])
        avg_price = crop_averages[crop]

        # If the price is less than 70% of the average, trigger alert
        if price < (avg_price * 0.70):
            warning = (
                f"⚠️  [bold yellow]Listing #{item['listing_id']} ({item['crop_name'].title()})[/bold yellow] "
                f"at [bold red]KSH {price}/kg[/bold red] in {item['location']} is significantly below "
                f"the current market average (KSH {avg_price:.2f}/kg)."
            )
            alerts.append(warning)

    return alerts


def display_dashboard_view():
    """
    Builds and displays the beautiful dashboard on the terminal.
    """
    # 1. Get the numbers from your reports.py file
    stats = reports.generate_summary_data()

    # 2. Build a beautiful table for the statistics
    stats_table = Table(show_header=False, expand=True)
    stats_table.add_column("Metric", style="cyan bold", width=30)
    stats_table.add_column("Value", style="green bold", justify="right")

    # Add the data rows to the table
    stats_table.add_row("Total Crops Listed on Platform", f"{stats['total_listings']} listings")
    stats_table.add_row("Total Successful Sales", f"{stats['total_transactions']} sales")
    stats_table.add_row("Total Food Saved from Waste", f"[bold green]{stats['food_saved_kg']} kg[/bold green]")
    stats_table.add_row("Total Food Bank Donations", f"KSH {stats['total_donations_ksh']}")
    stats_table.add_row("Estimated Meals Provided", f" {stats['meals_provided']} meals")

    # Print the stats table inside a green panel
    console.print("\n")
    console.print(
        Panel(
            stats_table,
            title="[bold white] AGRI-TECH SYSTEM DASHBOARD[/bold white]",
            border_style="green",
            padding=(1, 2)
        )
    )

    # 3. Check for price alerts and display them
    alerts = check_price_alerts()

    if not alerts:
        # No bad prices found -> Show a nice green success message
        alert_text = "[bold green]✓ All current market prices are stable and fair.[/bold green]"
        alert_border = "blue"
    else:
        # Bad prices found -> Combine them and show a red warning box
        alert_text = "\n".join(alerts)
        alert_border = "red"

    console.print(
        Panel(
            alert_text,
            title="[bold red] REAL-TIME MARKET PRICE ALERTS[/bold red]",
            border_style=alert_border,
            padding=(1, 2)
        )
    )


