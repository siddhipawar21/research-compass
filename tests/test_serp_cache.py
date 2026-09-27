from __future__ import annotations

from pathlib import Path

from core.serp import SearchCache, SerpClient, cache_key, normalize_params


def test_cache_miss_then_hit(tmp_path: Path):
    calls = {"n": 0}

    def fetcher(url, params, timeout):
        calls["n"] += 1
        return {"organic_results": [{"title": "Paper A", "link": "https://example.com/a", "snippet": "hello"}]}

    client = SerpClient("test-key", tmp_path / "cache.sqlite", fetcher=fetcher, max_searches=5)
    first = client.search("google_scholar", q="graph neural climate")
    second = client.search("google_scholar", q="graph neural climate")

    assert first.cached is False
    assert second.cached is True
    assert calls["n"] == 1
    assert client.meter.used_this_run == 1
    assert client.meter.cache_hits_this_run == 1
    assert first.data["organic_results"][0]["title"] == "Paper A"
    assert second.data == first.data


def test_param_normalization_stable_key():
    a = cache_key("google", {"q": " hello ", "num": 10, "api_key": "secret"})
    b = cache_key("google", {"num": "10", "q": "hello"})
    assert a == b
    assert "secret" not in str(normalize_params({"q": "x", "api_key": "secret"}))


def test_credit_cap_skips_network(tmp_path: Path):
    calls = {"n": 0}

    def fetcher(url, params, timeout):
        calls["n"] += 1
        return {"organic_results": []}

    client = SerpClient("k", tmp_path / "c.sqlite", fetcher=fetcher, max_searches=1)
    client.search("google", q="one")
    skipped = client.search("google", q="two")
    assert skipped.skipped is True
    assert calls["n"] == 1
    assert client.meter.skipped_this_run == 1


def test_failed_search_does_not_raise(tmp_path: Path):
    def fetcher(url, params, timeout):
        raise RuntimeError("boom")

    client = SerpClient("k", tmp_path / "c.sqlite", fetcher=fetcher, max_retries=1)
    out = client.search("google_news", q="x")
    assert out.error
    assert out.data == {}
    assert client.meter.errors_this_run == 1


def test_preload_fixture_is_cache_hit(tmp_path: Path):
    cache = SearchCache(tmp_path / "c.sqlite")
    cache.preload_fixture("google_trends", {"q": "asr", "data_type": "TIMESERIES"}, {"interest_over_time": {}})
    client = SerpClient("k", tmp_path / "c.sqlite", fetcher=lambda *a: {"should": "not be called"})
    out = client.search("google_trends", q="asr", data_type="TIMESERIES")
    assert out.cached is True
    assert client.meter.used_this_run == 0
