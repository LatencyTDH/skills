---
name: uber-receipts
description: Fetch Uber ride history and trip data via web session cookies. Use when user needs to retrieve Uber trips, export ride history, get trip details (dates, amounts, pickup/dropoff locations, distance), or import Uber data into expense management systems.
---

# Uber Receipts

Fetch Uber ride history using Uber's web GraphQL API.

## Setup

Script location: `scripts/uber_receipts.py` (relative to this skill)

Run from the scripts directory:
```bash
cd <skill-dir>/scripts && uv run uber_receipts.py [OPTIONS]
```

### Authentication

On first run, the script prompts for phone number + SMS code:
```
Uber Login Required
----------------------------------------
Phone number (with country code, e.g., +1234567890): +1...
SMS code sent to +1...
Enter SMS code: 123456
Login successful! Session cached.
```

Session is cached in `~/.uber_session.json` and auto-refreshes when expired.

To force re-authentication:
```bash
uv run uber_receipts.py --login
```

To clear cached session:
```bash
uv run uber_receipts.py --logout
```

---

## Commands

### Fetch Recent Trips
```bash
uv run uber_receipts.py
```
Returns last 50 trips by default.

### Filter by Date Range
```bash
uv run uber_receipts.py --start-date 2025-01-01 --end-date 2025-01-31
```

### Limit Results
```bash
uv run uber_receipts.py --limit 10
```

### Include Receipt Details
```bash
uv run uber_receipts.py --receipts
```
Fetches full trip details including fare breakdown (slower).

### Download Receipt PDFs
```bash
uv run uber_receipts.py --save-receipts
uv run uber_receipts.py --save-receipts --receipts-dir ~/expenses/uber
```
Downloads receipt PDFs to `~/Downloads/uber_receipts` by default.

### Export to File
```bash
uv run uber_receipts.py --output trips.json
```

### Raw API Response
```bash
uv run uber_receipts.py --raw
```
Dumps full API response for debugging.

### Combine Options
```bash
uv run uber_receipts.py --start-date 2025-01-01 --limit 100 --receipts --output january_trips.json -v
```

---

## Output Format

Generic JSON compatible with any expense system:

```json
{
  "trips": [
    {
      "id": "trip_uuid",
      "date": "Dec 28 • 2:26 PM",
      "amount": 30.95,
      "currency": "USD",
      "status": "completed",
      "title": "Driver Name or Destination",
      "pickup": "123 Main St",
      "dropoff": "456 Oak Ave",
      "distance": "5.2 mi",
      "duration": "18 min",
      "vehicle_type": "UberX",
      "driver": "Driver Name",
      "card_url": "https://riders.uber.com/trips/..."
    }
  ],
  "count": 1,
  "fetched_at": "2026-01-24T12:00:00Z",
  "receipts": [
    {
      "uuid": "trip_uuid",
      "path": "~/Downloads/uber_receipts/uber_2025-12-28_30.95_ed705777.pdf",
      "status": "downloaded"
    }
  ]
}
```

**Notes:**
- Full pickup/dropoff addresses require `--receipts` flag
- `receipts` array only present with `--save-receipts`

---

## Session Storage

Session cached at `~/.uber_session.json`:
```json
{
  "cookies": {
    "sid": "...",
    "csid": "...",
    "riders_csid": "...",
    "jwt-session": "..."
  },
  "jwt_exp": 1769366430,
  "saved_at": "2026-01-24T19:16:00+00:00"
}
```

JWT expires ~24 hours after login. Script auto-detects expiry and prompts for re-auth.

---

## Limitations

- Session expires ~24 hours after login
- Max ~50 trips per request page (pagination handled automatically)
- Date filtering uses trip request time
