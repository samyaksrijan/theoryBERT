# Fresh TOC and compiler challenge

This stage follows the 29 October 2026 BERT expansion. It tests unfamiliar wording and combined constraints, records failures by stage, and adapts the neural models with independent formal supervision. BERT remains the only interpreter of English requests; no live English rules or symbolic replacements are added.

## Frozen set and evaluation boundary

`data/challenges/toc-compiler-v1.jsonl` contains 165 cases: 100 DFA requests, 38 CFG requests and 27 compiler inputs. Its recorded SHA-256 is `ff33ccb8b859220015a605d404f75be78cfc7ca21075557805c0c375ad4bf73b`. The set was frozen before prediction. There are 71 development, 46 validation and 48 reserved test cases. Compiler prompts are kept together by English description so the same challenge wording does not cross partitions. Equivalent DFA/grammar target groups are also kept together within their respective modes.

DFA cases cover unfamiliar descriptions of prefixes/suffixes, substring overlap and exclusion, exact/minimum/maximum counts, modular conditions, singleton languages, longer patterns, intersections and alternatives. Two requests for the same prefix language require nine states and are separately marked outside the current eight-state learned representation. They are excluded from in-scope DFA accuracy.

CFG cases cover matching counts, nested and concatenated delimiters, independent ordered blocks, mirror strings, unrestricted words and arithmetic/ambiguity. Some targets are languages the existing model has seen, which is explicitly recorded. This set measures fresh wording and some new compositions; it is not an exclusively unseen-language benchmark.

The compiler cases cover precedence, associativity, unary signs, decimal lexemes, parentheses and identifiers, plus invalid or unsupported syntax. A source expression such as `1 / 0` is valid for symbolic compilation; it is not executed. Invalid input must be rejected without a substitute tree.

Gold DFA labels are independently checked against string predicates on 51,100 short-word cases. Product constructions are used only for offline gold labels. DFA scoring uses exact product-state language equivalence and retains a shortest distinguishing string for each wrong candidate. Graph edges and traces are checked separately against the predicted transition table.

CFG scoring records exact production equality and bounded membership agreement over short words. Bounded agreement is a diagnostic, not arbitrary CFG equivalence. Derivations and tree layouts are checked independently. Compiler ASTs are compared with Python's parsed expression structure without executing source. No compiler rejection counts as success when BERT generated the wrong grammar.

## Initial development findings

The initial model pair scored the following on development and validation cases combined:

| Task | Cases | Correct | Score |
| --- | ---: | ---: | ---: |
| DFA, in scope | 75 | 22 | 29.3% |
| CFG | 24 | 2 | 8.3% |
| Compiler | 18 | 9 | 50.0% |

These are substantially lower than earlier generated-template benchmark results. Most failures were language-analysis or malformed-production errors. The diagrams and checked traces faithfully represented the predicted structures. That distinction prevents a wrong predicted machine from being incorrectly classified as a rendering defect.

`artifacts/challenge-baseline/results.jsonl` records per-case predictions, failure stages, witnesses and diagnostics. `report.md` in that folder is the review list. The reserved test predictions are not inspected during training or checkpoint selection.

## Adaptation and promotion

The revised DFA stage has 6,738 examples / 1,468 canonical languages: 4,924 train, 1,173 validation and 641 existing test examples. It combines a modest replay of earlier training, broader phrasing, explicit negation/count boundaries and compound-language supervision. Prior held-out languages and the fresh validation/test targets are protected from new training. The data audit reports zero language-split overlap and zero exact held-out prompt overlap.

The grammar stage adds 456 broader descriptions (371 train / 85 validation), protects prior and fresh held-out targets, and warm-starts the neural cross-attention production decoder. It is trained against an immutable, fingerprinted BERT encoder. It does not retrieve or choose a grammar from an English rule table.

The promotion plan is written before final evaluation in `artifacts/challenge-promotion-plan.json`. A DFA candidate must improve fresh validation accuracy by at least ten percentage points while retaining at least 88.34% on the original validation set. Grammar promotion requires improved fresh CFG validation, no compiler-validation regression and at least 90% production accuracy on its mixed validation set. Known DFA/grammar product presets must also pass before promotion. Candidate selection is frozen before the reserved test is unsealed. Models that fail these validation gates remain optional artifacts; the active model is preserved.

The previous generated test set remains separate from the fresh test set. Final scores must show both. Development cases used for adaptation are never presented as evidence of held-out generalization.

## Product and resource behavior

Grammar failures retain BERT's actual productions for inspection. A changed grammar checkpoint invalidates reused predictions; input-only edits can reuse the unchanged neural analysis and reparse the new word. Research shows the reserved challenge scores separately from the generated benchmark.

Heavy jobs run sequentially at lower scheduling priority, with two CPU threads and the existing bounded MPS allocation. Guards retain a 3 GiB disk floor plus checkpoint write reserve for DFA training, monitor free memory, and stop at excess swap growth. The first attempt stopped at its swap allowance after cache construction. The restart reuses the file-backed cache; newly created caches are also reloaded through memory mapping before optimizer allocation. No resource limit is raised to bypass the guard. Only caches created by this stage are removed after training; existing checkpoints are retained.

## Reproduce

```sh
# Run once for a new challenge version. Existing frozen files are not overwritten.
python -m theorybert.data.challenges
python -m theorybert.evaluation.challenge
python -m theorybert.data.robust
python -m theorybert.training.local --config configs/bert-robust.json --initialize artifacts/bert-v3/best
# After the training process finishes; stages remain sequential.
python scripts/finish_challenge_work.py
```

The orchestration records selection decisions, before/after reserved-test results, original-benchmark results, resource snapshots and any activation. Exact files and SHA-256 values make accidental challenge edits detectable.

## Research basis

The challenge design follows behavioral testing ideas from [Beyond Accuracy: Behavioral Testing of NLP Models with CheckList](https://aclanthology.org/2020.acl-main.442/): test distinct capabilities and failure behaviors rather than relying only on a single aggregate score. The distinction between familiar primitives and new combinations is also motivated by [Measuring Compositional Generalization](https://research.google/blog/measuring-compositional-generalization/). This small project-specific set is not claimed to implement either published benchmark protocol in full.

## Final measured outcome

Selection was completed on validation data before the 48 reserved cases were evaluated. Two cases exceed the eight-state DFA representation; the remaining results are:

| Reserved challenge | Before | Selected models after |
| --- | ---: | ---: |
| DFA exact language equivalence | 7/23 (30.4%) | 7/23 (30.4%) |
| CFG reference/bounded-language match | 3/14 (21.4%) | 10/14 (71.4%) |
| Compiler grammar, AST/IR, or correct invalid-input rejection | 0/9 | 9/9 |

The compiler test portion contains one previously unseen English description with five valid and four invalid sources; it is not nine independent language-interpretation prompts. These samples are small and do not establish general correctness. All checked diagrams corresponded to the actual predicted structures.

The DFA adaptation updated actual upper pretrained BERT layers in 952 seconds. It reached 50% on fresh validation (previously 40.9%), but original validation fell from 90.34% to 87.38%, below the 88.34% floor. It also missed the required ten-point fresh-validation gain. All known product examples passed, but the statistical gates did not, so `artifacts/bert-v3/best` remains active. The candidate is retained for inspection. DFA unfamiliar-wording and composition errors are still a limitation.

The grammar decoder was adapted on 1,652 descriptions, with 1,267 train / 255 validation / 130 original test examples. Training took 73 seconds. Fresh CFG validation improved from 13.3% to 46.7%; original generated-test production accuracy remained 130/130, and all known grammar/compiler presets passed. The selected decoder is `artifacts/grammar-robust`, linked by fingerprint to the retained BERT encoder through `artifacts/active-grammar.json`. No symbolic English fallback was introduced.

The fresh test set is now unsealed and should be retired as an unbiased selection set for future adaptation. A later round needs a newly frozen test version. Evidence is in `artifacts/challenge-comparison.json`, `challenge-selection.json`, `challenge-test-before/`, `challenge-test-after/`, and `challenge-grammar-presets.json`.

## Final product checks and resources

All 79 automated tests passed, the frontend built successfully, and both real-BERT browser suites passed without page errors. HTTP checks passed acceptance/rejection, references, checkpoint gates, CFG ambiguity/epsilon, actual video exports and byte ranges. Failed grammar requests retain the actual BERT productions, and empty/error canvases use a status icon instead of a static example machine or tree.

The completed stage removed its 326 MiB activation cache and preserved prior checkpoints. Final checks reported about 6.6 GiB free storage, about 40% system memory availability and no thermal/performance warnings. There are no training jobs left running; the local product server remains available on port 8501. The full completion record is `artifacts/challenge-validation.json`.
