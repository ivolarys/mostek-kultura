"""A missed or failed publication must still be eligible for a scheduled retry."""

import importlib.util
from datetime import datetime
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_refresh.py"
spec = importlib.util.spec_from_file_location("check_refresh", SCRIPT)
refresh = importlib.util.module_from_spec(spec)


@pytest.fixture(scope="module", autouse=True)
def load_script():
    spec.loader.exec_module(refresh)


@pytest.mark.parametrize(
    ("published", "expected"),
    [
        ("2026-09-12T22:09:23+02:00", True),
        ("2026-09-13T04:29:59Z", True),
        ("2026-09-13T04:30:00Z", False),
        ("2026-09-13T06:45:00+02:00", False),
        ("2026-09-13T10:00:00Z", True),
        ("2026-09-13T07:00:00", True),
        ("invalid", True),
        (None, True),
        (123, True),
    ],
)
def test_retry_uses_published_freshness(published, expected):
    now = datetime.fromisoformat("2026-09-13T09:30:00+00:00")
    assert refresh.needs_refresh({"generated_at": published}, now) is expected


@pytest.mark.parametrize("status", [None, [], "", {}, {"generated_at": {}}])
def test_malformed_status_does_not_suppress_retry(status):
    assert refresh.needs_refresh(status, datetime.fromisoformat("2026-09-13T09:30:00+00:00"))


@pytest.mark.parametrize(
    ("published", "expected"),
    [("2026-09-12T04:31:00Z", False), ("2026-09-12T04:29:00Z", True)],
)
def test_delayed_trigger_before_next_morning_uses_previous_cutoff(published, expected):
    now = datetime.fromisoformat("2026-09-13T01:00:00+00:00")
    assert refresh.needs_refresh({"generated_at": published}, now) is expected


@pytest.mark.parametrize(
    ("now", "published"),
    [
        ("2026-10-25T08:00:00+01:00", "2026-10-25T05:30:00+01:00"),
        ("2027-03-28T08:00:00+02:00", "2027-03-28T06:30:00+02:00"),
    ],
)
def test_dst_transitions_follow_fixed_utc_schedule(now, published):
    assert not refresh.needs_refresh({"generated_at": published}, datetime.fromisoformat(now))


@pytest.mark.parametrize("event", ["push", "workflow_dispatch"])
def test_explicit_runs_bypass_freshness_lookup(monkeypatch, tmp_path, event):
    called = []
    monkeypatch.setattr(refresh, "_fetch_status", lambda now: called.append(now))
    monkeypatch.setenv("GITHUB_EVENT_NAME", event)
    output = tmp_path / "output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    assert refresh.main() == 0
    assert called == []
    assert output.read_text() == "should_build=true\n"


@pytest.mark.parametrize("problem", [TimeoutError(), OSError(), ValueError("bad JSON")])
def test_lookup_failure_still_runs_build(monkeypatch, tmp_path, problem):
    def fail(now):
        raise problem

    monkeypatch.setattr(refresh, "_fetch_status", fail)
    monkeypatch.setenv("GITHUB_EVENT_NAME", "schedule")
    output = tmp_path / "output"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    assert refresh.main() == 0
    assert output.read_text() == "should_build=true\n"


def test_fresh_published_site_skips_duplicate_build(monkeypatch, tmp_path):
    monkeypatch.setattr(refresh, "_fetch_status", lambda now: {"generated_at": now.isoformat()})
    monkeypatch.setenv("GITHUB_EVENT_NAME", "schedule")
    output = tmp_path / "output"
    output.write_text("another_output=keep\n")
    monkeypatch.setenv("GITHUB_OUTPUT", str(output))
    assert refresh.main() == 0
    assert output.read_text() == "another_output=keep\nshould_build=false\n"
