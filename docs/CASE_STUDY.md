# Case study: Suez or Cape? What the Red Sea diversions do to a US crude cargo for India

*Model run on 15 November 2026 with prices for 11 November 2026 (WTI $89.62, Brent $92.14, US EIA).
Re-checked on 17 November 2026 after the tool gained more ports, grades and cost lines: none of
them apply to this voyage (Corpus Christi takes a full Suezmax, and India is outside the EU carbon
scheme), so every figure below is unchanged.
All model figures use public benchmarks and documented estimates, not traded freight data.*

## What happened

In November 2023 Houthi forces in Yemen began attacking commercial ships in the southern Red Sea
and the Bab el-Mandeb strait, the southern gateway to the Suez Canal. Shipowners responded by
sending ships the long way round Africa.

- UNCTAD estimated in January 2024 that weekly Suez Canal transits had fallen **42%** in two
  months. ([UNCTAD](https://unctad.org/news/red-sea-black-sea-and-panama-canal-unctad-raises-alarm-global-trade-disruptions))
- Oil flows through Bab el-Mandeb averaged **4.0 million barrels a day** in the first eight
  months of 2024, down from **8.7 million** in 2023, while flows round the Cape of Good Hope rose
  from **6.0 to 9.2 million** barrels a day (Vortexa data, reported by the
  [US EIA, 11 October 2024](https://www.eia.gov/todayinenergy/detail.php?id=63446)).
- The EIA put the detour from the Arabian Sea to Europe at **about 15 days longer**
  ([EIA, June 2024](https://www.eia.gov/todayinenergy/detail.php?id=62263)).
- Suez Canal Authority revenue fell from a record **$10.25 billion in 2023 to $3.99 billion in
  2024** ([Africanews, April 2025](https://www.africanews.com/2025/04/17/egypts-revenue-from-the-suez-canal-plunged-sharply-in-2024//)).

Three years on the picture is mixed. Lloyd's List reported in November 2026 that crude tanker
volumes through Suez are back above pre-crisis levels, but the southern Red Sea is still rated a
substantial risk ([Lloyd's List Intelligence, Red Sea Brief, 12 November 2026](https://www.lloydslistintelligence.com/resources/blog/red-sea-brief---12-november-2026)).
Meanwhile the canal has added surcharges: laden crude tankers have paid **37% on top of normal
dues** since 15 July 2026 ([Shipping Australia](https://www.shippingaustralia.com.au/suez-canal-authority-announces-hike-in-surcharges)).

So a trader moving US crude to India faces a real choice on every cargo. The tool makes the
trade-off explicit.

## The trade-off in one sentence

**The Cape costs time; Suez costs cash.** Going round the Cape means the ship is hired for longer
and burns more fuel. Going through Suez means paying canal tolls and a war-risk premium. Which is
cheaper depends on how expensive the ship is per day.

## What the model says

One million barrels, Corpus Christi to Sikka on a Suezmax, round-voyage basis.

| | Via Suez | Via Cape | Difference |
|---|---|---|---|
| Distance, one way | 9,803 nm | 12,370 nm | +2,567 nm (+26%) |
| Days loaded | 36.4 | 43.6 | +7.2 |
| Days ship is tied up (round trip) | 70.1 | 84.9 | +14.8 |
| Fuel burned | 2,707 t | 3,354 t | +647 t |
| Canal tolls (published tariff, estimated tonnage; loaded out, empty back) | $1.04m | none | |
| War-risk premium (estimated, two passages) | $0.80m | none | |

The canal tolls apply the Suez Canal Authority's published tariff to an estimated canal tonnage of
81,000 tons (real Suezmaxes range from about 74,000 to 83,000): 311,770 SDR loaded, plus the 37%
surcharge, at about $1.36 per SDR, is about $581,000 one way. The ship's speeds and fuel use are
figures reported from the Platts freight guide that have not yet been confirmed against the
document itself, so the days and fuel above are treated as estimates too.

Now the same voyage under three freight markets (fuel estimated at $709 a tonne):

| Freight market | Ship hire per day (estimated) | Landed cost via Suez | Landed cost via Cape | Cheaper route |
|---|---|---|---|---|
| Calm market (late 2024 reference) | $30,000 | $97.49 | $96.66 | **Cape** by $0.83/bbl |
| One-year time charter (broker assessment, July 2026) | $69,500 | $100.26 | $100.02 | **Cape** by $0.24/bbl |
| Spot market, crisis (Oct-Nov 2026, estimated) | $300,000 | $116.43 | $119.59 | **Suez** by $3.16/bbl |

Landed cost includes financing, so the extra week at sea via the Cape also costs about $0.11 a
barrel in interest on a $90 million cargo.

## The insight: a break-even hire rate

The model can be solved for the hire rate at which the two routes cost the same:

- **About $86,000 a day** with the war-risk premium included.
- **About $32,000 a day** if there were no war risk at all, tolls only.

Below the break-even, time is cheap and it pays to avoid the tolls and sail round. Above it, every
day saved is worth more than the tolls. Three things follow:

1. **In a calm market the canal is not obviously worth it for this route.** With ships at $30,000
   a day, the canal tolls (about $1.04 a barrel round trip, of which the surcharges are about
   $0.25) roughly cancel the value of the time saved (about $1.01 a barrel), before any war-risk
   premium. Without the surcharges Suez would be about $0.22 a barrel cheaper than the Cape; with
   them it is break-even. The surcharges (37% loaded, 27% empty) make more sense when ships are
   expensive, as they are now.
2. **The security premium moves the answer a lot.** War risk nearly triples the break-even hire
   rate. A fall in the premium would pull cargoes back to the canal long before the route was
   "safe" in any absolute sense. That fits the 2026 pattern of tankers returning while risk
   ratings stay elevated.
3. **In today's market the route choice is second-order.** At $300,000 a day Suez saves about $3 a
   barrel, but the arb is shut by more than $23 either way, because the Brent-WTI gap is only
   $2.52. The binding constraint is the cost of the ship, not the route. Press reports say US
   crude arrivals into India fell to zero in the autumn of 2026
   ([ETI weekly tanker report](https://etint.substack.com/p/eti-tmwo-week-44-2026-delayed-report)),
   which is consistent with an arb this far shut on the model's estimated costs.

## What this analysis leaves out

- The war-risk premium (0.5% of an estimated $80 million hull value per passage) is our estimate.
  Real quotes are private and can move daily; some insurers would decline cover.
- Hire rates are estimates: public broker and press figures for other routes or contracts, or
  our own figures, not the rate for this route on this day.
- Risk is priced only through the premium. A trader would also weigh crew safety, the chance of
  delay or damage, and whether the shipowner will accept the routing at all.
- The longer Cape voyage exposes the cargo to price moves for an extra week. With hedging and a
  futures curve this would add a small gain or loss that the model does not capture.
- Ships can slow down or speed up to trade fuel against time; the model uses fixed speeds.

## Reproduce it

Open the dashboard, pick **Suezmax**, switch **Route** between Suez and Cape, and step through the
three **Freight market** settings. The **Voyage calculator** page shows the two routes side by
side; **Scenarios & history** has the "Suez Canal closed" switch and the hire-rate slider for
finding the break-even yourself.
