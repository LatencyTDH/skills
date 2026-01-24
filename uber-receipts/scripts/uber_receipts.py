#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "requests>=2.28.0",
# ]
# ///
"""
Uber Receipts Fetcher

Fetches ride history from Uber's web GraphQL API.

Setup:
    Run the script - it will prompt for phone number + SMS code on first use.
    Credentials are cached in ~/.uber_session.json and auto-refresh when expired.

Usage:
    uv run uber_receipts.py
    uv run uber_receipts.py --start-date 2025-01-01 --end-date 2025-12-31
    uv run uber_receipts.py --limit 50 --output trips.json
    uv run uber_receipts.py --receipts          # Include full receipt details
    uv run uber_receipts.py --save-receipts     # Download receipt PDFs
    uv run uber_receipts.py --login             # Force re-authentication
"""

import argparse
import base64
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

# Configuration
SESSION_FILE = Path.home() / ".uber_session.json"
GRAPHQL_URL = "https://m.uber.com/go/graphql"
AUTH_URL = "https://auth.uber.com"

# GraphQL Queries
ACTIVITIES_QUERY = """
query Activities($limit: Int = 10, $nextPageToken: String, $orderTypes: [RVWebCommonActivityOrderType!] = [RIDES, TRAVEL], $profileType: RVWebCommonActivityProfileType = PERSONAL, $startTimeMs: Float, $endTimeMs: Float) {
  activities {
    cityID
    past(
      limit: $limit
      nextPageToken: $nextPageToken
      orderTypes: $orderTypes
      profileType: $profileType
      startTimeMs: $startTimeMs
      endTimeMs: $endTimeMs
    ) {
      activities {
        ...RVWebCommonActivityFragment
        __typename
      }
      nextPageToken
      __typename
    }
    __typename
  }
}

fragment RVWebCommonActivityFragment on RVWebCommonActivity {
  buttons {
    isDefault
    startEnhancerIcon
    text
    url
    __typename
  }
  cardURL
  description
  imageURL {
    light
    dark
    __typename
  }
  subtitle
  title
  uuid
  __typename
}
"""

GET_TRIP_QUERY = """
query GetTrip($tripUUID: String!) {
  getTrip(tripUUID: $tripUUID) {
    trip {
      beginTripTime
      cityID
      countryID
      disableCanceling
      disableRating
      disableResendReceipt
      driver
      dropoffTime
      fare
      guest
      isRidepoolTrip
      isScheduledRide
      isSurgeTrip
      isUberReserve
      jobUUID
      marketplace
      paymentProfileUUID
      showRating
      status
      uuid
      vehicleDisplayName
      vehicleViewID
      waypoints
      __typename
    }
    mapURL
    polandTaxiLicense
    rating
    reviewer
    receipt {
      carYear
      distance
      distanceLabel
      duration
      vehicleType
      __typename
    }
    concierge {
      sourceType
      __typename
    }
    organization {
      name
      __typename
    }
    __typename
  }
}
"""


class UberAuth:
    """Handle Uber authentication via phone + OTP."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
    
    @staticmethod
    def load_session() -> Optional[dict]:
        """Load cached session from disk."""
        if not SESSION_FILE.exists():
            return None
        
        try:
            data = json.loads(SESSION_FILE.read_text())
            # Check if JWT is expired
            if "jwt_exp" in data and data["jwt_exp"] < time.time():
                return None  # Expired
            return data
        except (json.JSONDecodeError, KeyError):
            return None
    
    @staticmethod
    def save_session(cookies: dict, jwt_exp: Optional[int] = None):
        """Save session cookies to disk."""
        data = {
            "cookies": cookies,
            "jwt_exp": jwt_exp,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        SESSION_FILE.write_text(json.dumps(data, indent=2))
        SESSION_FILE.chmod(0o600)  # Restrict permissions
    
    @staticmethod
    def clear_session():
        """Delete cached session."""
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()
    
    def _extract_jwt_exp(self, jwt_session: str) -> Optional[int]:
        """Extract expiration timestamp from JWT."""
        try:
            # JWT is base64-encoded JSON in 3 parts separated by dots
            parts = jwt_session.split(".")
            if len(parts) != 3:
                return None
            # Decode payload (part 2), add padding if needed
            payload = parts[1]
            payload += "=" * (4 - len(payload) % 4)
            decoded = base64.urlsafe_b64decode(payload)
            data = json.loads(decoded)
            return data.get("exp")
        except Exception:
            return None
    
    def login(self) -> dict:
        """Interactive login flow. Returns cookies dict."""
        print("Uber Login Required", file=sys.stderr)
        print("-" * 40, file=sys.stderr)
        
        # Get phone number
        phone = input("Phone number (with country code, e.g., +1234567890): ").strip()
        if not phone.startswith("+"):
            phone = "+" + phone
        
        # Step 1: Initialize auth session
        init_resp = self.session.get(f"{AUTH_URL}/login/")
        if init_resp.status_code != 200:
            raise Exception(f"Failed to initialize auth: {init_resp.status_code}")
        
        # Extract CSRF token from cookies or page
        csrf_token = self.session.cookies.get("csid") or "x"
        
        # Step 2: Send phone number to get OTP
        send_otp_url = f"{AUTH_URL}/login/next"
        send_otp_payload = {
            "countryCode": phone[:3] if len(phone) > 10 else "+1",
            "phoneNumber": phone,
            "answerData": {"phoneNumber": phone},
        }
        
        headers = {
            "x-csrf-token": csrf_token,
            "Origin": AUTH_URL,
            "Referer": f"{AUTH_URL}/login/",
        }
        
        otp_resp = self.session.post(send_otp_url, json=send_otp_payload, headers=headers)
        
        if otp_resp.status_code not in (200, 201, 202):
            # Try alternative endpoint
            alt_url = f"{AUTH_URL}/login/v5/otp/send"
            alt_payload = {"phoneNumber": phone}
            otp_resp = self.session.post(alt_url, json=alt_payload, headers=headers)
            
        if otp_resp.status_code not in (200, 201, 202):
            raise Exception(f"Failed to send OTP: {otp_resp.status_code} - {otp_resp.text[:200]}")
        
        print(f"SMS code sent to {phone}", file=sys.stderr)
        
        # Step 3: Get OTP from user
        otp_code = input("Enter SMS code: ").strip()
        
        # Step 4: Verify OTP
        verify_url = f"{AUTH_URL}/login/next"
        verify_payload = {
            "answerData": {"otpValue": otp_code},
        }
        
        verify_resp = self.session.post(verify_url, json=verify_payload, headers=headers)
        
        if verify_resp.status_code not in (200, 201, 302):
            # Try alternative endpoint
            alt_verify_url = f"{AUTH_URL}/login/v5/otp/verify"
            alt_verify_payload = {"phoneNumber": phone, "otpValue": otp_code}
            verify_resp = self.session.post(alt_verify_url, json=alt_verify_payload, headers=headers)
        
        if verify_resp.status_code not in (200, 201, 302):
            raise Exception(f"OTP verification failed: {verify_resp.status_code}")
        
        # Step 5: Visit both domains to get subdomain-specific cookies
        # riders.uber.com first
        self.session.get("https://riders.uber.com/trips")
        riders_csid = self.session.cookies.get("csid")
        
        # Then m.uber.com for GraphQL
        self.session.get("https://m.uber.com/go/home")
        m_csid = self.session.cookies.get("csid")
        
        # Extract cookies
        cookies = {}
        for cookie in self.session.cookies:
            if "uber.com" in (cookie.domain or ""):
                cookies[cookie.name] = cookie.value
        
        # Store both csid values - m.uber.com as 'csid', riders.uber.com as 'riders_csid'
        if m_csid:
            cookies["csid"] = m_csid
        if riders_csid and riders_csid != m_csid:
            cookies["riders_csid"] = riders_csid
        
        if "sid" not in cookies:
            raise Exception("Login failed - no session cookie received")
        
        # Get JWT expiration
        jwt_exp = None
        if "jwt-session" in cookies:
            jwt_exp = self._extract_jwt_exp(cookies["jwt-session"])
        
        # Save session
        self.save_session(cookies, jwt_exp)
        print("Login successful! Session cached.", file=sys.stderr)
        
        return cookies


class UberClient:
    """Uber GraphQL API client."""

    def __init__(self, cookies: dict, verbose: bool = False):
        self.session = requests.Session()
        self.verbose = verbose
        self._cookies = cookies
        
        # Set up headers
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Content-Type": "application/json",
            "Origin": "https://m.uber.com",
            "Referer": "https://m.uber.com/go/home",
            "x-csrf-token": "x",
            "x-uber-rv-session-type": "desktop_session",
        })
        
        # Load cookies
        for name, value in cookies.items():
            self.session.cookies.set(name, value, domain=".uber.com")
    
    def _graphql(self, operation_name: str, query: str, variables: dict) -> dict:
        """Execute a GraphQL query."""
        payload = {
            "operationName": operation_name,
            "query": query,
            "variables": variables,
        }
        
        if self.verbose:
            print(f"GraphQL: {operation_name}", file=sys.stderr)
        
        response = self.session.post(GRAPHQL_URL, json=payload)
        response.raise_for_status()
        
        data = response.json()
        if "errors" in data:
            raise Exception(f"GraphQL error: {data['errors']}")
        
        return data.get("data", {})
    
    def get_activities(
        self,
        limit: int = 50,
        profile_type: str = "PERSONAL",
        start_time_ms: Optional[float] = None,
        end_time_ms: Optional[float] = None,
        next_page_token: Optional[str] = None,
    ) -> dict:
        """Fetch ride activities list."""
        variables = {
            "limit": limit,
            "orderTypes": ["RIDES", "TRAVEL"],
            "profileType": profile_type,
        }
        
        if start_time_ms:
            variables["startTimeMs"] = start_time_ms
        if end_time_ms:
            variables["endTimeMs"] = end_time_ms
        if next_page_token:
            variables["nextPageToken"] = next_page_token
        
        return self._graphql("Activities", ACTIVITIES_QUERY, variables)
    
    def get_trip(self, trip_uuid: str) -> dict:
        """Fetch detailed trip information including receipt."""
        variables = {"tripUUID": trip_uuid}
        return self._graphql("GetTrip", GET_TRIP_QUERY, variables)
    
    def _get_riders_session(self) -> requests.Session:
        """Get a session configured for riders.uber.com with the correct csid."""
        if hasattr(self, '_riders_session'):
            return self._riders_session
        
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        
        # Load cookies - use riders_csid if available, otherwise fall back to csid
        for name, value in self._cookies.items():
            if name == "csid":
                continue  # Skip - we'll set the riders-specific one
            session.cookies.set(name, value, domain=".uber.com")
        
        # Set the riders-specific csid
        riders_csid = self._cookies.get("riders_csid") or self._cookies.get("csid")
        if riders_csid:
            session.cookies.set("csid", riders_csid, domain=".uber.com")
        
        self._riders_session = session
        return session
    
    def download_receipt_pdf(self, trip_uuid: str, output_path: Path) -> bool:
        """Download receipt PDF for a trip.
        
        Args:
            trip_uuid: The trip UUID
            output_path: Path to save the PDF file
            
        Returns:
            True if successful, False otherwise
        """
        # Get session with riders.uber.com csid
        pdf_session = self._get_riders_session()
        
        # Construct the PDF download URL
        timestamp = int(time.time() * 1000)
        url = f"https://riders.uber.com/trips/{trip_uuid}/receipt?contentType=PDF&timestamp={timestamp}"
        
        if self.verbose:
            print(f"Downloading receipt PDF: {trip_uuid}", file=sys.stderr)
        
        try:
            headers = {
                "Referer": f"https://riders.uber.com/trips/{trip_uuid}",
            }
            
            response = pdf_session.get(url, headers=headers, allow_redirects=False)
            
            # Check for redirect to auth (session not valid for riders.uber.com)
            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get("Location", "")
                if "auth.uber.com" in location:
                    if self.verbose:
                        print(f"Session not valid for riders.uber.com - cookies expired or invalid", file=sys.stderr)
                    return False
            
            response.raise_for_status()
            
            # Check if we got a PDF
            content_type = response.headers.get("Content-Type", "")
            if "pdf" not in content_type.lower() and not response.content.startswith(b"%PDF"):
                if self.verbose:
                    print(f"Warning: Response may not be a PDF (Content-Type: {content_type})", file=sys.stderr)
                return False
            
            # Save the PDF
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(response.content)
            
            if self.verbose:
                print(f"Saved: {output_path}", file=sys.stderr)
            
            return True
            
        except Exception as e:
            if self.verbose:
                print(f"Failed to download receipt for {trip_uuid}: {e}", file=sys.stderr)
            return False
    
    def get_all_trips(
        self,
        limit: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        profile_type: str = "PERSONAL",
        include_receipts: bool = False,
    ) -> list:
        """Fetch all trips with optional pagination and filtering."""
        all_trips = []
        next_token = None
        page_size = min(50, limit) if limit else 50
        
        # Convert dates to milliseconds
        start_ms = start_date.timestamp() * 1000 if start_date else None
        end_ms = end_date.timestamp() * 1000 if end_date else None
        
        while True:
            result = self.get_activities(
                limit=page_size,
                profile_type=profile_type,
                start_time_ms=start_ms,
                end_time_ms=end_ms,
                next_page_token=next_token,
            )
            
            activities = result.get("activities", {})
            past = activities.get("past", {})
            trips = past.get("activities", [])
            
            if not trips:
                break
            
            for trip in trips:
                # Optionally fetch full receipt details
                if include_receipts and trip.get("uuid"):
                    try:
                        trip_details = self.get_trip(trip["uuid"])
                        trip["details"] = trip_details.get("getTrip", {})
                        time.sleep(0.2)  # Rate limiting
                    except Exception as e:
                        if self.verbose:
                            print(f"Failed to get details for {trip['uuid']}: {e}", file=sys.stderr)
                
                all_trips.append(trip)
                
                if limit and len(all_trips) >= limit:
                    return all_trips
            
            next_token = past.get("nextPageToken")
            if not next_token:
                break
            
            if self.verbose:
                print(f"Fetched {len(all_trips)} trips...", file=sys.stderr)
        
        return all_trips


def parse_trip(trip: dict) -> dict:
    """Parse raw trip data into standardized format."""
    # Extract price from description (e.g., "$30.95" or "$0.00 • Canceled")
    description = trip.get("description", "")
    amount = 0.0
    currency = "USD"
    status = "completed"
    
    if "Canceled" in description:
        status = "canceled"
    
    # Parse amount
    if description.startswith("$"):
        try:
            amount_str = description.split("$")[1].split()[0].replace(",", "")
            amount = float(amount_str)
        except (IndexError, ValueError):
            pass
    
    # Parse date from subtitle (e.g., "Dec 28 • 2:26 PM")
    subtitle = trip.get("subtitle", "")
    date_str = ""
    if "•" in subtitle:
        date_str = subtitle.split("•")[0].strip()
    
    # Extract locations from details if available
    pickup = ""
    dropoff = ""
    details = trip.get("details", {}).get("trip", {})
    waypoints = details.get("waypoints", [])
    if len(waypoints) >= 2:
        pickup = waypoints[0]
        dropoff = waypoints[-1]
    
    # Get receipt info if available
    receipt = trip.get("details", {}).get("receipt", {})
    distance = receipt.get("distance", "")
    distance_label = receipt.get("distanceLabel", "")
    duration = receipt.get("duration", "")
    vehicle_type = receipt.get("vehicleType", "")
    
    # Use trip details for fare if available
    if details.get("fare"):
        fare_str = details["fare"]
        if fare_str.startswith("$"):
            try:
                amount = float(fare_str[1:].replace(",", ""))
            except ValueError:
                pass
    
    trip_uuid = trip.get("uuid", "")
    receipt_url = f"https://riders.uber.com/trips/{trip_uuid}/receipt?contentType=PDF" if trip_uuid else ""
    
    return {
        "id": trip_uuid,
        "date": subtitle,
        "amount": amount,
        "currency": currency,
        "status": status,
        "title": trip.get("title", ""),
        "pickup": pickup,
        "dropoff": dropoff,
        "distance": f"{distance} {distance_label}".strip() if distance else "",
        "duration": duration,
        "vehicle_type": vehicle_type,
        "driver": details.get("driver", ""),
        "card_url": trip.get("cardURL", ""),
        "receipt_url": receipt_url,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Fetch Uber ride history",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run uber_receipts.py                    # Fetch recent trips
  uv run uber_receipts.py --limit 100        # Fetch up to 100 trips
  uv run uber_receipts.py --receipts         # Include full receipt details
  uv run uber_receipts.py --save-receipts    # Download receipt PDFs
  uv run uber_receipts.py --login            # Force re-authentication

First run will prompt for phone + SMS code. Session is cached in ~/.uber_session.json
        """
    )
    parser.add_argument("--start-date", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument("--limit", type=int, help="Maximum number of trips to fetch")
    parser.add_argument("--output", "-o", type=str, help="Output file path (default: stdout)")
    parser.add_argument("--raw", action="store_true", help="Output raw API response")
    parser.add_argument("--receipts", action="store_true", help="Include full receipt details (slower)")
    parser.add_argument("--save-receipts", action="store_true", help="Download receipt PDFs")
    parser.add_argument("--receipts-dir", type=str, 
                       default=str(Path.home() / "Downloads" / "uber_receipts"),
                       help="Directory to save receipt PDFs (default: ~/Downloads/uber_receipts)")
    parser.add_argument("--profile", type=str, default="PERSONAL", 
                       choices=["PERSONAL", "BUSINESS"],
                       help="Profile type to fetch trips for")
    parser.add_argument("--login", action="store_true", help="Force re-authentication")
    parser.add_argument("--logout", action="store_true", help="Clear cached session")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Handle logout
    if args.logout:
        UberAuth.clear_session()
        print("Session cleared.", file=sys.stderr)
        return
    
    # Get or create session
    cookies = None
    if not args.login:
        session_data = UberAuth.load_session()
        if session_data:
            cookies = session_data.get("cookies")
            if args.verbose:
                print(f"Using cached session from {session_data.get('saved_at', 'unknown')}", file=sys.stderr)
    
    if not cookies:
        # Need to login
        auth = UberAuth(verbose=args.verbose)
        try:
            cookies = auth.login()
        except Exception as e:
            print(f"Login failed: {e}", file=sys.stderr)
            sys.exit(1)
    
    # Parse dates
    start_date = None
    end_date = None
    if args.start_date:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    if args.end_date:
        end_date = datetime.strptime(args.end_date, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59, tzinfo=timezone.utc
        )
    
    # Initialize client
    client = UberClient(cookies=cookies, verbose=args.verbose)
    
    # Fetch trips
    try:
        trips = client.get_all_trips(
            limit=args.limit,
            start_date=start_date,
            end_date=end_date,
            profile_type=args.profile,
            include_receipts=args.receipts,
        )
    except requests.exceptions.HTTPError as e:
        if e.response.status_code in (401, 403):
            print("Session expired. Re-authenticating...", file=sys.stderr)
            UberAuth.clear_session()
            auth = UberAuth(verbose=args.verbose)
            try:
                cookies = auth.login()
                client = UberClient(cookies=cookies, verbose=args.verbose)
                trips = client.get_all_trips(
                    limit=args.limit,
                    start_date=start_date,
                    end_date=end_date,
                    profile_type=args.profile,
                    include_receipts=args.receipts,
                )
            except Exception as login_err:
                print(f"Re-authentication failed: {login_err}", file=sys.stderr)
                sys.exit(1)
        else:
            print(f"HTTP Error: {e}", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"Error fetching trips: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Download receipt PDFs if requested
    downloaded_receipts = []
    if args.save_receipts:
        receipts_dir = Path(args.receipts_dir)
        receipts_dir.mkdir(parents=True, exist_ok=True)
        print(f"Saving receipts to: {receipts_dir}", file=sys.stderr)
        
        for trip in trips:
            trip_uuid = trip.get("uuid")
            if not trip_uuid:
                continue
            
            # Parse date for filename (e.g., "Dec 28 • 2:26 PM" -> "2025-12-28")
            subtitle = trip.get("subtitle", "")
            try:
                # Extract date part before bullet
                date_part = subtitle.split("•")[0].strip() if "•" in subtitle else subtitle
                # Parse and format - assume current year if not specified
                parsed_date = datetime.strptime(date_part, "%b %d")
                # Use current year or previous year if date is in future
                now = datetime.now()
                year = now.year if parsed_date.replace(year=now.year) <= now else now.year - 1
                date_str = parsed_date.replace(year=year).strftime("%Y-%m-%d")
            except ValueError:
                date_str = "unknown-date"
            
            # Get amount for filename
            description = trip.get("description", "")
            amount_str = description.replace("$", "").split()[0] if description.startswith("$") else "0"
            
            # Create filename: uber_2025-12-28_30.95_ed705777.pdf
            short_uuid = trip_uuid[:8]
            filename = f"uber_{date_str}_{amount_str}_{short_uuid}.pdf"
            output_path = receipts_dir / filename
            
            # Skip if already exists
            if output_path.exists():
                if args.verbose:
                    print(f"Skipping (exists): {filename}", file=sys.stderr)
                downloaded_receipts.append({"uuid": trip_uuid, "path": str(output_path), "status": "skipped"})
                continue
            
            success = client.download_receipt_pdf(trip_uuid, output_path)
            downloaded_receipts.append({
                "uuid": trip_uuid, 
                "path": str(output_path) if success else None,
                "status": "downloaded" if success else "failed"
            })
            
            # Rate limiting
            time.sleep(0.3)
        
        # Print download summary
        successful = sum(1 for r in downloaded_receipts if r["status"] == "downloaded")
        skipped = sum(1 for r in downloaded_receipts if r["status"] == "skipped")
        failed = sum(1 for r in downloaded_receipts if r["status"] == "failed")
        print(f"Receipts: {successful} downloaded, {skipped} skipped, {failed} failed", file=sys.stderr)
    
    # Format output
    if args.raw:
        output = trips
    else:
        output = {
            "trips": [parse_trip(t) for t in trips],
            "count": len(trips),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        if args.save_receipts:
            output["receipts"] = downloaded_receipts
    
    # Write output
    json_output = json.dumps(output, indent=2, ensure_ascii=False)
    
    if args.output:
        Path(args.output).write_text(json_output)
        print(f"Wrote {len(trips)} trips to {args.output}", file=sys.stderr)
    else:
        print(json_output)


if __name__ == "__main__":
    main()
