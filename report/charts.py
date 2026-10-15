"""Compact, vector-only charts drawn from the saved matchmaking measurements.

The report supplies its canvas, registered fonts and data accessors through
ctx. These functions consume the same space as their earlier bar charts.
"""

from math import hypot

from reportlab.lib import colors
from reportlab.pdfbase.pdfmetrics import stringWidth


def _label(c, x, y, text, color, size=8.2, bold=False, align="left"):
    c.setFillColor(color)
    c.setFont("SansB" if bold else "Sans", size)
    getattr(c, {"left": "drawString", "right": "drawRightString",
                "center": "drawCentredString"}[align])(x, y, text)


def _palette(ctx):
    return {
        "role_fifo": ctx.get("BLACK", colors.HexColor("#24211F")),
        "fixed_50": ctx.get("WARMGRAY", colors.HexColor("#89847D")),
        "adaptive_10": ctx.get("BURGUNDY", colors.HexColor("#7A263A")),
        "adaptive_30": ctx.get("OCHRE", colors.HexColor("#A8782A")),
    }


def _point(c, x, y, policy, ink):
    """Every mark fits inside a radius of 3 pt, including polygon corners."""
    c.setStrokeColor(ink)
    c.setFillColor(ink)
    c.setLineWidth(.7)
    if policy == "role_fifo":
        c.circle(x, y, 2.65, stroke=1, fill=1)
    elif policy == "fixed_50":
        c.setFillColor(colors.white)
        c.rect(x - 2.1, y - 2.1, 4.2, 4.2, stroke=1, fill=1)
    else:
        pts = ([(x, y + 3), (x - 3, y), (x, y - 3), (x + 3, y)]
               if policy == "adaptive_10" else
               [(x, y + 3), (x - 2.6, y - 1.5), (x + 2.6, y - 1.5)])
        p = c.beginPath()
        p.moveTo(*pts[0])
        for xx, yy in pts[1:]:
            p.lineTo(xx, yy)
        p.close()
        c.drawPath(p, stroke=1, fill=1)


def result_figure(b, ctx):
    """Two objective-plane panels: 225 pt plus a short caption."""
    if b.w < 500:
        raise ValueError("The results figure needs the report's full width.")
    c, top, x = ctx["C"], b.y, b.x
    black, gray = ctx["BLACK"], ctx["GRAY"]
    palette = _palette(ctx)
    grid = colors.HexColor("#E8E3DC")
    gap = 28
    panel_width = (b.w - gap) / 2
    plot_width = panel_width - 40
    bottom, plot_height = top - 187, 135

    # Nearby scarce-support adaptive points have labels on opposite sides.
    panels = [
        ("balanced", "(a) Balanced roles", x, (0, 25),
         {"role_fifo": (9, -3, "left", False),
          "fixed_50": (9, -3, "left", False),
          "adaptive_10": (9, -3, "left", False),
          "adaptive_30": (9, -3, "left", False)}),
        ("support_scarce", "(b) Scarce support", x + panel_width + gap,
         (25, 50),
         {"role_fifo": (-9, -3, "right", False),
          "fixed_50": (9, 1, "left", False),
          "adaptive_10": (12, -14, "left", True),
          "adaptive_30": (-12, 12, "right", True)}),
    ]
    c.saveState()
    for scenario, title, left, limits, label_offsets in panels:
        _label(c, left, top - 10, title, black, 9, bold=True)
        records = {p: ctx["pooled"](scenario, p) for p in ctx["POLICIES"]}
        rates = {p: 100 * r["match_rate"] for p, r in records.items()}
        if scenario == "balanced":
            if any(abs(rates[p] - 100) > .05 for p in rates if p != "fixed_50"):
                raise ValueError("Balanced completion annotation needs revision.")
            subtitle = f"Complete: 100%; Fixed 50: {rates['fixed_50']:.1f}%"
        else:
            if max(rates.values()) - min(rates.values()) > .05:
                raise ValueError("Scarce completion annotation needs revision.")
            subtitle = f"Complete: {rates['role_fifo']:.0f}% for every policy"
        _label(c, left, top - 25, subtitle, gray, 8.1)

        axis_x = left + 34
        low, high = limits
        for tick in [0, 100, 200, 300]:
            yy = bottom + plot_height * tick / 360
            c.setStrokeColor(grid)
            c.setLineWidth(.45)
            c.line(axis_x, yy, axis_x + plot_width, yy)
            _label(c, axis_x - 6, yy - 2.8, str(tick), gray, 8,
                   align="right")
        c.setStrokeColor(gray)
        c.setLineWidth(.6)
        c.line(axis_x, bottom, axis_x, bottom + plot_height)
        c.line(axis_x, bottom, axis_x + plot_width, bottom)
        for tick in range(low, high + 1, 5):
            xx = axis_x + plot_width * (tick - low) / (high - low)
            c.line(xx, bottom, xx, bottom - 3)
            _label(c, xx, bottom - 14, str(tick), gray, 8, align="center")

        points = {}
        for policy, record in records.items():
            wait = record["mean_matched_wait_seconds"]
            quality = record["mean_team_pairwise_gap"]
            if not low <= wait <= high or not 0 <= quality <= 360:
                raise ValueError("A result falls outside the declared axes.")
            points[policy] = (axis_x + plot_width * (wait - low) / (high - low),
                              bottom + plot_height * quality / 360)
        locations = list(points.values())
        if any(hypot(ax - bx, ay - by) < 7
               for i, (ax, ay) in enumerate(locations)
               for bx, by in locations[i + 1:]):
            raise ValueError("Policy symbols overlap; revise the panel geometry.")

        for policy in ctx["POLICIES"]:
            xx, yy = points[policy]
            dx, dy, align, leader = label_offsets[policy]
            tx, ty = xx + dx, yy + dy
            label = ctx["LABELS"][policy]
            bold = policy == "adaptive_10"
            width = stringWidth(label, "SansB" if bold else "Sans", 8.2)
            label_left = tx - width if align == "right" else tx
            if label_left < left or label_left + width > left + panel_width:
                raise ValueError("A policy label exceeds its panel.")
            if leader:
                end_x = tx + 3 if align == "right" else tx - 3
                end_y = ty + 2.6
                length = hypot(end_x - xx, end_y - yy)
                c.setStrokeColor(palette[policy])
                c.setLineWidth(.5)
                c.line(xx + (end_x - xx) * 4 / length,
                       yy + (end_y - yy) * 4 / length, end_x, end_y)
            _point(c, xx, yy, policy, palette[policy])
            _label(c, tx, ty, label, palette[policy], 8.2, bold=bold,
                   align=align)

    c.saveState()
    c.translate(x + 7, bottom + plot_height / 2)
    c.rotate(90)
    _label(c, 0, 0, "Mean pairwise gap (points)", black, 8.4, align="center")
    c.restoreState()
    _label(c, x + b.w / 2, top - 219, "Mean matched-player wait (s)",
           black, 8.4, align="center")
    c.restoreState()
    b.y = top - 225
    b.caption("Figure 2.",
              "Each point pools five runs; uncertainty is not shown. The gap "
              "axis is shared, but wait-axis ranges differ. Completion is given "
              "under each title. Matched-only waits condition on service; "
              "Figure 3 also counts pending requests.")


def queue_residence_figure(b, ctx):
    """Four paired endpoints expose unmatched requests; 162 pt plus caption."""
    if b.w < 240:
        raise ValueError("The queue-residence figure needs a full text column.")
    c, top, x = ctx["C"], b.y, b.x
    black, gray = ctx["BLACK"], ctx["GRAY"]
    burgundy = _palette(ctx)["adaptive_10"]
    grid = colors.HexColor("#E8E3DC")
    link = colors.HexColor("#B9B0A5")
    axis_x, axis_width, limit = x + 65, b.w - 92, 120
    c.saveState()
    for start, fill, text in [(0, colors.white, "Matched only"),
                              (110, burgundy, "All arrivals")]:
        c.setStrokeColor(black if start == 0 else burgundy)
        c.setFillColor(fill)
        c.setLineWidth(.8)
        c.circle(x + start + 4, top - 6, 2.6, stroke=1, fill=1)
        _label(c, x + start + 13, top - 9, text, black, 8.2)

    for tick in [0, 40, 80, 120]:
        xx = axis_x + axis_width * tick / limit
        c.setStrokeColor(grid)
        c.setLineWidth(.45)
        c.line(xx, top - 24, xx, top - 119)
    for row, policy in enumerate(ctx["POLICIES"]):
        yy = top - 34 - row * 25
        _label(c, axis_x - 7, yy - 2.8, ctx["LABELS"][policy],
               black, 8.2, align="right")
        record = ctx["pooled"]("support_scarce", policy)
        matched = record["mean_matched_wait_seconds"]
        observed = record["observed_mean_queue_time_seconds"]
        if not (0 <= matched <= limit and 0 <= observed <= limit):
            raise ValueError("Queue time exceeds the figure's declared axis.")
        first = axis_x + axis_width * matched / limit
        second = axis_x + axis_width * observed / limit
        c.setStrokeColor(link)
        c.setLineWidth(1.05)
        c.line(first, yy, second, yy)
        c.setStrokeColor(black)
        c.setFillColor(colors.white)
        c.setLineWidth(.8)
        c.circle(first, yy, 2.7, stroke=1, fill=1)
        c.setStrokeColor(burgundy)
        c.setFillColor(burgundy)
        c.circle(second, yy, 2.7, stroke=1, fill=1)
        _label(c, first, yy + 6, f"{matched:.1f}", gray, 8, align="center")
        text = f"{observed:.1f}"
        if second + 6 + stringWidth(text, "Sans", 8) > x + b.w:
            raise ValueError("Queue-time label exceeds the column.")
        _label(c, second + 6, yy - 2.8, text, burgundy, 8)

    axis_y = top - 128
    c.setStrokeColor(gray)
    c.setLineWidth(.5)
    c.line(axis_x, axis_y, axis_x + axis_width, axis_y)
    for tick in [0, 40, 80, 120]:
        xx = axis_x + axis_width * tick / limit
        c.line(xx, axis_y, xx, axis_y - 2.5)
        _label(c, xx, axis_y - 13, str(tick), gray, 8, align="center")
    _label(c, axis_x + axis_width / 2, top - 155,
           "Mean queue time (s)", black, 8.2, align="center")
    c.restoreState()
    b.y = top - 162
    b.caption("Figure 3.",
              "Scarce support. Open circles average completed waits; filled "
              "circles show <i>W</i><sub>H</sub>, the observed queue residence "
              "of every arrival through the cutoff. Values pool five runs. "
              "Each line compares different populations, not additive "
              "parts of a wait.")
