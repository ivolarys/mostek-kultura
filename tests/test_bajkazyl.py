"""Bajkazyl dates and links must match the venue's own programme."""

from datetime import date

import pytest

from mostek_kultura.http import FixtureHttp
from mostek_kultura.normalize import PlaceResolver, flag_time, resolve_places
from mostek_kultura.sources import make_source


def source(cfg):
    return make_source(next(s for s in cfg.sources if s.name == 'bajkazyl-hk'))


class PayloadHttp:
    def __init__(self, payload):
        self.payload = payload

    def get_json(self, url):
        return self.payload


def test_bajkazyl_recording_matches_visible_dates_and_links(cfg, root):
    events = source(cfg).fetch(FixtureHttp(root / 'tests/fixtures/bajkazyl-hk'))
    assert len(events) >= 2
    current = flag_time(events, cfg.horizon_days, ref=date(2026, 9, 12))
    assert len(current) == 2
    talk = next(e for e in current if e.title == 'Beseda - Mobilita v Bajkazylu')
    assert talk.start.isoformat() == '2026-09-18T17:00:00+02:00'
    assert talk.end.isoformat() == '2026-09-18T19:00:00+02:00'
    assert talk.url == 'https://bajkazylhk.cz/akce/beseda-mobilita-v-bajkazylu-20260918-1500'
    assert talk.image == 'https://dbtools.cz/images/260918_etm.jpg'
    assert '[DESCRIPTION]' not in talk.description and '<br' not in talk.description
    concert = next(e for e in current if e.title.startswith('SHIT INFESTED'))
    assert concert.start.isoformat() == '2026-10-17T19:00:00+02:00'
    assert concert.end.isoformat() == '2026-10-17T22:00:00+02:00'
    assert concert.url.endswith('/shit-infested-roach-human-carcass-plan-to-kill-absent-god-20261017-1700')
    assert all(not e.all_day for e in current)
    assert all(e.native_category is None for e in current)  # Venue name is not a genre.
    resolve_places(current, PlaceResolver(cfg), {s.name: s.place for s in cfg.sources})
    assert all(e.place == 'Hradec Králové' and e.venue == 'Bajkazyl Hradec Králové' for e in current)


def test_bajkazyl_display_title_does_not_change_link_or_stable_id(cfg):
    item = {'id': 'stable-id', 'title': 'Vecirek BA', 'mainTitle': 'Večírek s novým názvem',
            'start': '2026-12-18T18:00:00.000Z', 'end': '2026-12-18T20:00:00.000Z',
            'images': [], 'location': ''}
    event = source(cfg).fetch(PayloadHttp([item]))[0]
    assert event.title == 'Večírek s novým názvem'
    assert event.start.isoformat() == '2026-12-18T19:00:00+01:00'
    assert event.url.endswith('/vecirek-ba-20261218-1800')
    renamed = source(cfg).fetch(PayloadHttp([{**item, 'mainTitle': 'Jiný zobrazovaný název'}]))[0]
    assert event.source_id == renamed.source_id


def test_bajkazyl_skips_bad_records_and_cancelled_events(cfg):
    valid = {'id': 'ok', 'title': 'Beseda', 'start': '2026-09-18T15:00:00Z', 'images': []}
    events = source(cfg).fetch(PayloadHttp([
        {'id': 'broken', 'title': 'Broken', 'start': 'not-a-date'},
        {**valid, 'id': 'cancelled', 'status': 'cancelled'},
        valid,
    ]))
    assert len(events) == 1
    assert events[0].title == 'Beseda' and events[0].end is None


def test_bajkazyl_empty_calendar_is_valid_but_error_payload_is_not(cfg):
    assert source(cfg).fetch(PayloadHttp([])) == []
    with pytest.raises(ValueError):
        source(cfg).fetch(PayloadHttp({'error': 'calendar unavailable'}))
