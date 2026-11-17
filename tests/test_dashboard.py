"""Smoke test: every dashboard page loads without an error, for several trade set-ups.

Uses Streamlit's built-in test runner, so no browser is needed. Prices come
from the snapshot shipped with the project, so the test works offline.
"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from engine import prices

ROOT = Path(__file__).resolve().parents[1]
PAGES = ["home.py", "voyage_page.py", "prices_page.py", "arbitrage_page.py", "ranking_page.py",
         "scenarios_page.py", "methodology_page.py"]
SETUPS = [
    {},                                                    # the starting case
    {"vessel": "vlcc"},                                    # too deep for Suez: forced via the Cape
    {"vessel": "aframax", "via": "cape", "market": "calm_2024"},
    {"benchmark": "dubai", "destination": "mumbai", "origin": "houston"},
    {"destination": "rotterdam", "vessel": "aframax"},     # Atlantic crossing: direct, no canal
    {"origin": "loop", "destination": "ningbo", "vessel": "vlcc"},
    {"vessel": "panamax", "destination": "singapore", "market": "time_charter_1yr_jul_2026"},
    {"vessel": "suezmax_eco", "destination": "paradip", "origin": "beaumont", "via": "cape"},
]


@pytest.fixture(autouse=True)
def offline_prices(monkeypatch):
    seed = prices._read(prices.SEED_FILE)
    monkeypatch.setattr(prices, "load_benchmarks", lambda refresh=False: (seed, "Test snapshot."))


@pytest.mark.parametrize("page", PAGES)
@pytest.mark.parametrize("setup", SETUPS, ids=["base", "vlcc", "aframax-cape-calm", "dubai-mumbai", "rotterdam-direct",
                                              "loop-ningbo-vlcc", "panamax-singapore", "eco-paradip-cape"])
def test_page_loads(page, setup):
    app = AppTest.from_file(str(ROOT / "app" / "main.py"), default_timeout=120).run()
    for key, value in setup.items():
        widget = app.radio(key=key) if key == "via" else app.selectbox(key=key)
        widget.set_value(value)
    app.run()
    app.switch_page(str(ROOT / "app" / page)).run()
    assert not app.exception, f"{page} raised: {[e.value for e in app.exception]}"
    assert len(app.title) == 1


# --- The pages must agree with each other -----------------------------------

def load_page(page, setup):
    app = AppTest.from_file(str(ROOT / "app" / "main.py"), default_timeout=120).run()
    for key, value in setup.items():
        widget = app.radio(key=key) if key == "via" else app.selectbox(key=key)
        widget.set_value(value)
    app.run()
    app.switch_page(str(ROOT / "app" / page)).run()
    assert not app.exception, f"{page} raised: {[e.value for e in app.exception]}"
    return app


def metric(app, label_start):
    return next(m.value for m in app.metric if m.label.startswith(label_start))


@pytest.mark.parametrize("setup", [{}, {"benchmark": "dubai"},
                                   {"benchmark": "dubai", "vessel": "vlcc", "market": "calm_2024"}],
                         ids=["brent", "dubai", "dubai-vlcc-calm"])
def test_pages_agree_on_freight_spread_and_fuel(setup):
    """Same sidebar choices, same numbers on every page.

    The Arbitrage page tells the reader to "see the Voyage page" for its freight
    line, and the Prices page says to compare its spread with that freight, so a
    difference between pages would be seen at once.
    """
    voyage_page = load_page("voyage_page.py", setup)
    prices_page = load_page("prices_page.py", setup)
    arbitrage_page = load_page("arbitrage_page.py", setup)
    scenarios_page = load_page("scenarios_page.py", setup)

    lines = arbitrage_page.dataframe[0].value.set_index("Line")["USD per barrel"]
    arbitrage_freight = next(value for line, value in lines.items() if line.startswith("+ Freight"))
    assert metric(voyage_page, "Freight per barrel") == arbitrage_freight
    assert metric(scenarios_page, "Freight per barrel") == arbitrage_freight

    assert metric(prices_page, "Spread:") == metric(scenarios_page, "Spread in this scenario")

    # Fuel is always priced off the latest daily Brent, also when Dubai (monthly) is chosen.
    seed = prices._read(prices.SEED_FILE)
    latest_brent, _ = prices.latest(seed, "brent")
    fuel = f"{prices.bunker_price_estimate(latest_brent):,.0f}"
    assert metric(prices_page, "Ship fuel") == "$" + fuel
    assert f"{voyage_page.number_input[1].value:,.0f}" == fuel


def test_dubai_views_are_monthly():
    prices_page = load_page("prices_page.py", {"benchmark": "dubai"})
    assert any("averages)" in m.label for m in prices_page.metric)
    scenarios_page = load_page("scenarios_page.py", {"benchmark": "dubai"})
    labels = [m.label for m in scenarios_page.metric]
    assert "Months the arb was open" in labels and "Best / worst month" in labels
    # With Brent, which is published daily, the history stays day by day.
    labels = [m.label for m in load_page("scenarios_page.py", {}).metric]
    assert "Days the arb was open" in labels and "Best / worst day" in labels


@pytest.mark.parametrize("market", ["spot_nov_2026", "time_charter_1yr_jul_2026", "calm_2024"])
def test_estimates_are_labelled_in_every_freight_market(market):
    arbitrage_page = load_page("arbitrage_page.py", {"market": market})
    lines = list(arbitrage_page.dataframe[0].value["Line"])
    for start in ("+ Freight", "+ Financing", "+ Insurance", "+ Transit loss", "+ Demurrage",
                  "+ Gulf Coast differential", "+ Quality adjustment"):
        line = next(text for text in lines if text.startswith(start))
        assert "estimated)" in line, f"'{line}' is not labelled as an estimate"
    sliders = [s.label for s in load_page("scenarios_page.py", {"market": market}).slider]
    assert "Ship hire, USD per day (estimated)" in sliders
    assert "Fuel (bunker) price, USD per tonne (estimated)" in sliders


def test_how_to_read_sentence_agrees_with_the_verdict():
    # Dubai, VLCC, calm market: costs are about $5 a barrel but the quality adjustment
    # adds $5.20, so the arb can be open with a raw gap smaller than the costs.
    # The sentence must reason from the adjusted gap, never the raw one.
    app = load_page("arbitrage_page.py", {"benchmark": "dubai", "vessel": "vlcc", "market": "calm_2024"})
    how_to_read = next(i.value for i in app.info if "How to read this" in i.value)
    assert "quality adjustment (+5.20)" in how_to_read
    is_open = any("ARB OPEN" in s.value for s in app.success)
    assert ("The adjusted gap is wide enough" in how_to_read) == is_open
    assert ("The adjusted gap is not wide enough" in how_to_read) == (not is_open)


def test_download_button_downloads_and_reports_it(monkeypatch):
    calls = []
    seed = prices._read(prices.SEED_FILE)

    def fake_load(refresh=False):
        calls.append(refresh)
        return seed, ("Downloaded just now." if refresh else "Saved copy.")
    monkeypatch.setattr(prices, "load_benchmarks", fake_load)

    app = load_page("prices_page.py", {})
    app.button[0].click().run()
    assert not app.exception
    # The click must really ask for a download, whatever is already held in memory.
    assert True in calls
    assert any("Downloaded just now." in c.value for c in app.caption)


def test_draught_warning_shows_in_the_sidebar():
    app = AppTest.from_file(str(ROOT / "app" / "main.py"), default_timeout=120).run()
    app.selectbox(key="origin").set_value("houston")
    app.selectbox(key="vessel").set_value("vlcc")
    app.run()
    assert any("reverse lightering" in w.value for w in app.sidebar.warning)
    app.selectbox(key="origin").set_value("loop")
    app.run()
    assert not any("reverse lightering" in w.value for w in app.sidebar.warning)
