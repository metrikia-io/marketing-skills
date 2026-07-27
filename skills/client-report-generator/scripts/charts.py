#!/usr/bin/env python3
"""
Inline SVG chart generation, no dependencies.

Three charts, and only three. Each one answers a question the reader actually has
when they open this report. A fourth chart would be decoration, and decoration on
an analytical report costs credibility rather than adding to it.

  A. What is my claimed number made of, and where does the contested part sit?
  B. What does my ROAS become once the contested part is removed?
  C. Is the gap steady or does it spike on particular days?

Palette is the validated categorical pair (blue slot 1, orange slot 2): CVD
separation ΔE 24.7, normal-vision 33.6, both well clear of the floors.
"""

BLUE = "#2a78d6"
ORANGE = "#eb6834"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SURFACE = "#fcfcfb"
GAP = 2  # surface gap between stacked segments, never a border


def _esc(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#x27;"))


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


def composition_chart(rows, width=640):
    """Horizontal stacked bars: click-attributed vs view-through, per campaign.

    Stacked because the question is compositional (how much of this claim rests on
    something the store cannot corroborate), and horizontal because campaign names
    are long enough that vertical bars would force rotated labels.
    """
    label_w, bar_h, row_gap, top = 168, 22, 18, 8
    plot_w = width - label_w - 74
    height = top + len(rows) * (bar_h + row_gap) + 4
    biggest = max((row["click"] + row["view"]) for row in rows) or 1
    parts = [_open(width, height)]
    for index, row in enumerate(rows):
        parts.append(_composition_row(row, index, label_w, bar_h, row_gap, top, plot_w, biggest))
    parts.append("</svg>")
    return "".join(parts)


def _composition_row(row, index, label_w, bar_h, row_gap, top, plot_w, biggest):
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
        _text(label_w + click_w + view_w + 8, y + 15, f"{share:.0%} view", 11, INK_2),
    ])


def roas_chart(values, width=640):
    """Three ways of measuring the same thing, on one axis.

    Deliberately not three hues: these are not three identities, they are one
    measure computed three ways, and the story is a single number. So the actionable
    bar is emphasized and the others recede, which is what emphasis is for.
    """
    bar_w, gap, left, top, plot_h = 96, 56, 8, 24, 150
    height = top + plot_h + 54
    # `or 1` guards the all-zero case (a channel with spend but no revenue), which
    # would otherwise divide by a zero ceiling and crash report generation.
    ceiling = (max(item["value"] for item in values) or 0) * 1.18 or 1
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
