# otm-tender-agent

A thin, dependency-light Python client for the two **REST-enabled tender business actions** introduced in **Oracle OTM 26B**:

| Action | Endpoint |
| --- | --- |
| Secure Resources | `POST /custom-actions/secureResources/tenders/{shipmentId}` |
| Withdraw Tender | `POST /custom-actions/withdrawTender/tenders/{shipmentId}` |

It's the action-side companion to a rate-inquiry agent: where rate inquiry answers *"what's the cheapest way to move this?"*, these actions *act on the shipment* — securing carrier resources (approve-for-execution **and** tender in one step) and withdrawing a tender when plans change.

## Why this approach

These actions are called **directly** against the Logistics REST `custom-actions` surface using a **staged integration user over HTTP Basic auth**. That means:

OTM 26B exposes these actions for integration and AI-agent workflows. This client calls them directly against the Logistics REST custom-actions surface using a staged integration user over HTTP Basic auth — no Fusion UI in the path, only the relevant ACLs granted to the integration user.
This mirrors the architecture of the companion `otm-riq-agent`, which hits `riqRateAndRoute` the same way — proving the full rate-shop -> tender lifecycle can be driven over REST with nothing more than an integration user.

## What OTM actually does

**Secure Resources** is a shortcut that automatically performs *Approve for Execution* and *Tender Shipment* together. The shipment must be at status type `SECURE RESOURCES`, value `NOT STARTED`. If a service provider is already assigned, OTM tenders to it; otherwise OTM evaluates eligible providers and tenders to the lowest-cost one.

**Withdraw Tender** retracts an outstanding tender so the shipment can be re-planned, re-tendered, or re-secured.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env      # then fill in your instance + integration user
```

```bash
python run_tender.py secure   DOMAIN.0123456
python run_tender.py withdraw DOMAIN.0123456
```

Config is read from environment variables (`.env` supported via python-dotenv):

| Var | Example |
| --- | --- |
| `OTM_BASE_URL` | `https://<instance>.otmgtm.<region>.ocs.oraclecloud.com` |
| `OTM_USERNAME` | `DOMAIN.INTEGRATION` |
| `OTM_PASSWORD` | *(integration user password)* |

## Implementation notes (learned the hard way)

**GID slash must be double-encoded.** OTM shipment GIDs contain a slash (`DOMAIN/XID`). As a REST path parameter, a single `%2F` is decoded too early and yields a **404**. The slash must be **double-encoded** (`%252F`). The client handles this automatically; if you call the endpoint by hand, encode accordingly.

**ACLs are per-action, and granting them is the real work.** Each REST resource/action is gated by its own View/Update/Action ACLs that must be granted to the integration user's role. Observed behavior during validation:

| ACL | Gates |
| --- | --- |
| `REST - Shipment - View` | GET on shipments (read / confirm a GID) |
| `REST - Tender Actions` | the `secureResources` action |
| `REST - Tender - Update` (functional `Tender - Update` may also apply) | the `withdrawTender` action (modifies an existing tender) |

A freshly-granted ACL may not take effect until the **ACL cache refreshes** (toggle the grant off/save/on/save, or recycle the integration user). A `403 Forbidden` after granting almost always means *not yet effective* or *wrong action ACL*, not bad credentials — auth failures return `401`, not `403`.

**Reading the response codes:**
- `2xx` — action succeeded.
- `400` with a business message (e.g. *"Shipment ... has outstanding tender offer ..."*) — **the call worked**; OTM reached business logic and enforced a precondition. This is a healthy response, not a failure of the integration.
- `403` — ACL not effective for this action (see above).
- `404` — almost always GID encoding (see double-encode note).

## Validation status

Validated against a live OTM 26B instance with a staged integration user:

- **Secure Resources — confirmed.** Reaches business logic and enforces its preconditions; the empty `{}` request body is accepted. (On an already-tendered shipment it correctly returns `400 - outstanding tender offer`, confirming the call path end-to-end.)
- **Withdraw Tender — implemented; ACL grant in progress.** Endpoint reachable; pending the `Tender - Update` grant becoming effective on the integration user's role.

The request body for both actions defaults to empty `{}` — confirmed sufficient for Secure Resources. If a future use case requires a body, pass it via the `body=` argument.

## License

MIT — see LICENSE.
