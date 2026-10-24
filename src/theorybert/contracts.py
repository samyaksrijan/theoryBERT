"""Shared JSON contracts. Candidates and references remain separate objects."""

from dataclasses import dataclass, asdict, field
from enum import Enum
import json


@dataclass
class DFA:
    states: list[str]
    alphabet: list[str]
    transitions: dict[str, dict[str, str]]
    start_state: str
    accept_states: list[str]
    schema_version: str = "1.0"

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            raise ValueError("DFA must be a JSON object.")
        try:
            obj = cls(**data)
        except TypeError as exc:
            raise ValueError(f"Invalid DFA fields: {exc}") from exc
        if not all(
            isinstance(x, list) and all(isinstance(v, str) for v in x)
            for x in (obj.states, obj.alphabet, obj.accept_states)
        ):
            raise ValueError(
                "States, alphabet and accept_states must be lists of strings."
            )
        if not isinstance(obj.start_state, str) or not isinstance(
            obj.transitions, dict
        ):
            raise ValueError("start_state must be a string and transitions an object.")
        if not all(
            isinstance(k, str)
            and isinstance(v, dict)
            and all(isinstance(a, str) and isinstance(t, str) for a, t in v.items())
            for k, v in obj.transitions.items()
        ):
            raise ValueError("Transitions must map state → symbol → state.")
        return obj


def strict_json(text):
    def pairs(items):
        out = {}
        for k, v in items:
            if k in out:
                raise ValueError(f"Duplicate JSON key: {k}")
            out[k] = v
        return out

    return json.loads(text, object_pairs_hook=pairs)


class Status(str, Enum):
    STRUCTURE_INVALID = "STRUCTURE_INVALID"
    REFERENCE_UNAVAILABLE = "REFERENCE_UNAVAILABLE"
    EQUIVALENCE_FAILED = "EQUIVALENCE_FAILED"
    VERIFIED = "VERIFIED"
    RESOURCE_LIMIT = "RESOURCE_LIMIT"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass
class VerificationReport:
    status: Status
    structural_errors: list[str] = field(default_factory=list)
    reference_provenance: str | None = None
    equivalent: bool | None = None
    counterexample: list[str] | None = None
    original_states: int = 0
    minimised_states: int | None = None
    checks: list[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    attempt: int = 1
    message: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class BenchmarkRecord:
    example_id: str
    language_id: str
    split: str
    family: str
    description: str
    ground_truth_dfa: dict
    paraphrase_group_id: str
    test_strings: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


@dataclass
class TraceStep:
    position: int
    source: str
    symbol: str
    destination: str


@dataclass
class DFATrace:
    symbols: list[str]
    initial_state: str
    steps: list[TraceStep]
    final_state: str
    accepted: bool

    def to_dict(self):
        return asdict(self)


@dataclass
class Production:
    lhs: str
    rhs: list[str]
    terminal_flags: list[bool]


@dataclass
class CFGSpec:
    start: str
    terminals: list[str]
    nonterminals: list[str]
    productions: list[Production]
    input_tokens: list[str]

    def to_dict(self):
        return asdict(self)


@dataclass
class TreeNode:
    node_id: str
    symbol: str
    terminal: bool
    children: list["TreeNode"] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(
            d["node_id"],
            d["symbol"],
            d["terminal"],
            [cls.from_dict(x) for x in d["children"]],
        )
