"""
matching.py - Member: Terer, Brian
Smart matching engine: scores and ranks available listings for a buyer.

Scoring model (100 points total):
    Location  40 pts  — exact town > same region > different region
    Price     35 pts  — cheaper vs. budget = higher score; over-budget = 0
    Quantity  25 pts  — enough supply relative to desired quantity
"""

import math
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, FloatPrompt
from rich import box
from database import fetch_all, fetch_one

console = Console()


# ---------------------------------------------------------------------------
# Distance simulation — group Kenyan towns/counties into geographic regions.
# Matching two listings in the same region earns partial location credit.
# ---------------------------------------------------------------------------
_REGION_MAP = {
    # Nairobi Metro
    "nairobi":      "nairobi_metro", "westlands":   "nairobi_metro",
    "kiambu":       "nairobi_metro", "thika":       "nairobi_metro",
    "ruiru":        "nairobi_metro",
    # Central
    "nyeri":        "central",       "muranga":     "central",
    "murang'a":     "central",       "kirinyaga":   "central",
    "nyandarua":    "central",       "karatina":    "central",
    # Rift Valley
    "nakuru":       "rift_valley",   "eldoret":     "rift_valley",
    "uasin gishu":  "rift_valley",   "nandi":       "rift_valley",
    "kericho":      "rift_valley",   "bomet":       "rift_valley",
    "laikipia":     "rift_valley",   "baringo":     "rift_valley",
    "kajiado":      "rift_valley",   "narok":       "rift_valley",
    "trans-nzoia":  "rift_valley",   "trans nzoia": "rift_valley",
    "west pokot":   "rift_valley",   "turkana":     "rift_valley",
    # Western & Nyanza
    "kisumu":       "western",       "kakamega":    "western",
    "vihiga":       "western",       "bungoma":     "western",
    "busia":        "western",       "siaya":       "western",
    "homa bay":     "western",       "migori":      "western",
    "kisii":        "western",       "nyamira":     "western",
    # Eastern
    "meru":         "eastern",       "embu":        "eastern",
    "tharaka":      "eastern",       "machakos":    "eastern",
    "makueni":      "eastern",       "kitui":       "eastern",
    "isiolo":       "eastern",
    # Coast
    "mombasa":      "coast",         "kilifi":      "coast",
    "kwale":        "coast",         "taita":       "coast",
    "lamu":         "coast",         "tana river":  "coast",
    # North Eastern
    "garissa":      "north_eastern", "wajir":       "north_eastern",
    "mandera":      "north_eastern",
}

_REGION_LABELS = {
    "nairobi_metro": "Nairobi Metro",
    "central":       "Central",
    "rift_valley":   "Rift Valley",
    "western":       "Western / Nyanza",
    "eastern":       "Eastern",
    "coast":         "Coast",
    "north_eastern": "North Eastern",
}


def _get_region(location):
    """Map a location string to its regional cluster, or None if unknown."""
    if not location:
        return None
    loc = location.lower().strip()
    if loc in _REGION_MAP:
        return _REGION_MAP[loc]
    for key, region in _REGION_MAP.items():
        if key in loc or loc in key:
            return region
    return None


def _distance_label(buyer_loc, listing_loc):
    """Return a human-readable proximity label."""
    if not buyer_loc or not listing_loc:
        return "Unknown"
    b = buyer_loc.lower().strip()
    l = listing_loc.lower().strip()
    if b == l or b in l or l in b:
        return "Same Town"
    br = _get_region(buyer_loc)
    lr = _get_region(listing_loc)
    if br and lr and br == lr:
        return f"Same Region ({_REGION_LABELS.get(br, br)})"
    return "Different Region"


# ---------------------------------------------------------------------------
# Individual scoring functions
# ---------------------------------------------------------------------------

def _score_location(buyer_location, listing_location, max_pts=40):
    """Location proximity score (0 – max_pts)."""
    if not buyer_location or not listing_location:
        return max_pts // 2          # neutral when location is unknown

    b = buyer_location.lower().strip()
    l = listing_location.lower().strip()

    if b == l or b in l or l in b:  # same town
        return max_pts

    br = _get_region(buyer_location)
    lr = _get_region(listing_location)
    if br and lr and br == lr:       # same region
        return int(max_pts * 0.60)

    return int(max_pts * 0.10)       # different region


def _score_price(listing_price, max_price, max_pts=35):
    """
    Price score (0 – max_pts).
    Full score when listing_price is well below budget.
    Score decays linearly as the listing approaches the buyer's ceiling.
    Over-budget listings score 0.
    """
    if max_price is None or max_price <= 0:
        return max_pts // 2          # neutral when no budget given

    if listing_price > max_price:
        return 0                     # over budget

    # ratio = 0 means free (unlikely), ratio = 1 means exactly at ceiling
    ratio = listing_price / max_price
    return int(max_pts * (1.0 - ratio * 0.6))


def _score_quantity(quantity_kg, desired_qty, max_pts=25):
    """
    Quantity score (0 – max_pts).
    If desired_qty given: full score when listing covers it, proportional below.
    Otherwise: logarithmic scale (more supply = more reliable).
    """
    if desired_qty and desired_qty > 0:
        ratio = min(quantity_kg / desired_qty, 1.0)
        return int(max_pts * ratio)

    # No preference — use log scale capped at 1 000 kg
    return int(max_pts * min(math.log1p(quantity_kg) / math.log1p(1000), 1.0))


# ---------------------------------------------------------------------------
# MatchingEngine class
# ---------------------------------------------------------------------------

class MatchingEngine:

    def get_match_score(self, listing, buyer_location=None,
                        max_price=None, desired_qty=None):
        """
        Score a single listing for a buyer's preferences.

        Returns
        -------
        (total_score, breakdown_dict)
            total_score  : 0–100 integer
            breakdown    : {'location': int, 'price': int, 'quantity': int}
        """
        loc_pts = _score_location(buyer_location, listing.get('location'))
        prc_pts = _score_price(listing['min_price'], max_price)
        qty_pts = _score_quantity(listing['quantity_kg'], desired_qty)

        return loc_pts + prc_pts + qty_pts, {
            'location': loc_pts,
            'price':    prc_pts,
            'quantity': qty_pts,
        }

    def find_top_matches(self, buyer_location=None, desired_crop=None,
                         max_price=None, desired_qty=None, top_n=5):
        """
        Score every available listing and return the top N matches, sorted
        by match score (highest first).

        Parameters
        ----------
        buyer_location : buyer's town/county for proximity scoring
        desired_crop   : optional crop name filter (partial match)
        max_price      : buyer's maximum price per kg
        desired_qty    : buyer's target quantity in kg
        top_n          : number of results to return (default 5)

        Returns list of listing dicts, each enriched with:
            match_score  : 0–100 int
            breakdown    : {'location', 'price', 'quantity'}
            distance     : proximity label string
        """
        query = """
            SELECT l.listing_id, l.crop_name, l.quantity_kg, l.min_price,
                   l.location, l.harvest_date, u.username AS farmer_name
            FROM listings l
            JOIN users u ON l.farmer_id = u.user_id
            WHERE l.status = 'available'
        """
        params = []

        if desired_crop:
            query += " AND l.crop_name LIKE ?"
            params.append(f"%{desired_crop}%")

        # Hard-filter by price ceiling before scoring (no point scoring over-budget rows)
        if max_price is not None:
            query += " AND l.min_price <= ?"
            params.append(max_price)

        listings = fetch_all(query, tuple(params))
        if not listings:
            return []

        scored = []
        for lst in listings:
            score, breakdown = self.get_match_score(
                lst,
                buyer_location=buyer_location,
                max_price=max_price,
                desired_qty=desired_qty,
            )
            scored.append({
                **lst,
                'match_score': score,
                'breakdown':   breakdown,
                'distance':    _distance_label(buyer_location, lst.get('location')),
            })

        scored.sort(key=lambda x: x['match_score'], reverse=True)
        return scored[:top_n]

    def display_matches(self, matches, buyer_location=None):
        """
        Render top matches as a rich table with colour-coded match percentages
        and score breakdowns.
        """
        if not matches:
            console.print("[yellow]No matching listings found.[/yellow]")
            return

        subtitle = f"Buyer location: [cyan]{buyer_location}[/cyan]" if buyer_location else ""
        console.print(Panel(
            f"[bold green]Top {len(matches)} Smart Match Result(s)[/bold green]"
            + (f"\n{subtitle}" if subtitle else ""),
            border_style="green"
        ))

        table = Table(box=box.DOUBLE_EDGE, border_style="green", show_lines=True)
        table.add_column("Rank",     style="bold cyan",  justify="center", width=5)
        table.add_column("Match %",  justify="center",   width=9)
        table.add_column("ID",       style="cyan",        justify="right",  width=4)
        table.add_column("Crop",     style="bold green",  justify="left")
        table.add_column("KSH/kg",   style="blue",        justify="right",  width=8)
        table.add_column("Qty (kg)", style="white",       justify="right",  width=8)
        table.add_column("Location", style="yellow",      justify="left")
        table.add_column("Proximity",style="dim",         justify="left")
        table.add_column("Farmer",   style="magenta",     justify="left")
        table.add_column("Score Breakdown", style="dim",  justify="left")

        for rank, m in enumerate(matches, 1):
            score = m['match_score']

            if score >= 75:
                score_cell = f"[bold green]{score}%[/bold green]"
                rank_cell  = f"[bold green]#{rank}[/bold green]"
            elif score >= 50:
                score_cell = f"[bold yellow]{score}%[/bold yellow]"
                rank_cell  = f"[bold yellow]#{rank}[/bold yellow]"
            else:
                score_cell = f"[red]{score}%[/red]"
                rank_cell  = f"[red]#{rank}[/red]"

            bd = m['breakdown']
            breakdown_str = (
                f"Loc {bd['location']}/40 · "
                f"Price {bd['price']}/35 · "
                f"Qty {bd['quantity']}/25"
            )

            table.add_row(
                rank_cell,
                score_cell,
                str(m['listing_id']),
                m['crop_name'],
                f"{m['min_price']:.2f}",
                f"{m['quantity_kg']:.1f}",
                m['location'] or "—",
                m['distance'],
                m['farmer_name'],
                breakdown_str,
            )

        console.print(table)

    def match_interactive(self, buyer_id=None):
        """
        Guided matching flow.  Reads the buyer's saved location as the default
        and asks for preferences before running the algorithm.

        Returns the list of top matches.
        """
        console.print(Panel(
            "[bold green]Smart Listing Matcher[/bold green]\n"
            "[dim]We'll score every available listing against your preferences "
            "and show the best fits.[/dim]",
            border_style="green"
        ))

        # Pre-fill from stored profile
        buyer_location = None
        if buyer_id:
            user = fetch_one("SELECT location FROM users WHERE user_id = ?", (buyer_id,))
            if user and user.get('location'):
                buyer_location = user['location']

        loc_input = Prompt.ask(
            f"[bold]Your location[/bold]",
            default=buyer_location or ""
        ).strip()
        buyer_location = loc_input or buyer_location

        desired_crop = Prompt.ask(
            "[bold]Crop you want[/bold] (leave blank for all)", default=""
        ).strip() or None

        use_price = Prompt.ask(
            "Set a max price per kg? [y/n]", choices=["y", "n"], default="n"
        )
        max_price = None
        if use_price == "y":
            try:
                max_price = FloatPrompt.ask("  Max price (KSH / kg)")
            except (ValueError, KeyboardInterrupt):
                max_price = None

        use_qty = Prompt.ask(
            "Set a desired quantity? [y/n]", choices=["y", "n"], default="n"
        )
        desired_qty = None
        if use_qty == "y":
            try:
                desired_qty = FloatPrompt.ask("  Desired quantity (kg)")
            except (ValueError, KeyboardInterrupt):
                desired_qty = None

        console.print("\n[bold]Analysing listings...[/bold]\n")

        matches = self.find_top_matches(
            buyer_location=buyer_location,
            desired_crop=desired_crop,
            max_price=max_price,
            desired_qty=desired_qty,
        )

        self.display_matches(matches, buyer_location=buyer_location)
        return matches
