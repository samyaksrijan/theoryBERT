"""Fixed trusted Manim code. All user input is data, never executable code."""

import json
import os
from pathlib import Path
import manimpango
import numpy as np
from manim import *
from theorybert.contracts import DFA, TreeNode
from theorybert.rendering.layout import (
    graph_layout,
    tree_layout,
    state_colour,
    NAVY,
    INDIGO,
    MUTED,
    BG,
)


class TheoryScene(Scene):
    def text(self, s, size=25, colour=NAVY, max_width=12, mono=False):
        t = Text(
            str(s),
            font=self.mono_font if mono else self.ui_font,
            font_size=size,
            color=colour,
        )
        if t.width > max_width:
            t.scale_to_fit_width(max_width)
        return t

    def construct(self):
        self.camera.background_color = BG
        fonts = Path(__file__).resolve().parents[3] / "frontend" / "public" / "fonts"
        self.ui_font, self.mono_font = "Arial", "monospace"
        for asset, family, field in (
            ("DMSans.ttf", "DM Sans", "ui_font"),
            ("IBMPlexMono.ttf", "IBM Plex Mono", "mono_font"),
        ):
            path = fonts / asset
            if path.is_file() and manimpango.register_font(str(path)):
                setattr(self, field, family)
        payload = json.load(open(os.environ["THEORYBERT_PAYLOAD"]))
        if payload["mode"] == "dfa":
            self.dfa(payload)
        else:
            self.cfg(payload)

    def dfa(self, p):
        d = DFA.from_dict(p["dfa"])
        tr = p["trace"]
        nodes, edges = graph_layout(d)

        extent = list(nodes.values()) + [
            e[k] for e in edges for k in ("c1", "c2", "label")
        ]
        extent.append((nodes[d.start_state][0], nodes[d.start_state][1] - 0.95))
        minx, maxx = min(x for x, y in extent), max(x for x, y in extent)
        miny, maxy = min(y for x, y in extent), max(y for x, y in extent)
        scale = min(1.15, 10.8 / max(1, maxx - minx), 4.4 / max(1, maxy - miny))
        centre = ((minx + maxx) / 2, (miny + maxy) / 2)

        def point(p):
            return np.array(
                [(p[0] - centre[0]) * scale, (p[1] - centre[1]) * scale - 0.1, 0]
            )

        title = self.text("Verified DFA · execution", 28).to_edge(UP, buff=0.25)
        subtitle = self.text("Double rings mark accepting states", 17, MUTED).next_to(
            title, DOWN, buff=0.14
        )
        self.add(title, subtitle)
        edge_mobs = {}
        for e in edges:
            curve = CubicBezier(
                *[point(e[k]) for k in ("start", "c1", "c2", "end")],
                color=MUTED,
                stroke_width=2,
            )
            # A separate arrow tip aligns with the final tangent.
            end = point(e["end"])
            tangent = end - point(e["c2"])
            tangent /= np.linalg.norm(tangent)
            tip = Arrow(
                end - tangent * 0.12,
                end,
                buff=0,
                color=MUTED,
                stroke_width=2,
                max_tip_length_to_length_ratio=0.8,
            )
            label = self.text(", ".join(e["symbols"]), 19).move_to(point(e["label"]))
            plate = BackgroundRectangle(label, color=BG, fill_opacity=1, buff=0.06)
            group = VGroup(curve, tip, plate, label)
            self.add(group)
            for a in e["symbols"]:
                edge_mobs[(e["source"], a)] = group
        circles = {}
        names = {}
        for i, (s, pt) in enumerate(nodes.items()):
            colour = state_colour(i)
            pos = point(pt)
            circle = Circle(
                radius=0.43 * scale,
                stroke_color=colour,
                stroke_width=2.5,
                fill_color=WHITE,
                fill_opacity=1,
            ).move_to(pos)
            label = self.text(s, 23 * scale, max_width=0.62 * scale, mono=True).move_to(
                pos
            )
            group = VGroup(circle)
            if s in d.accept_states:
                group.add(
                    Circle(
                        radius=0.35 * scale, stroke_color=colour, stroke_width=2
                    ).move_to(pos)
                )
            self.add(group, label)
            circles[s] = group
            names[s] = label
        start = point(nodes[d.start_state])
        self.add(
            Arrow(
                start + DOWN * 0.95 * scale,
                start + DOWN * 0.47 * scale,
                buff=0,
                color=MUTED,
            )
        )
        symbols = tr["symbols"]

        def input_window(index):
            lo = max(0, min(index - 5, len(symbols) - 12))
            hi = min(len(symbols), lo + 12)
            values = symbols[lo:hi]
            group = (
                VGroup(*[self.text(s, 26) for s in values]).arrange(RIGHT, buff=0.28)
                if values
                else VGroup(self.text("ε · empty input", 25))
            )
            group.move_to([0, -2.95, 0])
            return group, lo

        token_group, window_start = input_window(0)
        self.add(token_group)
        position_label = None
        current = tr["initial_state"]
        circles[current][0].set_fill(state_colour(d.states.index(current)))
        names[current].set_color(WHITE)
        if len(circles[current]) > 1:
            circles[current][1].set_stroke(WHITE)
        self.wait(0.5)
        for step in tr["steps"]:
            i = step["position"]
            self.remove(token_group)
            token_group, window_start = input_window(i)
            self.add(token_group)
            if position_label:
                self.remove(position_label)
            position_label = self.text(
                f"Symbol {i + 1} of {len(symbols)} · {step['source']} → {step['destination']}",
                18,
                MUTED,
            ).move_to([0, -3.38, 0])
            self.add(position_label)
            edge = edge_mobs[(step["source"], step["symbol"])]
            self.play(
                token_group[i - window_start].animate.set_color(INDIGO).scale(1.2),
                edge[0].animate.set_stroke(INDIGO, width=4),
                edge[1].animate.set_color(INDIGO),
                edge[-1].animate.set_color(INDIGO),
                run_time=0.35,
            )
            self.play(
                circles[current][0].animate.set_fill(WHITE),
                names[current].animate.set_color(NAVY),
                run_time=0.12,
            )
            if len(circles[current]) > 1:
                circles[current][1].set_stroke(state_colour(d.states.index(current)))
            current = step["destination"]
            if len(circles[current]) > 1:
                circles[current][1].set_stroke(WHITE)
            self.play(
                circles[current][0].animate.set_fill(
                    state_colour(d.states.index(current))
                ),
                names[current].animate.set_color(WHITE),
                run_time=0.2,
            )
            edge[0].set_stroke(MUTED, width=2)
            edge[1].set_color(MUTED)
            edge[-1].set_color(NAVY)
        if position_label:
            self.remove(position_label)
        outcome = "ACCEPT" if tr["accepted"] else "REJECT"
        result = self.text(
            f"{outcome} · final state {current}",
            25,
            "#23734A" if tr["accepted"] else "#AC3545",
        ).to_edge(DOWN, buff=0.2)
        self.play(FadeIn(result))
        self.wait(1.1)

    def cfg(self, p):
        root = TreeNode.from_dict(p["tree"])
        nodes, links, pos = tree_layout(root)
        title = self.text("Verified parse tree · legal derivation", 28).to_edge(
            UP, buff=0.25
        )
        self.add(title)

        def point(k):
            return np.array([*pos[k], 0])

        boxes = {}
        for k, n in nodes.items():
            label = self.text(n.symbol, 21, max_width=0.75).move_to(point(k))
            box = RoundedRectangle(
                width=max(0.5, label.width + 0.24),
                height=0.42,
                corner_radius=0.1,
                stroke_color=INDIGO,
                stroke_width=1.5,
                fill_color="#F8E6F0" if n.terminal else WHITE,
                fill_opacity=1,
            ).move_to(point(k))
            boxes[k] = VGroup(box, label)
        self.play(FadeIn(boxes[root.node_id]), run_time=0.3)
        production = None
        for step in p["steps"]:
            if production:
                self.remove(production)
            production = self.text(step["production"], 22, INDIGO).move_to(
                [0, -2.85, 0]
            )
            self.add(production)
            for child in step["children"]:
                edge = Line(
                    point(step["node_id"]) + DOWN * 0.22,
                    point(child) + UP * 0.22,
                    color="#BBAEC5",
                    stroke_width=2,
                )
                self.play(Create(edge), FadeIn(boxes[child]), run_time=0.18)
        if production:
            self.remove(production)
        tokens = " ".join(p["spec"]["input_tokens"]) or "ε"
        self.play(
            FadeIn(
                self.text(
                    "VERIFIED · terminal yield: " + tokens, 22, "#23734A"
                ).to_edge(DOWN, buff=0.35)
            )
        )
        self.wait(1.2)
