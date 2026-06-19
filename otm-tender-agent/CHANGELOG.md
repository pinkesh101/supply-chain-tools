# Changelog

## 0.1.0
- Initial release: Python client for OTM 26B Secure Resources and Withdraw Tender REST actions.
- Direct Logistics REST `custom-actions` access via staged integration user (HTTP Basic), no Fusion / IDCS admin required.
- Automatic double-encoding of GID path parameter (`%252F`) to avoid 404s.
- CLI runner (`run_tender.py secure|withdraw <GID>`).
- Secure Resources validated against a live OTM 26B instance.
