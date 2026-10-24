"""Shared deterministic geometry and visual language for previews and videos."""

import math
import html

NAVY = "#0D0C22"
INDIGO = "#D03676"
MUTED = "#A598AC"
BG = "#FDFCFE"
PALETTE = [
    "#D03676",
    "#7651BF",
    "#237B91",
    "#5C637D",
    "#8C5895",
    "#497584",
    "#AF4E7D",
    "#6F65A8",
]
VERSION = "theorybert-visual-3.1"


def state_colour(i):
    return PALETTE[i % len(PALETTE)]


def graph_layout(d):
    n = len(d.states)
    if n > 8:
        raise ValueError(
            "Visualisation supports at most 8 states. Inspect the transition table for larger DFAs."
        )
    if n == 1:
        points = [(0.0, 0.0)]
    elif n == 2:
        points = [(-1.6, 0.0), (1.6, 0.0)]
    elif n == 3:
        points = [(-1.8, 0.0), (1.6, 1.45), (1.6, -1.45)]
    else:
        points = [
            (
                3.1 * math.cos(math.pi - i * 2 * math.pi / n),
                1.95 * math.sin(math.pi - i * 2 * math.pi / n),
            )
            for i in range(n)
        ]
    nodes = dict(zip(d.states, points))
    edges = []
    labels = []
    grouped = {}
    for s, row in d.transitions.items():
        for a, t in row.items():
            grouped.setdefault((s, t), []).append(a)
    # Reserve loop labels before placing the longer curves around them.
    for (s, t), symbols in sorted(
        grouped.items(), key=lambda item: (item[0][0] != item[0][1], item[0])
    ):
        x, y = nodes[s]
        tx, ty = nodes[t]
        if s == t:
            # Loop extends away from the graph centre, with a top loop for a singleton.
            length = math.hypot(x, y)
            ux, uy = (x / length, y / length) if length else (0, 1)
            vx, vy = -uy, ux
            start = (x + ux * 0.28 + vx * 0.25, y + uy * 0.28 + vy * 0.25)
            end = (x + ux * 0.28 - vx * 0.25, y + uy * 0.28 - vy * 0.25)
            c1 = (x + ux * 1.25 + vx * 0.85, y + uy * 1.25 + vy * 0.85)
            c2 = (x + ux * 1.25 - vx * 0.85, y + uy * 1.25 - vy * 0.85)
            label = (x + ux * 1.03, y + uy * 1.03)
        else:
            dx, dy = tx - x, ty - y
            length = math.hypot(dx, dy)
            ux, uy = dx / length, dy / length
            start = (x + ux * 0.43, y + uy * 0.43)
            end = (tx - ux * 0.45, ty - uy * 0.45)
            vx, vy = -uy, ux
            best = None
            # Prefer small consistent curves; increase curvature to keep labels clear.
            bends = (
                (0.45, 0.85, 1.3, 1.75, 2.1)
                if (t, s) in grouped
                else (0.45, 0.85, 1.3, -0.45, -0.85, -1.3, 1.75)
            )
            for bend in bends:
                c1 = (
                    start[0] + dx * 0.32 + vx * bend,
                    start[1] + dy * 0.32 + vy * bend,
                )
                c2 = (end[0] - dx * 0.32 + vx * bend, end[1] - dy * 0.32 + vy * bend)
                for fraction in (0.5, 0.4, 0.6, 0.3, 0.7):
                    weights = (
                        (1 - fraction) ** 3,
                        3 * (1 - fraction) ** 2 * fraction,
                        3 * (1 - fraction) * fraction**2,
                        fraction**3,
                    )
                    label = tuple(
                        sum(w * p[k] for w, p in zip(weights, (start, c1, c2, end)))
                        for k in (0, 1)
                    )
                    clearance = min(
                        [
                            math.hypot(label[0] - a, label[1] - b) - 0.7
                            for a, b in points
                        ]
                        + [
                            math.hypot(label[0] - a, label[1] - b) - 0.7
                            for a, b in labels
                        ]
                        + [0.55]
                    )
                    score = clearance - abs(bend) * 0.04 - abs(fraction - 0.5) * 0.1
                    if best is None or score > best[0]:
                        best = (score, c1, c2, label)
            _, c1, c2, label = best
        labels.append(label)
        edges.append(
            {
                "source": s,
                "target": t,
                "symbols": symbols,
                "start": start,
                "end": end,
                "c1": c1,
                "c2": c2,
                "label": label,
            }
        )
    return nodes, edges


def dfa_svg(d, active=None, transition=None):
    nodes, edges = graph_layout(d)

    def xy(p):
        return (480 + p[0] * 91, 320 - p[1] * 78)

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 620" role="img" aria-label="DFA with {len(nodes)} states; double rings indicate accepting states"><defs>'
        + "".join(
            f'<marker id="{name}" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" markerWidth="12" markerHeight="12" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="{colour}"/></marker>'
            for name, colour in (("arrow", MUTED), ("active-arrow", INDIGO))
        )
        + "</defs>"
    ]
    for e in edges:
        p, c1, c2, q = [xy(e[k]) for k in ("start", "c1", "c2", "end")]
        highlighted = (
            transition is not None
            and transition[0] == e["source"]
            and transition[1] in e["symbols"]
        )
        colour = INDIGO if highlighted else MUTED
        svg.append(
            f'<path d="M {p[0]} {p[1]} C {c1[0]} {c1[1]}, {c2[0]} {c2[1]}, {q[0]} {q[1]}" fill="none" stroke="{colour}" stroke-width="{4 if highlighted else 2}" marker-end="url(#{"active-arrow" if highlighted else "arrow"})"/>'
        )
    for e in edges:
        x, y = xy(e["label"])
        label = html.escape(", ".join(e["symbols"]))
        w = max(30, len(label) * 17 + 18)
        highlighted = (
            transition is not None
            and transition[0] == e["source"]
            and transition[1] in e["symbols"]
        )
        svg.append(
            f'<rect x="{x - w / 2}" y="{y - 19}" width="{w}" height="38" rx="8" fill="{"#F8E6F0" if highlighted else BG}"/><text x="{x}" y="{y + 6}" text-anchor="middle" class="edge-label" font-family="sans-serif" font-size="32" fill="{INDIGO if highlighted else NAVY}">{label}</text>'
        )
    for i, (s, p) in enumerate(nodes.items()):
        x, y = xy(p)
        colour = state_colour(i)
        svg.append(
            f'<circle cx="{x}" cy="{y}" r="34" fill="{colour if s == active else "#FFFFFF"}" stroke="{colour}" stroke-width="2.5"/>'
        )
        if s in d.accept_states:
            svg.append(
                f'<circle cx="{x}" cy="{y}" r="28" fill="none" stroke="{colour if s != active else "#FFFFFF"}" stroke-width="2"/>'
            )
        svg.append(
            f'<text x="{x}" y="{y + 6}" text-anchor="middle" class="node-label" font-family="sans-serif" font-size="{min(32, 120 / max(1, len(s)))}" fill="{"#FFFFFF" if s == active else NAVY}">{html.escape(s)}</text>'
        )
    sx, sy = xy(nodes[d.start_state])
    svg.append(
        f'<path d="M {sx} {sy + 83} L {sx} {sy + 38}" stroke="{MUTED}" stroke-width="2" marker-end="url(#arrow)"/>'
    )
    svg.append(
        f'<text x="480" y="590" text-anchor="middle" font-family="sans-serif" class="legend" font-size="17" fill="{MUTED}">→ initial state · double ring = accepting state</text></svg>'
    )
    geometry = [xy(p) for p in nodes.values()] + [
        xy(e[k]) for e in edges for k in ("start", "end", "c1", "c2", "label")
    ]
    minx = min(x for x, y in geometry) - 82
    maxx = max(x for x, y in geometry) + 55
    miny = min(y for x, y in geometry) - 42
    maxy = max(max(y for x, y in geometry) + 65, sy + 110)
    svg.insert(
        1,
        "<style>@media(max-width:500px){.node-label{font-size:34px}.edge-label{font-size:30px}.legend{display:none}}</style>",
    )
    result = "".join(svg).replace(
        'viewBox="0 0 960 620"', f'viewBox="{minx} {miny} {maxx - minx} {maxy - miny}"'
    )
    result = result.replace(
        'x="480" y="590"', f'x="{(minx + maxx) / 2}" y="{maxy - 10}"'
    )
    return result


def tree_layout(root):
    nodes, links, positions = {}, [], {}
    leaf = [0]

    def walk(n, depth=0):
        if len(nodes) >= 45 or depth > 10:
            raise ValueError(
                "Tree too large for a readable video. Use at most 45 nodes and 10 levels."
            )
        nodes[n.node_id] = n
        xs = []
        for child in n.children:
            links.append((n.node_id, child.node_id))
            xs.append(walk(child, depth + 1))
        if not xs:
            x = leaf[0]
            leaf[0] += 1
        else:
            x = sum(xs) / len(xs)
        positions[n.node_id] = (x, depth)
        return x

    walk(root)
    if leaf[0] > 12:
        raise ValueError("Use a tree with at most 12 leaves for readable labels.")
    span = max(1, leaf[0] - 1)
    depth = max(y for x, y in positions.values())
    positions = {
        k: (
            (x / span - 0.5) * 10 if leaf[0] > 1 else 0,
            2.1 - y * min(0.8, 4.3 / max(1, depth)),
        )
        for k, (x, y) in positions.items()
    }
    return nodes, links, positions


def tree_svg(root):
    nodes, links, pos = tree_layout(root)

    def xy(k):
        x, y = pos[k]
        return 480 + x * 76, 280 - y * 83

    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 620" role="img" aria-label="Verified parse tree">'
    ]
    for s, t in links:
        x, y = xy(s)
        a, b = xy(t)
        svg.append(f'<path d="M{x},{y} L{a},{b}" stroke="#BBAEC5" stroke-width="2"/>')
    for k, n in nodes.items():
        x, y = xy(k)
        w = max(44, min(100, len(n.symbol) * 16 + 20))
        svg.append(
            f'<rect x="{x - w / 2}" y="{y - 20}" width="{w}" height="40" rx="12" fill="{"#F8E6F0" if n.terminal else "white"}" stroke="{INDIGO}"/><text x="{x}" y="{y + 6}" text-anchor="middle" font-size="30" font-family="sans-serif" fill="{NAVY}">{html.escape(n.symbol)}</text>'
        )
    svg.insert(
        1,
        "<style>@media(max-width:500px){text{font-size:34px}path{stroke-width:3}}</style>",
    )
    svg.append("</svg>")
    # A tight tree frame keeps labels legible on phones and avoids a blank lower half.
    points = [xy(k) for k in nodes]
    minx = min(x for x, y in points) - 48
    maxx = max(x for x, y in points) + 48
    miny = min(y for x, y in points) - 40
    maxy = max(y for x, y in points) + 40
    return "".join(svg).replace(
        'viewBox="0 0 960 620"', f'viewBox="{minx} {miny} {maxx - minx} {maxy - miny}"'
    )
