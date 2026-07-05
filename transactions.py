"""
transactions.py - Member: Haggai Kiptoo
Handles transactions, 2% donations, and food bank registry
"""

from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, FloatPrompt, IntPrompt
from rich import box
from database import fetch_one, fetch_all, insert_data, update_data

console = Console()

class TransactionManager:
    def create_transaction(self, buyer_id, listing_id, quantity):
        listing = fetch_one("""SELECT l.listing_id, l.farmer_id, l.crop_name, l.quantity_kg, 
            l.min_price, u.username FROM listings l JOIN users u ON l.farmer_id = u.user_id 
            WHERE l.listing_id = ? AND l.status = 'Available'""", (listing_id,))
        if not listing: console.print("[red]❌ Not available[/red]"); return None
        _, _, crop, available, price, farmer = listing
        if quantity > available: console.print(f"[red]❌ Only {available}kg[/red]"); return None
        
        total, donation, farmer_pay = quantity * price, (quantity * price) * 0.02, (quantity * price) * 0.98
        tid = insert_data("transactions", {"buyer_id": buyer_id, "listing_id": listing_id, 
            "quantity": quantity, "total_price": total, "donation_amount": donation, 
            "transaction_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        insert_data("donations", {"transaction_id": tid, "amount": donation, 
            "food_bank_id": 1, "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        new_qty, status = available - quantity, 'Sold' if available - quantity == 0 else 'Available'
        update_data("listings", {"quantity_kg": new_qty, "status": status}, "listing_id = ?", (listing_id,))
        
        console.print(f"\n[green]✅ Transaction done![/green]")
        console.print(Panel(f"[bold]Crop:[/bold] {crop}  [bold]Qty:[/bold] {quantity}kg\n"
            f"[bold]Total:[/bold] KSH {total:.2f}  [green]💰 Donation:[/green] KSH {donation:.2f}\n"
            f"[blue]👨‍🌾 Farmer:[/blue] KSH {farmer_pay:.2f}", title="Summary", border_style="green"))
        return {'id': tid, 'total': total, 'donation': donation}
    
    def display_transactions(self, user_id, role):
        q = ("""SELECT t.transaction_id, l.crop_name, u.username, t.quantity, t.total_price, 
            t.donation_amount, t.transaction_date FROM transactions t JOIN listings l 
            ON t.listing_id = l.listing_id JOIN users u ON """ + 
            ("l.farmer_id = u.user_id WHERE t.buyer_id = ?" if role == 'buyer' else 
             "t.buyer_id = u.user_id WHERE l.farmer_id = ?" if role == 'farmer' else 
             "u.user_id IN (l.farmer_id, t.buyer_id)") + " ORDER BY t.transaction_date DESC")
        rows = fetch_all(q, (user_id,)) if role != 'admin' else fetch_all(q.replace(" WHERE ", " WHERE 1=1 AND "))
        
        if not rows: console.print("[yellow]No transactions[/yellow]"); return
        table = Table(title="Transaction History", box=box.ROUNDED)
        [table.add_column(c, style=s) for c, s in [("ID","cyan"),("Crop","green"),("User","yellow"),("Qty","white"),("Total","blue"),("Donation","green"),("Date","magenta")]]
        food, donations = 0, 0
        for r in rows: 
            table.add_row(str(r[0]), r[1], r[2], str(r[3]), f"{r[4]:.2f}", f"{r[5]:.2f}", r[6][:16])
            food, donations = food + r[3], donations + r[5]
        console.print(table)
        console.print(f"[green]🌾 Food Saved: {food}kg[/green]  [blue]💰 Donations: KSH {donations:.2f}[/blue]")
    
    def display_food_bank(self):
        s = fetch_one("SELECT COUNT(*), SUM(amount), SUM(quantity) FROM transactions t JOIN donations d ON t.transaction_id = d.transaction_id")
        console.print(Panel(f"[bold green]🌾 Food Bank[/bold green]\nDonations: {s[0] if s else 0}\n"
            f"Amount: KSH {s[1] if s else 0:.2f}\nFood Saved: {s[2] if s else 0:.1f}kg\n"
            f"Meals: {int((s[2] if s else 0) * 3)}", title="🌍 Impact", border_style="green", box=box.DOUBLE))
    
    def process_purchase(self, buyer_id):
        from listings import ListingManager
        ListingManager().display_all_listings()
        try:
            lid = IntPrompt.ask("\n[bold yellow]Listing ID[/bold yellow]")
            if not lid: return None
            qty = FloatPrompt.ask("[bold yellow]Quantity (kg)[/bold yellow]", default=1.0)
            if qty <= 0: console.print("[red]Qty must be > 0[/red]"); return None
            if Prompt.ask("[bold red]Confirm? (y/n)[/bold red]", choices=["y", "n"]) != 'y':
                console.print("[yellow]Cancelled[/yellow]"); return None
            return self.create_transaction(buyer_id, lid, qty)
        except ValueError: console.print("[red]Invalid input[/red]"); return None