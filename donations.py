"""
donations.py - Member: Haggai Kiptoo
Manages donation tracking and social impact metrics.
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from database import fetch_one, fetch_all, insert_data

console = Console()


class DonationManager:

    def __init__(self):
        # Ensure the default food bank record exists
        if not fetch_one("SELECT food_bank_id FROM food_bank WHERE food_bank_id = 1"):
            insert_data("food_bank", {
                "food_bank_id":      1,
                "name":              "Agri-Tech Food Bank",
                "location":          "Nairobi",
                "total_food_saved_kg": 0,
            })

    def display_donations(self, limit=20):
        rows = fetch_all(
            """SELECT d.donation_id, u.username, d.amount, fb.name, d.date
               FROM donations d
               JOIN transactions t  ON d.transaction_id = t.transaction_id
               JOIN users u         ON t.buyer_id        = u.user_id
               JOIN food_bank fb    ON d.food_bank_id    = fb.food_bank_id
               ORDER BY d.date DESC LIMIT ?""",
            (limit,)
        )
        if not rows:
            console.print("[yellow]No donations recorded yet.[/yellow]")
            return

        table = Table(title="Donation History", box=box.ROUNDED)
        for col, style in [("ID","cyan"),("Donor","blue"),("Amount (KSH)","green"),
                            ("Food Bank","yellow"),("Date","magenta")]:
            table.add_column(col, style=style)

        total = 0
        for r in rows:
            table.add_row(
                str(r['donation_id']),
                r['username'],
                f"{r['amount']:.2f}",
                r['name'],
                r['date'][:16]
            )
            total += r['amount']

        console.print(table)
        console.print(f"[green]Total Donated: KSH {total:.2f}[/green]")

    def display_personal_impact(self, user_id):
        s = fetch_one(
            """SELECT COUNT(*)             AS count,
                      SUM(quantity)         AS food,
                      SUM(donation_amount)  AS donated
               FROM transactions WHERE buyer_id = ?""",
            (user_id,)
        )
        if not s or not s['count']:
            console.print("[yellow]No purchases yet.[/yellow]")
            return

        user = fetch_one("SELECT username FROM users WHERE user_id = ?", (user_id,))
        name    = user['username'] if user else "User"
        food    = s['food']    or 0
        donated = s['donated'] or 0

        console.print(Panel(
            f"[bold green]{name}'s Impact[/bold green]\n"
            f"Purchases: {s['count']}\n"
            f"Food Saved: {food:.1f}kg\n"
            f"Donated: KSH {donated:.2f}\n"
            f"Meals Provided: {int(food * 3)}",
            title="My Impact",
            border_style="green",
            box=box.ROUNDED
        ))

    def display_global_impact(self):
        s = fetch_one(
            """SELECT COUNT(*)                AS count,
                      SUM(quantity)            AS food,
                      SUM(donation_amount)     AS donated,
                      COUNT(DISTINCT buyer_id) AS donors
               FROM transactions"""
        )
        if not s or not s['count']:
            console.print("[yellow]No transactions yet.[/yellow]")
            return

        food    = s['food']    or 0
        donated = s['donated'] or 0

        console.print(Panel(
            f"[bold green]Global Impact[/bold green]\n"
            f"Food Saved: {food:.1f}kg\n"
            f"Meals Provided: {int(food * 3)}\n"
            f"Unique Donors: {s['donors'] or 0}\n"
            f"Total Donated: KSH {donated:.2f}\n"
            f"Transactions: {s['count']}",
            title="Global Impact",
            border_style="green",
            box=box.DOUBLE
        ))
