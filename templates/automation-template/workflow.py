"""
[Automation Name]

Brief description of what this script does, what it connects, and what it produces.

Usage:
    python workflow.py

Requirements:
    pip install -r requirements.txt

Environment variables:
    Copy .env.example → .env and fill in your values.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
EXAMPLE_API_KEY = os.getenv("EXAMPLE_API_KEY")


def main():
    # TODO: implement automation logic here
    print("Automation running...")


if __name__ == "__main__":
    main()
