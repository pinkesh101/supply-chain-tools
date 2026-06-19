"""
run_tender.py
-------------
Small CLI to exercise the two OTM 26B tender actions from the command line.

Usage:
    python run_tender.py secure   SHIPMENT_GID
    python run_tender.py withdraw SHIPMENT_GID

Config comes from environment variables (or a .env file loaded by python-dotenv):
    OTM_BASE_URL   e.g. https://<instance>.otmgtm.<region>.ocs.oraclecloud.com
    OTM_USERNAME   staged integration user, e.g. DOMAIN.INTEGRATION
    OTM_PASSWORD   integration user password
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys

from otm_tender_client import OTMConfig, OTMTenderClient

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv optional; env vars can be set directly


def build_client() -> OTMTenderClient:
    missing = [v for v in ("OTM_BASE_URL", "OTM_USERNAME", "OTM_PASSWORD") if not os.getenv(v)]
    if missing:
        sys.exit(f"Missing required env vars: {', '.join(missing)}")
    cfg = OTMConfig(
        base_url=os.environ["OTM_BASE_URL"].rstrip("/"),
        username=os.environ["OTM_USERNAME"],
        password=os.environ["OTM_PASSWORD"],
    )
    return OTMTenderClient(cfg)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="OTM 26B tender actions (Secure Resources / Withdraw Tender)")
    parser.add_argument("action", choices=["secure", "withdraw"])
    parser.add_argument("shipment_id", help="Shipment GID, e.g. DOMAIN.0123456")
    args = parser.parse_args()

    client = build_client()
    if args.action == "secure":
        result = client.secure_resources(args.shipment_id)
    else:
        result = client.withdraw_tender(args.shipment_id)

    print(json.dumps(result, indent=2, default=str))
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
