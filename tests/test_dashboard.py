"""Smoke test: every dashboard page loads without an error, for several trade set-ups.

Uses Streamlit's built-in test runner, so no browser is needed. Prices come
from the snapshot shipped with the project, so the test works offline.
"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from engine import prices
from engine import assumptions as A

ROOT = Path(__file__).resolve().parents[1]
PAGES = ["home.py", "voyage_page.py", "prices_page.py", "arbitrage_page.py", "ranking_page.py",
         "scenarios_page.py", "methodology_page.py"]
RADIOS = ("via", "freight_basis", "speed_mode")
SETUPS = [
    {},                                                    # the starting case
    {"vessel": "vlcc"},                                    # too deep for Suez: forced via the Cape
    {"vessel": "aframax", "via": "cape", "market": "calm_2024"},
    {"benchmark": "dubai", "destination": "mumbai", "origin": "houston"},
    {"destination": "rotterdam", "vessel": "aframax"},     # Atlantic crossing: direct, no canal
    {"origin": "loop", "destination": "ningbo", "vessel": "vlcc"},
    {"vessel": "panamax", "destination": "singapore", "market": "time_charter_1yr_jul_2026"},
    {"vessel": "suezmax_eco", "destination": "paradip", "origin": "beaumont", "via": "cape"},
    {"grade_us_gulf": "mars", "benchmark": "dubai", "origin": "loop"},
    {"grade_us_gulf": "wti_midland", "destination": "rotterdam", "freight_basis": "lump_sum"},
    {"origin": "hound_point", "destination": "rotterdam", "vessel": "aframax"},
    {"origin": "mongstad", "benchmark": "dubai",
     "destination": "ningbo", "vessel": "vlcc"},
    {"speed_mode": "cheapest"},                            # spot market: flat out
    {"speed_mode": "cheapest", "market": "calm_2024",      # calm market, EU carbon: slower
     "destination": "rotterdam", "vessel": "aframax"},
    {"speed_mode": "custom"},
    {"speed_mode": "cheapest", "freight_basis": "lump_sum"},
]


@pytest.fixture(autouse=True)
def offline_prices(monkeypatch):
    seed = prices._read(prices.SEED_FILE)
    monkeypatch.setattr(prices, "load_benchmarks", lambda refresh=False: (seed, "Test snapshot."))


@pytest.mark.parametrize("page", PAGES)
@pytest.mark.parametrize("setup", SETUPS, ids=["base", "vlcc", "aframax-cape-calm", "dubai-mumbai", "rotterdam-direct",
                                              "loop-ningbo-vlcc", "panamax-singapore", "eco-paradip-cape",
                                              "mars-dubai-loop", "midland-rotterdam-lump-sum",
                                              "forties-rotterdam", "sverdrup-dubai-ningbo-vlcc",
                                              "speed-cheapest", "speed-cheapest-calm-rotterdam",
                                              "speed-custom", "speed-cheapest-lump-sum"])
def test_page_loads(page, setup):
    app = AppTest.from_file(str(ROOT / "app" / "main.py"), default_timeout=120).run()
    for key, value in setup.items():
        widget = app.radio(key=key) if key in RADIOS else app.selectbox(key=key)
        widget.set_value(value)
        if key == "origin":
            app.run()  # the grade list depends on the load port, so apply it first
    app.run()
    app.switch_page(str(ROOT / "app" / page)).run()
    assert not app.exception, f"{page} raised: {[e.value for e in app.exception]}"
    assert len(app.title) == 1


# --- The pages must agree with each other -----------------------------------

def load_page(page, setup):
    app = AppTest.from_file(str(ROOT / "app" / "main.py"), default_timeout=120).run()
    for key, value in setup.items():
        widget = app.radio(key=key) if key in RADIOS else app.selectbox(key=key)
        widget.set_value(value)
        if key == "origin":
            app.run()  # the grade list depends on the load port, so apply it first
    app.run()
    app.switch_page(str(ROOT / "app" / page)).run()
    assert not app.exception, f"{page} raised: {[e.value for e in app.exception]}"
    return app


@pytest.mark.parametrize("basis", ["worldscale", "lump_sum"])
def test_pages_agree_on_a_broker_quote(basis):
    """With a quote typed in, every page uses it, and every page still loads."""
    setup = {"freight_basis": basis}
    voyage_page = load_page("voyage_page.py", setup)
    arbitrage_page = load_page("arbitrage_page.py", setup)
    scenarios_page = load_page("scenarios_page.py", setup)
    for page in ("home.py", "ranking_page.py", "prices_page.py", "methodology_page.py"):
        load_page(page, setup)

    lines = arbitrage_page.dataframe[0].value.set_index("Line")["USD per barrel"]
    arbitrage_freight = next(value for line, value in lines.items() if line.startswith("+ Freight"))
    assert metric(voyage_page, "Net freight per barrel") == arbitrage_freight
    assert metric(scenarios_page, "Freight per barrel") == arbitrage_freight
    # Pre-filled to match the daily-hire estimate, so before commissions the owner would earn the
    # default market's hire rate. The 1.25% brokerage on the (grossed-up) quote comes out of that,
    # a few per cent of the daily rate.
    hire = A.get("market", "freight_markets", A.get("market", "default_freight_market"),
                 "hire_usd_per_day", "suezmax")
    tce = float(metric(voyage_page, "Owner's daily earnings").replace("$", "").replace(",", ""))
    assert 0.93 * hire < tce < hire
    # Switching on an untouched, pre-filled quote changes nothing (to within rounding).
    hire_mode = load_page("arbitrage_page.py", {})
    to_number = lambda text: float(text.replace("$", "").replace(",", ""))
    assert to_number(metric(arbitrage_page, "Margin per barrel")) == pytest.approx(
        to_number(metric(hire_mode, "Margin per barrel")), abs=0.02)
    # The grid needs a daily hire rate, so in quote mode it is replaced by an explanation.
    assert any("broker's quote replaces" in i.value for i in scenarios_page.info)


def metric(app, label_start):
    return next(m.value for m in app.metric if m.label.startswith(label_start))


@pytest.mark.parametrize("setup", [{}, {"benchmark": "dubai"},
                                   {"benchmark": "dubai", "vessel": "vlcc", "market": "calm_2024"},
                                   {"speed_mode": "cheapest", "market": "calm_2024"}],
                         ids=["brent", "dubai", "dubai-vlcc-calm", "cheapest-speed-calm"])
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


def test_typed_in_curve_reaches_the_arbitrage_page():
    flat = load_page("arbitrage_page.py", {})
    app = AppTest.from_file(str(ROOT / "app" / "main.py"), default_timeout=120).run()
    app.number_input(key="curve_m2_minus_m1").set_value(0.60)
    app.run()
    app.switch_page(str(ROOT / "app" / "arbitrage_page.py")).run()
    assert not app.exception
    lines = app.dataframe[0].value.set_index("Line")["USD per barrel"]
    curve = next(value for line, value in lines.items() if line.startswith("+ Futures curve"))
    assert curve.startswith("$") and curve != "$0.00"
    # Contango raises the margin by exactly the curve effect.
    to_number = lambda text: float(text.replace("$", "").replace(",", ""))
    assert to_number(metric(app, "Margin per barrel")) == pytest.approx(
        to_number(metric(flat, "Margin per barrel")) + to_number(curve), abs=0.011)


def test_north_sea_cargo_is_priced_off_brent():
    app = load_page("arbitrage_page.py", {"origin": "mongstad"})
    lines = list(app.dataframe[0].value["Line"])
    assert "Brent benchmark price" in lines
    assert any(line.startswith("+ Differential to Dated Brent") for line in lines)
    assert not any("Gulf Coast" in line for line in lines)
    labels = [s.label for s in load_page("scenarios_page.py", {"origin": "mongstad"}).slider]
    assert any("minus Brent" in label for label in labels)


def test_cheapest_speed_shows_on_the_voyage_page():
    calm = load_page("voyage_page.py", {"speed_mode": "cheapest", "market": "calm_2024"})
    assert any(s.value.startswith("How fast should it sail") for s in calm.subheader)
    used = metric(calm, "Speed used, loaded / empty")
    assert used == metric(calm, "Cheapest at these costs")
    # Cheaper than the usual speed, or the same: never worse.
    gain = metric(calm, "Cheapest speed instead of usual")
    assert not gain.startswith("-")
    # The Arbitrage page states the same speeds in its freight line.
    arbitrage_page = load_page("arbitrage_page.py", {"speed_mode": "cheapest", "market": "calm_2024"})
    freight_text = next(text for text in arbitrage_page.dataframe[0].value["Where it comes from"]
                        if "days of ship hire" in text)
    laden, ballast = used.replace(" knots", "").split(" / ")
    assert f"sailing at {laden} knots loaded and {ballast} empty" in freight_text


def test_arbitrage_page_offers_the_trade_recap():
    app = load_page("arbitrage_page.py", {})
    buttons = app.get("download_button")
    assert len(buttons) == 1
    assert "Download this trade" in buttons[0].proto.label
