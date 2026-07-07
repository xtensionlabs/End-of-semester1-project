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

VALID_ROLES = ["farmer", "buyer", "admin"]

# ---------------------------------------------------------------------------
# Session state — kept in memory for the lifetime of the running program.
# ---------------------------------------------------------------------------
_current_user = None


def get_current_user():
    """Return the currently logged-in user's data as a dict, or None."""
    return _current_user


def logout_user():
    """Clear the current session."""
    global _current_user
    if _current_user:
        console.print(f"[yellow]Logged out {_current_user['username']}.[/yellow]")
    _current_user = None


def is_farmer():
    return bool(_current_user) and _current_user["role"] == "farmer"


def is_buyer():
    return bool(_current_user) and _current_user["role"] == "buyer"


def is_admin():
    return bool(_current_user) and _current_user["role"] == "admin"


# ---------------------------------------------------------------------------
# Programmatic login (used by tests / other modules; no prompts)
# ---------------------------------------------------------------------------
def login_user(username, password):
    """
    Attempt to log in with a username/password.
    On success, stores the user in session and returns True.
    On failure, returns False.
    """
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


# ---------------------------------------------------------------------------
# Interactive flows (what the terminal menu calls)
# ---------------------------------------------------------------------------
def register():
    """Interactive registration flow. Returns the new user_id, or None."""
    console.print(Panel("[bold green]Create a New Account[/bold green]"))

    username = Prompt.ask("Choose a username").strip()
    if users.username_exists(username):
        console.print(f"[bold red]Username '{username}' is already taken.[/bold red]")
        return None

    password = Prompt.ask("Choose a password", password=True)
    confirm = Prompt.ask("Confirm password", password=True)
    if password != confirm:
        console.print("[bold red]Passwords do not match.[/bold red]")
        return None

    role = Prompt.ask("Role", choices=VALID_ROLES, default="farmer")
    location = Prompt.ask("Location (e.g. town/county)", default="")
    phone = Prompt.ask("Phone number", default="")

    user_id = users.create_user(username, password, role, location, phone)
    if user_id is None:
        console.print("[bold red]Registration failed — username taken.[/bold red]")
        return None

    console.print(
        Panel(f"[bold green]Account created for {username} (role: {role}).[/bold green]")
    )
    return user_id


def login():
    """Interactive login flow. Returns True on success, False otherwise."""
    console.print(Panel("[bold cyan]Log In[/bold cyan]"))

    username = Prompt.ask("Username").strip()
    password = Prompt.ask("Password", password=True)

    if login_user(username, password):
        console.print(
            f"[bold green]Welcome back, {username}! (role: {_current_user['role']})[/bold green]"
        )
        return True

    console.print("[bold red]Invalid username or password.[/bold red]")
    return False


def view_profile():
    """Display the current user's profile in a table."""
    if not _current_user:
        console.print("[bold red]No user is logged in.[/bold red]")
        return

    table = Table(title="My Profile", show_header=False)
    table.add_row("Username", _current_user["username"])
    table.add_row("Role", _current_user["role"])
    table.add_row("Location", _current_user["location"] or "-")
    table.add_row("Phone", _current_user["phone"] or "-")
    console.print(table)


def change_location():
    """Interactively update the logged-in user's location."""
    if not _current_user:
        console.print("[bold red]No user is logged in.[/bold red]")
        return

    new_location = Prompt.ask("New location").strip()
    users.update_user_location(_current_user["user_id"], new_location)
    _current_user["location"] = new_location
    console.print(f"[bold green]Location updated to '{new_location}'.[/bold green]")


# ---------------------------------------------------------------------------
# Standalone demo/test menu — run `python auth.py` to try it out.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from database import init_db

    init_db()

    while True:
        console.print(Panel("[bold]1[/bold]. Register   [bold]2[/bold]. Login   "
                             "[bold]3[/bold]. Profile   [bold]4[/bold]. Change Location   "
                             "[bold]5[/bold]. Logout   [bold]6[/bold]. Quit"))
        choice = Prompt.ask("Choose an option", choices=["1", "2", "3", "4", "5", "6"])

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
            console.print("[bold cyan]Goodbye![/bold cyan]")
            break
