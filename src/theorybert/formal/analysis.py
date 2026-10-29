"""Inspectable facts computed from the actual machine and grammar."""

from collections import deque
from theorybert.formal.cfg import ParseError, grammar_spec


def machine_analysis(dfa, symbols):
    access, queue = {dfa.start_state: ""}, deque([dfa.start_state])
    while queue:
        source = queue.popleft()
        for symbol in dfa.alphabet:
            target = dfa.transitions[source][symbol]
            if target not in access:
                access[target] = access[source] + symbol
                queue.append(target)
    completions = {s: "" for s in dfa.accept_states}
    # Fixed-point shortest suffixes, with deterministic alphabet tie breaks.
    for _ in dfa.states:
        updated = dict(completions)
        for state in dfa.states:
            values = [a + completions[t] for a, t in dfa.transitions[state].items() if t in completions]
            if values:
                best = min(values + ([completions[state]] if state in completions else []), key=lambda v: (len(v), v))
                updated[state] = best
        if updated == completions:
            break
        completions = updated
    counts = {s: 0 for s in dfa.states}
    current, path = dfa.start_state, [dfa.start_state]
    counts[current] += 1
    for symbol in symbols:
        current = dfa.transitions[current][symbol]
        path.append(current)
        counts[current] += 1
    return {"states": {s: {"access_word": access.get(s), "accepting_suffix": completions.get(s), "dead": s not in completions, "visits": counts[s]} for s in dfa.states}, "path": path, "reachable_states": len(access), "accepting_states": len(dfa.accept_states), "transitions": sum(map(len, dfa.transitions.values()))}


def tokenize_input(grammar_text, text, mode="literal"):
    _, spec = grammar_spec(grammar_text, [])
    if len(text) > 4000:
        raise ParseError("RESOURCE_LIMIT", "Use at most 4,000 input characters.")
    if mode == "whitespace":
        import re
        return [{"token": m[0], "lexeme": m[0], "start": m.start(), "end": m.end()} for m in re.finditer(r"\S+", text)]
    if mode != "literal":
        raise ParseError("TOKENISATION_FAILURE", "Choose literal or whitespace tokenization.")
    terminals = sorted(spec.terminals, key=lambda t: (-len(t), t))
    rows, offset = [], 0
    while offset < len(text):
        # Spaces inside a declared terminal are preserved; outside they separate.
        token = next((t for t in terminals if text.startswith(t, offset)), None)
        if token is None:
            if text[offset].isspace():
                offset += 1
                continue
            raise ParseError("TOKENISATION_FAILURE", f"No grammar terminal matches at character {offset + 1}: {text[offset:offset+16]!r}. Quote this terminal in the grammar or use whitespace tokenization.")
        rows.append({"token": token, "lexeme": token, "start": offset, "end": offset + len(token)})
        offset += len(token)
        if len(rows) > 64:
            raise ParseError("RESOURCE_LIMIT", "Use at most 64 input tokens.")
    return rows


def grammar_analysis(spec):
    first = {n: set() for n in spec.nonterminals}
    nullable = set()

    def sequence(rhs, flags):
        result = set()
        for symbol, terminal in zip(rhs, flags):
            if terminal:
                result.add(symbol)
                return result, False
            result.update(first[symbol])
            if symbol not in nullable:
                return result, False
        return result, True

    changed = True
    while changed:
        before = (sum(map(len, first.values())), len(nullable))
        for prod in spec.productions:
            symbols, empty = sequence(prod.rhs, prod.terminal_flags)
            first[prod.lhs].update(symbols)
            if empty:
                nullable.add(prod.lhs)
        changed = before != (sum(map(len, first.values())), len(nullable))
    # Tagged end marker avoids conflating a terminal literally named '$'.
    end = object()
    follow = {n: set() for n in spec.nonterminals}
    follow[spec.start].add(end)
    changed = True
    while changed:
        before = sum(map(len, follow.values()))
        for prod in spec.productions:
            for i, (symbol, terminal) in enumerate(zip(prod.rhs, prod.terminal_flags)):
                if terminal:
                    continue
                tail, empty = sequence(prod.rhs[i+1:], prod.terminal_flags[i+1:])
                follow[symbol].update(tail)
                if empty:
                    follow[symbol].update(follow[prod.lhs])
        changed = before != sum(map(len, follow.values()))
    table = {}
    for i, prod in enumerate(spec.productions):
        lookaheads, empty = sequence(prod.rhs, prod.terminal_flags)
        if empty:
            lookaheads |= follow[prod.lhs]
        for token in lookaheads:
            table.setdefault((prod.lhs, token), []).append(i)
    reachable, productive = {spec.start}, set()
    for _ in spec.nonterminals:
        for p in spec.productions:
            if p.lhs in reachable:
                reachable.update(s for s, t in zip(p.rhs, p.terminal_flags) if not t)
            if all(t or s in productive for s, t in zip(p.rhs, p.terminal_flags)):
                productive.add(p.lhs)
    def display(token):
        return "⟨EOF⟩" if token is end else token
    cells = [{"nonterminal": n, "lookahead": display(t), "productions": ids, "end_of_input": t is end} for (n, t), ids in table.items()]
    cells.sort(key=lambda c: (c["nonterminal"], c["lookahead"]))
    warnings = []
    for n in spec.nonterminals:
        if n not in reachable:
            warnings.append(f"{n} is unreachable from {spec.start}.")
        if n not in productive:
            warnings.append(f"{n} cannot derive a finite terminal string.")
    return {"nullable": sorted(nullable), "first": {n: sorted(v) for n, v in first.items()}, "follow": {n: sorted(map(display, v)) for n, v in follow.items()}, "ll1": not any(len(c["productions"]) > 1 for c in cells), "table": cells, "conflicts": [c for c in cells if len(c["productions"]) > 1], "warnings": warnings, "productions": [f"{p.lhs} → {' '.join(p.rhs) or 'ε'}" for p in spec.productions]}
