"""Derive a distinct demo ingest credential for each device."""

import hmac


def device_key(secret: str, device_id: str) -> str:
    return hmac.digest(secret.encode(), device_id.encode(), "sha256").hex()
