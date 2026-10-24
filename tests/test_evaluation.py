from theorybert.data.generators import pattern_dfa
from theorybert.evaluation.evaluate import evaluate, write_results


def test_raw_accuracy_is_separate_from_gate_success(tmp_path):
    reference = pattern_dfa("01", "ends")
    wrong = pattern_dfa("01", "contains")

    class Predictor:
        source = "Explicit candidate sequence fixture"

        def predict(self, description, budget):
            return iter([wrong, reference])

    records = [
        {
            "example_id": "held-out",
            "language_id": "suffix01",
            "description": "ends in 01",
            "ground_truth_dfa": reference.to_dict(),
            "metadata": {"category": "semantic", "notation": "plain"},
        }
    ]
    rows = evaluate(Predictor(), records, budget=2)
    assert rows[0]["raw_equivalence"] == 0
    assert rows[0]["first_candidate_accuracy"] == 0
    assert rows[0]["success_within_budget"] == 1
    assert rows[0]["released_correct"] == 1
    assert rows[0]["incorrect_released"] == 0
    assert rows[0]["attempts"] == 2
    write_results(rows, tmp_path)
    assert (tmp_path / "report.md").is_file()


def test_mismatched_alphabet_is_reported_without_aborting():
    from theorybert.contracts import DFA

    class Predictor:
        source = "Incompatible alphabet fixture"

        def predict(self, description, budget):
            return iter([DFA(["s"], ["a"], {"s": {"a": "s"}}, "s", [])])

    rows = evaluate(
        Predictor(),
        [
            {
                "example_id": "alphabet-mismatch",
                "language_id": "suffix01",
                "description": "ends in 01",
                "ground_truth_dfa": pattern_dfa("01").to_dict(),
                "metadata": {"category": "semantic"},
            }
        ],
    )
    assert rows[0]["structural_validity"] == 1
    assert rows[0]["verification_status"] == "STRUCTURE_INVALID"
    assert rows[0]["raw_equivalence"] == rows[0]["released"] == 0
    assert "Alphabet mismatch" in rows[0]["verification_message"]
