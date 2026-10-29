# BERT-based TOC and compiler engine

Implemented 29 October 2026. BERT interprets natural-language requests. Formal algorithms validate, execute, and visualize the predicted structures. **No handwritten English compiler, grammar-library lookup, or automatic symbolic repair replaces a failed BERT prediction.** Explicit user-supplied formal inputs and reference demonstrations remain separately labeled.

## What determines the visualization

A language specification determines a DFA's states, transitions and accepting states. A test word determines its execution path. For the language “ends with 01”, changing `1101` to `00` must retain the three-state machine while changing the path and acceptance. Changing the language to “ends with 0101” requires a different, five-state minimal machine.

The canvas consumes BERT's actual candidate. Its layout follows reachability levels for pattern and branching machines and uses circular arrangements for complete counter cycles. Transition labels come from the actual table. The shared geometry also drives video export. The interactive canvas supports 64 states; learned prediction and readable video export retain eight-state limits. An input-only simulation endpoint reuses the built machine instead of rerunning BERT and preserves the correct new word for later export.

A CFG and tokenized input determine the parse tree. Input edits trigger a new bounded parse after an initial success. Node count, terminal leaves and derivation steps come from that input. Illegal inputs fail explicitly. Empty productions show ε.

## Neural analysis and exact mathematical stages

DFA Studio uses the evaluated pretrained BERT encoder, a contextual extension and direct structured heads for state count, accepting bits and transition destinations. Natural-language requests always use this learned path. The handwritten baseline remains an offline research comparator; it is unavailable as a product prediction source. A wrong BERT candidate fails verification rather than being replaced with a constructed answer.

Grammar Lab adds a separately trained production-token decoder with two cross-attention layers over immutable BERT token features. At inference, English is encoded by BERT and the neural decoder predicts grammar tokens directly. The output is not selected from a grammar library or matched by English rules. The decoder is bounded to its trained grammar families and vocabulary; a malformed output fails visibly. Its frozen encoder is linked by a weight fingerprint so incompatible weights cannot be silently combined.

After prediction, exact stages handle the mathematics:

1. DFA structure checks and minimization; exact product-state equivalence when an independent reference is available.
2. Grammar-terminal tokenization, Earley parsing and independent verification of the selected derivation.
3. Nullable, FIRST/FOLLOW and predictive-table analysis for the actual productions.
4. Arithmetic parse-tree → AST → three-address code lowering, followed by independent symbolic reconstruction of the IR.
5. Diagrams and playback generated from those same structures and traces.

BERT is the basis for understanding the request. Exact algorithms make its outputs inspectable and catch errors. Neither structurally valid DFAs nor valid derivations prove agreement with arbitrary English. Candidate previews and grammar-language limitations remain visible. Reference demonstrations and manually supplied formal structures do not claim learned inference.

## Grammar and compiler UI

The default Grammar Lab source is **BERT language analysis → CFG**. Describe the intended language, supply an input, and inspect the actual generated productions. A separate formal-input source permits exact work with a CFG supplied directly by the user. Subsequent input-only changes reuse the BERT-generated productions and reparse the new word.

Grammar-terminal lexing uses longest match and character spans, so `aabb` and `id+id*id` do not require inserted spaces. Whitespace tokenization allows explicit boundaries for overlapping terminals. Lexical and parsing errors remain distinct.

The compiler-analysis tab computes nullable symbols, FIRST and FOLLOW fixed points, predictive-table entries and LL(1) conflicts. Conflicts are not presented as an ambiguity proof. Earley parsing handles left recursion and ambiguity with bounded enumeration. A tagged end marker distinguishes end of input from a literal `$` terminal.

The **Arithmetic compiler** preset supplies an English description for BERT's grammar decoder. Its predicted productions must match the compiler's supported expression grammar before lowering proceeds; a different prediction fails explicitly. The lexer handles identifiers, decimal numbers, binary `+ - * /`, unary signs and parentheses. The AST retains operator order and operands, while the IR uses explicit symbolic temporaries. An independent reconstruction pass checks operand order, arity and definitions. This is an expression compiler front end; it does not execute source or emit machine code.

## Training and evaluation

The DFA corpus grows from 3,207 to **6,275 descriptions / 696 canonical languages**: 4,889 train, 745 validation, and 641 test examples. Added supervision includes bit patterns through length six, forbidden substrings, singleton languages and bounded counts. Formal constructors generate labels. Independent string predicates and regex full matches validate their semantics.

All previous records and language splits are preserved. New equivalent-language groups receive stable hash-based splits. The audit reports zero canonical languages crossing partitions. Existing held-out languages cannot enter training through new paraphrases.

`configs/bert-v3.json` fine-tunes the top two pretrained BERT blocks and direct DFA heads from the previous real engine. Best-checkpoint selection uses validation equivalence, then validation loss. Both old and new models are evaluated on the same expanded test set; the original test subset is also compared. Promotion requires an expanded-test improvement and no regression on the original subset. No rules or compiler repairs enter learned scores.

The grammar decoder uses independently generated English/CFG supervision for balanced counts, balanced delimiters, palindromes, arbitrary words and ordered blocks over six supported terminal symbols. Arithmetic grammars are training fixtures and are excluded from held-out accuracy claims. Selection uses validation production-token accuracy then loss. Held-out production accuracy is **not** arbitrary CFG language-equivalence accuracy; equivalence between general CFGs is not decidable.

Reproduce after preparing the previous corpus and pretrained assets:

```sh
python -m theorybert.data.expand
python -m theorybert.training.local --config configs/bert-v3.json --initialize artifacts/bert-engine/best
python -m theorybert.evaluation.evaluate --checkpoint artifacts/bert-v3/best --dataset data/generated/english-dfa-v3.jsonl --output artifacts/bert-v3-evaluation
python -m theorybert.models.grammar --encoder artifacts/bert-v3/best
python -m pytest -q
cd frontend && npm run build
```

## Resource control

Heavy BERT jobs run sequentially at lower scheduling priority. Training uses two CPU threads and bounded MPS allocation, cached frozen layers and memory-mapped loads. Guards check available memory, swap growth and disk reserve. The first attempt stopped at its swap threshold; the restarted run reused the cache with lower memory pressure. Decoder training has a separate, tighter swap-growth allowance. Only regenerable caches created in this task are removed after training; existing user checkpoints and files are preserved. No paid service or hosted deployment is used.

## Research basis

- [BERT: original paper](https://aclanthology.org/N19-1423/) establishes bidirectional contextual language representations with task-specific output layers. Here, learned DFA heads and a production decoder consume BERT representations; formal checking does not replace language analysis.

- [Cornell: Automating Lexical Analysis](https://www.cs.cornell.edu/courses/cs4120/2023sp/notes/leximpl/) explains regex/NFA/DFA construction and transition-based execution. It supports keeping formal machinery independent from language-model predictions.
- [NLTK: Earley chart parser](https://www.nltk.org/api/nltk.parse.earleychart.html) documents the parser used to build trees; a separate checker verifies the actual derivation.
- [Cornell: Intermediate Representations](https://www.cs.cornell.edu/courses/cs4120/2023sp/notes/ir/) motivates lowering syntax trees into simpler IR.
- [Hugging Face: Fine-tuning a pretrained model](https://huggingface.co/docs/transformers/v4.57.1/en/training) describes supervised fine-tuning and evaluation. This project uses structured losses and exact automaton equivalence for DFA evaluation.
- [scikit-learn: Common pitfalls](https://scikit-learn.org/stable/common_pitfalls.html) documents data leakage and consistent processing. Prior language splits are frozen and audited before expansion.

## Evidence

`artifacts/v3-data-audit.json`, `bert-v3/training.csv`, `bert-v3/summary.json`, `v3-comparison.json`, `bert-v3-evaluation/`, and `bert-grammar/summary.json` record actual counts, training audits and measurements. Family, state-count and macro-language breakdowns accompany DFA results. Resource samples and cache cleanup are logged separately. `artifacts/dynamic-ui/` records real browser checks and screenshots.

## Recorded results — 29 October 2026

The new DFA checkpoint was selected at epoch 9 by validation equivalence (90.34%). Fine-tuning took 1,553 seconds. Upper pretrained BERT weights changed and frozen-weight fingerprints matched.

| Same held-out examples | Previous BERT | New BERT |
| --- | ---: | ---: |
| Original test: 379 descriptions / 26 languages | 62.53% exact equivalence | 90.24% exact equivalence |
| Expanded test: 641 descriptions / 74 languages | 36.97% exact equivalence | 87.68% exact equivalence |
| Expanded test: success within five, using independent reference | 47.43% | 93.45% |

The grammar cross-attention decoder scored 130/130 exact production-token outputs on the held-out generated grammar descriptions (13 grammars). Its scope is the generated families and six terminal symbols, with shared English templates across splits. This is a small development benchmark, not a claim of universal CFG synthesis. Arithmetic grammars are seen training fixtures. The initial pooled-feature decoder scored only 30% and is retained separately as a pilot; the production decoder was selected on validation results.

All 73 automated tests passed after removing symbolic English fallbacks. A real-browser run passed BERT-dependent DFA state changes, automatic traces, BERT grammar generation and input-dependent trees, BERT-generated arithmetic productions followed by AST/IR construction, and mobile layout, with no page errors. Five screenshots are in `artifacts/dynamic-ui/`.
