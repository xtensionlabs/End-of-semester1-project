"""
transactions.py - Member: Haggai Kiptoo
Handles transactions, 2% micro-donations, and food bank registry.
"""

from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, FloatPrompt, IntPrompt
from rich import box
from database import fetch_one, fetch_all, insert_data, update_data

console = Console()

DONATION_RATE = 0.02


class TransactionManager:

    def create_transaction(self, buyer_id, listing_id, quantity):
        listing = fetch_one(
            """SELECT l.listing_id, l.farmer_id, l.crop_name, l.quantity_kg,
               l.min_price, u.username
               FROM listings l JOIN users u ON l.farmer_id = u.user_id
               WHERE l.listing_id = ? AND l.status = 'available'""",
            (listing_id,)
        )
        if not listing:
            console.print("[red]Listing not found or no longer available.[/red]")
            return None

        available = listing['quantity_kg']
        if quantity > available:
            console.print(f"[red]Only {available}kg available for this listing.[/red]")
            return None

        crop    = listing['crop_name']
        price   = listing['min_price']
        farmer  = listing['username']

        total       = round(quantity * price, 2)
        donation    = round(total * DONATION_RATE, 2)
        farmer_pay  = round(total - donation, 2)
        now         = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        tid = insert_data("transactions", {
            "buyer_id":         buyer_id,
            "listing_id":       listing_id,
            "quantity":         quantity,
            "total_price":      total,
            "donation_amount":  donation,
            "transaction_date": now,
        })

        # Route 2% donation to the default food bank (id = 1)
        insert_data("donations", {
            "transaction_id": tid,
            "amount":         donation,
            "food_bank_id":   1,
            "date":           now,
        })

        # Reduce listing quantity; mark sold when fully purchased
        new_qty    = available - quantity
        new_status = 'sold' if new_qty == 0 else 'available'
        update_data("listings", {"quantity_kg": new_qty, "status": new_status}, {"listing_id": listing_id})

        # Keep food_bank aggregate in sync
        fb = fetch_one("SELECT total_food_saved_kg FROM food_bank WHERE food_bank_id = 1")
        if fb:
            update_data(
                "food_bank",
                {"total_food_saved_kg": fb['total_food_saved_kg'] + quantity},
                {"food_bank_id": 1}
            )

        console.print(Panel(
            f"[bold]Crop:[/bold] {crop}   [bold]Qty:[/bold] {quantity}kg\n"
            f"[bold]Total:[/bold] KSH {total:.2f}   "
            f"[green]Donation (2%):[/green] KSH {donation:.2f}\n"
            f"[blue]Farmer ({farmer}) receives:[/blue] KSH {farmer_pay:.2f}",
            title="[green]Transaction Complete[/green]",
            border_style="green"
        ))
        return {'id': tid, 'total': total, 'donation': donation}

    def display_transactions(self, user_id, role):
        if role == 'buyer':
            query = """
                SELECT t.transaction_id, l.crop_name,
                       u.username  AS other_party,
                       t.quantity, t.total_price, t.donation_amount, t.transaction_date
                FROM transactions t
                JOIN listings l ON t.listing_id = l.listing_id
                JOIN users u    ON l.farmer_id  = u.user_id
                WHERE t.buyer_id = ?
                ORDER BY t.transaction_date DESC"""
            rows = fetch_all(query, (user_id,))

        elif role == 'farmer':
            query = """
                SELECT t.transaction_id, l.crop_name,
                       u.username  AS other_party,
                       t.quantity, t.total_price, t.donation_amount, t.transaction_date
                FROM transactions t
                JOIN listings l ON t.listing_id  = l.listing_id
                JOIN users u    ON t.buyer_id     = u.user_id
                WHERE l.farmer_id = ?
                ORDER BY t.transaction_date DESC"""
            rows = fetch_all(query, (user_id,))

        else:  # admin — show all transactions with both buyer and farmer names
            query = """
                SELECT t.transaction_id, l.crop_name,
                       buyer.username  AS buyer_name,
                       farmer.username AS farmer_name,
                       t.quantity, t.total_price, t.donation_amount, t.transaction_date
                FROM transactions t
                JOIN listings l ON t.listing_id   = l.listing_id
                JOIN users buyer  ON t.buyer_id   = buyer.user_id
                JOIN users farmer ON l.farmer_id  = farmer.user_id
                ORDER BY t.transaction_date DESC"""
            rows = fetch_all(query)

        if not rows:
            console.print("[yellow]No transactions found.[/yellow]")
            return

        if role == 'admin':
            table = Table(title="All Transactions (Admin View)", box=box.ROUNDED)
            for col, style in [("ID","cyan"),("Crop","green"),("Buyer","yellow"),
                                ("Farmer","blue"),("Qty(kg)","white"),
                                ("Total(KSH)","blue"),("Donation(KSH)","green"),("Date","magenta")]:
                table.add_column(col, style=style)
            total_food = total_donations = 0
            for r in rows:
                table.add_row(
                    str(r['transaction_id']), r['crop_name'],
                    r['buyer_name'], r['farmer_name'],
                    f"{r['quantity']:.1f}", f"{r['total_price']:.2f}",
                    f"{r['donation_amount']:.2f}", r['transaction_date'][:16]
                )
                total_food      += r['quantity']
                total_donations += r['donation_amount']
        else:
            party_label = "Farmer" if role == 'buyer' else "Buyer"
            table = Table(title="Transaction History", box=box.ROUNDED)
            for col, style in [("ID","cyan"),("Crop","green"),(party_label,"yellow"),
                                ("Qty(kg)","white"),("Total(KSH)","blue"),
                                ("Donation(KSH)","green"),("Date","magenta")]:
                table.add_column(col, style=style)
            total_food = total_donations = 0
            for r in rows:
                table.add_row(
                    str(r['transaction_id']), r['crop_name'], r['other_party'],
                    f"{r['quantity']:.1f}", f"{r['total_price']:.2f}",
                    f"{r['donation_amount']:.2f}", r['transaction_date'][:16]
                )
                total_food      += r['quantity']
                total_donations += r['donation_amount']

        console.print(table)
        console.print(
            f"[green]Food Saved: {total_food:.1f}kg[/green]  "
            f"[blue]Total Donations: KSH {total_donations:.2f}[/blue]"
        )

    def display_food_bank(self):
        s = fetch_one(
            """SELECT COUNT(*)       AS cnt,
                      SUM(d.amount)  AS total_amount,
                      SUM(t.quantity) AS total_food
               FROM transactions t
               JOIN donations d ON t.transaction_id = d.transaction_id"""
        )
        cnt         = s['cnt']          if s else 0
        total_amount = s['total_amount'] or 0 if s else 0
        total_food   = s['total_food']   or 0 if s else 0

        console.print(Panel(
            f"[bold green]Food Bank Summary[/bold green]\n"
            f"Total Donations: {cnt}\n"
            f"Amount Donated: KSH {total_amount:.2f}\n"
            f"Food Saved: {total_food:.1f}kg\n"
            f"Estimated Meals Provided: {int(total_food * 3)}",
            title="Impact Dashboard",
            border_style="green",
            box=box.DOUBLE
        ))

    def process_purchase(self, buyer_id):
        import listings
        listings.view_all_active_listings()
        try:
            lid = IntPrompt.ask("\n[bold yellow]Enter Listing ID to purchase[/bold yellow]")
            if not lid:
                return None
            qty = FloatPrompt.ask("[bold yellow]Quantity (kg)[/bold yellow]", default=1.0)
            if qty <= 0:
                console.print("[red]Quantity must be greater than 0.[/red]")
                return None
            confirm = Prompt.ask("[bold red]Confirm purchase? (y/n)[/bold red]", choices=["y", "n"])
            if confirm != 'y':
                console.print("[yellow]Purchase cancelled.[/yellow]")
                return None
            return self.create_transaction(buyer_id, lid, qty)
        except (ValueError, KeyboardInterrupt):
            console.print("[red]Invalid input.[/red]")
            return None
