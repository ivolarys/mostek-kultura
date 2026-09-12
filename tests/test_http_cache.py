"""Regression coverage for one-build HTTP reuse without cross-source data leakage."""

import gzip
import json
from dataclasses import replace
from datetime import datetime

import httpx
import pytest

from mostek_kultura import build as pipeline
from mostek_kultura.config import SourceConfig
from mostek_kultura.dates import TZ
from mostek_kultura.http import FixtureHttp, Http
from mostek_kultura.model import Event


def mock_http(handler, **kwargs):
    http = Http(**kwargs)
    http.close()
    http.clients = [httpx.Client(transport=httpx.MockTransport(handler)) for _ in range(2)]
    http.client = http.clients[0]
    return http


def test_cached_compressed_get_keeps_encoding_isolated_and_records_each_source(tmp_path):
    calls = []
    text = 'Příliš žluťoučký kůň'

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(200, content=gzip.compress(text.encode('iso-8859-2')),
                              headers={'Content-Encoding': 'gzip',
                                       'Content-Type': 'text/html; charset=iso-8859-2'})

    with mock_http(handler, cache_gets=True) as http:
        url = 'https://example.cz/program?month=9'
        http.record_dir = tmp_path / 'first'
        assert http.get_text(url) == text
        assert http.get_text(url, encoding='latin-1') != text
        http.record_dir = tmp_path / 'second'
        assert http.get_text(url) == text
        assert FixtureHttp(tmp_path / 'first').get_text(url) != text
        assert FixtureHttp(tmp_path / 'second').get_text(url) == text
        assert http.get_text('https://example.cz/program?month=10') == text
    assert len(calls) == 2  # Full URL: different months must never share a cached response.
    assert all(client.is_closed for client in http.clients)


def test_cached_json_is_independent_and_standalone_get_is_fresh():
    calls = []

    def handler(request):
        calls.append(request.method)
        return httpx.Response(200, json={'items': [len(calls)]})

    with mock_http(handler, cache_gets=True) as http:
        first = http.get_json('https://example.cz/program')
        first['items'].append(99)
        assert http.get_json('https://example.cz/program') == {'items': [1]}
    with mock_http(handler) as http:
        assert http.get_json('https://example.cz/program') != http.get_json('https://example.cz/program')
    assert len(calls) == 3


def test_posts_are_never_cached_and_invalidate_previous_get():
    calls = []

    def handler(request):
        calls.append(request.method)
        return httpx.Response(200, text=str(len(calls)))

    with mock_http(handler, cache_gets=True) as http:
        url = 'https://example.cz/program'
        assert http.get_text(url) == http.get_text(url) == '1'
        assert http.post_text(url, {'hall': '1'}) == '2'
        assert http.post_text(url, {'hall': '1'}) == '3'
        assert http.get_text(url) == '4'
    assert calls == ['GET', 'POST', 'POST', 'GET']


def test_failed_get_is_not_cached(monkeypatch):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(503 if len(calls) == 1 else 200, text='recovered')

    def no_pinned(url):
        raise RuntimeError('no fallback in test')

    monkeypatch.setattr('mostek_kultura.http.time.sleep', lambda _: None)
    with mock_http(handler, cache_gets=True, retries=1) as http:
        monkeypatch.setattr(http, '_get_pinned', no_pinned)
        with pytest.raises(RuntimeError):
            http.get_text('https://example.cz/program')
        assert http.get_text('https://example.cz/program') == 'recovered'
        assert http.get_text('https://example.cz/program') == 'recovered'
    assert len(calls) == 2


def test_hkinfo_shared_fetch_records_all_sources_and_expires_after_build(root, cfg, tmp_path, monkeypatch):
    recording = FixtureHttp(root / 'tests/fixtures/hradec-vyber')
    calls, transports = [], []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(200, text=recording.get_text(str(request.url)))

    def factory(**kwargs):
        http = mock_http(handler, **kwargs)
        transports.append(http)
        return http

    monkeypatch.setattr(pipeline, 'Http', factory)
    sources = {'nablesi', 'sauna-nuuk', 'hradec-vyber'}
    events, statuses = pipeline.fetch_all(cfg, tmp_path, offline=False, only=sources,
                                         record=True, persist=False)
    assert len(calls) == 3  # Three months shared by three separately filtered sources.
    assert {e.source for e in events} == sources
    assert all(s.status == 'ok' and s.count for s in statuses)
    for name in sources:
        manifest = json.loads((tmp_path / 'tests/fixtures' / name / 'manifest.json').read_text())
        assert set(manifest) == set(calls)
    again, repeated_statuses = pipeline.fetch_all(cfg, tmp_path, offline=False, only=sources,
                                                persist=False)
    assert len(calls) == 6  # A subsequent build fetches current data again.
    assert [e.to_dict() for e in again] == [e.to_dict() for e in events]
    assert [s.name for s in repeated_statuses] == [s.name for s in statuses]
    assert all(c.is_closed for http in transports for c in http.clients)
    assert all(http.record_dir is None for http in transports)


def test_source_parse_failure_preserves_fallback_and_closes_transport(cfg, tmp_path, monkeypatch):
    source = SourceConfig(name='broken', type='manual', url='https://example.cz/program')
    cfg = replace(cfg, sources=[source])
    cached = Event('Záložní akce', datetime(2026, 9, 20, tzinfo=TZ), source='broken')
    pipeline.save_last_good(tmp_path / 'cache/last_good/broken.json', [cached])
    http = mock_http(lambda _: httpx.Response(200, text='changed markup'), cache_gets=True)

    class BrokenSource:
        def fetch(self, transport):
            transport.get_text(source.url)
            raise ValueError('unexpected markup')

    monkeypatch.setattr(pipeline, 'Http', lambda **_: http)
    monkeypatch.setattr(pipeline, 'make_source', lambda _: BrokenSource())
    events, statuses = pipeline.fetch_all(cfg, tmp_path, offline=False, only=None, record=True)
    assert [e.to_dict() for e in events] == [cached.to_dict()]
    assert statuses[0].status == 'fallback'
    assert 'unexpected markup' in statuses[0].error
    assert http.record_dir is None
    assert all(client.is_closed for client in http.clients)


def test_cached_json_preserves_bom_encoding_detection():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, content=json.dumps({'title': 'Výstava'}, ensure_ascii=False).encode('utf-16'),
                              headers={'Content-Type': 'application/json'})

    with mock_http(handler, cache_gets=True) as http:
        assert http.get_json('https://example.cz/data') == {'title': 'Výstava'}
        assert http.get_json('https://example.cz/data') == {'title': 'Výstava'}
    assert len(calls) == 1
