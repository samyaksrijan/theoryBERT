"""Bounded Thompson NFA construction and subset determinization for binary regexes."""

from collections import defaultdict
from re import _parser as sre, _constants as C
from theorybert.contracts import DFA
from theorybert.formal.dfa import canonicalise


def regex_to_binary(pattern, max_states=8):
    """Thompson construction for an explicit, checked subset of Python regex.

    Source BRICS complement/intersection/word-boundary constructs are rejected.
    Labels denote full matches restricted to the explicitly stated binary domain.
    """
    if any(c in pattern for c in ("~", "&", "@", "#")) or "\\b" in pattern:
        raise ValueError("unsupported source-regex dialect")
    parsed = sre.parse(pattern)
    edges, epsilon = defaultdict(lambda: defaultdict(set)), defaultdict(set)
    serial = 0

    def state():
        nonlocal serial
        serial += 1
        if serial > 512:
            raise ValueError("NFA state limit")
        return serial

    def category(kind, a):
        if kind == C.CATEGORY_DIGIT:
            return a.isdigit()
        if kind == C.CATEGORY_NOT_DIGIT:
            return not a.isdigit()
        if kind == C.CATEGORY_WORD:
            return a.isalnum() or a == "_"
        if kind == C.CATEGORY_NOT_WORD:
            return not (a.isalnum() or a == "_")
        if kind == C.CATEGORY_SPACE:
            return a.isspace()
        if kind == C.CATEGORY_NOT_SPACE:
            return not a.isspace()
        raise ValueError("unsupported character category")

    def sequence(tokens):
        start = current = state()
        for op, value in tokens:
            end = state()
            if op in (C.LITERAL, C.NOT_LITERAL, C.ANY, C.IN, C.CATEGORY):
                for a in "01":
                    if op == C.LITERAL:
                        matched = ord(a) == value
                    elif op == C.NOT_LITERAL:
                        matched = ord(a) != value
                    elif op == C.ANY:
                        matched = True
                    elif op == C.CATEGORY:
                        matched = category(value, a)
                    else:
                        negative = bool(value and value[0][0] == C.NEGATE)
                        matched = False
                        for kind, item in value[int(negative):]:
                            if kind == C.LITERAL:
                                matched |= ord(a) == item
                            elif kind == C.RANGE:
                                matched |= item[0] <= ord(a) <= item[1]
                            elif kind == C.CATEGORY:
                                matched |= category(item, a)
                            else:
                                raise ValueError("unsupported character class")
                        matched ^= negative
                    if matched:
                        edges[current][a].add(end)
            elif op == C.SUBPATTERN:
                if value[1] or value[2]:
                    raise ValueError("inline flags")
                lo, hi = sequence(value[3])
                epsilon[current].add(lo)
                epsilon[hi].add(end)
            elif op == C.BRANCH:
                for branch in value[1]:
                    lo, hi = sequence(branch)
                    epsilon[current].add(lo)
                    epsilon[hi].add(end)
            elif op in (C.MAX_REPEAT, C.MIN_REPEAT):
                minimum, maximum, child = value
                if minimum > 16 or (maximum != C.MAXREPEAT and maximum > 16):
                    raise ValueError("repeat bound")
                at = current
                for _ in range(minimum):
                    lo, hi = sequence(child)
                    epsilon[at].add(lo)
                    at = hi
                epsilon[at].add(end)
                if maximum == C.MAXREPEAT:
                    lo, hi = sequence(child)
                    epsilon[at].add(lo)
                    epsilon[hi].update((lo, end))
                else:
                    for _ in range(maximum - minimum):
                        lo, hi = sequence(child)
                        epsilon[at].add(lo)
                        epsilon[hi].add(end)
                        at = hi
            else:
                raise ValueError("unsupported regex operator")
            current = end
        return start, current

    start, final = sequence(parsed)

    def closure(states):
        seen, pending = set(states), list(states)
        while pending:
            for target in epsilon[pending.pop()]:
                if target not in seen:
                    seen.add(target)
                    pending.append(target)
        return frozenset(seen)

    initial = closure([start])
    subsets, names, transitions = [initial], {initial: "q0"}, {}
    for subset in subsets:
        row = {}
        for a in "01":
            target = closure(set().union(*(edges[s][a] for s in subset)))
            if target not in names:
                if len(names) >= 256:
                    raise ValueError("determinization limit")
                names[target] = f"q{len(names)}"
                subsets.append(target)
            row[a] = names[target]
        transitions[names[subset]] = row
    dfa = canonicalise(DFA(list(names.values()), list("01"), transitions, "q0", [names[s] for s in subsets if final in s]))
    if len(dfa.states) > max_states:
        raise ValueError("target exceeds model state bound")
    return dfa
