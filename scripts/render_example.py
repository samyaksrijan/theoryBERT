import argparse
from theorybert.data.generators import benchmark_examples
from theorybert.pipeline import run_candidates
from theorybert.formal.cfg import EXAMPLES, parse
from theorybert.rendering.renderer import render, seal_tree

p = argparse.ArgumentParser()
p.add_argument("--mode", choices=["dfa", "cfg"], default="dfa")
p.add_argument("--string", default="1101")
p.add_argument("--quality", choices=["preview", "high"], default="preview")
a = p.parse_args()
if a.mode == "dfa":
    e = benchmark_examples()[0]
    seal = run_candidates([e["dfa"]], e["dfa"], "Reference demonstration").verified
    symbols = list(a.string)
else:
    grammar, tokens = EXAMPLES["Arithmetic"]
    spec, trees, _ = parse(grammar, tokens.split())
    seal = seal_tree(spec, trees[0])
    symbols = None
print(render(seal, symbols, a.quality))
