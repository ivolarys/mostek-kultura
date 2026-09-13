"""Decide whether a scheduled site refresh still needs to run."""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import UTC, datetime, timedelta
from datetime import time as datetime_time
from typing import Any
from urllib.request import Request, urlopen

STATUS_URL = "https://ivolarys.github.io/mostkultura/status.json"


def _parse_generated_at(status: Any) -> datetime | None:
    if not isinstance(status, dict):
        return None
    value = status.get("generated_at")
    if not isinstance(value, str) or not value:
        return None
    try:
        generated_at = datetime.fromisoformat(value)
    except ValueError:
        return None
    if generated_at.tzinfo is None or generated_at.utcoffset() is None:
        return None
    return generated_at.astimezone(UTC)


def needs_refresh(status: Any, now: datetime) -> bool:
    """Return whether status is missing a valid build since the latest 04:30 UTC."""
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        return True

    current = now.astimezone(UTC)
    cutoff = datetime.combine(current.date(), datetime_time(4, 30), UTC)
    if current < cutoff:
        cutoff -= timedelta(days=1)

    generated_at = _parse_generated_at(status)
    return generated_at is None or generated_at < cutoff or generated_at > current


def fetch_status(now: datetime) -> Any:
    separator = "&" if "?" in STATUS_URL else "?"
    url = f"{STATUS_URL}{separator}_={int(now.timestamp())}-{time.time_ns()}"
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "User-Agent": "mostkultura-refresh-check/1",
        },
    )
    with urlopen(request, timeout=15) as response:
        return json.load(response)


# Kept as the patch point used by the command-level tests.
_fetch_status = fetch_status


def _write_output(should_build: bool) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as output:
            output.write(f"should_build={'true' if should_build else 'false'}\n")


def main() -> int:
    event_name = os.environ.get("GITHUB_EVENT_NAME", "schedule")
    if event_name != "schedule":
        print(f"{event_name} event always refreshes")
        _write_output(True)
        return 0

    now = datetime.now(UTC)
    try:
        status = _fetch_status(now)
        should_build = needs_refresh(status, now)
        generated_at = _parse_generated_at(status)
        if should_build:
            reason = "published status is stale or invalid"
        else:
            reason = f"already refreshed at {generated_at.isoformat()}"
    # This guard must fail open for every retrieval or decoding failure.
    except Exception as exc:  # noqa: BLE001
        should_build = True
        reason = f"status check failed ({type(exc).__name__}); refreshing"

    print(reason)
    _write_output(should_build)
    return 0


if __name__ == "__main__":
    sys.exit(main())
