"""Security audit logging."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


SECURITY_LOG_PATH = Path("data/security_logs/security_access.log")


def security_log(
    email: str,
    action: str,
    result: str,
    ip: str = "unknown",
    user_agent: str = "unknown",
    details: str = "",
    log_path: str | Path = SECURITY_LOG_PATH,
) -> Path:
    """Append a JSON-line security event."""

    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "email": email or "unknown",
        "ip": ip or "unknown",
        "user_agent": user_agent or "unknown",
        "action": action,
        "result": result,
        "details": details,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True) + "\n")
    return path

