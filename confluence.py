"""Fetch the OneTrust 3rd Party Vendors page from Confluence Cloud.

Uses Basic auth (email + API token). Returns the rendered HTML body, which
preserves the vendor table so Gemini can read it directly.
"""
import base64
import json
import logging
import urllib.request

import config

log = logging.getLogger(__name__)


def _auth_header():
    raw = f"{config.CONFLUENCE_EMAIL}:{config.CONFLUENCE_API_TOKEN}".encode()
    return "Basic " + base64.b64encode(raw).decode()


def is_configured():
    return all(
        [
            config.CONFLUENCE_BASE_URL,
            config.CONFLUENCE_EMAIL,
            config.CONFLUENCE_API_TOKEN,
            config.CONFLUENCE_PAGE_ID,
        ]
    )


def fetch_onetrust_vendors():
    """Return the page's rendered HTML, or None if unconfigured / on error."""
    if not is_configured():
        log.warning("Confluence not configured; skipping OneTrust vendor fetch.")
        return None

    url = (
        f"{config.CONFLUENCE_BASE_URL}/rest/api/content/"
        f"{config.CONFLUENCE_PAGE_ID}?expand=body.view"
    )
    req = urllib.request.Request(
        url,
        headers={"Authorization": _auth_header(), "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
        return data.get("body", {}).get("view", {}).get("value") or None
    except Exception:  # noqa: BLE001 - degrade gracefully in POC
        log.exception("Failed to fetch Confluence OneTrust vendors page")
        return None