"""
OTM Rate Inquiry AI Agent
=========================
A natural language rate inquiry agent for Oracle Transportation Management (OTM).
Type a plain English request and get live freight rates back from OTM.

Features:
    - Natural language input (city names, weight in any unit)
    - Automatic unit conversion (tons, kg → lbs)
    - Live OTM REST API rate lookup
    - Multi-option rate display with carrier, mode, transit time, distance
    - Expandable location shortcut map

Usage:
    pip install -r requirements.txt
    cp .env.example .env        # fill in your OTM credentials
    python otm_riq_agent.py

Example queries:
    "rate from Houston to San Antonio for 1000 lbs"
    "best freight option HOU to SAN 5000 pounds"
    "cheapest rate from Houston to San Antonio 2 tons"

Author : Pinkesh Kumar
GitHub : https://github.com/pinkesh101/supply-chain-tools
"""

import re
import os
import requests
import json
from datetime import datetime
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

# ── Load environment variables ────────────────────────────────────────────────
load_dotenv()

OTM_BASE_URL = os.getenv("OTM_BASE_URL")
OTM_USERNAME = os.getenv("OTM_USERNAME")
OTM_PASSWORD = os.getenv("OTM_PASSWORD")
OTM_DOMAIN   = os.getenv("OTM_DOMAIN", "YOUR_DOMAIN")

if not all([OTM_BASE_URL, OTM_USERNAME, OTM_PASSWORD]):
    raise EnvironmentError(
        "Missing OTM credentials. Copy .env.example to .env and fill in your values."
    )

# ── Location shortcut map ─────────────────────────────────────────────────────
# Maps common city names / codes to OTM Location GIDs.
# Format: "city name or code": "DOMAIN.LOCATION_XID"
# Add your own locations here.
LOCATION_SHORTCUTS = {
    "houston":     f"{OTM_DOMAIN}.HOU-TX-77002-1407JEFFERSONST",
    "hou":         f"{OTM_DOMAIN}.HOU-TX-77002-1407JEFFERSONST",
    "san antonio": f"{OTM_DOMAIN}.SAN-TX-78201-110WARNERAVE",
    "san":         f"{OTM_DOMAIN}.SAN-TX-78201-110WARNERAVE",
}


# ─────────────────────────────────────────────────────────────────────────────
# PARAMETER EXTRACTION  —  pure Python regex, no external API required
# ─────────────────────────────────────────────────────────────────────────────

def extract_riq_params(user_input: str) -> dict:
    """
    Extract source location, destination location, and weight
    from a plain English rate inquiry request.

    Supports weight units: lb/lbs, pound/pounds, ton/tons, kg
    Supports patterns:  "from X to Y",  "X to Y"
    """
    lower = user_input.lower()

    # ── Weight ────────────────────────────────────────────────────────────────
    weight = 1000.0
    m = re.search(r'(\d+(?:\.\d+)?)\s*(lb|lbs|pound|pounds|ton|tons|kg)', lower)
    if m:
        val  = float(m.group(1))
        unit = m.group(2)
        if "ton" in unit:
            val *= 2000.0
        elif "kg" in unit:
            val *= 2.205
        weight = val

    # ── Locations ─────────────────────────────────────────────────────────────
    source, dest = None, None

    # Pattern 1: "from <city> to <city>"
    m = re.search(
        r'from\s+([a-z ]+?)\s+to\s+([a-z ]+?)(?:\s+for|\s+\d|\s*$)', lower
    )
    if m:
        source = m.group(1).strip()
        dest   = m.group(2).strip()

    # Pattern 2: "<city> to <city>" without "from"
    if not source:
        m = re.search(
            r'([a-z ]+?)\s+to\s+([a-z ]+?)(?:\s+for|\s+\d|\s*$)', lower
        )
        if m:
            source = m.group(1).strip()
            dest   = m.group(2).strip()

    # Clean trailing noise words
    noise = r'\s*(for|with|rate|freight|truck|lbs?|pounds?)\s*$'
    if source:
        source = re.sub(noise, '', source).strip()
    if dest:
        dest = re.sub(noise, '', dest).strip()

    return {
        "source":      source,
        "destination": dest,
        "weight_lb":   weight,
        "confidence":  "high" if source and dest else "low"
    }


def resolve_location_gid(hint: str) -> str | None:
    """
    Resolve a city name or code to an OTM Location GID.
    Checks LOCATION_SHORTCUTS first; if not found, searches OTM live.
    """
    hint_lower = hint.lower().strip()

    # 1. Shortcut map
    for key, gid in LOCATION_SHORTCUTS.items():
        if key in hint_lower:
            return gid

    # 2. Already a full GID (contains domain separator)
    if "." in hint and "/" in hint:
        return hint

    # 3. Live OTM search
    url    = f"{OTM_BASE_URL}/logisticsRestApi/resources-int/v2/locations"
    params = {"limit": 5, "city": hint.upper()}
    try:
        r = requests.get(url, auth=HTTPBasicAuth(OTM_USERNAME, OTM_PASSWORD),
                         params=params, timeout=15)
        if r.status_code == 200:
            items = r.json().get("items", [])
            if items:
                return items[0]["locationGid"]
    except Exception as e:
        print(f"  [Location search error: {e}]")

    return None


# ─────────────────────────────────────────────────────────────────────────────
# OTM RATE INQUIRY API CALL
# ─────────────────────────────────────────────────────────────────────────────

def call_riq(source_gid: str, dest_gid: str, weight_lb: float,
             pickup_date: str = None) -> dict:
    """
    POST to OTM /custom-actions/riqRateAndRoute.
    Returns the full API response as a dict.
    """
    if not pickup_date:
        pickup_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S-05:00")

    url = f"{OTM_BASE_URL}/logisticsRestApi/resources-int/v2/custom-actions/riqRateAndRoute"

    payload = {
        "requestType": "LowestCost",
        "perspective": "B",
        "orderReleases": {
            "sourceLocationGid": source_gid,
            "destLocationGid":   dest_gid,
            "earlyPickupDate":   {"value": pickup_date},
            "releaseMethodGid":  "ONE_TO_ONE",
            "lines": {
                "items": [{
                    "orderReleaseLineGid": "line001",
                    "packagedItemGid":     "DEFAULT",
                    "weight": {
                        "value": weight_lb,
                        "unit":  "LB"
                    },
                    "itemPackageCount": 1
                }]
            }
        }
    }

    try:
        r = requests.post(
            url,
            auth=HTTPBasicAuth(OTM_USERNAME, OTM_PASSWORD),
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30
        )
        if r.status_code in (200, 201):
            return r.json()
        return {"error": f"OTM {r.status_code}: {r.text[:300]}"}
    except Exception as e:
        return {"error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# RESPONSE FORMATTER
# ─────────────────────────────────────────────────────────────────────────────

def format_response(riq_result: dict, source: str,
                    dest: str, weight: float) -> str:
    """Format the OTM RIQ API response into clean readable text."""
    responses = riq_result.get("rateAndRouteResponse", [])
    if not responses:
        return "No rates found for this lane."

    w = 54
    lines = [
        f"\n  {'─'*w}",
        f"  Rate Results: {source.title()} → {dest.title()} | {weight:.0f} LB",
        f"  {'─'*w}",
        f"  Options found: {len(responses)}\n",
    ]

    for i, r in enumerate(responses, 1):
        cost     = r.get("totalActualCost", {}).get("value", "N/A")
        currency = r.get("totalActualCost", {}).get("currency", "USD")
        carrier  = r.get("serviceProvider", {}).get("servprovGid", "N/A").split(".")[-1]
        mode     = r.get("transportMode", {}).get("transportModeGid", "N/A")
        transit  = r.get("transitTime", {}).get("amount", "N/A")
        legs     = r.get("toShipments", [{}])
        distance = legs[0].get("distance", {}).get("amount", "N/A") if legs else "N/A"
        start    = r.get("startTime", {}).get("value", "N/A")
        end      = r.get("endTime", {}).get("value", "N/A")
        offering = r.get("primaryRateOffering", {}).get(
                       "rateOfferingGid", "N/A").split(".")[-1]

        lines += [
            f"  Option {i}:",
            f"    Cost          : ${cost} {currency}",
            f"    Carrier       : {carrier}",
            f"    Mode          : {mode}",
            f"    Transit Time  : {transit} hours",
            f"    Distance      : {distance} MI",
            f"    Pickup        : {start}",
            f"    Delivery      : {end}",
            f"    Rate Offering : {offering}",
            "",
        ]

    lines.append(f"  {'─'*w}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# AGENT PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

def run_rate_inquiry(user_input: str) -> str:
    """
    End-to-end agent pipeline:
      Step 1 — Extract source, dest, weight from natural language
      Step 2 — Resolve location GIDs from OTM
      Step 3 — Call OTM riqRateAndRoute API
      Step 4 — Format and return results
    """
    print("\n  [Step 1] Parsing request...")
    params      = extract_riq_params(user_input)
    source_hint = params.get("source")
    dest_hint   = params.get("destination")
    weight      = float(params.get("weight_lb", 1000.0))

    if not source_hint or not dest_hint:
        return (
            "Please include both a source and destination city.\n"
            "Example: 'rate from Houston to San Antonio for 1000 lbs'"
        )

    print(f"  → Source: '{source_hint}' | Dest: '{dest_hint}' | Weight: {weight} LB")

    print("  [Step 2] Resolving OTM location GIDs...")
    source_gid = resolve_location_gid(source_hint)
    dest_gid   = resolve_location_gid(dest_hint)

    if not source_gid:
        return (f"Could not find '{source_hint}' in OTM. "
                f"Add it to LOCATION_SHORTCUTS or check the city name.")
    if not dest_gid:
        return (f"Could not find '{dest_hint}' in OTM. "
                f"Add it to LOCATION_SHORTCUTS or check the city name.")

    print(f"  → Source GID : {source_gid}")
    print(f"  → Dest GID   : {dest_gid}")

    print("  [Step 3] Calling OTM Rate Inquiry API...")
    result = call_riq(source_gid, dest_gid, weight)

    if "error" in result:
        return f"OTM API error: {result['error']}"

    responses = result.get("rateAndRouteResponse", [])
    if not responses:
        return "OTM returned no rate options for this lane."

    print(f"  → {len(responses)} rate option(s) received")

    print("  [Step 4] Formatting results...")
    return format_response(result, source_hint, dest_hint, weight)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  OTM Rate Inquiry AI Agent")
    print("  github.com/pinkesh101/supply-chain-tools")
    print("=" * 60)
    print("\nExample queries:")
    print("  - rate from Houston to San Antonio for 1000 lbs")
    print("  - best rate HOU to SAN 5000 pounds")
    print("  - freight cost Houston to San Antonio 2 tons")
    print("  - cheapest option Houston to San Antonio 500 kg")
    print("\nType 'quit' to exit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "bye", "q"):
            print("Goodbye!")
            break

        result = run_rate_inquiry(user_input)
        print(f"\nAgent: {result}\n")
        print("-" * 60)


if __name__ == "__main__":
    main()
