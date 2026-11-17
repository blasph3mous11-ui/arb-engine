"""All the charts, in one place so they share one look.

Display code only: every number drawn here was calculated in engine/.
"""

import plotly.graph_objects as go

# One fixed palette. Blue and orange tell series apart; green and red are
# reserved for "arb open" and "arb closed".
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
GOOD, CRITICAL = "#0ca30c", "#d03b3b"
INK, SECONDARY, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, SURFACE = "#e1e0d9", "#c3c2b7", "#fcfcfb"


def _style(fig: go.Figure, height: int = 380, y_title: str = "", x_title: str = "") -> go.Figure:
    fig.update_layout(
        height=height, paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        font=dict(color=SECONDARY, size=13), margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(color=SECONDARY)),
        hoverlabel=dict(bgcolor="white", font=dict(color=INK)), bargap=0.35,
    )
    fig.update_xaxes(title=x_title, gridcolor=GRID, linecolor=AXIS, zeroline=False,
                     tickfont=dict(color=MUTED))
    fig.update_yaxes(title=y_title, gridcolor=GRID, linecolor=AXIS, zeroline=False,
                     tickfont=dict(color=MUTED))
    return fig


def route_map(routes: dict, ports: list[dict]) -> go.Figure:
    """World map with one line per route. routes = {label: [(lon, lat), ...]}."""
    fig = go.Figure()
    for (label, points), colour in zip(routes.items(), [BLUE, ORANGE]):
        fig.add_trace(go.Scattergeo(
            lon=[p[0] for p in points], lat=[p[1] for p in points], mode="lines",
            line=dict(width=2, color=colour), name=label, hoverinfo="name"))
    fig.add_trace(go.Scattergeo(
        lon=[p["longitude"] for p in ports], lat=[p["latitude"] for p in ports],
        text=[p["name"] for p in ports], mode="markers+text", textposition="top center",
        marker=dict(size=9, color=INK, line=dict(width=2, color=SURFACE)),
        textfont=dict(color=INK), showlegend=False, hoverinfo="text"))
    fig.update_geos(projection_type="natural earth", showland=True, landcolor="#f0efec",
                    showocean=True, oceancolor=SURFACE, showcountries=True, countrycolor=GRID,
                    coastlinecolor=AXIS, lataxis_range=[-50, 62], lonaxis_range=[-140, 150])
    fig.update_layout(height=420, margin=dict(l=0, r=0, t=30, b=0), paper_bgcolor=SURFACE,
                      legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0))
    return fig


def cost_bars(per_bbl: dict) -> go.Figure:
    """Horizontal bars: freight cost per barrel by component, largest on top."""
    items = sorted(((k, v) for k, v in per_bbl.items() if v > 0), key=lambda kv: kv[1])
    fig = go.Figure(go.Bar(
        x=[v for _, v in items], y=[k for k, _ in items], orientation="h", marker_color=BLUE,
        text=[f"${v:,.2f}" for _, v in items], textposition="outside", textfont=dict(color=INK),
        hovertemplate="%{y}: $%{x:,.2f} per barrel<extra></extra>", cliponaxis=False))
    fig = _style(fig, height=60 + 50 * len(items), x_title="USD per barrel")
    # Leave room on the right for the value labels.
    fig.update_xaxes(range=[0, max(v for _, v in items) * 1.3])
    return fig


def price_lines(prices, columns: dict) -> go.Figure:
    """Daily price history. columns = {column name: label}."""
    fig = go.Figure()
    for (column, label), colour in zip(columns.items(), [BLUE, ORANGE, AQUA]):
        series = prices[column].dropna()
        fig.add_trace(go.Scatter(x=series.index, y=series.values, mode="lines", name=label,
                                 line=dict(width=2, color=colour),
                                 hovertemplate="%{x|%d %b %Y}: $%{y:,.2f}<extra>" + label + "</extra>"))
    fig.update_layout(hovermode="x unified")
    return _style(fig, y_title="USD per barrel")


def single_line(series, label: str, zero_label: str | None = None) -> go.Figure:
    """One series over time, with an optional marked zero line."""
    fig = go.Figure(go.Scatter(x=series.index, y=series.values, mode="lines", name=label,
                               line=dict(width=2, color=BLUE),
                               hovertemplate="%{x|%d %b %Y}: $%{y:,.2f}<extra></extra>"))
    if zero_label:
        fig.add_hline(y=0, line=dict(color=INK, width=1), annotation_text=zero_label,
                      annotation_position="bottom right", annotation_font_color=SECONDARY)
    return _style(fig, y_title="USD per barrel")


def waterfall(result) -> go.Figure:
    """Purchase price, each cost stacked on top, landed cost, margin, sale value."""
    labels, bases, heights, colours, texts = [], [], [], [], []

    def add(label, base, height, colour, text):
        labels.append(label); bases.append(base); heights.append(height)
        colours.append(colour); texts.append(text)

    add("Purchase price", 0, result.purchase_price, BLUE, f"${result.purchase_price:,.2f}")
    running = result.purchase_price
    for name, cost in result.cost_stack.items():
        if cost > 0:
            add(name, running, cost, ORANGE, f"+${cost:,.2f}")
            running += cost
    add("Landed cost", 0, result.landed_cost, BLUE, f"${result.landed_cost:,.2f}")
    margin = result.margin_per_bbl
    add("Margin", min(result.landed_cost, result.sale_value), abs(margin),
        GOOD if margin > 0 else CRITICAL, f"{'+' if margin > 0 else '-'}${abs(margin):,.2f}")
    add("Sale value", 0, result.sale_value, BLUE, f"${result.sale_value:,.2f}")

    fig = go.Figure(go.Bar(x=labels, y=heights, base=bases, marker_color=colours, text=texts,
                           textposition="outside", textfont=dict(color=INK), cliponaxis=False,
                           hovertemplate="%{x}: %{text} per barrel<extra></extra>"))
    # Start the axis just below the cheapest level so the cost steps are visible.
    top = max(result.landed_cost, result.sale_value)
    floor = min(result.purchase_price, result.sale_value)
    pad = max((top - floor) * 0.6, 2)
    fig.update_yaxes(range=[max(floor - pad, 0), top + pad * 0.4])
    return _style(fig, height=430, y_title="USD per barrel")


def tornado(rows: list[dict]) -> go.Figure:
    """One bar pair per driver, showing the margin if that input is lower or higher."""
    rows = rows[::-1]  # plotly draws the first row at the bottom
    base = rows[0]["base"]
    names = [r["driver"] for r in rows]
    fig = go.Figure()
    for side, colour, legend in [("low", BLUE, "Input lower"), ("high", ORANGE, "Input higher")]:
        fig.add_trace(go.Bar(
            y=names, x=[r[f"{side}_margin"] - base for r in rows], base=base, orientation="h",
            marker_color=colour, name=legend,
            text=[r[f"{side}_label"] if r[f"{side}_label"] != "no change" else "" for r in rows],
            textposition="outside", textfont=dict(color=SECONDARY), cliponaxis=False,
            customdata=[r[f"{side}_margin"] for r in rows],
            hovertemplate="%{y}<br>Margin: $%{customdata:,.2f} per barrel<extra>" + legend + "</extra>"))
    fig.add_vline(x=base, line=dict(color=INK, width=1), annotation_text=f"Today {'-' if base < 0 else ''}${abs(base):,.2f}",
                  annotation_position="top", annotation_font_color=SECONDARY)
    fig.update_layout(barmode="overlay", margin=dict(l=10, r=60, t=50, b=10))
    return _style(fig, height=110 + 48 * len(rows), x_title="Margin, USD per barrel")


def history(margin) -> go.Figure:
    """Margin through time, shaded green where the arb was open and red where closed."""
    fig = go.Figure()
    for clipped, colour, label in [(margin.clip(lower=0), GOOD, "Arb open"),
                                   (margin.clip(upper=0), CRITICAL, "Arb closed")]:
        fig.add_trace(go.Scatter(x=margin.index, y=clipped.values, mode="lines", name=label,
                                 line=dict(width=0), fill="tozeroy", fillcolor=colour,
                                 opacity=0.35, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=margin.index, y=margin.values, mode="lines", name="Margin",
                             line=dict(width=2, color=BLUE),
                             hovertemplate="%{x|%d %b %Y}: $%{y:,.2f} per barrel<extra></extra>"))
    fig.add_hline(y=0, line=dict(color=INK, width=1))
    return _style(fig, height=400, y_title="Margin, USD per barrel")


def ranking_bars(rows: list[dict]) -> go.Figure:
    """Margin per barrel for each discharge port, best at the top. Green pays, red loses."""
    rows = rows[::-1]  # plotly draws the first row at the bottom
    margins = [r["margin"] for r in rows]
    fig = go.Figure(go.Bar(
        x=margins, y=[r["port"] for r in rows], orientation="h",
        marker_color=[GOOD if m > 0 else CRITICAL for m in margins],
        text=[f"{'-' if m < 0 else '+'}${abs(m):,.2f}" for m in margins],
        textposition="outside", textfont=dict(color=INK), cliponaxis=False,
        hovertemplate="%{y}<br>Margin: %{text} per barrel<extra></extra>"))
    fig.add_vline(x=0, line=dict(color=INK, width=1))
    fig = _style(fig, height=90 + 46 * len(rows), x_title="Margin, USD per barrel")
    # Leave room on both sides for the value labels.
    span = max(abs(min(margins)), abs(max(margins)), 1)
    fig.update_xaxes(range=[min(min(margins), 0) - span * 0.2, max(max(margins), 0) + span * 0.2])
    fig.update_layout(margin=dict(l=10, r=40, t=20, b=10))
    return fig


def margin_heatmap(grid, today_hire: float, today_spread: float) -> go.Figure:
    """Margin for each pairing of hire rate (across) and price spread (up).

    Red loses, green pays, with a pale neutral where the margin is zero. The black
    line is break-even and the dot is where today's inputs sit.
    """
    limit = max(abs(float(grid.values.min())), abs(float(grid.values.max())), 1.0)
    hires, spreads = list(grid.columns), list(grid.index)
    fig = go.Figure(go.Heatmap(
        x=hires, y=spreads, z=grid.values, zmid=0, zmin=-limit, zmax=limit,
        colorscale=[[0.0, CRITICAL], [0.5, "#f0efec"], [1.0, GOOD]],
        colorbar=dict(title="Margin<br>USD/bbl", tickfont=dict(color=MUTED)),
        hovertemplate="Hire $%{x:,.0f} a day<br>Spread $%{y:,.2f}<br>Margin $%{z:,.2f} per barrel<extra></extra>"))
    # The break-even line: where the margin is exactly zero.
    fig.add_trace(go.Contour(
        x=hires, y=spreads, z=grid.values, showscale=False, hoverinfo="skip",
        contours=dict(start=0, end=0, size=1, coloring="none"), line=dict(color=INK, width=2),
        name="Break-even"))
    inside = hires[0] <= today_hire <= hires[-1] and spreads[0] <= today_spread <= spreads[-1]
    if inside:
        fig.add_trace(go.Scatter(
            x=[today_hire], y=[today_spread], mode="markers+text", text=["These inputs"],
            textposition="top center", textfont=dict(color=INK),
            marker=dict(size=12, color=INK, line=dict(width=2, color=SURFACE)),
            hovertemplate="These inputs<extra></extra>", showlegend=False))
    fig = _style(fig, height=460, x_title="Ship hire, USD per day",
                 y_title="Price spread, USD per barrel")
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)
    return fig
