# Glossary

Plain-language definitions of the trading and shipping terms used in this project, in the order
they come up.

## The trade

**Arbitrage ("arb")**
Profiting from the same thing being priced differently in two places. In physical oil: buy a
cargo where it is cheap, ship it to where it is dear, and keep the difference after costs. If the
difference covers the costs the "arb is open"; if not it is "closed".

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

**Time charter equivalent (TCE)**
A way to compare the two: take what a voyage charter pays, subtract fuel, port and canal costs,
and divide by the days taken. The result is the daily earnings the owner actually keeps, directly
comparable with a time charter hire rate. Published TCE figures are where our hire rates come from.

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
voyage loses value. This tool buys and sells at today's prices and does not model the curve; a
real trader would hedge with futures and this effect would show up.

**Hedging**
Taking an offsetting position in futures so that a move in the oil price during the voyage does
not change the profit. Not modelled here.
