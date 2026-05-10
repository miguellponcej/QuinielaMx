"""Optional IP allowlist support."""

from __future__ import annotations


def is_ip_allowed(ip: str | None, enabled: bool, allowed_ips: tuple[str, ...]) -> bool:
    """Return whether an IP is allowed."""

    if not enabled:
        return True
    if not ip:
        return False
    return ip in set(allowed_ips)

