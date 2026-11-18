# Glossary

Plain-language definitions of the trading and shipping terms used in this project, in the order
they come up.

## The trade

**Arbitrage ("arb")**
Profiting from the same thing being priced differently in two places. In physical oil: buy a
cargo where it is cheap, ship it to where it is dear, and keep the difference after costs. If the
difference covers the costs the "arb is open"; if not it is "closed".

**Dated Brent**
The price of physical North Sea crude loading in the coming weeks, assessed daily by Platts from
a basket of grades (Brent, Forties, Oseberg, Ekofisk, Troll and, since 2023, WTI Midland). North
Sea cargoes are priced as Dated Brent plus or minus a differential. The tool uses the free EIA
Brent spot price in its place.

**Forties and Johan Sverdrup**
Two North Sea crudes. Forties (about 41 API, 0.65% sulphur) is a light sweet grade piped to
Scotland and loaded at Hound Point, and is part of the Dated Brent basket. Johan Sverdrup (about
29 API, 0.8% sulphur) is a heavier Norwegian grade loaded at Mongstad, popular with refiners in
Europe and Asia. In 2026 it traded at large premiums because Middle East sour crude was scarce.

**Benchmark (Brent, WTI, Dubai)**
A widely published reference price that other crudes are priced against. WTI is the US benchmark,
Brent the North Sea / Atlantic one, Dubai the Middle East one used for most oil sold into Asia.
Actual cargoes trade at "benchmark plus or minus a differential".

**Spread**
The gap between two prices. Here, mostly the destination benchmark minus the origin benchmark
(Brent minus WTI). The spread is the gross prize; freight and other costs come out of it.

**Differential**
The premium or discount of a specific cargo to its benchmark, reflecting location and quality.
Real differentials are negotiated privately and reported only by paid services.

**FOB (free on board)**
A price for oil delivered onto the ship at the load port. The buyer arranges and pays for the
shipping. Our purchase price is an FOB price.

**Landed cost (delivered cost)**
What a barrel has cost by the time it arrives: purchase price plus freight, financing, insurance,
losses and delays.

**Margin**
Sale value minus landed cost. Quoted per barrel and in total dollars for the cargo.

**Break-even spread**
The price gap at which the margin is exactly zero. If the actual spread is wider, the arb is open.

## Crude quality

**API gravity**
A measure of how light or heavy a crude is. Higher numbers mean lighter oil, which yields more
petrol and diesel and is usually worth more. WTI is about 40, Dubai about 31.

**Sweet and sour (sulphur content)**
"Sweet" crude has little sulphur (under about 0.5%), "sour" has more. Sulphur has to be removed in
refining, so sour crude sells at a discount.

**Quality differential**
The price adjustment for shipping a grade that is lighter/heavier or sweeter/sourer than the
benchmark it is sold against. We use a simple rule: a dollar value per degree of API gravity and
per percentage point of sulphur.

**Barrels and tonnes**
Oil is priced in barrels (159 litres, a volume) but ships are sized in tonnes (a weight). The
conversion depends on the oil's density: light crude is roughly 7.6 barrels to the tonne.

## Ships and voyages

**Panamax**
The smallest crude tanker in this tool, about 0.5 million barrels (60,000-80,000 tonnes
deadweight). Named for the old Panama Canal locks it was built to fit. Its size class is also
called LR1.

**Eco ship and scrubber**
An "eco" ship is a modern design that burns noticeably less fuel at the same speed: about 37
tonnes a day for a Suezmax against 44 for an older one. A scrubber is equipment that cleans the
exhaust so the ship may burn cheaper high-sulphur fuel. The tool models the lower fuel use but
prices all fuel at the low-sulphur estimate, so it understates the scrubber's benefit.

**LOOP and reverse lightering**
LOOP, the Louisiana Offshore Oil Port, is a deep-water terminal 18 miles off Louisiana and the
one US facility that can fully load a VLCC. Ports such as Houston and Corpus Christi are too
shallow, so a VLCC loading there is topped up offshore from smaller ships. That ship-to-ship
top-up is called reverse lightering; the tool charges an estimated $1.00 for each barrel that has
to be loaded offshore, and shows a warning when it applies.

**Direct route**
A voyage with no canal choice to make, such as the US Gulf to Rotterdam straight across the
Atlantic. No canal toll, no canal day, no Red Sea war-risk premium.

**Aframax, Suezmax, VLCC**
The three main crude tanker sizes. An Aframax carries about 0.75 million barrels, a Suezmax about
1 million (the largest ship that can pass the Suez Canal fully loaded), and a VLCC ("very large
crude carrier") about 2 million.

**Deadweight (dwt)**
The total weight a ship can carry: cargo plus fuel, water and stores. A Suezmax is about 158,000
tonnes deadweight.

**Laden and ballast**
A ship is "laden" when carrying cargo and "in ballast" when sailing empty (carrying sea water for
stability). The empty return trip earns nothing, so the cargo has to pay for it.

**Knot and nautical mile**
A nautical mile is 1.852 km. A knot is one nautical mile per hour. A tanker at 13 knots covers
312 nautical miles a day.

**Slow steaming and the cheapest speed**
Sailing slower than a ship's normal speed to save fuel. Engine fuel per day rises roughly with
the cube of speed (10% slower burns about 27% less a day), but every extra day costs the ship's
hire and the interest on the cargo. The cheapest speed balances the two: when ships are dear (as
in late 2026) it pays to sail fast; when ships are cheap and fuel dear, to slow down. In steep
contango a hedged cargo even earns money by taking longer.

**Trade recap**
A short summary of a deal (cargo, ports, ship, prices, costs, result) that traders send to
colleagues and counterparties. The Arbitrage page downloads one as a spreadsheet.

**Bunkers**
Ship fuel. Usually the second-largest voyage cost after the ship itself. "VLSFO" is very low
sulphur fuel oil, the standard grade since 2020.

**Time charter and hire rate**
Hiring a ship by the day, like renting a van: the charterer pays a daily "hire" and also buys the
fuel and pays port and canal costs. Our voyage calculator is built this way.

**Voyage charter and Worldscale**
The other way to hire a ship: pay one price to move one cargo from A to B, with the owner paying
fuel and port costs. Tanker voyage rates are quoted in "Worldscale" points, a percentage of a
published reference rate for each route. Worldscale rates assume a round trip, which is why we
charge the cargo for the empty leg home.

**Flat rate (Worldscale)**
The reference freight for one specific route, in dollars per tonne, published once a year by the
Worldscale Association for a standard ship. Brokers quote a percentage of it: WS 100 is the flat
rate, WS 150 is one and a half times it. Freight = points / 100 x flat rate x tonnes of cargo.
Flat rates are sold by subscription, so the tool asks you to type the one for your route.

**Address commission and brokerage**
Percentages taken out of the freight in a voyage charter. The address commission (often 2.5%) is
returned to the charterer, so a quote costs the charterer a little less than its headline. The
brokerage (often 1.25%) is paid by the owner to the brokers. Both reduce what the owner keeps.

**EU ETS (Emissions Trading System)**
The EU's carbon market. Since 2024 ships calling at EU ports must buy allowances for their CO2:
all of it at berth and on voyages between EU ports, half of it on voyages to or from outside the
EU. Coverage was phased in (40% of 2024 emissions, 70% of 2025) and is 100% from 2026. Charter
contracts usually pass the cost to the charterer.

**Lump sum**
A single dollar figure for the whole voyage, used instead of Worldscale for some routes and
cargoes, such as US Gulf exports to Asia.

**Time charter equivalent (TCE)**
A way to compare the two: take what a voyage charter pays, subtract fuel, port and canal costs,
and divide by the days taken. The result is the daily earnings the owner actually keeps, directly
comparable with a time charter hire rate. Published TCE figures are where our hire rates come from.
When you type a broker's quote, the Voyage page works out the TCE it implies, so you can see
whether a quote is generous or thin compared with the market hire rate.

**Freight**
The cost of shipping, usually quoted in dollars per barrel or per tonne of cargo.

**Canal toll and SCNT**
The fee for passing the Suez Canal, charged on a sliding scale per "Suez Canal Net Ton" (a
measure of the ship's volume) and priced in SDR, the IMF's basket currency. About $0.6 million
for a loaded Suezmax in late 2026.

**Demurrage**
The daily penalty a charterer pays the shipowner when loading or discharging takes longer than
the agreed time ("laytime"). It roughly matches what the ship could be earning elsewhere.

**War-risk premium**
Extra insurance charged for sailing through a dangerous area, as a percentage of the ship's
value. Since late 2023 this has applied to the southern Red Sea, on the way to and from Suez.

## Money

**SOFR**
The Secured Overnight Financing Rate, the main US dollar benchmark interest rate. Trade loans are
priced at "SOFR plus a margin".

**Financing cost**
A cargo is worth tens of millions of dollars and is paid for long before the buyer pays.
The trader borrows the money in between and the interest is a cost of the trade. The longer the
voyage and the higher the oil price, the bigger it is.

**Letter of credit (LC)**
A bank's promise to pay the seller once shipping documents are presented. It lets a seller ship to
a buyer it does not know well, and banks lend against it. We do not model LC fees separately;
they would sit inside the financing margin.

**Transit loss (ocean loss)**
The small shortfall between the volume measured at loading and at discharge, from evaporation,
oil left clinging to tanks, and measurement differences.

**Contango and backwardation**
The shape of the futures curve. Contango: later deliveries cost more than prompt ones, so a cargo
gains value while at sea (or in storage). Backwardation: later deliveries are cheaper, so a long
voyage loses value. The tool shows this as the futures curve effect, using the gap between the
first two futures months that you type in the sidebar.

**Hedging**
Taking an offsetting position in futures so that a move in the oil price during the voyage does
not change the profit. The trader sells futures when the cargo is bought and buys them back when
it is sold. The tool models one consequence of this, the futures curve effect: a hedged cargo
gains about the gap between the first two futures months for each month at sea in contango, and
loses it in backwardation. You type today's gap in the sidebar.
