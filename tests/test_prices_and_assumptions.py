"""Price loading fall-backs, and the "no hidden numbers" rule for assumptions."""

import pandas as pd
import pytest

from engine import assumptions as A
from engine import prices


def test_bunker_estimate_uses_the_documented_ratio():
    ratio = A.get("market", "bunkers", "usd_per_tonne_per_brent_dollar")
    # Brent at $100 a barrel gives ratio x 100 dollars a tonne (7.7 -> $770).
    assert prices.bunker_price_estimate(100.0) == pytest.approx(100.0 * ratio)


def test_falls_back_to_seed_when_download_fails(monkeypatch, tmp_path):
    def broken():
        raise ConnectionError("no internet")
    monkeypatch.setattr(prices, "download_benchmarks", broken)
    monkeypatch.setattr(prices, "CACHE_FILE", tmp_path / "benchmarks.csv")
    table, note = prices.load_benchmarks()
    assert {"brent", "wti"} <= set(table.columns)
    assert len(table) > 100
    assert "snapshot" in note


def test_download_is_cached_and_reused(monkeypatch, tmp_path):
    calls = []

    def fake_download():
        calls.append(1)
        return pd.DataFrame({"brent": [90.0], "wti": [80.0], "dubai": [88.0]},
                            index=pd.DatetimeIndex(["2026-01-02"], name="date"))
    monkeypatch.setattr(prices, "download_benchmarks", fake_download)
    monkeypatch.setattr(prices, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(prices, "CACHE_FILE", tmp_path / "benchmarks.csv")
    prices.load_benchmarks()
    table, _ = prices.load_benchmarks()  # second call must read the file, not download
    assert len(calls) == 1
    assert prices.latest(table, "brent") == (90.0, pd.Timestamp("2026-01-02"))


def test_every_assumption_is_documented():
    """Each number must say where it came from, when it was checked, and if it is an estimate."""
    rows = A.all_records()
    assert len(rows) > 60
    for row in rows:
        where = f"{row['file']}: {row['assumption']}"
        assert row["source"], f"{where} has no source"
        assert row["checked"], f"{where} has no 'checked' date"
    for name in A.FILES:
        _check_flags(A.load(name), name)


def _check_flags(node, where):
    if A.is_record(node):
        if "source" in node:
            assert "estimate" in node, f"{where} does not say whether it is an estimate"
            if node["estimate"] and "Our" not in node["source"]:
                assert node.get("note"), f"{where} is an estimate with no explanation"
    elif isinstance(node, dict):
        for key, child in node.items():
            _check_flags(child, f"{where} / {key}")
