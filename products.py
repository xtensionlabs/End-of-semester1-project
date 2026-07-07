"""
products.py
Member 3: Mwangi, Wendy — Product & Listing Management
Stores and manages the registered crop commodity catalogue.
"""

from rich.console import Console
from rich.table import Table
from rich import box

console = Console()

# Master catalogue of tradeable commodities.
# Sorted alphabetically; call add_crop() to extend at runtime.
CROPS = sorted([
    "Avocado",
    "Bananas",
    "Beans",
    "Cabbage",
    "Carrots",
    "Groundnuts",
    "Kale",
    "Maize",
    "Mangoes",
    "Onions",
    "Peas",
    "Potatoes",
    "Rice",
    "Sorghum",
    "Sunflower",
    "Sweet Potatoes",
    "Tea Leaves",
    "Tomatoes",
    "Wheat",
])


def display_crops():
    """Render all registered commodities in a numbered rich table."""
    table = Table(
        title="Registered Market Commodities",
        box=box.SIMPLE_HEAD,
        border_style="green",
    )
    table.add_column("No.", style="cyan", justify="right", width=4)
    table.add_column("Crop Name", style="bold green")
    for i, crop in enumerate(CROPS, 1):
        table.add_row(str(i), crop)
    console.print(table)


def get_crop(choice):
    """Return the crop name at the given 1-based index, or None."""
    if 1 <= choice <= len(CROPS):
        return CROPS[choice - 1]
    return None


def crop_exists(crop_name):
    """Return True if crop_name (case-insensitive) is in the catalogue."""
    return crop_name.strip().title() in CROPS


def add_crop(crop_name):
    """Add a new crop to the in-memory catalogue (persists for this session)."""
    name = crop_name.strip().title()
    if name not in CROPS:
        CROPS.append(name)
        CROPS.sort()
        console.print(f"[green]'{name}' added to the commodity list.[/green]")
    else:
        console.print(f"[yellow]'{name}' is already registered.[/yellow]")


def view_all_crops():
    """Display the full crop catalogue."""
    display_crops()


if __name__ == "__main__":
    from rich.prompt import Prompt

    while True:
        console.print("\n[bold]Crop Management Menu:[/bold]")
        console.print("  1. View all crops")
        console.print("  2. Add a new crop")
        console.print("  3. Exit")
        choice = Prompt.ask("Choice", choices=["1", "2", "3"])
        if choice == "1":
            view_all_crops()
        elif choice == "2":
            new_crop = Prompt.ask("New crop name").strip()
            add_crop(new_crop)
        elif choice == "3":
            console.print("[cyan]Exiting crop management.[/cyan]")
            break
