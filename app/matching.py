"""
matching.py — Smart Listing Matcher
=====================================
Member  : Terer, Brian Kipkirui
Module  : Marketplace Engine (Matching)
Team    : Lab 2, Group 5 — Moringa School

Purpose
-------
When a buyer says "I want Maize near Nakuru for under KSH 50/kg", this module
scores every available listing against those three preferences and returns the
best fits, ranked highest first.

How scoring works (100 points total)
--------------------------------------
  Location  40 pts — same town = full marks; same county region = partial;
                     different region = minimal.  Location matters most because
                     transport cost in rural Kenya is a major price component.
  Price     35 pts — zero if the listing exceeds the buyer's budget ceiling;
                     otherwise scales down as the price approaches that ceiling.
  Quantity  25 pts — full marks if the listing covers the desired quantity;
                     proportional credit below that; log-scale if no preference.

Technical Concepts Demonstrated
---------------------------------
  FUNCTIONS            — _score_location, _score_price, _score_quantity are
                         pure helper functions: each takes parameters and
                         returns a value with no side effects.
  SELECTION STRUCTURES — nested if/elif in every scoring function decides
                         which scoring band the listing falls into.
  ITERATIVE STRUCTURES — `for` loop in find_top_matches() scores every
                         available listing in sequence.
  DATA TYPES & CASTING — scores are computed as floats then cast to int()
                         so the final score is always a whole number.
  VARIABLE DECLARATIONS— ratio, loc_pts, prc_pts, qty_pts are clearly named
                         intermediate variables that make the maths readable.
  INTERACTIVE I/O      — match_interactive() collects buyer preferences via
                         Prompt.ask() and displays results in a Rich table.
  ERROR HANDLING       — try/except around FloatPrompt.ask() catches invalid
                         number input without crashing the matcher.
  DATA STORAGE         — fetch_all() queries the SQLite listings table;
                         results are enriched with score data and returned.
"""

import math    # math.log1p() — natural log used in the quantity scoring formula

from rich.console import Console
from rich.table   import Table
from rich.panel   import Panel
from rich.prompt  import Prompt, FloatPrompt
from rich         import box

from database import fetch_all, fetch_one

console = Console()


# ===========================================================================
# SECTION 1 — GEOGRAPHIC REGION MAP
# Group Kenyan towns / counties into 7 broad regions so two buyers in
# "Nakuru" and "Eldoret" (both Rift Valley) can still get partial location
# credit even though they are different towns.
# ===========================================================================

# Dictionary mapping each town name (lowercase) to its region key.
# Data type: dict — keys are str (town names), values are str (region keys).
_REGION_MAP = {
    # ── Nairobi Metropolitan Area ──────────────────────────────────────────
    "nairobi":    "nairobi_metro",
    "westlands":  "nairobi_metro",
    "kiambu":     "nairobi_metro",
    "thika":      "nairobi_metro",
    "ruiru":      "nairobi_metro",

    # ── Central Kenya ──────────────────────────────────────────────────────
    "nyeri":      "central",
    "muranga":    "central",
    "murang'a":   "central",
    "kirinyaga":  "central",
    "nyandarua":  "central",
    "karatina":   "central",

    # ── Rift Valley ────────────────────────────────────────────────────────
    "nakuru":     "rift_valley",
    "eldoret":    "rift_valley",
    "uasin gishu":"rift_valley",
    "nandi":      "rift_valley",
    "kericho":    "rift_valley",
    "bomet":      "rift_valley",
    "laikipia":   "rift_valley",
    "baringo":    "rift_valley",
    "kajiado":    "rift_valley",
    "narok":      "rift_valley",
    "trans-nzoia":"rift_valley",
    "trans nzoia":"rift_valley",
    "west pokot": "rift_valley",
    "turkana":    "rift_valley",

    # ── Western Kenya & Nyanza ─────────────────────────────────────────────
    "kisumu":     "western",
    "kakamega":   "western",
    "vihiga":     "western",
    "bungoma":    "western",
    "busia":      "western",
    "siaya":      "western",
    "homa bay":   "western",
    "migori":     "western",
    "kisii":      "western",
    "nyamira":    "western",

    # ── Eastern Kenya ──────────────────────────────────────────────────────
    "meru":       "eastern",
    "embu":       "eastern",
    "tharaka":    "eastern",
    "machakos":   "eastern",
    "makueni":    "eastern",
    "kitui":      "eastern",
    "isiolo":     "eastern",

    # ── Coast ──────────────────────────────────────────────────────────────
    "mombasa":    "coast",
    "kilifi":     "coast",
    "kwale":      "coast",
    "taita":      "coast",
    "lamu":       "coast",
    "tana river": "coast",

    # ── North Eastern ──────────────────────────────────────────────────────
    "garissa":    "north_eastern",
    "wajir":      "north_eastern",
    "mandera":    "north_eastern",
}

# Human-readable labels for each region key — used in the results table.
_REGION_LABELS = {
    "nairobi_metro": "Nairobi Metro",
    "central":       "Central",
    "rift_valley":   "Rift Valley",
    "western":       "Western / Nyanza",
    "eastern":       "Eastern",
    "coast":         "Coast",
    "north_eastern": "North Eastern",
}


# ===========================================================================
# SECTION 2 — PRIVATE GEOGRAPHY HELPERS
# These functions are prefixed with _ (single underscore) to signal that
# they are internal helpers — not part of the public API of this module.
# ===========================================================================

def _get_region(location):
    """
    Look up the regional cluster for a given location string.

    Parameters
    ----------
    location : str | None  — town or county name (any casing)

    Returns
    -------
    str | None — region key from _REGION_MAP, or None if not found

    Selection structure demonstrated
    ----------------------------------
    Three selection branches handle: empty input, exact match, partial match.
    """
    # SELECTION: guard against None or empty string input.
    if not location:
        return None

    # Normalise to lowercase and strip surrounding whitespace so
    # "Nakuru ", "NAKURU", and "nakuru" all match the same key.
    loc = location.lower().strip()

    # SELECTION: try an exact dictionary lookup first (fastest path).
    if loc in _REGION_MAP:
        return _REGION_MAP[loc]

    # ITERATIVE: if no exact match, check whether any known key is a
    # substring of the input (or vice versa) to catch partial names like
    # "Uasin Gishu County" matching "uasin gishu".
    for key, region in _REGION_MAP.items():
        if key in loc or loc in key:
            return region

    return None   # location is not in our map — return None (unknown region)


def _distance_label(buyer_loc, listing_loc):
    """
    Produce a human-readable proximity label for the results table.

    Parameters
    ----------
    buyer_loc   : str | None  — buyer's location
    listing_loc : str | None  — listing's location

    Returns
    -------
    str — one of "Same Town", "Same Region (Rift Valley)", "Different Region",
          or "Unknown" when either location is missing.

    Selection structure demonstrated
    ----------------------------------
    Three nested if/elif levels: unknown → same town → same region → different.
    """
    # SELECTION: handle missing location data gracefully.
    if not buyer_loc or not listing_loc:
        return "Unknown"

    # Normalise both locations for case-insensitive comparison.
    b = buyer_loc.lower().strip()
    l = listing_loc.lower().strip()

    # SELECTION: exact town match (or one name is a substring of the other).
    if b == l or b in l or l in b:
        return "Same Town"

    # Look up the region for each location.
    br = _get_region(buyer_loc)
    lr = _get_region(listing_loc)

    # SELECTION: same region but different town.
    if br and lr and br == lr:
        # Include the human-readable region name in the label.
        return f"Same Region ({_REGION_LABELS.get(br, br)})"

    return "Different Region"


# ===========================================================================
# SECTION 3 — SCORING FUNCTIONS
# Three pure functions, one per scoring dimension.
# Each accepts relevant numeric parameters and returns an integer score.
# The scores are independent — changing one does not affect the others.
# ===========================================================================

def _score_location(buyer_location, listing_location, max_pts=40):
    """
    Calculate the location proximity score for one listing.

    Scoring bands
    -------------
    Same town   → max_pts        (40 pts)  — shortest possible distance
    Same region → max_pts * 0.60 (24 pts)  — moderate distance, known region
    Different   → max_pts * 0.10 ( 4 pts)  — long distance, still shows listing
    Unknown loc → max_pts // 2   (20 pts)  — neutral when data is missing

    Parameters
    ----------
    buyer_location   : str | None
    listing_location : str | None
    max_pts          : int  maximum points available (default 40)

    Returns
    -------
    int — location score in range [0, max_pts]

    Selection structure demonstrated
    ----------------------------------
    Nested if/elif:
      Level 1 — guard for missing data
      Level 2 — same town check
      Level 3 — same region check
      Level 4 — default (different region)

    Type casting demonstrated
    --------------------------
    max_pts * 0.60 produces a float; int() truncates it to a whole number
    so the final score is always an integer (e.g. int(24.0) → 24).
    """
    # SELECTION level 1: missing location data → neutral score.
    if not buyer_location or not listing_location:
        # Integer floor division (//) keeps the result as int, not float.
        return max_pts // 2   # 20 pts when location is unknown

    # Normalise both strings to lowercase for fair comparison.
    b = buyer_location.lower().strip()   # str variable
    l = listing_location.lower().strip() # str variable

    # SELECTION level 2: same town → full location score.
    if b == l or b in l or l in b:
        return max_pts   # 40 pts — best possible location score

    # Look up the geographic region for both locations.
    br = _get_region(buyer_location)   # str | None
    lr = _get_region(listing_location) # str | None

    # SELECTION level 3: same region but different town → partial credit.
    if br and lr and br == lr:
        # TYPE CAST: multiply float 0.60 by int max_pts → float result.
        # Wrap in int() to produce a clean integer score (24, not 24.0).
        return int(max_pts * 0.60)   # 24 pts

    # SELECTION level 4 (implicit else): different region → minimal score.
    return int(max_pts * 0.10)   # 4 pts — listing still appears, just ranked lower


def _score_price(listing_price, max_price, max_pts=35):
    """
    Calculate the price score for one listing relative to the buyer's budget.

    The score decays linearly as the listing price rises toward the buyer's
    ceiling — a listing at exactly the ceiling earns only 35% of max_pts,
    while a very cheap listing earns close to the full 35 pts.

    Formula
    -------
    ratio = listing_price / max_price          (float in [0.0, 1.0])
    score = max_pts * (1.0 - ratio * 0.6)      (float)
    return int(score)                           (int)

    Over-budget listings score exactly 0 and are excluded from top results.

    Parameters
    ----------
    listing_price : float  — KSH per kg for this listing
    max_price     : float | None  — buyer's budget ceiling (KSH/kg)
    max_pts       : int   — maximum price points available (default 35)

    Returns
    -------
    int — price score in range [0, max_pts]

    Selection structure demonstrated
    ----------------------------------
    if no budget set   → neutral score (max_pts // 2)
    elif over budget   → zero (hard exclusion)
    else               → linear decay formula

    Type casting demonstrated
    --------------------------
    listing_price / max_price produces a Python float.
    The final multiplication also produces a float.
    int() truncates the decimal part to give a clean integer score.
    """
    # VARIABLE DECLARATION: ratio will hold a float in [0.0, 1.0].
    ratio = 0.0

    # SELECTION: no budget provided → neutral score so the listing is
    # still ranked but neither favoured nor penalised for price.
    if max_price is None or max_price <= 0:
        return max_pts // 2   # 17 pts — neutral

    # SELECTION: listing is over the buyer's budget → hard zero.
    # This listing will still appear in the scored list but ranked last.
    if listing_price > max_price:
        return 0

    # Calculate the ratio: 0.0 = free (maximum score), 1.0 = at ceiling.
    # Both values are floats — Python's / operator always produces a float.
    ratio = listing_price / max_price   # float in range (0.0, 1.0]

    # Apply the decay formula.
    # At ratio=0.0: score = max_pts * 1.0  = 35 (best price)
    # At ratio=1.0: score = max_pts * 0.4  = 14 (at ceiling)
    # The *0.6 factor ensures a listing at the ceiling still earns some pts.
    # TYPE CAST: int() converts the float result to a whole-number score.
    return int(max_pts * (1.0 - ratio * 0.6))


def _score_quantity(quantity_kg, desired_qty, max_pts=25):
    """
    Calculate the quantity score for one listing.

    If the buyer specified a desired quantity:
      listing covers all of it → full marks
      listing covers part of it → proportional credit

    If no desired quantity (buyer browsing):
      Use a logarithmic scale so very large supplies score well without
      capping out at an arbitrary threshold.

    Parameters
    ----------
    quantity_kg  : float  — kg available in this listing
    desired_qty  : float | None  — kg the buyer wants (None = no preference)
    max_pts      : int   — maximum quantity points available (default 25)

    Returns
    -------
    int — quantity score in range [0, max_pts]

    Selection structure demonstrated
    ----------------------------------
    if desired_qty given   → proportional ratio formula
    else                   → logarithmic scale formula

    Type casting demonstrated
    --------------------------
    Both formulas produce floats; int() truncates to an integer score.

    Variable declarations demonstrated
    ------------------------------------
    `ratio` is a float variable holding a value clamped to [0.0, 1.0].
    """
    # SELECTION: buyer specified a quantity preference.
    if desired_qty and desired_qty > 0:
        # ratio = fraction of the desired quantity that this listing covers.
        # min(..., 1.0) caps the ratio at 1.0 so surplus supply doesn't
        # score more than 100% — a listing with 2× the desired qty should
        # score exactly the same as one with 1× the desired qty.
        ratio = min(quantity_kg / desired_qty, 1.0)  # float in [0.0, 1.0]

        # TYPE CAST: int() converts e.g. 18.75 → 18.
        return int(max_pts * ratio)

    # SELECTION: no quantity preference — use a log scale.
    # math.log1p(x) = ln(1 + x) — avoids log(0) when quantity_kg = 0.
    # We scale so that 1 000 kg = full marks (log1p(1000) ≈ 6.91).
    # Quantities above 1 000 kg are capped at max_pts via min(..., 1.0).
    return int(
        max_pts * min(
            math.log1p(quantity_kg) / math.log1p(1000),
            1.0   # cap at 1.0 so extremely large supplies don't exceed max_pts
        )
    )


# ===========================================================================
# SECTION 4 — MatchingEngine CLASS
# Wraps the scoring functions in a class to provide a clean public API.
# The class owns the top-level orchestration: fetch listings → score each
# → sort → display → collect buyer input.
# ===========================================================================

class MatchingEngine:
    """
    Orchestrates the full buyer-to-listing matching flow.

    Public methods
    --------------
    get_match_score()  — score a single listing dict
    find_top_matches() — score all available listings and return top N
    display_matches()  — render results as a colour-coded Rich table
    match_interactive()— guided interactive flow (used by the buyer menu)
    """

    def get_match_score(self, listing, buyer_location=None,
                        max_price=None, desired_qty=None):
        """
        Score one listing against a buyer's three preferences.

        Parameters
        ----------
        listing        : dict  — one row from the listings table
        buyer_location : str | None
        max_price      : float | None  — KSH/kg budget ceiling
        desired_qty    : float | None  — kg the buyer wants

        Returns
        -------
        tuple : (total_score: int, breakdown: dict)
            total_score  — sum of all three component scores (0–100)
            breakdown    — {'location': int, 'price': int, 'quantity': int}

        Functions demonstrated
        -----------------------
        get_match_score calls three other functions (_score_location,
        _score_price, _score_quantity) and combines their return values.
        Separating each dimension into its own function means we can test,
        adjust, or replace any one scoring rule without touching the others.

        Variable declarations demonstrated
        ------------------------------------
        loc_pts, prc_pts, qty_pts are clearly named intermediate variables
        that make the final return statement easy to read and verify.
        """
        # Call each scoring function and store the result in a named variable.
        # Data type: all three are ints (the scoring functions cast to int).
        loc_pts = _score_location(buyer_location, listing.get('location'))
        prc_pts = _score_price(listing['min_price'], max_price)
        qty_pts = _score_quantity(listing['quantity_kg'], desired_qty)

        # Return a tuple: (total score, score breakdown dict).
        # The breakdown is used in the results table to explain the score.
        return loc_pts + prc_pts + qty_pts, {
            'location': loc_pts,   # out of 40
            'price':    prc_pts,   # out of 35
            'quantity': qty_pts,   # out of 25
        }

    def find_top_matches(self, buyer_location=None, desired_crop=None,
                         max_price=None, desired_qty=None, top_n=5):
        """
        Score every available listing and return the top N results.

        Parameters
        ----------
        buyer_location : str | None  — used for location scoring
        desired_crop   : str | None  — optional crop name filter (LIKE match)
        max_price      : float | None — hard-filter AND price scoring
        desired_qty    : float | None — quantity scoring
        top_n          : int  — number of results to return (default 5)

        Returns
        -------
        list of dicts — each listing dict enriched with:
            'match_score' : int   total score 0–100
            'breakdown'   : dict  {'location', 'price', 'quantity'}
            'distance'    : str   human-readable proximity label

        Iterative structure demonstrated
        ---------------------------------
        The `for lst in listings` loop on line ~274 is the core of the
        algorithm.  It visits every available listing in the database,
        calls get_match_score() on each one, and collects the results.
        Only after ALL listings are scored does it sort and slice the top N.

        Data storage and retrieval demonstrated
        ----------------------------------------
        fetch_all() sends a parameterized SQL SELECT to the SQLite database
        and returns the results as a list of dicts.  The `params` list is
        built dynamically based on which optional filters the buyer provided.
        """
        # BASE QUERY: join listings with users to get the farmer's username.
        # Only listings with status = 'available' are considered.
        query = """
            SELECT l.listing_id, l.crop_name, l.quantity_kg, l.min_price,
                   l.location, l.harvest_date, u.username AS farmer_name
            FROM   listings l
            JOIN   users    u ON l.farmer_id = u.user_id
            WHERE  l.status = 'available'
        """
        # params is a list; we append values in parallel with WHERE clauses.
        # Data type: list of mixed types (str for LIKE, float for price).
        params = []

        # SELECTION: add an optional crop name filter if the buyer specified one.
        if desired_crop:
            # LIKE '%value%' matches partial names, e.g. "Mai" finds "Maize".
            query += " AND l.crop_name LIKE ?"
            params.append(f"%{desired_crop}%")  # str with % wildcards

        # SELECTION: hard-filter by price ceiling before scoring.
        # No point fetching and scoring listings the buyer cannot afford.
        if max_price is not None:
            query += " AND l.min_price <= ?"
            params.append(max_price)   # float

        # DATA RETRIEVAL: execute the query and get back a list of dicts.
        listings = fetch_all(query, tuple(params))

        # SELECTION: guard — return empty list if no listings match the filter.
        if not listings:
            return []

        # scored will collect every listing enriched with its match score.
        # Data type: list of dicts
        scored = []

        # ITERATIVE STRUCTURE — for loop:
        # Visit every listing returned by the database query.
        # For each one, calculate its match score and append the enriched
        # dict to the `scored` list.
        for lst in listings:
            # Call get_match_score() and unpack the returned tuple.
            score, breakdown = self.get_match_score(
                lst,
                buyer_location=buyer_location,
                max_price=max_price,
                desired_qty=desired_qty,
            )

            # Build an enriched dict using ** (dict unpacking) to merge
            # the original listing fields with the new score fields.
            scored.append({
                **lst,                  # all original columns (crop_name, price, etc.)
                'match_score': score,   # int: total score 0–100
                'breakdown':   breakdown,
                'distance':    _distance_label(buyer_location, lst.get('location')),
            })

        # Sort the scored list in descending order by match_score.
        # `reverse=True` puts the highest score first.
        scored.sort(key=lambda x: x['match_score'], reverse=True)

        # Return only the top N results (list slicing).
        return scored[:top_n]

    def display_matches(self, matches, buyer_location=None):
        """
        Render the top match results as a colour-coded Rich table.

        Colour coding conveys match quality at a glance:
          Green  (>= 75%)  — excellent match
          Yellow (>= 50%)  — acceptable match
          Red    (<  50%)  — weak match, still shown for transparency

        Parameters
        ----------
        matches        : list of enriched listing dicts (from find_top_matches)
        buyer_location : str | None  — shown in the subtitle panel

        Selection structure demonstrated
        ----------------------------------
        The if/elif/else inside the `for rank, m in enumerate(matches)` loop
        chooses the Rich colour markup based on the listing's score.
        """
        # SELECTION: nothing to display if no matches were found.
        if not matches:
            console.print("[yellow]No matching listings found.[/yellow]")
            return

        # Show a header panel — include the buyer's location if known.
        subtitle = (
            f"Buyer location: [cyan]{buyer_location}[/cyan]"
            if buyer_location else ""
        )
        console.print(Panel(
            f"[bold green]Top {len(matches)} Smart Match Result(s)[/bold green]"
            + (f"\n{subtitle}" if subtitle else ""),
            border_style="green",
        ))

        # Build the results table with one column per field.
        table = Table(box=box.DOUBLE_EDGE, border_style="green", show_lines=True)
        table.add_column("Rank",            style="bold cyan",  justify="center", width=5)
        table.add_column("Match %",                             justify="center", width=9)
        table.add_column("ID",              style="cyan",       justify="right",  width=4)
        table.add_column("Crop",            style="bold green", justify="left")
        table.add_column("KSH/kg",          style="blue",       justify="right",  width=8)
        table.add_column("Qty (kg)",        style="white",      justify="right",  width=8)
        table.add_column("Location",        style="yellow",     justify="left")
        table.add_column("Proximity",       style="dim",        justify="left")
        table.add_column("Farmer",          style="magenta",    justify="left")
        table.add_column("Score Breakdown", style="dim",        justify="left")

        # ITERATIVE STRUCTURE: enumerate() gives us a rank counter (1, 2, 3…)
        # alongside each match dict.
        for rank, m in enumerate(matches, 1):
            score = m['match_score']   # int: 0–100

            # SELECTION — nested if/elif/else: choose colour by score band.
            if score >= 75:
                # Green: strong match — buyer should strongly consider this listing.
                score_cell = f"[bold green]{score}%[/bold green]"
                rank_cell  = f"[bold green]#{rank}[/bold green]"
            elif score >= 50:
                # Yellow: moderate match — acceptable but not ideal.
                score_cell = f"[bold yellow]{score}%[/bold yellow]"
                rank_cell  = f"[bold yellow]#{rank}[/bold yellow]"
            else:
                # Red: weak match — shown for completeness but ranked last.
                score_cell = f"[red]{score}%[/red]"
                rank_cell  = f"[red]#{rank}[/red]"

            # Build a compact breakdown string showing each dimension's score.
            bd = m['breakdown']   # dict: {'location', 'price', 'quantity'}
            breakdown_str = (
                f"Loc {bd['location']}/40 · "
                f"Price {bd['price']}/35 · "
                f"Qty {bd['quantity']}/25"
            )

            table.add_row(
                rank_cell,
                score_cell,
                str(m['listing_id']),           # int → str for Rich table
                m['crop_name'],
                f"{m['min_price']:.2f}",         # float formatted to 2 d.p.
                f"{m['quantity_kg']:.1f}",       # float formatted to 1 d.p.
                m['location'] or "—",
                m['distance'],
                m['farmer_name'],
                breakdown_str,
            )

        console.print(table)

    def match_interactive(self, buyer_id=None):
        """
        Guided interactive matching flow — called from the buyer menu.

        Collects buyer preferences through a short form, runs find_top_matches(),
        and displays the colour-coded results table.

        Parameters
        ----------
        buyer_id : int | None
            If provided, the buyer's saved location is loaded from the database
            and pre-filled as the default answer in the location prompt.

        Returns
        -------
        list — the top matches list (same as find_top_matches())

        Interactive I/O demonstrated
        ------------------------------
        Four Prompt.ask() calls collect: location, desired crop, max price,
        desired quantity.  Each is optional — the buyer can skip any filter
        by pressing Enter, and the algorithm handles None values gracefully.

        Error handling demonstrated
        ----------------------------
        FloatPrompt.ask() raises ValueError if the user types text instead of
        a number.  The try/except block catches that and treats it as "no
        preference" rather than crashing.
        """
        # Display an introductory panel explaining what this feature does.
        console.print(Panel(
            "[bold green]Smart Listing Matcher[/bold green]\n"
            "[dim]We score every available listing against your preferences "
            "and show the best fits.[/dim]",
            border_style="green",
        ))

        # ── Pre-fill buyer's saved location ───────────────────────────────
        # DATA RETRIEVAL: look up this buyer's location from the users table.
        buyer_location = None   # str | None — default to None if not found

        if buyer_id:
            # fetch_one returns a dict or None — use .get() to safely read
            # the 'location' key without risking a KeyError.
            user = fetch_one(
                "SELECT location FROM users WHERE user_id = ?",
                (buyer_id,)   # parameterized query — prevents SQL injection
            )
            if user and user.get('location'):
                buyer_location = user['location']   # str

        # INTERACTIVE INPUT: ask for the buyer's location.
        # The buyer's stored location is offered as the default value.
        loc_input = Prompt.ask(
            "[bold]Your location[/bold]",
            default=buyer_location or ""   # pre-fill if we found a saved location
        ).strip()
        # Use the typed input if non-empty; fall back to the stored location.
        buyer_location = loc_input or buyer_location

        # INTERACTIVE INPUT: optional crop name filter.
        desired_crop = Prompt.ask(
            "[bold]Crop you want[/bold] (leave blank for all)",
            default=""
        ).strip() or None   # convert empty string to None (= no filter)

        # INTERACTIVE INPUT: optional price ceiling.
        use_price = Prompt.ask(
            "Set a max price per kg? [y/n]",
            choices=["y", "n"],
            default="n"
        )
        max_price = None   # float | None

        # SELECTION: only ask for the price if the buyer said 'y'.
        if use_price == "y":
            # ERROR HANDLING: FloatPrompt.ask raises ValueError on bad input.
            # We catch it and fall back to None (= no price filter).
            try:
                max_price = FloatPrompt.ask("  Max price (KSH / kg)")
            except (ValueError, KeyboardInterrupt):
                max_price = None   # treat invalid input as "no preference"

        # INTERACTIVE INPUT: optional desired quantity.
        use_qty = Prompt.ask(
            "Set a desired quantity? [y/n]",
            choices=["y", "n"],
            default="n"
        )
        desired_qty = None   # float | None

        # SELECTION: only ask for quantity if the buyer said 'y'.
        if use_qty == "y":
            try:
                desired_qty = FloatPrompt.ask("  Desired quantity (kg)")
            except (ValueError, KeyboardInterrupt):
                desired_qty = None

        console.print("\n[bold]Analysing listings...[/bold]\n")

        # Run the matching algorithm with all collected preferences.
        matches = self.find_top_matches(
            buyer_location=buyer_location,
            desired_crop=desired_crop,
            max_price=max_price,
            desired_qty=desired_qty,
        )

        # Display the colour-coded results table.
        self.display_matches(matches, buyer_location=buyer_location)

        # Return the matches list so the caller can use it if needed.
        return matches
