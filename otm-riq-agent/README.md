# OTM Rate Inquiry AI Agent

A natural language freight rate inquiry agent for **Oracle Transportation Management (OTM)**.  
Type a plain English request — get live freight rates back from OTM instantly.

## What It Does

- Accepts natural language rate requests
- Extracts origin, destination, and weight automatically
- Handles unit conversion (tons, kg → lbs)
- Calls the OTM `riqRateAndRoute` REST API live
- Returns cost, carrier, mode, transit time, and distance

## Example

```
You: rate from Houston to San Antonio for 1000 lbs

  [Step 1] Parsing request...
  → Source: 'houston' | Dest: 'san antonio' | Weight: 1000.0 LB
  [Step 2] Resolving OTM location GIDs...
  [Step 3] Calling OTM Rate Inquiry API...
  [Step 4] Formatting results...

Agent:
  ──────────────────────────────────────────────────────
  Rate Results: Houston → San Antonio | 1000 LB
  ──────────────────────────────────────────────────────
  Options found: 1

  Option 1:
    Cost          : $100 USD
    Carrier       : AVRT
    Mode          : LTL
    Transit Time  : 4.18 hours
    Distance      : 229.78 MI
    Pickup        : 2026-06-17T03:00:00-05:00
    Delivery      : 2026-06-17T07:10:40-05:00
    Rate Offering : AVRT-LTL-2016
  ──────────────────────────────────────────────────────
```

## Setup

### 1. Clone and install

```bash
git clone https://github.com/pinkesh101/supply-chain-tools.git
cd supply-chain-tools/otm-riq-agent
pip install -r requirements.txt
```

### 2. Configure credentials

```bash
cp .env.example .env
```

Edit `.env` with your OTM instance details:

```
OTM_BASE_URL=https://your-otm-instance.oraclecloud.com
OTM_USERNAME=YOUR_DOMAIN.INTEGRATION
OTM_PASSWORD=your_password_here
OTM_DOMAIN=YOUR_DOMAIN
```

### 3. Add your locations

Open `otm_riq_agent.py` and update `LOCATION_SHORTCUTS` with your OTM location GIDs:

```python
LOCATION_SHORTCUTS = {
    "houston":     "YOUR_DOMAIN.YOUR_LOCATION_GID",
    "dallas":      "YOUR_DOMAIN.YOUR_LOCATION_GID",
    # add more...
}
```

### 4. Run

```bash
python otm_riq_agent.py
```

## How It Works

```
User Input (natural language)
        ↓
  Regex parser extracts source, destination, weight
        ↓
  LOCATION_SHORTCUTS map → OTM Location GIDs
  (fallback: live OTM location search by city)
        ↓
  POST /logisticsRestApi/resources-int/v2/custom-actions/riqRateAndRoute
        ↓
  Formatted rate results displayed
```

## Requirements

- Python 3.10+
- OTM Cloud instance with REST API enabled
- Staged integration user with RIQ ACLs:
  - `External Integration`
  - `INTEGRATION`
  - `REST - Location - View`
  - `REST - RIQ Actions`

## Tech Stack

- Python + `requests`
- Oracle OTM REST API (resources-int/v2)
- `python-dotenv` for credential management

## Author

**Pinkesh Kumar** — Principal OTM/GTM Architect  
[github.com/pinkesh101](https://github.com/pinkesh101)
