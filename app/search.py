"""
search.py - Member: Terer, Brian
Marketplace search engine: filter and sort available crop listings.
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, FloatPrompt
from rich import box
from database import fetch_all

console = Console()

_SORT_OPTIONS = {
    "price_asc":    ("l.min_price ASC",    "Price: Low to High"),
    "price_desc":   ("l.min_price DESC",   "Price: High to Low"),
    "quantity":     ("l.quantity_kg DESC", "Quantity: Most First"),
    "crop":         ("l.crop_name ASC",    "Crop Name (A–Z)"),
    "harvest":      ("l.harvest_date ASC", "Harvest Date: Soonest"),
}


class SearchEngine:

    def search_listings(self, crop_name=None, location=None,
                        min_price=None, max_price=None, sort_by="price_asc"):
        """
        Query available listings with optional filters.

        Parameters
        ----------
        crop_name  : partial name match (case-insensitive)
        location   : partial location match (case-insensitive)
        min_price  : lower bound for KSH/kg price
        max_price  : upper bound for KSH/kg price
        sort_by    : one of the keys in _SORT_OPTIONS

        Returns list of listing dicts.
        """
        query = """
            SELECT l.listing_id, l.crop_name, l.quantity_kg, l.min_price,
                   l.location, l.harvest_date, u.username AS farmer_name
            FROM listings l
            JOIN users u ON l.farmer_id = u.user_id
            WHERE l.status = 'available'
        """
        params = []

        if crop_name:
            query += " AND l.crop_name LIKE ?"
            params.append(f"%{crop_name}%")

        if location:
            query += " AND l.location LIKE ?"
            params.append(f"%{location}%")

        if min_price is not None:
            query += " AND l.min_price >= ?"
            params.append(min_price)

        if max_price is not None:
            query += " AND l.min_price <= ?"
            params.append(max_price)

        order_clause, _ = _SORT_OPTIONS.get(sort_by, _SORT_OPTIONS["price_asc"])
        query += f" ORDER BY {order_clause}"

        return fetch_all(query, tuple(params))

    def display_results(self, listings, title="Search Results"):
        """Render a listing set as a formatted rich table."""
        if not listings:
            console.print("[yellow]No listings match your search criteria.[/yellow]")
            return

        table = Table(title=title, box=box.ROUNDED, border_style="cyan", show_lines=True)
        columns = [
            ("ID",        "cyan",    "right"),
            ("Crop",      "bold green", "left"),
            ("Qty (kg)",  "white",   "right"),
            ("KSH / kg",  "blue",    "right"),
            ("Location",  "yellow",  "left"),
            ("Farmer",    "magenta", "left"),
            ("Harvest",   "dim",     "left"),
        ]
        for name, style, justify in columns:
            table.add_column(name, style=style, justify=justify)

        for l in listings:
            table.add_row(
                str(l['listing_id']),
                l['crop_name'],
                f"{l['quantity_kg']:.1f}",
                f"{l['min_price']:.2f}",
                l['location'] or "—",
                l['farmer_name'],
                l['harvest_date'] or "—",
            )

        console.print(table)
        console.print(f"[dim]  {len(listings)} listing(s) found.[/dim]\n")

    def search_interactive(self):
        """
        Guided search flow.  Returns the list of matching listings so a
        caller (e.g. a buy-flow) can hand-off to TransactionManager.
        """
        console.print(Panel(
            "[bold cyan]Crop Listing Search[/bold cyan]\n"
            "[dim]Press Enter to skip any filter.[/dim]",
            border_style="cyan"
        ))

        crop_name = Prompt.ask("[bold]Crop name[/bold]", default="").strip() or None
        location  = Prompt.ask("[bold]Location[/bold]",  default="").strip() or None

        use_price = Prompt.ask(
            "Apply price filter? [y/n]", choices=["y", "n"], default="n"
        )
        min_price = max_price = None
        if use_price == "y":
            try:
                min_price = FloatPrompt.ask("  Min price (KSH/kg)", default=0.0)
                max_price = FloatPrompt.ask("  Max price (KSH/kg)", default=9999.0)
                if min_price > max_price:
                    console.print("[red]Min price exceeds max price — filter ignored.[/red]")
                    min_price = max_price = None
            except (ValueError, KeyboardInterrupt):
                min_price = max_price = None

        # Build a menu string from the sort options
        sort_keys  = list(_SORT_OPTIONS.keys())
        sort_labels = [f"[bold]{k}[/bold] – {v}" for k, v in _SORT_OPTIONS.values()]
        console.print("\n[bold]Sort options:[/bold]")
        for key, (_, label) in _SORT_OPTIONS.items():
            console.print(f"  [cyan]{key}[/cyan] — {label}")

        sort_by = Prompt.ask(
            "\n[bold]Sort by[/bold]",
            choices=sort_keys,
            default="price_asc"
        )

        results = self.search_listings(
            crop_name=crop_name,
            location=location,
            min_price=min_price,
            max_price=max_price,
            sort_by=sort_by,
        )

        console.print()
        self.display_results(results)
        return results
