"""Earley parsing in a time-bounded worker; independent tree checking."""

import json
import subprocess
import sys
from itertools import islice
from nltk import CFG, Nonterminal
from nltk.parse import EarleyChartParser
from theorybert.contracts import CFGSpec, Production, TreeNode

EXAMPLES = {
    "Balanced a / b": ("S -> 'a' S 'b' |", "a a b b"),
    "Arithmetic": (
        "E -> E '+' T | T\nT -> T '*' F | F\nF -> '(' E ')' | 'id'",
        "id + id * id",
    ),
    "Ambiguous expression": ("E -> E '+' E | 'id'", "id + id + id"),
}


class ParseError(ValueError):
    def __init__(self, kind, message):
        self.kind = kind
        super().__init__(message)


def grammar_spec(text, tokens):
    if len(text) > 12000 or len(tokens) > 64:
        raise ParseError(
            "RESOURCE_LIMIT",
            "Use at most 12,000 grammar characters and 64 input tokens.",
        )
    try:
        grammar = CFG.fromstring(text)
    except (ValueError, IndexError) as exc:
        raise ParseError(
            "MALFORMED_GRAMMAR", f"Check productions and quoted terminals: {exc}"
        ) from exc
    prods = grammar.productions()
    if len(prods) > 200:
        raise ParseError("RESOURCE_LIMIT", "Use at most 200 productions.")
    nonterminals = {str(p.lhs()) for p in prods} | {
        str(s) for p in prods for s in p.rhs() if isinstance(s, Nonterminal)
    }
    terminals = {s for p in prods for s in p.rhs() if isinstance(s, str)}
    if "" in terminals:
        raise ParseError(
            "MALFORMED_GRAMMAR",
            "For ε use a blank right-hand side, not a quoted empty terminal.",
        )
    if terminals & nonterminals:
        raise ParseError(
            "MALFORMED_GRAMMAR", "Use distinct names for terminals and nonterminals."
        )
    unknown = set(tokens) - terminals
    if unknown:
        raise ParseError(
            "TOKENISATION_FAILURE",
            f"Tokens {sorted(unknown)} are not grammar terminals. Separate tokens with spaces.",
        )
    return grammar, CFGSpec(
        str(grammar.start()),
        sorted(terminals),
        sorted(nonterminals),
        [
            Production(
                str(p.lhs()),
                [str(s) for s in p.rhs()],
                [isinstance(s, str) for s in p.rhs()],
            )
            for p in prods
        ],
        tokens,
    )


def serialise_tree(tree):
    count = [0]

    def visit(t):
        count[0] += 1
        if count[0] > 512:
            raise ParseError("RESOURCE_LIMIT", "Parse tree exceeds 512 nodes.")
        node_id = f"n{count[0] - 1}"
        if isinstance(t, str):
            return TreeNode(node_id, t, True)
        return TreeNode(node_id, str(t.label()), False, [visit(c) for c in t])

    return visit(tree)


def check_tree(spec, root):
    errors, leaves, ids, steps = [], [], set(), []
    legal = {(p.lhs, tuple(p.rhs), tuple(p.terminal_flags)) for p in spec.productions}
    if root.symbol != spec.start or root.terminal:
        errors.append("Root must be the grammar start symbol.")

    def visit(node, depth=0):
        if depth > 128 or len(ids) > 512:
            errors.append("Tree resource limit exceeded.")
            return
        if not node.node_id or node.node_id in ids:
            errors.append("Node IDs must be unique and nonempty.")
            return
        ids.add(node.node_id)
        if node.terminal:
            if node.children or node.symbol not in spec.terminals:
                errors.append("Malformed or undeclared terminal.")
            leaves.append(node.symbol)
        else:
            if node.symbol not in spec.nonterminals:
                errors.append("Undeclared nonterminal.")
            rhs = tuple(c.symbol for c in node.children)
            flags = tuple(c.terminal for c in node.children)
            if (node.symbol, rhs, flags) not in legal:
                errors.append(f"Illegal production at {node.node_id}.")
            steps.append(
                {
                    "node_id": node.node_id,
                    "production": f"{node.symbol} → {' '.join(rhs) or 'ε'}",
                    "children": [c.node_id for c in node.children],
                }
            )
            for c in node.children:
                visit(c, depth + 1)

    visit(root)
    if leaves != spec.input_tokens:
        errors.append("Terminal yield differs from the input token sequence.")
    # Leftmost derivation uses the same stable node identities as the animation.
    frontier = [(root.node_id, root.symbol)]
    by_id = {}

    def collect(n):
        by_id[n.node_id] = n
        for c in n.children:
            collect(c)

    if not errors:
        collect(root)
        for step in steps:
            i = next(i for i, p in enumerate(frontier) if p[0] == step["node_id"])
            frontier[i : i + 1] = [
                (c.node_id, c.symbol) for c in by_id[step["node_id"]].children
            ]
            step["sentential_form"] = " ".join(s for _, s in frontier) or "ε"
    return errors, steps


def _parse_local(text, tokens, limit):
    grammar, spec = grammar_spec(text, tokens)
    trees = [
        serialise_tree(t)
        for t in islice(EarleyChartParser(grammar).parse(tokens), limit + 1)
    ]
    if not trees:
        raise ParseError(
            "NO_DERIVATION",
            "No derivation exists for these tokens. Check the grammar or choose an example.",
        )
    return spec, trees[:limit], len(trees) > limit


def parse(text, tokens, limit=5, timeout=8):
    if not 1 <= limit <= 10:
        raise ParseError("RESOURCE_LIMIT", "Tree limit must be between 1 and 10.")
    grammar_spec(text, tokens)
    try:
        p = subprocess.run(
            [sys.executable, "-m", "theorybert.formal.cfg", "--worker"],
            input=json.dumps({"grammar": text, "tokens": tokens, "limit": limit}),
            text=True,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise ParseError(
            "RESOURCE_LIMIT",
            "Parsing exceeded the time budget. Shorten the input or simplify the grammar.",
        ) from exc
    if p.returncode:
        raise ParseError("INTERNAL_ERROR", p.stderr[-1200:])
    data = json.loads(p.stdout)
    if "error" in data:
        raise ParseError(data["kind"], data["error"])
    _, spec = grammar_spec(text, tokens)
    trees = [TreeNode.from_dict(t) for t in data["trees"]]
    for tree in trees:
        errors, _ = check_tree(spec, tree)
        if errors:
            raise ParseError(
                "INTERNAL_ERROR",
                "Independent checker rejected parser output: " + "; ".join(errors),
            )
    return spec, trees, data["truncated"]


if __name__ == "__main__":
    try:
        req = json.load(sys.stdin)
        spec, trees, truncated = _parse_local(
            req["grammar"], req["tokens"], req["limit"]
        )
        print(
            json.dumps({"trees": [t.to_dict() for t in trees], "truncated": truncated})
        )
    except (ParseError, ValueError, RecursionError) as exc:
        print(
            json.dumps(
                {"error": str(exc), "kind": getattr(exc, "kind", "RESOURCE_LIMIT")}
            )
        )
