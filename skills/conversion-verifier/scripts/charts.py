#!/usr/bin/env python3
"""
Inline SVG chart generation, no dependencies.

Three charts, and only three. Each one answers a question the reader actually has
when they open this report. A fourth chart would be decoration, and decoration on
an analytical report costs credibility rather than adding to it.

  A. Which campaigns sit on the wrong side of break-even once the contested part
     is removed, and which do not? (the budget decision)
  B. What is my claimed number made of? (the mechanism behind A)
  C. How much of each campaign's claim is contested? (where A comes from)

Two earlier charts were removed rather than restyled. A three-bar chart of three
ROAS figures was a chart doing a stat tile's job, and the day-by-day line answered
a question no reader was asking by the time they reached it.

Palette is the validated categorical pair (blue slot 1, orange slot 2): CVD
separation ΔE 24.7, normal-vision 33.6, both well clear of the floors.
"""

BLUE = "#2a78d6"
ORANGE = "#eb6834"
ORANGE_INK = "#b8430f"  # the orange stepped dark enough to be legible as text
CONNECTOR = "#cfcdc4"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SURFACE = "#ffffff"  # matches the report surface, so halos and rings are invisible
GAP = 2  # surface gap between stacked segments, never a border


def _esc(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _text(x, y, content, size=11, fill=INK_2, anchor="start", weight="400"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}" '
            f'font-family="system-ui,-apple-system,sans-serif">{_esc(content)}</text>')


def _rect(x, y, width, height, fill, radius=0):
    if width <= 0:
        return ""
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{height:.1f}" '
            f'fill="{fill}" rx="{radius}"/>')


def _open(width, height):
    return (f'<svg viewBox="0 0 {width} {height}" width="100%" '
            f'style="max-width:{width}px;height:auto" role="img" '
            f'xmlns="http://www.w3.org/2000/svg">')


def composition_chart(rows, width=640, share_label="view", pct_space=""):
    """Horizontal stacked bars: click-attributed vs view-through, per campaign.

    Stacked because the question is compositional (how much of this claim rests on
    something the store cannot corroborate), and horizontal because campaign names
    are long enough that vertical bars would force rotated labels.
    """
    label_w, bar_h, row_gap, top = 168, 22, 18, 8
    # Reserve the share label's real width on the right. It used to get a flat 74px,
    # which clipped "18 % view-through" to "18 % view-th" in the French report.
    plot_w = width - label_w - (7 * len(share_label) + 46)
    height = top + len(rows) * (bar_h + row_gap) + 4
    biggest = max((row["click"] + row["view"]) for row in rows) or 1
    parts = [_open(width, height)]
    for index, row in enumerate(rows):
        parts.append(_composition_row(row, index, label_w, bar_h, row_gap, top, plot_w, biggest,
                                      share_label, pct_space))
    parts.append("</svg>")
    return "".join(parts)


def _composition_row(row, index, label_w, bar_h, row_gap, top, plot_w, biggest,
                     share_label="view", pct_space=""):
    y = top + index * (bar_h + row_gap)
    click_w = plot_w * row["click"] / biggest
    view_w = plot_w * row["view"] / biggest
    total = row["click"] + row["view"]
    share = row["view"] / total if total else 0
    weight = "600" if row.get("emphasis") else "400"
    return "".join([
        _text(0, y + 15, row["label"], 11, INK, weight=weight),
        _rect(label_w, y, click_w, bar_h, BLUE, 3),
        _rect(label_w + click_w + GAP, y, max(0, view_w - GAP), bar_h, ORANGE, 3),
        _text(label_w + click_w + view_w + 8, y + 15,
              f"{share:.0%}".replace("%", pct_space + "%") + f" {share_label}", 11, INK_2),
    ])


LOSS_WASH = 0.07  # opacity of the below-break-even ground, a wash and never a block


def bracket_chart(rows, breakeven=None, width=700, decimal="."):
    """Per campaign, the honest range: clicks alone at one end, declared at the other.

    A single ROAS number hides the only thing a buyer needs, which is how much of
    that number is contestable. Drawing it as a segment says the truthful thing
    directly: the real figure is somewhere on this line, and what decides the budget
    is which side of break-even the line sits on.

    Break-even is drawn as a threshold with the losing ground washed behind it, so
    the verdict is a position rather than a number the reader has to compare.
    """
    label_w, row_h, top = 190, 56, 26
    plot_h = len(rows) * row_h
    low, high = _bracket_bounds(rows, breakeven)
    scale = (width - label_w - 20) / (high - low)

    def x_of(value):
        return label_w + (value - low) * scale

    ground = _breakeven_ground(x_of(breakeven), label_w, top, plot_h) if breakeven else ""
    body = "".join(_bracket_row(row, top + index * row_h, x_of, decimal)
                   for index, row in enumerate(rows))
    return "".join([_open(width, top + plot_h + 34), ground, body,
                    _bracket_axis(low, high, x_of, top + plot_h, decimal), "</svg>"])


def _bracket_bounds(rows, breakeven):
    """Pad the axis around everything that must be visible, break-even included."""
    values = [row["low"] for row in rows] + [row["high"] for row in rows]
    if breakeven is not None:
        values.append(breakeven)
    low, high = min(values), max(values)
    pad = max(0.12, (high - low) * 0.12)
    return max(0.0, low - pad), high + pad


def _breakeven_ground(x, label_w, top, plot_h):
    return "".join([
        f'<rect x="{label_w:.1f}" y="{top - 12:.1f}" width="{x - label_w:.1f}" '
        f'height="{plot_h:.1f}" fill="{ORANGE}" opacity="{LOSS_WASH}"/>',
        f'<line x1="{x:.1f}" y1="{top - 12:.1f}" x2="{x:.1f}" '
        f'y2="{top + plot_h - 12:.1f}" stroke="{ORANGE_INK}" stroke-width="1.5"/>',
    ])


def _bracket_row(row, y, x_of, decimal="."):
    """One campaign: a connector, a dot at each end, and both values labelled."""
    low_x, high_x = x_of(row["low"]), x_of(row["high"])
    low_ink = ORANGE_INK if row.get("below_breakeven") else INK
    return "".join([
        _text(0, y + 6, row["label"], 12, INK, weight="600"),
        _text(0, y + 22, row["sub"], 11, MUTED) if row.get("sub") else "",
        f'<line x1="{low_x:.1f}" y1="{y + 12:.1f}" x2="{high_x:.1f}" y2="{y + 12:.1f}" '
        f'stroke="{CONNECTOR}" stroke-width="2"/>',
        _dot(low_x, y + 12, ORANGE),
        _dot(high_x, y + 12, BLUE),
        _value_label(low_x, y - 2, row["low"], low_ink, decimal),
        _value_label(high_x, y - 2, row["high"], INK, decimal),
    ])


def _value_label(x, y, value, fill, decimal="."):
    """A value label carrying a surface halo, so it stays readable wherever it lands.

    A dot sitting exactly on the break-even threshold puts its label on top of that
    line, and the line then shows through the gaps between characters. Painting the
    surface as a stroke under the glyphs clears it without moving the label off the
    value it belongs to.
    """
    text = f"{value:.2f}x".replace(".", decimal)
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="12" fill="{fill}" '
            f'text-anchor="middle" font-weight="600" stroke="{SURFACE}" stroke-width="3.5" '
            f'paint-order="stroke" '
            f'font-family="system-ui,-apple-system,sans-serif">{_esc(text)}</text>')


def _dot(x, y, fill):
    """A 2px surface ring keeps the dot legible where it lands on the connector."""
    return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="{fill}" '
            f'stroke="{SURFACE}" stroke-width="2"/>')


def _bracket_axis(low, high, x_of, y, decimal="."):
    ticks = [low + (high - low) * step / 3 for step in range(4)]
    marks = "".join(_text(x_of(tick), y + 16, f"{tick:.2f}x".replace(".", decimal),
                          11, MUTED, anchor="middle")
                    for tick in ticks)
    return (f'<line x1="{x_of(low):.1f}" y1="{y:.1f}" x2="{x_of(high):.1f}" y2="{y:.1f}" '
            f'stroke="{GRID}" stroke-width="1"/>{marks}')


def claim_split_chart(click, view, width=700):
    """One bar: the claimed total, split into what the store can corroborate and what it cannot."""
    total = click + view
    if not total:
        return ""
    bar_h, top = 26, 6
    click_w = width * click / total
    return "".join([
        _open(width, top + bar_h + 8),
        _rect(0, top, click_w - GAP, bar_h, BLUE, 0),
        _rect(click_w, top, width - click_w, bar_h, ORANGE, 3),
        "</svg>",
    ])


def roas_chart(values, width=640):
    """Three ways of measuring the same thing, on one axis.

    Deliberately not three hues: these are not three identities, they are one
    measure computed three ways, and the story is a single number. So the actionable
    bar is emphasized and the others recede, which is what emphasis is for.
    """
    bar_w, gap, left, top, plot_h = 96, 56, 8, 24, 150
    height = top + plot_h + 54
    ceiling = max(item["value"] for item in values) * 1.18
    parts = [_open(width, height)]
    parts.extend(_gridlines(width, top, plot_h, ceiling, suffix="x"))
    for index, item in enumerate(values):
        parts.append(_roas_bar(item, index, bar_w, gap, left, top, plot_h, ceiling))
    parts.append("</svg>")
    return "".join(parts)


def _nice_step(ceiling, target_lines=4):
    """Round the axis interval to something a reader can do arithmetic with.

    Raw ceiling/3 produces ticks like 0.9x and 1.9x, which are technically
    correct and quietly awful: nobody can estimate a bar against them.
    """
    rough = ceiling / max(1, target_lines - 1)
    magnitude = 10 ** (len(str(int(rough))) - 1) if rough >= 1 else 0.1
    for multiple in (1, 2, 2.5, 5, 10):
        if magnitude * multiple >= rough:
            return magnitude * multiple
    return magnitude * 10


def _gridlines(width, top, plot_h, ceiling, suffix=""):
    step = _nice_step(ceiling)
    lines = []
    value = 0.0
    while value <= ceiling:
        y = top + plot_h - (plot_h * value / ceiling)
        lines.append(f'<line x1="0" y1="{y:.1f}" x2="{width}" y2="{y:.1f}" '
                     f'stroke="{GRID}" stroke-width="1"/>')
        label = f"{value:.1f}{suffix}" if suffix else f"{value:,.0f}"
        lines.append(_text(width, y - 4, label, 10, MUTED, anchor="end"))
        value += step
    return lines


def _roas_bar(item, index, bar_w, gap, left, top, plot_h, ceiling):
    x = left + index * (bar_w + gap)
    bar_h = plot_h * item["value"] / ceiling
    y = top + plot_h - bar_h
    fill = BLUE if item.get("emphasis") else AXIS
    ink = INK if item.get("emphasis") else INK_2
    weight = "600" if item.get("emphasis") else "400"
    label_lines = item["label"].split("|")
    out = [_rect(x, y, bar_w, bar_h, fill, 3),
           _text(x + bar_w / 2, y - 8, f"{item['value']:.2f}x", 14, ink,
                 anchor="middle", weight="600")]
    for line_index, line in enumerate(label_lines):
        out.append(_text(x + bar_w / 2, top + plot_h + 18 + line_index * 13, line,
                         10, ink, anchor="middle", weight=weight))
    return "".join(out)


def daily_chart(days, width=640):
    """Two count series over time, one axis, same unit.

    The shape is the finding. Steady offset means systematic over-attribution;
    spikes on particular days mean something broke. Only the extremes carry
    labels, since numbering every point produces noise nobody reads.
    """
    left, top, plot_h = 4, 20, 132
    plot_w = width - left - 46
    height = top + plot_h + 40
    ceiling = max(max(day["claimed"], day["actual"]) for day in days) * 1.15 or 1
    parts = [_open(width, height)]
    parts.extend(_gridlines(width, top, plot_h, ceiling))
    for key, color in (("actual", BLUE), ("claimed", ORANGE)):
        parts.append(_daily_line(days, key, color, left, top, plot_h, plot_w, ceiling))
    parts.extend(_daily_axis(days, left, top, plot_h, plot_w))
    parts.append("</svg>")
    return "".join(parts)


def _daily_line(days, key, color, left, top, plot_h, plot_w, ceiling):
    step = plot_w / max(1, len(days) - 1)
    points = " ".join(
        f"{left + index * step:.1f},{top + plot_h - plot_h * day[key] / ceiling:.1f}"
        for index, day in enumerate(days))
    return (f'<polyline points="{points}" fill="none" stroke="{color}" '
            f'stroke-width="2" stroke-linejoin="round"/>')


def _daily_axis(days, left, top, plot_h, plot_w):
    step = plot_w / max(1, len(days) - 1)
    baseline = (f'<line x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" '
                f'y2="{top + plot_h}" stroke="{AXIS}" stroke-width="1"/>')
    ticks = [baseline]
    for index in (0, len(days) // 2, len(days) - 1):
        anchor = "start" if index == 0 else "end" if index == len(days) - 1 else "middle"
        ticks.append(_text(left + index * step, top + plot_h + 16,
                           days[index]["date"][5:], 10, MUTED, anchor=anchor))
    return ticks
