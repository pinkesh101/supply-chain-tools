"""
Ship Confirm Failure Detection Agent
=====================================
Author: Pinkesh Kumar
Description:
    A generic automated agent that monitors shipping confirmation failures
    in WMS/ERP integration pipelines. Detects, classifies, and reports
    failure patterns to help logistics teams resolve issues proactively.

Use Case:
    Enterprise supply chain systems where a Warehouse Management System (WMS)
    integrates with an ERP (e.g., Oracle EBS) for ship confirmation.
    This agent monitors staging tables for failures and classifies root causes.

Failure Patterns Detected:
    1. LPN Already Shipped     - License plate already confirmed on prior delivery
    2. Quantity Tolerance       - Load quantity exceeds ERP tolerance threshold
    3. Delivery Not Found       - No matching delivery in ERP for the shipment
    4. Order Line Closed        - Sales order line closed/cancelled before ship confirm
    5. Freight Terms Mismatch   - Conflicting freight terms across order lines
    6. Booked Flow Status       - Order not yet eligible for ship confirmation

Requirements:
    - Python 3.8+
    - cx_Oracle (for Oracle DB connection)
    - python-dotenv (for secure credential management)
    - Install: pip install cx_Oracle python-dotenv

Setup:
    Create a .env file in the same folder with:
        DB_HOST=your_database_host
        DB_PORT=1521
        DB_SERVICE=your_service_name
        DB_USER=your_username
        DB_PASSWORD=your_password
"""

import os
import cx_Oracle
from datetime import datetime
from dotenv import load_dotenv

# ─── Load credentials from .env file (never hardcode credentials) ────────────
load_dotenv()

DB_HOST     = os.getenv("DB_HOST")
DB_PORT     = os.getenv("DB_PORT", "1521")
DB_SERVICE  = os.getenv("DB_SERVICE")
DB_USER     = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# ─── Failure Classification Rules ────────────────────────────────────────────
FAILURE_PATTERNS = {
    "LPN_ALREADY_SHIPPED": {
        "keywords": ["lpn onhand is not available", "lpn context"],
        "description": "LPN was already shipped on a prior delivery and is no longer in inventory.",
        "action": "Remove LPN from current load. Verify prior shipment completed successfully."
    },
    "QUANTITY_TOLERANCE": {
        "keywords": ["max allowable qty", "tolerance"],
        "description": "Load quantity exceeds ERP tolerance threshold for the sales order line.",
        "action": "Check load qty vs ordered qty. Look for duplicate LPN allocations."
    },
    "DELIVERY_NOT_FOUND": {
        "keywords": ["delivery already available", "no delivery found"],
        "description": "LPNs already ship-confirmed on a different trip.",
        "action": "Verify trip exists. Check if delivery was processed under a different load."
    },
    "ORDER_LINE_CLOSED": {
        "keywords": ["line closed", "line cancelled", "order closed"],
        "description": "Sales order line was closed or cancelled before ship confirmation.",
        "action": "Check for a replacement load created for remaining open lines."
    },
    "FREIGHT_TERMS_MISMATCH": {
        "keywords": ["freight terms", "grouping"],
        "description": "Conflicting freight terms across order lines violate delivery grouping rules.",
        "action": "Compare freight terms across all lines. Separate into matching groups."
    },
    "BOOKED_FLOW_STATUS": {
        "keywords": ["booked", "flow status"],
        "description": "Sales order line is in BOOKED status — delivery record does not exist yet.",
        "action": "Wait for order to progress to PICKED status before ship confirmation."
    },
    "UNKNOWN": {
        "keywords": [],
        "description": "Failure pattern not recognized.",
        "action": "Manual investigation required. Check staging table error message."
    }
}


def get_db_connection():
    """Establish Oracle database connection using credentials from .env"""
    dsn = cx_Oracle.makedsn(DB_HOST, DB_PORT, service_name=DB_SERVICE)
    connection = cx_Oracle.connect(user=DB_USER, password=DB_PASSWORD, dsn=dsn)
    return connection


def classify_failure(error_message: str) -> dict:
    """
    Classify a ship confirm failure based on the error message.
    Returns the matching failure pattern with description and recommended action.
    """
    if not error_message:
        return FAILURE_PATTERNS["UNKNOWN"]

    error_lower = error_message.lower()

    for pattern_name, pattern_info in FAILURE_PATTERNS.items():
        if pattern_name == "UNKNOWN":
            continue
        for keyword in pattern_info["keywords"]:
            if keyword.lower() in error_lower:
                return {
                    "pattern": pattern_name,
                    **pattern_info
                }

    return {"pattern": "UNKNOWN", **FAILURE_PATTERNS["UNKNOWN"]}


def fetch_failures(connection, hours_back: int = 24) -> list:
    """
    Fetch ship confirm failures from the staging table.
    Looks back a specified number of hours (default: 24).
    """
    query = """
        SELECT
            s.TRIP_ID,
            s.SALES_ORDER,
            s.STATUS_CODE,
            s.ERROR_MESSAGE,
            s.CREATION_DATE,
            s.LAST_UPDATE_DATE
        FROM
            WMS_SHIP_CONFIRM_STAGING s
        WHERE
            s.STATUS_CODE = 'E'
            AND s.CREATION_DATE >= SYSDATE - (:hours_back / 24)
        ORDER BY
            s.CREATION_DATE DESC
    """
    cursor = connection.cursor()
    cursor.execute(query, hours_back=hours_back)

    columns = [col[0] for col in cursor.description]
    failures = [dict(zip(columns, row)) for row in cursor.fetchall()]
    cursor.close()

    return failures


def run_agent(hours_back: int = 24):
    """
    Main agent function.
    Connects to the database, fetches failures, classifies them,
    and prints a summary report.
    """
    print("=" * 60)
    print(f"  SHIP CONFIRM FAILURE DETECTION AGENT")
    print(f"  Run Time : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Looking back {hours_back} hours")
    print("=" * 60)

    try:
        print("\n[1/3] Connecting to database...")
        connection = get_db_connection()
        print("      Connected successfully.")

        print("\n[2/3] Fetching failures from staging table...")
        failures = fetch_failures(connection, hours_back)
        print(f"      Found {len(failures)} failure(s).")

        print("\n[3/3] Classifying failures...\n")

        if not failures:
            print("  ✅ No ship confirm failures found in the last"
                  f" {hours_back} hours.")
        else:
            for i, failure in enumerate(failures, 1):
                classification = classify_failure(failure.get("ERROR_MESSAGE", ""))

                print(f"  Failure #{i}")
                print(f"  {'─' * 50}")
                print(f"  Trip ID      : {failure.get('TRIP_ID', 'N/A')}")
                print(f"  Sales Order  : {failure.get('SALES_ORDER', 'N/A')}")
                print(f"  Status       : {failure.get('STATUS_CODE', 'N/A')}")
                print(f"  Error        : {failure.get('ERROR_MESSAGE', 'N/A')}")
                print(f"  Pattern      : {classification['pattern']}")
                print(f"  Description  : {classification['description']}")
                print(f"  Action       : {classification['action']}")
                print(f"  Detected At  : {failure.get('CREATION_DATE', 'N/A')}")
                print()

        connection.close()

    except cx_Oracle.DatabaseError as e:
        print(f"\n  ❌ Database connection failed: {e}")
        print("     Check your .env credentials and network connectivity.")

    print("=" * 60)
    print("  Agent run complete.")
    print("=" * 60)


if __name__ == "__main__":
    run_agent(hours_back=24)
