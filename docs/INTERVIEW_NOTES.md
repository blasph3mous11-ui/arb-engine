# Interview notes

Figures quoted are from the model run on 19 November 2026 (prices for 17 November, freight
for the week to 13 November). Re-check them
on the dashboard before an interview; prices move every day.

## The two-minute explanation

"I built a tool that answers the question a physical crude trader asks every morning: if I buy a
cargo here and ship it there, do I make money, and what drives the answer?

The starting case is a million barrels of US Gulf Coast crude on a Suezmax to the west coast of
India. The tool does two things. First, a voyage calculator: it takes the sea distance, the ship's
speed and fuel consumption, and works out how many days the ship is tied up and what that costs in
hire, bunkers, port charges and canal tolls. Second, an arbitrage engine: it takes the price at
origin, adds freight, financing, insurance and transit loss to get a landed cost, and compares
that with the value at destination after a quality adjustment. The difference is the margin, and
the tool says whether the arb is open or closed.

What I learned building it is how dominant freight is, and how dominant the ship's daily rate is
within freight. Right now the Brent-WTI spread is about $3.40. With Hormuz effectively shut,
freight to India was about $25 a barrel at October's peak; tanker rates have since roughly halved
and it is now about $14.60, but the arb is still shut by about $12. In a calm market the same
voyage costs $5 to $6. The tool also shows
the Suez-versus-Cape decision: the Cape costs time, Suez costs cash, and there is a break-even
hire rate, around $86,000 a day on my numbers, above which the canal is worth paying for.

From there I built it out the way a desk would use it. It covers four US Gulf terminals and two
North Sea ones, seven discharge ports, five ship sizes and five crude grades. A ranking page costs
one cargo to every destination, the netback view. You can type a broker's Worldscale or lump-sum
quote and see what it pays the owner per day. It includes the costs people forget: reverse
lightering at shallow US ports, EU carbon on voyages into Rotterdam, and the futures-curve effect
on a hedged cargo.

I was careful about data. Real freight rates and physical differentials are paywalled, so I used
public benchmarks, the published Suez tariff, and estimates that are labelled as estimates on
screen, each with a source. Every number is in a file with where it came from, and every
calculation has a test with a hand-worked answer."

## Ten likely questions, with honest answers

**1. Walk me through your freight calculation.**
Time-charter basis. Days = distance / (speed x 24) for the loaded and empty legs, plus two days in
each port, plus a day per canal transit. Cost = days x daily hire + fuel burned x bunker price +
port charges + canal tolls + war-risk premium. Divide by barrels loaded. For the base case: 9,803
nm, 70 days round trip, 2,707 tonnes of fuel; at $151,000 a day that is $10.58 of hire, $1.94 of
fuel, $1.04 of tolls, $0.80 of war risk and $0.23 of port costs per barrel: $14.59.

**2. Why charge the cargo for the ballast leg?**
Because that is how tanker freight is priced: Worldscale flat rates assume a round voyage back to
the load port. In reality owners triangulate, picking up another cargo nearby, so the true cost
can be lower. The model has a switch for it, and I would call the round-trip figure conservative.

**3. Where do your freight rates come from? Would a trader use them?**
No. A trader would use a broker quote or a Baltic/Platts assessment in Worldscale or lump sum for
the actual route. Those are paywalled. I use public figures: Fearnleys' one-year time charter
rates, and for the spot market the Baltic Exchange's weekly Atlantic assessments reported in the
press: $151,000 a day for a Suezmax (West Africa-Europe), $72,000 for an Aframax (US Gulf-Europe)
and $248,000 for a VLCC (US Gulf-China), all for the week to 13 November. Every hire rate in the
tool is flagged as an estimate, including the published ones, because none of them is for this
exact route. As a check: at that $248,000 a day the tool builds a US Gulf-China VLCC voyage at
about $31m, against the Baltic's published lump sum of $33.8m, about 9% lower, which I would put
down to commissions, port charges and the Baltic's exact route assumptions.
The value of my approach is not the level, it is that you can see which driver moves the answer.
If you have a real quote, you can type it in: Worldscale points times the route's flat rate
(which you type too, because flat rates are sold by subscription) times the cargo's tonnes, or a
lump sum. The tool then shows the owner's daily earnings (TCE) after commissions. Typing $15m for
the base voyage gives net freight of $14.62 a barrel to the charterer and about $149,000 a day to
the owner.

**4. Your origin price is WTI Cushing. That is not a Gulf Coast export price.**
Correct. The export grade is WTI at Houston (MEH) or WTI Midland, priced at a differential to
Cushing that reflects pipeline tariffs and export demand. Free data only gives Cushing, so each
grade carries an estimated differential you can edit: WTI Midland +$1.30 (Argus, March 2026),
Mars +$1.50 (May 2026). They are dated snapshots, and this year they moved a lot: Mars went from
around $13 over WTI in March to about $1.50 by May. North Sea cargoes are priced the same way off
Brent: Forties at Dated Brent, Johan Sverdrup at about +$6 (Platts, October-November 2026). In a
real desk model I would use the Platts or Argus assessments.

**5. How do you value the crude at destination?**
A benchmark (Brent daily, or Dubai monthly) plus a quality adjustment: $0.40 per degree of API
gravity and $1.00 per percentage point of sulphur, relative to the benchmark grade. That is a
rule of thumb. A refiner values crude by gross product worth: the yield of each product times its
price, less processing cost, for their specific refinery. And very light crude is not always
worth more. I would also need the actual delivered premium, which is negotiated and private.

**6. What is missing on the price side? What about hedging and curve structure?**
A real cargo prices over a window (for example five days around bill of lading), sells on a
different window a month later, and the trader hedges the gap with futures or swaps. The shape of
the curve then matters: in contango the hedged cargo gains value at sea, in backwardation it
loses. The tool models that one effect: you type the gap between the first two futures months,
and it adds that gap times the months the cargo is financed. A $0.60 contango over 34 days is
worth +$0.68 a barrel. The free EIA futures series stopped in April 2024, so I show its 1985-2024
history for scale: half of all months were within about 35 cents either way, with extremes of
+$7.38 in April 2020 and -$2.70 in July 2022. What I still do not model: pricing windows, basis
risk between the futures and the destination benchmark, and the cost of the hedge.

**7. How did you get the Suez Canal toll?**
From the canal authority's published tariff (Circular 7/2023, effective January 2024): a sliding
scale in SDR per Suez Canal Net Ton. For 81,000 SCNT loaded: 5,000 x 11.04 + 5,000 x 7.82 + 10,000
x 5.91 + 20,000 x 2.93 + 30,000 x 2.53 + 11,000 x 2.17 = 311,770 SDR. Add the 37% surcharge in
force since July 2026 and convert at $1.36: about $581,000. The ship's actual SCNT is on its
canal certificate; 81,000 is my estimate. It excludes tugs, pilotage extras and agency fees.

**8. Suez or Cape: how does a trader actually decide?**
On my numbers it is a break-even on the daily hire rate: about $86,000 a day including a war-risk
premium, $32,000 without. Below that the Cape is cheaper. In practice it is not only arithmetic:
the owner has to agree to the routing, crew and insurers may refuse, and a longer voyage changes
your price exposure and delivery window. The model prices risk only through an estimated premium.

**9. What is the biggest weakness of the model?**
The freight level. The whole answer swings on the daily hire rate, which I cannot observe for
this route. Second, the historical view holds freight constant, when in reality freight rises
exactly when the arb is wide, because everyone wants a ship; so that chart overstates how often
the arb was open. I say so on the chart. Third, the quality and destination differentials are
rules of thumb.

**10. If the arb is closed by $12, why does anyone ship crude at all?**
Three reasons the model does not capture. Traders with ships on long-term charter face a much
lower cost: at the July 2026 one-year rate of $69,500 a day my landed cost falls by about $5.70 a
barrel (still closed at today's spread, but far closer). Physical prices in a tight market trade
well above the benchmark, so the real delivered price in India may be much higher than Brent
flat. And term contracts, refinery needs and security of supply move cargoes that spot arithmetic
would not. When the spot arb is this far shut, though, spot flows do stop, and press reports say
US arrivals into India fell to zero this autumn.

## Extra questions worth preparing

- **Would the ship not slow down to save fuel?** Only if the ship is cheap. Engine fuel rises
  roughly with the cube of speed, but every day also costs hire and interest on the cargo, so the
  tool finds the speed where the two balance. At $151,000 a day it says sail flat out (15 knots,
  the top of the range I allow): the round trip falls from 70 to 60 days and freight from $14.59 to
  $13.64, improving the margin by about $1 a barrel. At the calm 2024 rate of $30,000 the cheapest
  speed is about 12.8 knots loaded, almost exactly the published assessment speed, so the choice is
  worth a fraction of a cent. In contango it pays a hedged cargo to dawdle: at +$0.50 a month the
  loaded leg slows to about 11 knots. The cube rule overstates savings well below normal speed
  (Adland, Cariou and Wolff, 2020, from tanker noon reports), which I flag on the page.

- **What is demurrage and who pays it?** The daily penalty the charterer pays the owner when
  loading or discharging overruns the agreed laytime. In the model: delay days x (hire rate + idle
  fuel).
- **What is TCE?** Time charter equivalent: voyage revenue less fuel, port and canal costs,
  divided by days. It turns a voyage rate into a daily earning comparable with a time charter.
  My calculator runs that logic in reverse.
- **Why can a VLCC not use Suez loaded?** Draught: the canal allows about 20.1 m and a full VLCC
  draws about 22 m. It can go through empty, or part-discharge into the SUMED pipeline.
- **Who pays the commissions?** In a voyage charter they come out of the freight. The address
  commission (often 2.5%) goes back to the charterer, so a quote costs the charterer a little less
  than its headline; the brokerage (often 1.25%) is paid by the owner. Adding them as an extra
  cost would double-count, so the tool applies them only to a typed-in quote.
- **Why does a VLCC from Houston cost more than one from LOOP?** Houston's channel is about 45 ft
  and a full VLCC draws about 70, so it leaves part-loaded and is topped up offshore by smaller
  ships (reverse lightering). About 60% of the cargo has to go on offshore, and at an estimated
  $1.00 per offshore barrel that is about 60 cents a barrel of cargo, in line with a 2018 Columbia
  University range of 50-75 cents. A Suezmax at Houston only needs a little topping up, about 17
  cents. LOOP is offshore deep water, so a VLCC loads in full there.
- **What does EU carbon add?** Since 2026 ships pay for 100% of CO2 under the EU scheme: half of
  a voyage into or out of the EU, all of a voyage between EU (or Norwegian) ports, all of the fuel
  at berth in those ports. On a Suezmax from Houston to Rotterdam it is about 20 cents a barrel.
  The UK is outside the EU scheme; its own scheme covers only domestic voyages for now.
- **Where should the cargo go?** The ranking page costs the same cargo to every port by its
  better route. Today Rotterdam is the least bad (-$4.63 on the base case) because it is the
  shortest voyage; Ulsan is the worst (-$17.19). All ports are valued against one benchmark, so
  the ranking shows the effect of the voyage only, not of local premiums.
- **How would you extend it?** Real freight and physical price assessments if I had access;
  valuation by the products a refinery makes (gross product worth), which needs yield data I
  could not get free; pricing windows and basis risk on the hedge; a Panama Canal option for
  smaller ships once I can source the toll.

## Numbers to have in your head

| | |
|---|---|
| Suezmax cargo | about 1 million barrels (130,000 tonnes) |
| VLCC cargo | about 2 million barrels |
| US Gulf to west coast India | about 9,800 nm via Suez, 12,400 nm via the Cape |
| Voyage time loaded | about 36 days via Suez, 44 via the Cape |
| Suezmax fuel burn | about 44 tonnes a day loaded, 35 empty |
| Suez toll, loaded Suezmax | about $0.58 million including the 37% surcharge |
| Barrels per tonne, light crude | about 7.6 |
| Financing a $90m cargo for 36 days at 5.9% | about $0.54 a barrel |
| One day of delay at $151,000 a day on 1m barrels | about $0.15 a barrel |
| Spot hire, week to 13 Nov 2026 (Baltic, Atlantic) | VLCC $248,000, Suezmax $151,000, Aframax $72,000 a day |
| North Sea to west coast India | about 6,600 nm via Suez |
| Quality rule ($0.40 per API degree, $1 per sulphur point) vs Brent | WTI Midland +$1.65, Mars -$5.04, Johan Sverdrup -$4.28 |
| Reverse lightering (estimate) | about $0.60 a barrel for a VLCC at Houston, $0.17 for a Suezmax |
| North Sea crude sold against Brent | keeps its differential; Forties to Rotterdam costs about $1.07 a barrel to deliver (calm market) |
| EU carbon, US Gulf to Rotterdam, Suezmax | about $0.20 a barrel |
| Suez or Cape break-even hire rate | about $86,000 a day with war-risk cover, $32,000 without |
