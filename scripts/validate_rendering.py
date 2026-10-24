"""Render representative verified fixtures and extract reviewable final frames."""

import json
import random
import subprocess
from pathlib import Path

from theorybert.contracts import DFA
from theorybert.data.generators import benchmark_examples
from theorybert.formal.cfg import EXAMPLES, parse
from theorybert.formal.dfa import canonicalise
from theorybert.pipeline import run_candidates
from theorybert.rendering.renderer import render, seal_tree


def main():
    output = Path("artifacts/visuals")
    output.mkdir(parents=True, exist_ok=True)
    suffix = benchmark_examples()[0]["dfa"]
    rng = random.Random(42)
    states = [f"q{i}" for i in range(8)]
    for _ in range(100):
        dense = canonicalise(
            DFA(
                states,
                list("01"),
                {s: {a: rng.choice(states) for a in "01"} for s in states},
                "q0",
                [s for s in states if rng.random() < 0.5],
            )
        )
        if len(dense.states) == 8:
            break
    else:
        raise RuntimeError(
            "Could not prepare the seeded eight-state rendering fixture."
        )
    cases = [
        ("accept", suffix, list("1101")),
        ("reject", suffix, list("00")),
        ("empty", suffix, []),
        ("dense", dense, list("0101")),
        (
            "no-accepting-states",
            DFA(["q0"], list("01"), {"q0": {"0": "q0", "1": "q0"}}, "q0", []),
            list("01"),
        ),
        (
            "universal",
            DFA(["q0"], list("01"), {"q0": {"0": "q0", "1": "q0"}}, "q0", ["q0"]),
            [],
        ),
    ]
    fixtures = [
        (
            name,
            run_candidates([dfa], dfa, "Rendering validation fixture").verified,
            symbols,
        )
        for name, dfa, symbols in cases
    ]
    grammar, tokens = EXAMPLES["Arithmetic"]
    spec, trees, _ = parse(grammar, tokens.split())
    fixtures.append(("cfg", seal_tree(spec, trees[0]), None))
    manifest = {}
    for name, evidence, symbols in fixtures:
        video, seconds, hit = render(evidence, symbols)
        frame = output / f"{name}.png"
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-sseof",
                "-0.1",
                "-i",
                str(video),
                "-frames:v",
                "1",
                str(frame),
            ],
            check=True,
            timeout=20,
        )
        manifest[name] = {
            "video": str(video),
            "render_seconds": seconds,
            "cache_hit": hit,
            "final_frame": str(frame),
        }
        print(f"{name}: {seconds:.2f}s · {'cached' if hit else 'rendered'}", flush=True)
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(output / "manifest.json")


if __name__ == "__main__":
    main()
