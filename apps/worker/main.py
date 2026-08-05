"""Minimal JobOS worker entry point for WP-001."""

import json
from datetime import UTC, datetime


def main() -> None:
    """Emit a bootstrap event and exit.

    Task polling is intentionally deferred to WP-004.
    """
    event = {
        "timestamp": datetime.now(UTC).isoformat(),
        "event": "worker.bootstrap",
        "status": "ok",
        "work_package": "WP-001",
    }
    print(json.dumps(event, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
