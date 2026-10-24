"""Complete deterministic automata over explicit symbol sequences."""

from collections import deque
from theorybert.contracts import DFA, DFATrace, TraceStep


def validate(d: DFA) -> list[str]:
    errors = []
    if d.schema_version != "1.0":
        errors.append("Unsupported schema_version; expected 1.0.")
    if not d.states:
        errors.append("At least one state is required.")
    if len(set(d.states)) != len(d.states):
        errors.append("States must be unique.")
    if any(not s for s in d.states):
        errors.append("State names must be nonempty.")
    if len(set(d.alphabet)) != len(d.alphabet) or any(not s for s in d.alphabet):
        errors.append("Alphabet symbols must be unique and nonempty.")
    if len(set(d.accept_states)) != len(d.accept_states):
        errors.append("Accept states must be unique.")
    if d.start_state not in d.states:
        errors.append("Start state is undeclared.")
    if set(d.accept_states) - set(d.states):
        errors.append("Accept state is undeclared.")
    if set(d.transitions) - set(d.states):
        errors.append("Transition source is undeclared.")
    for state in d.states:
        row = d.transitions.get(state, {})
        if set(row) != set(d.alphabet):
            errors.append(
                f"{state}: expected exactly one transition per alphabet symbol."
            )
        for target in row.values():
            if target not in d.states:
                errors.append(f"{state}: destination {target!r} is undeclared.")
    return errors


def require_valid(d):
    errors = validate(d)
    if errors:
        raise ValueError(" ".join(errors))


def trace(d, symbols):
    require_valid(d)
    symbols = list(symbols)
    state, steps = d.start_state, []
    for i, symbol in enumerate(symbols):
        if symbol not in d.alphabet:
            raise ValueError(
                f"Symbol {symbol!r} at position {i + 1} is outside the alphabet {d.alphabet}."
            )
        target = d.transitions[state][symbol]
        steps.append(TraceStep(i, state, symbol, target))
        state = target
    return DFATrace(symbols, d.start_state, steps, state, state in d.accept_states)


def simulate(d, symbols):
    return trace(d, symbols).accepted


def reachable(d):
    require_valid(d)
    seen, queue = {d.start_state}, deque([d.start_state])
    while queue:
        for target in d.transitions[queue.popleft()].values():
            if target not in seen:
                seen.add(target)
                queue.append(target)
    return seen


def remove_unreachable(d):
    keep = reachable(d)
    return DFA(
        [s for s in d.states if s in keep],
        sorted(d.alphabet),
        {s: dict(d.transitions[s]) for s in d.states if s in keep},
        d.start_state,
        [s for s in d.accept_states if s in keep],
    )


def minimise(d):
    d = remove_unreachable(d)
    accept = set(d.accept_states)
    groups = [g for g in (accept, set(d.states) - accept) if g]
    while True:
        index = {s: i for i, g in enumerate(groups) for s in g}
        refined = []
        for group in groups:
            buckets = {}
            for s in sorted(group):
                key = tuple(index[d.transitions[s][a]] for a in sorted(d.alphabet))
                buckets.setdefault(key, set()).add(s)
            refined.extend(buckets.values())
        if len(refined) == len(groups):
            break
        groups = refined
    names = {s: f"m{i}" for i, g in enumerate(groups) for s in g}
    return DFA(
        [f"m{i}" for i in range(len(groups))],
        sorted(d.alphabet),
        {
            f"m{i}": {a: names[d.transitions[sorted(g)[0]][a]] for a in d.alphabet}
            for i, g in enumerate(groups)
        },
        names[d.start_state],
        sorted({names[s] for s in d.accept_states}),
    )


def canonicalise(d, minimal=True):
    d = minimise(d) if minimal else remove_unreachable(d)
    alphabet = sorted(d.alphabet)
    order, seen = [d.start_state], {d.start_state}
    for s in order:
        for a in alphabet:
            target = d.transitions[s][a]
            if target not in seen:
                seen.add(target)
                order.append(target)
    rename = {s: f"q{i}" for i, s in enumerate(order)}
    return DFA(
        list(rename.values()),
        alphabet,
        {rename[s]: {a: rename[d.transitions[s][a]] for a in alphabet} for s in order},
        "q0",
        [rename[s] for s in order if s in d.accept_states],
    )


def equivalent(a, b, max_pairs=100000):
    """Product BFS returns (equivalent, shortest counterexample or None).

    Alphabets must match exactly as sets. [] denotes the empty-string witness.
    """
    require_valid(a)
    require_valid(b)
    if set(a.alphabet) != set(b.alphabet):
        raise ValueError(
            "Alphabet mismatch: equivalence requires matching alphabets; no implicit completion."
        )
    start = (a.start_state, b.start_state)
    queue, pred = deque([start]), {start: None}
    aa, ba = set(a.accept_states), set(b.accept_states)
    while queue:
        pair = queue.popleft()
        if (pair[0] in aa) != (pair[1] in ba):
            witness = []
            while pred[pair] is not None:
                pair, symbol = pred[pair]
                witness.append(symbol)
            return False, witness[::-1]
        for symbol in sorted(a.alphabet):
            nxt = (a.transitions[pair[0]][symbol], b.transitions[pair[1]][symbol])
            if nxt not in pred:
                if len(pred) >= max_pairs:
                    raise TimeoutError("Product-state budget exceeded.")
                pred[nxt] = (pair, symbol)
                queue.append(nxt)
    return True, None
