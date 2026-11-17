# Progress

Read this first at the start of every session.

## Where things stand (17 November 2026)

**All five phases are built and working**, and the tool now covers 4 US Gulf load ports, 7
discharge ports (India, Europe, East Asia) and 5 ship types. See the latest dated entry for the
test count. The dashboard has seven pages. The code is on GitHub: https://github.com/blasph3mous11-ui/arb-engine

## Upgrade plan in progress (see `docs/UPGRADE_PLAN.md`)

Stages: 0 loose ends, 1 destination ranking, 2 freight-vs-spread grid, 3 broker freight quote,
4 commission / lightering / EU carbon, 5 futures curve, 6 more grades, 7 other load regions
(needs the owner's go-ahead). Resume from the first stage not marked done below.

- **Stage 1, done 17 Nov 2026: "Where to send it" page.** `engine/ranking.py` costs the same
  cargo to every discharge port by its cheapest available route and ranks by margin
  (`app/ranking_page.py`, `charts.ranking_bars`, `tests/test_ranking.py`). Decision: every port
  is valued against the one sell benchmark chosen in the sidebar, so the ranking reflects the
  voyage only; real per-market premiums are paywalled and the page says so. Today (spot market,
  Suezmax from Corpus Christi): Rotterdam is least bad at -$10.82 a barrel, Ulsan worst at
  -$33.67. 127 tests pass.
- **Stage 5, done 17 Nov 2026: futures curve effect.** Found that the EIA stopped publishing its
  free NYMEX WTI futures series (RCLC1-4) in April 2024 and no other permitted free source exists,
  so today's curve is typed in (sidebar, "Hedging: the futures curve", default 0).
  `costs.curve_roll_value` = slope x days financed / 30, added to the sale value as "Futures
  curve effect (hedged)" (`ArbInputs.curve_m2_minus_m1`, `ArbResult.curve_value`); transit loss
  is still charged on the physical value only. The 1985-2024 monthly history is saved in
  `data/seed/wti_curve_history.csv` (`prices.curve_history`) and charted on the Arbitrage page
  for scale: half of all months between -$0.37 and +$0.34; extremes +$7.38 (April 2020) and
  -$2.70 (July 2022). Not modelled: pricing windows, basis risk, hedge costs. 157 tests pass.
- **Stage 4, done 17 Nov 2026: missing voyage costs.** Two new lines in the cost stack, paid by
  the cargo on top of freight: "Reverse lightering" ($0.60/bbl, estimate from Columbia CGEP's
  2018 range of 50-75 cents, charged whenever `voyage.needs_lightering` is true) and "EU carbon
  (ETS)" (`costs.eu_ets_covered_fuel`, `costs.eu_ets_cost`; Rotterdam is flagged `eu_ets`; 3.114
  t CO2/t fuel, 100% coverage from 2026, half of voyage emissions, EUR 75/t May 2026 snapshot and
  $1.10/EUR both estimates). Decision on commissions: they come out of freight, so adding them as
  a cost would double-count. They apply only to typed-in quotes: the charterer pays the quote less
  2.5% address commission, and the owner's TCE (`arbitrage.owner_tce`) is after 3.75% in total.
  Sanity: EU carbon about $0.20-0.23/bbl on a US Gulf-Rotterdam voyage; base case unchanged at
  -$23.64. 151 tests pass.
- **Stage 3, done 17 Nov 2026: broker freight quotes.** Sidebar "How is freight set?": daily
  hire rate (default), Worldscale (points and flat rate) or lump sum. Engine:
  `voyage.worldscale_freight_usd`, `voyage.implied_tce`, `arbitrage.cargo_tonnes`,
  `ArbInputs.freight_override_usd` (replaces built-up freight; demurrage then uses the quote's
  implied TCE), `ArbResult.implied_tce`; tornado flexes the quote instead of the hire rate.
  Decisions: Worldscale flat rates are paywalled, so the user types them; the boxes are
  pre-filled to reproduce the daily-hire freight for that exact voyage, so turning the option on
  changes nothing until real figures are typed. The ranking page and the hire grid always use the
  daily hire rate (a quote covers one voyage) and say so. 144 tests pass.
- **Stage 2, done 17 Nov 2026: freight-versus-spread grid** on the Scenarios page.
  `scenarios.margin_grid` re-runs the trade for every pairing of ship hire rate and price gap;
  `charts.margin_heatmap` draws it with the break-even line and a dot for the current inputs.
  Axis ranges are our choice (`costs.yaml`, `scenario_ranges`, `grid_*`). 130 tests pass.
- **Live-site fix, 17 Nov 2026:** after an upload the hosting service kept old calculation code
  in memory while showing the new pages (the grid chart errored). `app/main.py` now compares
  file times on each run and reloads the engine code when they change. If a page ever errors
  right after an upload, restart the app once from "Manage app" on the live site.
- **Owner checklist (figures to confirm by eye, then set `estimate: false` in the YAML):**
  1. Platts "Specifications Guide Global Freight": Suezmax/LR1 speeds 13 / 12.5 knots; Suezmax
     fuel 44 / 35 t/day (older ship) and 37 / 25 (eco, scrubber); port fuel 12 / 56-71 / 7.5;
     Corpus Christi Suezmax port cost $78,000.
  2. Baltic Exchange tanker emissions white paper: VLCC 12 knots, 58.5 t/day laden, 44 ballast.
  3. sea-distances.org: Houston-Mumbai via Suez (about 9,700 nm) and via the Cape (about
     11,900 nm); Houston-Rotterdam (about 5,000 nm).
- **Stage 0, done 17 Nov 2026.** Licence added; route map widened; owner checklist added.
  Independent review of the ports/ships/routes expansion (one reviewer completed before the
  session ended; each finding was re-checked by hand before fixing):
  1. Full cargoes were loaded at shallow ports with no warning. Added `laden_draught_ft` per ship
     and `channel_depth_ft` per load port (Corpus Christi 54 ft and Beaumont 40 ft published;
     Houston 45 ft and LOOP estimates) and a sidebar warning, `voyage.draught_warning`. The top-up
     cost itself is Stage 4.
  2. Paradip's route ended 85 nm past the port. `voyage.sea_route` now closes any route ending
     more than 25 nm from its port at the nearest approach (Paradip 25 nm shorter each way);
     tested for every port pair.
  3. Eco Suezmax spot hire note now says honestly that the cargo gets the fuel saving.
  4. Time-charter description no longer claims an overstatement that is false for the eco ship.
  5. Calm-market wording and test: "a few dollars a barrel" holds for the big ships only; the
     test now covers every ship and route with size-based bounds.
  6. Stale headline counts in this file. Not done from the plan: new README screenshots.
  134 tests pass.

## Expansion, 17 November 2026: more ports, ships and proper route handling

The owner asked for more load and discharge ports and more ship types.

- **Load ports added:** LOOP (the one US terminal that can fully load a VLCC) and Beaumont /
  Nederland. **Discharge ports added:** Paradip, Rotterdam, Singapore, Ningbo-Zhoushan, Ulsan.
  All new port costs are estimates (no free published figures found) and are flagged as such.
- **Ships added:** Panamax (0.5m barrels) and a modern eco, scrubber-fitted Suezmax that burns
  about 37 t/day loaded against 44. Each has a hire rate in all three freight markets.
- **Routes are now worked out per voyage.** The routing library reports whether the shortest
  path passes the Suez Canal. If it does, the tool offers Suez and Cape (Cape only for a VLCC).
  If it does not (US Gulf to Rotterdam), there is a single direct route with no toll, no canal
  day and no war-risk premium. Asking for a route that does not exist is an error, not a silent
  wrong answer.
- **Decision: stay a US crude export tool.** Every load port is US Gulf and the grade is WTI.
  Adding other load regions would need new grades and price sources; not done.
- **Decision: no Panama Canal route.** A VLCC cannot use it, a full Suezmax is at or beyond the
  draught limit, and there is no free source for the tanker toll, so the route is not offered
  rather than guessed. Recorded in `ports.yaml` under `routing`.
- **Sanity checks (calm market, fuel $600/t):** Houston-Rotterdam Aframax $2.60/bbl; LOOP-Ningbo
  VLCC via Cape $3.66/bbl; Houston-Rotterdam is 5,002 nm against about 5,000 in published tables.
- **Not yet done:** the case study and interview notes still discuss only the India route (by
  design). The new port costs and the Panamax figures are the weakest numbers in the tool.

The project now lives in `Desktop\crude-arb-project\arb-engine`, with its Python environment
set up there (`.venv`) and the tests and dashboard confirmed working from that folder.

Published: the code is on GitHub and the dashboard is deployed on Streamlit Community Cloud at
https://crude-arb-engine.streamlit.app (Python 3.13, main file `app/main.py`). It redeploys
itself whenever new code is pushed to GitHub.

## What was built

| Phase | Status | What it means in trading terms |
|---|---|---|
| 0 Setup | done | Project skeleton, Python packages, git. |
| 1 Voyage calculator | done | The tool knows how far it is (9,803 nm via Suez, 12,370 nm via the Cape), how long a Suezmax takes (36 days loaded), what it burns (44 t/day loaded) and what the Suez Canal charges (about $0.58m loaded, from the official tariff). Freight per barrel is broken into hire, fuel, ports, tolls and war risk. |
| 2 Prices | done | Daily Brent and WTI from the US EIA and monthly Dubai from the World Bank, no sign-up needed, cached locally. Bunker price is estimated from Brent (x 7.7) and labelled as an estimate. |
| 3 Cost stack and arb | done | Purchase price + freight + financing + insurance + transit loss + demurrage = landed cost, compared with destination value after a quality adjustment. Waterfall chart and ARB OPEN / ARB CLOSED verdict. |
| 4 Scenarios and history | done | Sliders for hire rate, bunker price, interest rate, spread and delay, plus a "Suez closed" switch. Tornado chart, break-even spread, and the model re-run over past prices with the caveats stated on the chart. |
| 5 Polish and publish | docs done, publishing pending | Landing page, Methodology page, case study, README with screenshots, interview notes, deployment guide. |

Phases 1 to 4 were written in one sitting and verified together at the end, then committed as
separate phase commits.

## Independent review, 15 November 2026: what it found and what was fixed

A line-by-line review confirmed 25 defects (several overlapping). None changed the headline
result for the starting case; most were about labels, wording and pages disagreeing. All fixed:

- **Dubai benchmark, pages disagreed.** With Dubai chosen, the Prices page showed a $13.08 spread
  (monthly Dubai against one day's WTI) while the Arbitrage page showed $0.63, and the fuel price
  jumped to an October-average figure ($954 a tonne instead of $709). Now every page builds its
  base case in one place: crude prices are same-month averages, the fuel price always uses the
  latest daily Brent, and Prices, Voyage, Arbitrage and Scenarios show the same spread ($0.63),
  fuel ($709) and freight ($25.02). A test checks this.
- **Dubai history mixed a month with a day.** The spread and "would past gaps have paid" charts
  set a flat monthly Dubai price against daily WTI, inventing gaps of -$22 to +$21 a barrel. They
  now compare monthly averages (true range over two years: -$7.62 to +$4.36) and are labelled
  "months", not "days".
- **Estimate flags and labels.** The time-charter and calm-market hire rates (published figures,
  but for another route or contract), the Platts and Baltic ship figures and Corpus Christi port
  cost (read only from search extracts), and the dollar-per-SDR rate are now flagged
  `estimate: true`: 67 of the 100 assumptions are estimates. README, the Start page, the
  ASSUMPTIONS header and the on-screen labels (Freight, Financing, Demurrage, the Scenarios
  sliders) now match the flags.
- **"How to read this" on the Arbitrage page** compared the raw price gap with costs and could
  have contradicted the verdict. It now uses the gap after the quality and differential
  adjustments, which less costs is exactly the margin.
- **Wrong or unsupported statements corrected:** the spot hire note ($20-25 a barrel corresponds
  to about $230,000-300,000 a day in the model, not $280,000-300,000; $300,000 is the top of the
  range); the case study's "37% surcharge alone almost cancels the time saved" (it is the whole
  toll, $1.04 a barrel against $1.01 of time saved; the surcharges are $0.25); "what the model
  would predict" (forecasting language, removed); the VLCC canal tonnage note (the figure is not
  used: a VLCC goes both ways round the Cape); the licence line in `DEPLOY.md`; the calm-market
  VLCC freight quoted here ($3.37, not $3.44); the time-charter setting now says it pairs an
  eco-ship hire rate with older-ship fuel figures.
- **Small engine and page fixes:** a mistyped route name (for example "Cape") is now rejected
  instead of being costed as the cheapest of all; the tornado's interest-rate bar is labelled
  with the cut actually made when the rate is below 2%; the "Suez closed" switch no longer leaves
  a "use Suez instead" bar; the Voyage page's fuel box no longer rounds the fuel price; the
  "Download the latest prices" button always downloads and the note gives the download time.

## Today's result (prices for 11 November 2026)

WTI $89.62, Brent $92.14, so the gross spread is $2.52. Estimated freight in today's crisis
tanker market is $25.02 a barrel. **ARB CLOSED by $23.64 a barrel.** Break-even spread: $26.20.
At the one-year time-charter rate the arb is closed by $7.47; at calm-market rates by $4.70.

## Decisions made along the way (and why)

- **Three freight-market settings instead of one.** Research showed the tanker market in late
  2026 is in crisis (Strait of Hormuz effectively closed; press reports of $20-25/bbl US-India
  freight versus $3-3.50 before). The brief's sanity check ("a few dollars a barrel") holds in the
  calm-market setting ($5-6 Suezmax, $3.37 VLCC); today's setting is deliberately much higher.
- **Price source: EIA spreadsheet downloads, not the EIA API or FRED.** They need no API key, so
  there is no `.env` to manage. FRED was unreachable from the build machine.
- **Dubai is monthly only.** No free daily Dubai price exists. When Dubai is chosen as the sell
  benchmark the tool compares monthly averages for the same month, on every page and in the
  historical view (one point per month). The fuel price always uses the latest daily Brent.
- **Round-voyage freight.** The cargo pays for the empty leg home, as Worldscale does.
- **Origin port default is Corpus Christi**, the one port with a published (Platts) port cost.
- **Red Sea war-risk premium added** to the Suez route (estimate), because without it the Suez
  versus Cape comparison is unrealistic.
- **Dashboard smoke test added** (`tests/test_dashboard.py`): loads every page for four different
  trade set-ups.
- **Git author is a placeholder** ("Arb Engine Owner"). Set the real name before publishing; see
  `docs/DEPLOY.md`.

## Known gaps and things to verify by eye

- Platts ship speeds, fuel figures and the Corpus Christi port cost, and the Baltic VLCC figures,
  were read from search-engine extracts, because the PDFs block automated download. They are now
  flagged `estimate: true` and shown as estimated. **Owner to do:** open the Platts Specifications
  Guide (Global Freight) and the Baltic tanker white paper and confirm 13.0 / 12.5 knots, 44 / 35
  t/day, $78,000 (Suezmax) and 12 knots, 58.5 / 44 t/day (VLCC). Once confirmed, set those records
  back to `estimate: false` and remove the "search-engine extract" wording.
- The bunker ratio (7.7) was calibrated against a Brent quote of $95.84 on 13 November 2026 whose
  source was not recorded and could not be re-confirmed. The note in `market.yaml` says so.
- The reference distances used in one test (9,700 and 11,900 nm Houston-Mumbai) are from memory of
  published tables; verify on sea-distances.org.
- The spot hire rate ($300,000 a day Suezmax) is an estimate anchored on press reports.
- README has two screenshots (arbitrage, voyage). A scenarios screenshot would be a nice addition.
- Not modelled: hedging and futures-curve structure, brokerage commission, VLCC reverse
  lightering, slow steaming. Listed on the Methodology page.

## How to run

Easiest: double-click `run_dashboard.bat` in the project folder. It opens the dashboard in the
browser (and sets up the Python packages first if they are missing).

By hand, in a terminal in the project folder (the first two lines are only needed once):

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app/main.py
```

Tests: `pytest`. Regenerate the assumptions document after editing any YAML:
`python -m engine.assumptions`.

Note: keep the project in a folder with a short path (for example `Documents\arb-engine`).
Windows fails to load one of the packages if the full path is very long.

## What comes next

1. Owner: follow `docs/DEPLOY.md` (GitHub, then Streamlit Community Cloud).
2. Optional improvements, in order of value: futures-curve and hedging effect; a second route or
   grade (add entries to `data/assumptions/ports.yaml` and `costs.yaml`); refresh the dated
   assumptions before interviews.
