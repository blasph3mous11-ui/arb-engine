# Interview notes

Figures quoted are from the model run on 15 November 2026 (prices for 11 November). Re-check them
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
within freight. Right now the Brent-WTI spread is about $2.50, and in today's tanker market,
with Hormuz effectively shut, my estimate of freight to India is about $25 a barrel, so the arb
is shut by more than $20. In a calm market the same voyage costs $5 to $6. The tool also shows
the Suez-versus-Cape decision: the Cape costs time, Suez costs cash, and there is a break-even
hire rate, around $86,000 a day on my numbers, above which the canal is worth paying for.

I was careful about data. Real freight rates and physical differentials are paywalled, so I used
public benchmarks, the published Suez tariff, and estimates that are labelled as estimates on
screen, each with a source. Every number is in a file with where it came from, and every
calculation has a test with a hand-worked answer."

## Ten likely questions, with honest answers

**1. Walk me through your freight calculation.**
Time-charter basis. Days = distance / (speed x 24) for the loaded and empty legs, plus two days in
each port, plus a day per canal transit. Cost = days x daily hire + fuel burned x bunker price +
port charges + canal tolls + war-risk premium. Divide by barrels loaded. For the base case: 9,803
nm, 70 days round trip, 2,707 tonnes of fuel; at $300,000 a day that is $21 of hire, $1.9 of fuel,
$1.0 of tolls, $0.8 of war risk and $0.2 of port costs per barrel: $25.02.

**2. Why charge the cargo for the ballast leg?**
Because that is how tanker freight is priced: Worldscale flat rates assume a round voyage back to
the load port. In reality owners triangulate, picking up another cargo nearby, so the true cost
can be lower. The model has a switch for it, and I would call the round-trip figure conservative.

**3. Where do your freight rates come from? Would a trader use them?**
No. A trader would use a broker quote or a Baltic/Platts assessment in Worldscale or lump sum for
the actual route. Those are paywalled. I use public figures: Fearnleys' one-year time charter
rates and Baltic TCE numbers reported in the press, and for today's spot market an estimate
anchored on press reports of $20-25 a barrel for US crude to India. It is flagged as an estimate.
The value of my approach is not the level, it is that you can see which driver moves the answer.

**4. Your origin price is WTI Cushing. That is not a Gulf Coast export price.**
Correct. The export grade is WTI at Houston (MEH) or WTI Midland, priced at a differential to
Cushing that reflects pipeline tariffs and export demand. Free data only gives Cushing, so I add
an estimated $1.00 and expose it. In a real desk model I would use the MEH assessment.

**5. How do you value the crude at destination?**
A benchmark (Brent daily, or Dubai monthly) plus a quality adjustment: $0.40 per degree of API
gravity and $1.00 per percentage point of sulphur, relative to the benchmark grade. That is a
rule of thumb. A refiner values crude by gross product worth: the yield of each product times its
price, less processing cost, for their specific refinery. And very light crude is not always
worth more. I would also need the actual delivered premium, which is negotiated and private.

**6. What is missing on the price side? What about hedging and curve structure?**
The model buys and sells at today's spot prices. A real cargo prices over a window (for example
five days around bill of lading), sells on a different window a month later, and the trader hedges
the gap with futures or swaps. The shape of the curve then matters: in contango the cargo gains
value at sea, in backwardation it loses. For a 36-day voyage that can be worth more than my
financing cost. It is the first thing I would add.

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

**10. If the arb is closed by $23, why does anyone ship crude at all?**
Three reasons the model does not capture. Traders with ships on long-term charter face a much
lower cost: at the July 2026 one-year rate of $69,500 a day my landed cost falls by about $16 a
barrel (still closed at today's spread, but far closer). Physical prices in a tight market trade
well above the benchmark, so the real delivered price in India may be much higher than Brent
flat. And term contracts, refinery needs and security of supply move cargoes that spot arithmetic
would not. When the spot arb is this far shut, though, spot flows do stop, and press reports say
US arrivals into India fell to zero this autumn.

## Extra questions worth preparing

- **What is demurrage and who pays it?** The daily penalty the charterer pays the owner when
  loading or discharging overruns the agreed laytime. In the model: delay days x (hire rate + idle
  fuel).
- **What is TCE?** Time charter equivalent: voyage revenue less fuel, port and canal costs,
  divided by days. It turns a voyage rate into a daily earning comparable with a time charter.
  My calculator runs that logic in reverse.
- **Why can a VLCC not use Suez loaded?** Draught: the canal allows about 20.1 m and a full VLCC
  draws about 22 m. It can go through empty, or part-discharge into the SUMED pipeline.
- **How would you extend it?** Curve structure and hedging; real freight assessments if I had
  access; more routes and grades (the ports, ships and grades are data files, so that is mostly
  adding entries); gross-product-worth valuation by refinery type.

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
| One day of delay at $300,000 a day on 1m barrels | about $0.30 a barrel |
