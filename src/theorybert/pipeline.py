"""The verification boundary. Only sealed, rechecked evidence may render."""

from dataclasses import dataclass, field
from itertools import islice
from time import perf_counter
import json
from theorybert.contracts import DFA, VerificationReport, Status
from theorybert.formal.dfa import validate, minimise, equivalent, canonicalise


def identity(d):
    return json.dumps(canonicalise(d).to_dict(), sort_keys=True)


@dataclass(frozen=True)
class VerifiedDFA:
    candidate_json: str
    reference_json: str
    provenance: str

    def checked(self):
        candidate = DFA.from_dict(json.loads(self.candidate_json))
        reference = DFA.from_dict(json.loads(self.reference_json))
        if not equivalent(candidate, reference)[0]:
            raise ValueError("Verification seal is invalid.")
        return candidate


@dataclass
class PipelineResult:
    candidate: DFA | None
    reports: list[VerificationReport]
    verified: VerifiedDFA | None
    source: str
    attempted_candidates: list[DFA] = field(default_factory=list)


def verify(candidate, reference=None, provenance=None, attempt=1):
    start = perf_counter()
    r = VerificationReport(
        Status.STRUCTURE_INVALID,
        original_states=len(candidate.states),
        reference_provenance=provenance,
        attempt=attempt,
    )
    try:
        r.checks.append("Complete deterministic structure")
        r.structural_errors = validate(candidate)
        if r.structural_errors:
            r.message = "Candidate rejected: repair the listed structural errors."
        else:
            r.minimised_states = len(minimise(candidate).states)
            r.checks.append("Reachability and partition-refinement minimisation")
            if reference is None:
                r.status = Status.REFERENCE_UNAVAILABLE
                r.message = "Structure valid; semantic equivalence unverified. Upload an independent reference DFA or choose a benchmark."
            elif validate(reference):
                r.status = Status.INTERNAL_ERROR
                r.message = "Reference DFA is invalid: " + "; ".join(
                    validate(reference)
                )
            else:
                r.checks.append("Exact product-BFS equivalence, matching alphabets")
                r.equivalent, r.counterexample = equivalent(candidate, reference)
                r.status = (
                    Status.VERIFIED if r.equivalent else Status.EQUIVALENCE_FAILED
                )
                r.message = (
                    "Exact language equivalence established."
                    if r.equivalent
                    else "Candidate rejected by verifier. A shortest distinguishing string is available."
                )
    except TimeoutError as exc:
        r.status, r.message = Status.RESOURCE_LIMIT, str(exc)
    except ValueError as exc:
        r.status, r.message = Status.STRUCTURE_INVALID, str(exc)
    except Exception as exc:
        r.status, r.message = Status.INTERNAL_ERROR, str(exc)
    r.elapsed_seconds = perf_counter() - start
    return r


def run_candidates(
    candidates,
    reference=None,
    provenance=None,
    source="TheoryBERT",
    budget=5,
    timeout=20,
):
    if not 1 <= budget <= 32:
        raise ValueError("Candidate budget must be 1–32.")
    reports, attempted, seen, candidate, sealed = [], [], set(), None, None
    start = perf_counter()
    # Limit consumption too: an unbounded stream of duplicates must terminate.
    for proposed in islice(candidates, budget * 8):
        if perf_counter() - start > timeout:
            reports.append(
                VerificationReport(
                    Status.RESOURCE_LIMIT, message="Candidate time budget exceeded."
                )
            )
            break
        key = json.dumps(proposed.to_dict(), sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        # Freeze the actual attempt; generators may reuse and mutate an object.
        candidate = DFA.from_dict(json.loads(key))
        attempted.append(candidate)
        report = verify(candidate, reference, provenance, len(reports) + 1)
        reports.append(report)
        if report.status == Status.VERIFIED:
            sealed = VerifiedDFA(
                key,
                json.dumps(reference.to_dict(), sort_keys=True),
                provenance or "User-supplied reference",
            )
            break
        if len(attempted) >= budget:
            break
    if not reports:
        reports.append(
            VerificationReport(
                Status.RESOURCE_LIMIT,
                message="No candidate was produced within the prediction budget. Try a larger budget or check the model configuration.",
            )
        )
    return PipelineResult(candidate, reports, sealed, source, attempted)
