#!/usr/bin/env python3
"""One-time migration: populate organizers/participants arrays from member_roles.

Usage:
    python scripts/backfill_member_arrays.py

Or via the API:
    curl -X POST -H "Authorization: Bearer $TOKEN" \
        $API_URL/v2/admin/backfill-member-arrays
"""

import sys
from pathlib import Path

# Add src to path so we can import storage modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from room_storage import backfill_member_arrays

if __name__ == "__main__":
    count = backfill_member_arrays()
    print(f"Backfilled {count} rooms with organizers/participants arrays.")
