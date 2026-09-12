import os
from pathlib import Path

import pytest

from mostek_kultura.config import load_config

ROOT = Path(__file__).resolve().parent.parent

# The day the fixtures in tests/fixtures/ were recorded. Freezing `dates.now()/today()` to it
# makes the offline test suite reproducible regardless of the real calendar date (normalize.py's
# flag_time() drops events that are in the past relative to "today"). Left alone if the caller
# already set MOSTEK_NOW (e.g. to simulate a future "today" against the parser tests).
FIXTURE_DAY = "2026-09-11T12:00:00+02:00"


@pytest.fixture(scope="session", autouse=True)
def _frozen_clock():
    mp = pytest.MonkeyPatch()
    if "MOSTEK_NOW" not in os.environ:
        mp.setenv("MOSTEK_NOW", FIXTURE_DAY)
    yield
    mp.undo()


@pytest.fixture(scope="session")
def cfg():
    return load_config(ROOT / "config.yaml")


@pytest.fixture(scope="session")
def root():
    return ROOT
