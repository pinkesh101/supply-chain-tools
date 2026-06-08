# 🚚 Supply Chain Automation Tools

> AI-powered monitoring and automation tools for enterprise supply chain and logistics systems.

Built by a supply chain architect with 15+ years of hands-on experience in Oracle OTM, Oracle EBS, and WMS integrations.

---

## 🔧 Tools Included

### 1. Ship Confirm Failure Detection Agent (`ship_confirm_agent.py`)

An automated agent that monitors WMS-to-ERP ship confirmation pipelines, detects failures, classifies root causes, and recommends corrective actions — all without manual investigation.

> Failure patterns based on real-world WMS/ERP integration experience across enterprise logistics environments.

#### What it does:
- Connects to your Oracle database and scans the ship confirm staging table
- Automatically classifies failures into known patterns
- Prints a clear report with the root cause and recommended action for each failure

#### Failure Patterns Detected:

| Pattern | Description | Action |
|---|---|---|
| LPN Already Shipped | LPN was confirmed on a prior delivery | Remove LPN from current load |
| Quantity Tolerance | Load qty exceeds ERP tolerance | Check for duplicate LPN allocations |
| Delivery Not Found | No matching delivery in ERP | Verify trip and prior deliveries |
| Order Line Closed | SO line closed before ship confirm | Check for replacement load |
| Freight Terms Mismatch | Conflicting freight terms on order lines | Separate into matching groups |
| Booked Flow Status | Order not yet eligible for ship confirm | Wait for PICKED status |

#### Sample Output:
```
============================================================
  SHIP CONFIRM FAILURE DETECTION AGENT
  Run Time : 2026-06-08 09:00:00
  Looking back 24 hours
============================================================

[1/3] Connecting to database...
      Connected successfully.

[2/3] Fetching failures from staging table...
      Found 2 failure(s).

[3/3] Classifying failures...

  Failure #1
  ──────────────────────────────────────────────────
  Trip ID      : TRIP-10045
  Sales Order  : SO-88821
  Status       : E
  Error        : LPN onhand is not available
  Pattern      : LPN_ALREADY_SHIPPED
  Description  : LPN was already shipped on a prior delivery
  Action       : Remove LPN from current load
  Detected At  : 2026-06-08 07:45:00
============================================================
  Agent run complete.
============================================================
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Oracle Database access
- Oracle Instant Client installed

### Installation

```bash
# Clone the repository
git clone https://github.com/pinkesh101/supply-chain-tools.git
cd supply-chain-tools

# Install dependencies
pip install cx_Oracle python-dotenv
```

### Configuration

Create a `.env` file in the project root (never commit this file!):

```
DB_HOST=your_database_host
DB_PORT=1521
DB_SERVICE=your_service_name
DB_USER=your_username
DB_PASSWORD=your_password
```

### Run the Agent

```bash
python ship_confirm_agent.py
```

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│   WMS System    │────▶│  Ship Confirm Agent  │────▶│  Failure Report │
│  (Warehouse)    │     │  (This Tool)         │     │  + Root Cause   │
└─────────────────┘     └──────────────────────┘     └─────────────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │   Oracle ERP/EBS     │
                        │  Staging Tables      │
                        └──────────────────────┘
```

---

## 🔒 Security

- All credentials stored in `.env` file — never hardcoded
- `.env` is excluded from Git via `.gitignore`
- Follows enterprise security best practices

---

## 📋 Roadmap

- [ ] Freight Invoice Auditor — AI-powered freight bill validation
- [ ] EDI Pipeline Monitor — Automated EDI failure detection
- [ ] Order Hold Alert — Cross-reference active loads vs ERP order holds
- [ ] Web Dashboard — Visual failure monitoring interface

---

## 👤 Author

**Pinkesh Kumar**
- 15+ years Oracle OTM / EBS / Supply Chain Architecture
- AI + Supply Chain Automation
- GitHub: [@pinkesh101](https://github.com/pinkesh101)
- Email: er.pinkesh@gmail.com

---

## 📄 License

MIT License — free to use, modify, and distribute.
