"""
donations.py - Member: Haggai Kiptoo
Manages donation tracking and impact metrics
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from database import fetch_one, fetch_all, insert_data

console = Console()

class DonationManager:
    def __init__(self):
        if not fetch_one("SELECT * FROM food_bank WHERE food_bank_id = 1"):
            insert_data("food_bank", {"food_bank_id": 1, "name": "Agri-Tech Food Bank", 
                                     "location": "Nairobi", "total_food_saved": 0})
    
    def display_donations(self, limit=20):
        rows = fetch_all("""SELECT d.donation_id, u.username, d.amount, d.date, fb.name 
            FROM donations d JOIN transactions t ON d.transaction_id = t.transaction_id
            JOIN users u ON t.buyer_id = u.user_id JOIN food_bank fb ON d.food_bank_id = fb.food_bank_id
            ORDER BY d.date DESC LIMIT ?""", (limit,))
        if not rows: console.print("[yellow]No donations[/yellow]"); return
        table = Table(title="💚 Donation History", box=box.ROUNDED)
        [table.add_column(c, style=s) for c, s in [("ID","cyan"),("Donor","blue"),("Amount","green"),("Food Bank","yellow"),("Date","magenta")]]
        total = 0
        for r in rows: table.add_row(str(r[0]), r[1], f"{r[2]:.2f}", r[3], r[4][:16]); total += r[2]
        console.print(table); console.print(f"[green]💰 Total: KSH {total:.2f}[/green]")
    
    def display_personal_impact(self, user_id):
        s = fetch_one("SELECT COUNT(*), SUM(quantity), SUM(donation_amount) FROM transactions WHERE buyer_id = ?", (user_id,))
        if not s or s[0] == 0: console.print("[yellow]No purchases yet[/yellow]"); return
        user = fetch_one("SELECT username FROM users WHERE user_id = ?", (user_id,))
        name = user[0] if user else "User"
        console.print(Panel(f"[bold green]🌟 {name}'s Impact[/bold green]\n"
            f"🛒 {s[0]} purchases\n🌾 {s[1] or 0:.1f}kg food saved\n"
            f"💰 KSH {s[2] or 0:.2f} donated\n🍽️ {int((s[1] or 0) * 3)} meals provided", 
            title="My Impact", border_style="green", box=box.ROUNDED))
    
    def display_global_impact(self):
        s = fetch_one("SELECT COUNT(*), SUM(quantity), SUM(donation_amount), COUNT(DISTINCT buyer_id) FROM transactions")
        if not s or s[0] == 0: console.print("[yellow]No transactions yet[/yellow]"); return
        console.print(Panel(f"[bold green]🌍 Global Impact[/bold green]\n"
            f"🌾 {s[1] or 0:.1f}kg food saved\n🍽️ {int((s[1] or 0) * 3)} meals provided\n"
            f"💚 {s[3] or 0} donors\n💰 KSH {s[2] or 0:.2f} donated\n🛒 {s[0]} transactions",
            title="🌍 Global Impact", border_style="green", box=box.DOUBLE))