"""
auth.py
=======
Member: Warui, Aaron
User registration, login, session management, and role-based access
control for the Agri-Tech Digital Marketplace.

Exposes:
    register()          -> interactive registration flow
    login()              -> interactive login flow
    login_user(username, password) -> programmatic login, returns bool
    logout_user()
    get_current_user()   -> dict of the logged-in user, or None
    is_farmer(), is_buyer(), is_admin()
    view_profile()
    change_location()
"""

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

import users

console = Console()

VALID_ROLES = ["Farmer", "Buyer", "Admin"]

_current_user = None


def get_current_user():
    return _current_user


def logout_user():
    global _current_user
    if _current_user:
        console.print(f"[yellow]Logged out {_current_user['username']}.[/yellow]")
    _current_user = None


def is_farmer():
    return bool(_current_user) and _current_user["role"] == "Farmer"


def is_buyer():
    return bool(_current_user) and _current_user["role"] == "Buyer"


def is_admin():
    return bool(_current_user) and _current_user["role"] == "Admin"


def login_user(username, password):
    global _current_user
    row = users.get_user_by_username(username)

    if row is None:
        return False

    if not users.verify_password(password, row["password"]):
        return False

    _current_user = {
        "user_id": row["user_id"],
        "username": row["username"],
        "role": row["role"],
        "location": row["location"],
        "phone": row["phone"],
    }

    return True


def register():
    console.print(Panel("[bold green]Create a New Account[/bold green]"))

    username = Prompt.ask("Choose a username").strip()

    if users.username_exists(username):
        console.print("[bold red]Username already exists.[/bold red]")
        return None

    password = Prompt.ask("Choose a password", password=True)
    confirm = Prompt.ask("Confirm password", password=True)

    if password != confirm:
        console.print("[bold red]Passwords do not match.[/bold red]")
        return None

    role = Prompt.ask("Role", choices=VALID_ROLES, default="Farmer")
    location = Prompt.ask("Location", default="")
    phone = Prompt.ask("Phone", default="")

    user_id = users.create_user(
        username,
        password,
        role,
        location,
        phone
    )

    console.print("[bold green]Registration Successful![/bold green]")
    return user_id


def login():
    console.print(Panel("[bold cyan]Login[/bold cyan]"))

    username = Prompt.ask("Username")
    password = Prompt.ask("Password", password=True)

    if login_user(username, password):
        console.print(f"[green]Welcome {username}![/green]")
        return True

    console.print("[red]Invalid username/password[/red]")
    return False


def view_profile():

    if not _current_user:
        console.print("[red]No user logged in.[/red]")
        return

    table = Table(title="My Profile", show_header=False)

    table.add_row("Username", _current_user["username"])
    table.add_row("Role", _current_user["role"])
    table.add_row("Location", _current_user["location"] or "-")
    table.add_row("Phone", _current_user["phone"] or "-")

    console.print(table)


def change_location():

    if not _current_user:
        console.print("[red]No user logged in.[/red]")
        return

    new_location = Prompt.ask("New location")

    users.update_user_location(
        _current_user["user_id"],
        new_location
    )

    _current_user["location"] = new_location

    console.print("[green]Location updated successfully.[/green]")


if __name__ == "__main__":

    from database import init_db

    init_db()

    while True:

        console.print(
            "\n1.Register\n2.Login\n3.Profile\n4.Change Location\n5.Logout\n6.Exit"
        )

        choice = input("Choice: ")

        if choice == "1":
            register()

        elif choice == "2":
            login()

        elif choice == "3":
            view_profile()

        elif choice == "4":
            change_location()

        elif choice == "5":
            logout_user()

        elif choice == "6":
            break