"""
main.py — Agri-Tech Digital Marketplace
=========================================
Team  : Lab 2, Group 5 — Moringa School
Course: Computer Programming

Group Members
-------------
  Member 1 — Otieno, David Abel   : Core Infrastructure & Database (database.py, schema.sql)
  Member 2 — Warui, Aaron Wangai  : User Management & Authentication (auth.py, users.py)
  Member 3 — Mwangi, Wendy        : Product & Listing Management (listings.py, products.py)
  Member 4 — Terer, Brian Kipkirui: Marketplace Engine (search.py, matching.py)
  Member 5 — Haggai Kiptoo        : Transaction & Donation System (transactions.py, donations.py)
  Member 6 — Maina, Njeri         : UI/UX + Reporting & Dashboard (ui.py, dashboard.py, reports.py)

Project Structure
-----------------
  main.py        ← this file — single entry point
  app/           ← all 12 source modules
  data/          ← sample CSV for bulk-import testing
  exports/       ← generated reports (CSV, JSON, TXT)
  market.db      ← SQLite database (auto-created on first run)

Problem Statement
-----------------
Small-scale farmers in rural Kenya face severe financial losses and high crop spoilage
because they cannot access competitive markets. Exploitative middlemen suppress farm-gate
prices while low-income urban consumers face artificial food scarcity.

SDG Alignment
-------------
  SDG 1  — No Poverty             : Fair digital prices keep farming families viable.
  SDG 2  — Zero Hunger            : A 2% micro-donation funds food banks on every sale.
  SDG 8  — Decent Work & Growth   : Direct market access increases farmer income.
  SDG 12 — Responsible Consumption: Matching supply with demand reduces food waste.

How to Run
----------
    python main.py
"""

import sys
import os

# Add app/ to the Python import path so every module inside it can do
# bare imports like `import database` or `from auth import login` without
# needing package prefixes.  This keeps all 12 source files unchanged.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))

from ui import run_application

if __name__ == "__main__":
    run_application()
