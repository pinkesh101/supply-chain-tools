"""
otm_tender_client.py
--------------------
Thin Python client for the two REST-enabled tender business actions
introduced in Oracle OTM 26B:

    Secure Resources : POST /custom-actions/secureResources/tenders/{shipmentId}
    Withdraw Tender  : POST /custom-actions/withdrawTender/tenders/{shipmentId}

Design goals
============
- Same architecture as the otm-riq-agent: hit the Logistics REST custom-actions
  surface DIRECTLY with a staged integration user over HTTP Basic auth. No Fusion
  UI, no IDCS confidential app, no Agent Studio subscription required.
- No fabricated payload schema. The 26B "What's New" publishes the endpoint paths
  but NOT the request body. These actions are addressed by a path parameter
  ({shipmentId}); functionally, Secure Resources needs no extra input (it mirrors
  the UI action, which derives the service provider from the shipment or picks the
  lowest-cost eligible one). The body is therefore sent as an explicit, overridable
  argument that defaults to empty {} -- confirm against your instance metadata
  before relying on it in production. See README "Verify before you trust" section.

Auth & ACLs
===========
- HTTP Basic auth with a staged integration user (e.g. DOMAIN.INTEGRATION).
- Each REST action is gated by View + Edit ACLs that must be granted to the user
  or role first. A 401/403 almost always means a missing ACL, not bad credentials.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Optional

from urllib.parse import quote

import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger("otm_tender")


@dataclass
class OTMConfig:
    """Connection settings. Pull secrets from env / a secrets file, never hardcode."""
    base_url: str            # e.g. https://<instance>.otmgtm.<region>.ocs.oraclecloud.com
    username: str            # staged integration user, e.g. DOMAIN.INTEGRATION
    password: str
    # REST base path for the int-api custom-actions surface. Confirm for your release;
    # this mirrors the resources-int/v2 path used by the riqRateAndRoute action.
    rest_base_path: str = "/logisticsRestApi/resources-int/v2"
    timeout: int = 30
    verify_tls: bool = True


class OTMTenderClient:
    def __init__(self, config: OTMConfig):
        self.cfg = config
        self._auth = HTTPBasicAuth(config.username, config.password)
        self._session = requests.Session()

    # ------------------------------------------------------------------ #
    # internal
    # ------------------------------------------------------------------ #
    def _post_action(
        self,
        action_path: str,
        shipment_id: str,
        body: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """POST a custom-action for a single shipment and return a normalized result."""
        # OTM GIDs contain a slash (DOMAIN/XID). As a REST path parameter it must be
        # URL-encoded, and OTM's routing requires the slash DOUBLE-encoded (%252F):
        # a single %2F is decoded too early in the request path and yields a 404.
        encoded_id = quote(shipment_id, safe="").replace("%2F", "%252F")
        url = f"{self.cfg.base_url}{self.cfg.rest_base_path}/custom-actions/{action_path}/tenders/{encoded_id}"
        payload = body if body is not None else {}

        logger.info("POST %s", url)
        resp = self._session.post(
            url,
            auth=self._auth,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            data=json.dumps(payload),
            timeout=self.cfg.timeout,
            verify=self.cfg.verify_tls,
        )

        result: dict[str, Any] = {
            "shipment_id": shipment_id,
            "action": action_path,
            "status_code": resp.status_code,
            "ok": resp.ok,
        }
        try:
            result["body"] = resp.json()
        except ValueError:
            result["body"] = resp.text

        if not resp.ok:
            # 401/403 -> almost always a missing View/Edit ACL on the integration user.
            logger.error(
                "Action %s failed for %s: HTTP %s -- check ACLs and shipment status.",
                action_path, shipment_id, resp.status_code,
            )
        return result

    # ------------------------------------------------------------------ #
    # public actions
    # ------------------------------------------------------------------ #
    def secure_resources(
        self, shipment_id: str, body: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """
        Secure Resources: shortcut that Approves-for-Execution AND Tenders the shipment.

        Precondition (from OTM functional docs): the shipment should be at status type
        SECURE RESOURCES with value NOT_STARTED. If a service provider is already on the
        shipment, OTM tenders to it; otherwise OTM selects the lowest-cost eligible one.
        """
        return self._post_action("secureResources", shipment_id, body)

    def withdraw_tender(
        self, shipment_id: str, body: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """
        Withdraw Tender: retracts an outstanding tender offer for the shipment, returning
        it to a state where it can be re-planned, re-tendered, or re-secured.
        """
        return self._post_action("withdrawTender", shipment_id, body)
