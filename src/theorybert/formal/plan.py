"""Typed regular-language plans, compiled without interpreting English."""

from collections import deque
from dataclasses import dataclass
import json

from theorybert.contracts import DFA
from theorybert.data.generators import pattern_dfa, modulo_dfa
from theorybert.formal.dfa import canonicalise
from theorybert.formal.regex import regex_to_binary

SCHEMA = {
    "ALL": (), "NONE": (),
    "STARTS": ("pattern",), "ENDS": ("pattern",),
    "CONTAINS": ("pattern",), "EXACT": ("pattern",),
    "NOT": ("expr",), "AND": ("expr", "expr"), "OR": ("expr", "expr"),
    "COUNT_EQ": ("symbol", "number"), "COUNT_LE": ("symbol", "number"), "COUNT_GE": ("symbol", "number"),
    "COUNT_MOD": ("symbol", "number", "number"),
    "LENGTH_EQ": ("number",), "LENGTH_LE": ("number",), "LENGTH_GE": ("number",),
    "LENGTH_MOD": ("number", "number"),
}


@dataclass(frozen=True)
class LanguagePlan:
    op: str
    args: tuple = ()

    def to_dict(self):
        return {"op": self.op, "args": [a.to_dict() if isinstance(a, LanguagePlan) else a for a in self.args]}

    @classmethod
    def from_dict(cls, value):
        return cls(value["op"], tuple(cls.from_dict(a) if isinstance(a, dict) else a for a in value.get("args", [])))

    def display(self):
        return self.op + "(" + ", ".join(a.display() if isinstance(a, LanguagePlan) else json.dumps(a) for a in self.args) + ")"


def validate_plan(plan, depth=0):
    if depth > 4 or plan.op not in SCHEMA:
        raise ValueError("Plan depth or operator is unsupported.")
    schema = SCHEMA[plan.op]
    if len(plan.args) != len(schema):
        raise ValueError("Plan argument count is invalid.")
    for kind, arg in zip(schema, plan.args):
        if kind == "expr":
            if not isinstance(arg, LanguagePlan):
                raise ValueError("Expected a subexpression.")
            validate_plan(arg, depth+1)
        elif kind == "pattern":
            if not isinstance(arg, str) or not 1 <= len(arg) <= 32 or set(arg)-set("01"):
                raise ValueError("Plan patterns must be 1–32 binary characters.")
        elif kind == "symbol" and arg not in ("0", "1"):
            raise ValueError("Plan symbol must be 0 or 1.")
        elif kind == "number" and (type(arg) is not int or not 0 <= arg <= 16):
            raise ValueError("Plan number must be an integer from 0 through 16.")
    if plan.op.endswith("MOD"):
        modulus, remainder = plan.args[-2:]
        if not modulus or remainder >= modulus:
            raise ValueError("Remainder must be smaller than a positive modulus.")


def negate(d):
    return canonicalise(DFA(d.states, d.alphabet, d.transitions, d.start_state, [s for s in d.states if s not in d.accept_states]))


def boolean_product(a, b, operation):
    initial = (a.start_state, b.start_state)
    names, queue, transitions, accepts = {initial: "q0"}, deque([initial]), {}, []
    while queue:
        s, t = queue.popleft()
        state = names[s, t]
        left, right = s in a.accept_states, t in b.accept_states
        if (left and right) if operation == "AND" else (left or right):
            accepts.append(state)
        transitions[state] = {}
        for bit in "01":
            target = (a.transitions[s][bit], b.transitions[t][bit])
            if target not in names:
                if len(names) >= 256:
                    raise ValueError("Plan construction exceeds the 256 product-state budget.")
                names[target] = f"q{len(names)}"
                queue.append(target)
            transitions[state][bit] = names[target]
    return canonicalise(DFA(list(names.values()), list("01"), transitions, "q0", accepts))


def compile_plan(plan, max_states=64):
    validate_plan(plan)
    def build(p):
        op, args = p.op, p.args
        if op in ("ALL", "NONE"):
            return DFA(["q0"], list("01"), {"q0": {"0": "q0", "1": "q0"}}, "q0", ["q0"] if op == "ALL" else [])
        if op in ("STARTS", "ENDS", "CONTAINS"):
            return pattern_dfa(args[0], {"STARTS": "starts", "ENDS": "ends", "CONTAINS": "contains"}[op])
        if op == "EXACT":
            return regex_to_binary(args[0], max_states=64)
        if op == "NOT":
            return negate(build(args[0]))
        if op in ("AND", "OR"):
            return boolean_product(build(args[0]), build(args[1]), op)
        if op.endswith("MOD"):
            return modulo_dfa(args[-2], args[-1], args[0] if op.startswith("COUNT") else None)
        symbol = args[0] if op.startswith("COUNT") else None
        n = args[-1]
        count = str(n) if op.endswith("EQ") else f"0,{n}" if op.endswith("LE") else f"{n},"
        regex = f"[01]{{{count}}}" if symbol is None else f"{1-int(symbol)}*({symbol}{1-int(symbol)}*){{{count}}}"
        return regex_to_binary(regex, max_states=64)
    result = canonicalise(build(plan))
    if len(result.states) > max_states:
        raise ValueError(f"The interpreted language needs {len(result.states)} states, above the {max_states}-state budget.")
    return result
