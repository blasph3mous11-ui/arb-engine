# Upgrade plan: Crude Arbitrage & Voyage Engine

## Context

The dashboard is built, live (https://crude-arb-engine.streamlit.app) and on GitHub
(blasph3mous11-ui/arb-engine, 115 tests passing). The owner asked what is left to upgrade and
then asked for a staged, followable plan. The aim of every stage is the same as the project's:
make the tool more convincing to someone on a physical trading desk, while keeping every number
sourced, every estimate labelled, and everything explainable by a non-programmer in an interview.

Project folder: `C:\Users\Admin\OneDrive\Desktop\crude-arb-project\arb-engine`

## Rules that apply to every stage

- Calculations live in `engine/` only; `app/` only collects inputs and displays.
- Every new number is a YAML record (`value, unit, source, url, checked, estimate, note`).
  `tests/test_prices_and_assumptions.py::test_every_assumption_is_documented` enforces this.
- Estimates are labelled "estimated" on screen. No forecasting. Never claim traded freight data.
- Free data only. If a real figure cannot be found free, it is an estimate with reasoning,
  or the feature takes the number as user input instead of guessing.
- New `ArbInputs` fields get defaults, so `tests/test_arbitrage.py::hand_inputs` and every
  hand-worked test stay valid. New voyage cost lines default to zero for the same reason.
- Python 3.10-compatible syntax. Plain-language text on every page.

**Closing routine for each stage (do all, in order):**
1. `.venv/Scripts/python.exe -m pytest -q` passes.
2. `python -m engine.assumptions` if any YAML changed (regenerates `docs/ASSUMPTIONS.md`).
3. Read the rendered page text headlessly for 3-4 set-ups (the AppTest pattern in
   `tests/test_dashboard.py`), checking wording against the numbers.
4. Update `docs/PROGRESS.md` (dated entry: what, decisions, sanity numbers), `docs/GLOSSARY.md`
   for new terms, the Methodology "does not do" list (`app/methodology_page.py`), README table.
5. Commit, push to `origin main`, then open the live link and check the changed page.
6. Tell the owner in trading terms what changed and what to click.

---

## Stage 0: Close the loose ends (do first)

Goal: nothing already shipped is unverified.

1. Independent review of the last commit (ports, ships, routes): one reviewer on engine
   correctness across every origin x destination x ship x route, one on page wording, new YAML
   records and docs. Each finding adversarially verified before fixing. Same method as the
   review that found the 25 defects.
2. Fix confirmed findings; add a test for each.
3. Add `LICENSE` (MIT) to the repository root.
4. Retake README screenshots from the live site (arbitrage, voyage with a new port, scenarios).
5. Fix `charts.route_map` (`app/charts.py`): longitude range clips Ningbo/Ulsan; widen it.
6. Write a short owner checklist in `docs/PROGRESS.md`: the figures to confirm by eye (Platts
   guide, Baltic white paper, sea-distances.org) and which `estimate:` flags to flip after.

Done when: review findings are fixed or rejected with evidence, tests pass, pushed.

## Stage 1: "Where should this cargo go?" page

Goal: for one cargo (load port, ship, freight market), rank every discharge port by margin.
This is the netback view a trader uses.

1. Engine: new `engine/ranking.py` with `rank_destinations(base_inputs, prices_by_benchmark)`.
   For each key in `voyage.port_keys("destination")`: get `voyage.route_options(...)`, run
   `arbitrage.run` for each available route, keep the cheapest landed cost. Return rows:
   port, region, best route, distance, days loaded, freight, landed cost, sale value, margin.
2. Benchmark per destination: use the sidebar benchmark for all ports (one like-for-like
   comparison), and state that on the page. Do not mix daily Brent with monthly Dubai.
3. Chart: `charts.ranking_bars(rows)`, horizontal bars of margin per barrel, green/red by sign
   (reuse `GOOD`/`CRITICAL`), value labels, sorted best first.
4. Page: `app/ranking_page.py`: headline ("Best destination today: X, margin Y"), the chart, a
   table with every column, and a sentence explaining why the winner wins (shortest voyage,
   no canal, etc.). Add the tuple to `PAGES` in `app/main.py` and `tests/test_dashboard.py`.
5. Tests: hand-worked ranking with `voyage.sea_route` monkeypatched to fixed distances per port
   (two ports, known margins, assert order and best route); every destination appears once;
   smoke test via the existing `SETUPS`.

Reuse: `arbitrage.run`, `ArbInputs.with_changes`, `voyage.route_options`, `ui.base_inputs`,
`ui.usd`, `ui.route_phrase`.

## Stage 2: Freight-versus-spread grid

Goal: one chart showing which combinations of ship cost and price gap open the arb.

1. Engine: `scenarios.margin_grid(inputs, hire_values, spread_values)` returning a DataFrame.
   The spread axis moves the destination price only, exactly as `scenarios.breakeven_spread`
   does. Grid ranges go in `costs.yaml` under `scenario_ranges` (our choice, flagged).
2. Chart: `charts.margin_heatmap(grid, today_hire, today_spread)`: two-hue diverging scale with
   a neutral midpoint at zero margin, a marker for today's position, a contour at break-even.
3. Page: add as a section on `app/scenarios_page.py` under the tornado, with a caption on how
   to read it and the same held-constant caveat.
4. Tests: grid cell equals a single `arbitrage.run` with those inputs (use the hand-worked
   trade: the cell at hire $50,000 and spread $10 must be $3.9276); break-even contour agrees
   with `breakeven_spread`.

## Stage 3: Type in a broker's freight quote

Goal: let the user enter freight the way a broker quotes it, and show what the owner earns.

1. Decision recorded in YAML/docs: Worldscale flat rates are paywalled, so the user types both
   the Worldscale points and the flat rate ($/tonne); nothing is guessed. Lump sum ($) is the
   second option. Default mode stays "daily hire rate".
2. Engine (`engine/voyage.py`): `freight_from_quote(...)`:
   - lump sum: freight = the lump sum.
   - Worldscale: freight = points/100 x flat rate x cargo tonnes, using
     `units.barrels_to_tonnes` and the grade's API gravity (first real use of those helpers).
   - `implied_tce(...)` = (freight - bunkers - ports - canal - war risk) / total days.
3. `ArbInputs`: add `freight_override_usd: float | None = None`. When set, `arbitrage.run`
   uses it for the "Freight" line; demurrage uses the implied TCE as the daily rate.
4. UI: on `app/voyage_page.py`, a "How is freight quoted?" selector (daily hire / Worldscale /
   lump sum) with the matching inputs and a metric "Owner's daily earnings (TCE)". Stored in
   `st.session_state` so Arbitrage and Scenarios use the same freight; the tornado hire row is
   replaced by a freight +/-% row in that mode.
5. Tests: hand-worked Worldscale example (WS 100, flat $20/t, 131,480 t = $2,629,600);
   TCE back-out reproduces the hire rate when the quote equals hire-based freight; pages agree
   on freight in each mode (extend `test_pages_agree_on_freight_spread_and_fuel`).
6. Glossary: lump sum, flat rate; expand Worldscale and TCE entries.

## Stage 4: Missing voyage costs

Goal: add the cost lines a desk would ask about. Each defaults to zero in `estimate_voyage`.

1. Broker commission: `costs.yaml` `freight.commission_pct` (research a public source for the
   usual 1.25-3.75% total; flag estimate). Computed on the gross freight subtotal in
   `voyage_from_assumptions`, added as cost key "Broker commission" (not inside the subtotal,
   to avoid circularity).
2. Reverse lightering: per-port field `max_cargo_bbl_at_berth` in `ports.yaml` (LOOP: full
   VLCC; others: research, else estimate), and `lightering_usd_per_bbl` on the shortfall.
   Research EIA's lightering article for a cost figure. Cost key "Lightering (ship-to-ship)".
3. EU carbon: port flag `eu_ets: true` (Rotterdam). Cost = fuel tonnes x CO2 factor (3.114
   t CO2 per tonne fuel oil, IMO, sourced) x 50% for a voyage from outside the EU x EUA price.
   Check for a free EUA price source at build time; if none, a dated YAML snapshot flagged as
   estimate. Verify the current phase-in percentage from the EU regulation text.
   Cost key "EU carbon (ETS)".
4. Pages: new keys flow into `charts.cost_bars`, the Voyage comparison table and the Freight
   line automatically; update the Arbitrage "every line explained" text and Methodology table.
5. Tests: one hand-worked test per cost; a Rotterdam voyage carries the ETS line and a Sikka
   voyage does not; a VLCC from Houston carries lightering and from LOOP does not.

## Stage 5: Price timing and the futures curve

Goal: show how much the shape of the curve adds or subtracts over the voyage.

1. Data check first: EIA publishes free daily NYMEX WTI futures for contracts 1-4 (same
   spreadsheet pattern as the spot series). Confirm at build time. Free Brent futures are not
   expected to exist; if not, say so and model the WTI curve only.
2. Engine (`engine/prices.py`): download and cache the four WTI contracts; `curve_slope()` =
   contract 2 minus contract 1 per month (contango positive, backwardation negative).
3. Engine (`engine/costs.py`): `curve_roll_value(slope_per_month, days)` = slope x days/30.
   Explained as: a hedged cargo sold a month later gains in contango, loses in backwardation.
4. `ArbInputs.curve_value_usd_per_bbl: float = 0.0`; a new line "Curve effect (estimated)" in
   the stack and waterfall, off by default behind a toggle on the Arbitrage page.
5. Honest limits on the page: applies the WTI curve as a proxy for the hedge on both legs;
   no pricing windows; not a forecast.
6. Tests: hand-worked roll ($0.60/month contango x 36 days = +$0.72); zero when toggle off;
   parser test on a small fixture file.

## Stage 6: More grades and better valuation

Goal: ship real export grades and value them more defensibly.

1. Add grades to `costs.yaml`: WTI Midland, Mars, and one more (research EIA/producer assay
   pages for API and sulphur). Each needs an origin price basis: EIA publishes free spot
   prices for some US grades (check Mars, LLS at build time); otherwise WTI plus an estimated
   differential, flagged.
2. Sidebar: "Grade shipped" selector; `ui.base_inputs` passes `grade`. Remove WTI-only wording
   (`app/arbitrage_page.py`, `app/home.py`, `app/prices_page.py`, Methodology).
3. Valuation: keep the API/sulphur rule as the default. Add an optional simple
   gross-product-worth view only if free product prices (EIA gasoline, diesel, fuel oil spot)
   and a sourced yield table per grade can be found; otherwise document why not.
4. Tests: quality differential by hand for each new grade; grade switch changes sale value
   and purchase price as expected; estimate labels present.

## Stage 7: Other load regions (largest change; confirm scope with owner first)

Goal: beyond US exports, for example West Africa or the North Sea.

1. Owner decision needed: which region(s). Each needs a free origin price (Brent for the North
   Sea is available; West African and Middle East grades are not free, so differentials would
   be estimates).
2. Per-origin price source and differential in `ports.yaml` (replaces the single Gulf Coast
   differential); `ui.base_inputs`, `prices.monthly_averages` and the Scenarios history stop
   assuming the `"wti"` column.
3. Routing: war risk must depend on whether the path passes Bab el-Mandeb (use searoute's
   `traversed_passages`), not on "via Suez"; update `routing.red_sea_on_suez_route` and
   `test_every_port_pair_has_a_sensible_route`.
4. Tests and docs as per the closing routine; the case study gains a second example.

---

## Order and dependencies

0 -> 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7. Stages 1 and 2 are independent and small; 3 and 4 both
touch `voyage_from_assumptions`, so do 3 before 4; 6 removes the WTI-only assumptions that 7
needs. Stop for the owner's go-ahead before Stage 7.

## Verification (end to end, after each stage)

- Full test suite, plus the headless page read for: base case, Rotterdam direct on an Aframax,
  LOOP to Ningbo on a VLCC, Dubai benchmark.
- Sanity numbers stay in range: calm-market freight "a few dollars a barrel"; today's base case
  margin moves only by the amount the new cost lines explain.
- Live site re-checked after each push; `docs/PROGRESS.md` updated so the next session can
  resume from the right stage.
