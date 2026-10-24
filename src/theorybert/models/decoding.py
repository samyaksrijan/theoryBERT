"""Bounded best-first alternatives; no reference or feedback is consulted.

First candidate uses argmax state count and independent active-row argmax heads.
Search cost is count NLL + the sum of local NLL gaps from each variable's best
choice. The gaps prevent a spurious preference for fewer active variables.
"""

import heapq
from time import perf_counter
import torch
from theorybert.contracts import DFA


def decode_candidates(out, budget=5, timeout=3):
    if not 1 <= budget <= 32:
        raise ValueError("Use a candidate budget of 1–32.")
    count = out["count"][0].detach().cpu().log_softmax(-1)
    accept = out["accept"][0].detach().cpu()
    transitions = out["transition"][0].detach().cpu()
    heap, choices, seen = [], {}, set()
    for n in range(1, len(count) + 1):
        variables = []
        for i in range(n):
            probs = torch.stack(
                [
                    torch.nn.functional.logsigmoid(-accept[i]),
                    torch.nn.functional.logsigmoid(accept[i]),
                ]
            )
            variables.append(sorted([(float(-probs[j]), j) for j in range(2)]))
        for i in range(n):
            for a in range(2):
                probs = transitions[i, a, :n].log_softmax(-1)
                variables.append(sorted([(float(-probs[j]), j) for j in range(n)]))
        choices[n] = variables
        ranks = (0,) * len(variables)
        heapq.heappush(heap, (float(-count[n - 1]), n, ranks))
        seen.add((n, ranks))
    start = perf_counter()
    emitted = 0
    while heap and emitted < budget and perf_counter() - start < timeout:
        cost, n, ranks = heapq.heappop(heap)
        variables = choices[n]
        vals = [v[r][1] for v, r in zip(variables, ranks)]
        states = [f"q{i}" for i in range(n)]
        yield DFA(
            states,
            list("01"),
            {
                s: {a: states[vals[n + i * 2 + int(a)]] for a in "01"}
                for i, s in enumerate(states)
            },
            "q0",
            [states[i] for i in range(n) if vals[i]],
        )
        emitted += 1
        for i, v in enumerate(variables):
            if ranks[i] + 1 >= len(v):
                continue
            nxt = list(ranks)
            nxt[i] += 1
            nxt = tuple(nxt)
            if (n, nxt) in seen:
                continue
            seen.add((n, nxt))
            heapq.heappush(heap, (cost - v[ranks[i]][0] + v[nxt[i]][0], n, nxt))
