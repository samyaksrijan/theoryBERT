"""TheoryBERT · local verified visual learning workspace."""

import hashlib
import html
import importlib.util
import json
from pathlib import Path
import time
import pandas as pd
import streamlit as st
from theorybert.contracts import DFA, Status, strict_json
from theorybert.data.generators import benchmark_examples
from theorybert.formal.dfa import canonicalise, trace, validate
from theorybert.formal.cfg import EXAMPLES, parse, check_tree
from theorybert.pipeline import run_candidates
from theorybert.rendering.layout import dfa_svg, tree_svg, state_colour
from theorybert.rendering.renderer import render, seal_tree
from theorybert.ui.style import CSS

st.set_page_config(
    page_title="TheoryBERT · Verified visual learning", page_icon="◉", layout="wide"
)
st.html(CSS)
# Permanent shadow values survive Streamlit widget cleanup when switching modes.
for field in (
    "dfa_description",
    "dfa_string",
    "dfa_source",
    "cfg_grammar",
    "cfg_string",
):
    if field in st.session_state:
        st.session_state["saved_" + field] = st.session_state[field]
    elif "saved_" + field in st.session_state:
        st.session_state[field] = st.session_state["saved_" + field]

st.html(
    '<div class="tb-brand"><div class="tb-monogram">T</div><h1>TheoryBERT</h1><span class="tb-tag">Verified visual learning</span></div><p class="tb-intro">Explore formal languages. Check the mathematics. Watch the execution.</p>'
)


def fingerprint(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def section(number, text):
    st.html(
        f'<div class="tb-section"><span class="tb-step">{number}</span>{text}</div>'
    )


def status(title, detail, kind="neutral"):
    st.html(
        f'<div class="tb-status {kind}"><strong>{html.escape(title)}</strong><span>{html.escape(detail)}</span></div>'
    )


@st.cache_resource(show_spinner=False)
def load_model(path, stamp):
    from theorybert.models.theorybert import load_checkpoint
    from theorybert.baselines.predictors import Learned

    return Learned(*load_checkpoint(path))


@st.cache_data(show_spinner=False)
def cached_verification(candidate_dicts, reference_dict, provenance, source, budget):
    return run_candidates(
        [DFA.from_dict(d) for d in candidate_dicts],
        DFA.from_dict(reference_dict) if reference_dict else None,
        provenance,
        source,
        budget=budget,
    )


@st.cache_data(show_spinner=False)
def cached_trace(dfa_dict, symbols):
    return trace(DFA.from_dict(dfa_dict), symbols)


def choose_dfa(example):
    st.session_state["dfa_description"] = example["description"]
    st.session_state["dfa_string"] = example["test"]
    st.session_state["example_id"] = example["id"]


def choose_cfg(name):
    st.session_state["cfg_grammar"], st.session_state["cfg_string"] = EXAMPLES[name]


def table(d):
    rows = [
        {
            "State": s,
            "Role": ("Initial · " if s == d.start_state else "")
            + ("Accepting" if s in d.accept_states else "Non-accepting"),
            **d.transitions[s],
        }
        for s in d.states
    ]
    colours = {s: state_colour(i) for i, s in enumerate(d.states)}
    frame = pd.DataFrame(rows)
    st.dataframe(
        frame.style.map(
            lambda x: f"color: {colours.get(x, '#17243B')}; font-weight: 600",
            subset=["State"],
        ),
        hide_index=True,
        width="stretch",
    )


def branches(node):
    if node.children:
        yield node
    for child in node.children:
        yield from branches(child)


left, right = st.columns([0.43, 0.57], gap="large")
# Draw settings below the workspace, but execute them before workspace actions.
advanced = st.expander(
    "Advanced settings · checkpoints, reference & rendering", expanded=False
)
with advanced:
    a, b = st.columns(2, gap="large")
    with a:
        st.markdown("**Model & research configuration**")
        checkpoint = st.text_input(
            "Local checkpoint directory",
            value=json.loads(Path("artifacts/active-model.json").read_text())["checkpoint"] if Path("artifacts/active-model.json").is_file() else "",
            placeholder="artifacts/theorybert/best",
            key="checkpoint",
        )
        st.caption(
            "Learned inference: binary alphabet {0, 1}, up to 8 states. A smoke checkpoint is a mechanics test, not a research model."
        )
        budget = st.number_input(
            "Candidate budget",
            min_value=1,
            max_value=16,
            value=5,
            help="Best-first alternatives from model logits; no learned counterexample repair.",
        )
        parse_limit = st.number_input(
            "Maximum parse trees", min_value=1, max_value=10, value=5
        )
        st.caption(
            "Frozen backbone; trainable new-token embeddings, contextual extension and structured heads. Full experiments run from the command line."
        )
    with b:
        st.markdown("**Independent DFA reference**")
        upload = st.file_uploader("Upload reference DFA JSON", type=["json"])
        reference_text = st.text_area(
            "Or paste reference DFA JSON",
            height=100,
            placeholder='{"schema_version": "1.0", "states": …}',
            key="reference_text",
        )
        reference_error = None
        user_reference = None
        if upload is not None or reference_text.strip():
            try:
                raw = (
                    upload.getvalue().decode("utf-8")
                    if upload is not None
                    else reference_text
                )
                user_reference = DFA.from_dict(strict_json(raw))
                errors = validate(user_reference)
                if errors:
                    raise ValueError(" ".join(errors))
                if len(user_reference.states) > 64:
                    raise ValueError("Use at most 64 reference states.")
                st.caption(
                    "Reference loaded. You are responsible for grounding it independently in the intended language."
                )
            except (ValueError, UnicodeDecodeError) as exc:
                reference_error = str(exc)
                st.error(reference_error)
        quality = st.selectbox(
            "Video quality",
            ["preview", "high"],
            format_func=lambda x: (
                "Preview · 480p / 15 fps" if x == "preview" else "High · 1080p / 60 fps"
            ),
        )
        st.caption(
            "Local rendering only. Preview is faster; changing quality never retrains the model."
        )

with left:
    with st.container(key="work-input"):
        section("01", "Define your task")
        mode = (
            st.segmented_control(
                "Learning mode",
                ["TOC / DFA", "CFG / Parse tree"],
                default="TOC / DFA",
                width="stretch",
                key="mode",
            )
            or "TOC / DFA"
        )
        is_dfa = mode == "TOC / DFA"
        st.html('<div class="tb-kicker">Try an example</div>')
        if is_dfa:
            examples = benchmark_examples()
            with st.container(horizontal=True, gap="small"):
                for ex in examples:
                    st.button(ex["name"], on_click=choose_dfa, args=(ex,), key=ex["id"])
            description = st.text_area(
                "Language description",
                key="dfa_description",
                height=120,
                placeholder="e.g. Binary strings that end in 01.",
            )
            source = st.selectbox(
                "Prediction source",
                [
                    "TheoryBERT checkpoint",
                    "Reference demonstration",
                    "Incorrect candidate fixture",
                ],
                key="dfa_source",
                help="The source is always identified. Reference demonstrations do not run a learned model.",
            )
            symbols_text = st.text_input(
                "Test string",
                key="dfa_string",
                placeholder="e.g. 1101 · leave blank for ε",
                help="Binary characters with no spaces. Empty input is ε.",
            )
            selected = next(
                (
                    e
                    for e in examples
                    if e["id"] == st.session_state.get("example_id")
                    and description == e["description"]
                ),
                None,
            )
            reference = user_reference or (selected["dfa"] if selected else None)
            provenance = (
                "User-supplied independent reference"
                if user_reference
                else (f"Manual benchmark: {selected['id']}" if selected else None)
            )
            cp = Path(checkpoint).expanduser() if checkpoint else None
            checkpoint_ready = bool(
                cp and (cp / "config.json").is_file() and (cp / "weights.pt").is_file()
            )
            input_error = None
            if set(symbols_text) - set("01"):
                input_error = "Use only 0 and 1, with no spaces. Leave the field blank for the empty string."
            elif len(symbols_text) > 40:
                input_error = "Use at most 40 symbols for a readable animation."
            if input_error:
                st.error(input_error)
            blocked = None
            if not description.strip():
                blocked = "Choose an example or describe a binary language to begin."
            elif len(description) > 4000:
                blocked = "Shorten the description to at most 4,000 characters."
            elif source == "Reference demonstration" and not selected:
                blocked = "Choose an example chip to use its labelled reference demonstration."
            elif source == "TheoryBERT checkpoint" and not checkpoint_ready:
                blocked = "No checkpoint found. Set a checkpoint directory in Advanced settings, or select a reference demonstration."
            elif source == "Incorrect candidate fixture" and not reference:
                blocked = "Choose a benchmark or upload a reference for the deliberately incorrect fixture."
            elif reference_error:
                blocked = "Fix the reference JSON in Advanced settings."
            elif input_error:
                blocked = input_error
            if source == "Reference demonstration":
                st.caption("Source: reference demonstration · no learned prediction.")
            elif source == "Incorrect candidate fixture":
                st.caption(
                    "Source: deliberately incorrect fixture · accepting states are complemented. This is not a model result."
                )
            elif source == "Rule-based baseline":
                st.caption(
                    "Source: limited handwritten baseline · unsupported descriptions return an error."
                )
            if reference:
                st.caption("Verification: exact equivalence to " + provenance + ".")
            elif description:
                st.caption(
                    "An independent reference is required to unlock DFA animation. Prediction and structural checks are still available."
                )
            signature = fingerprint(
                {
                    "pipeline_schema": 2,
                    "mode": mode,
                    "description": description,
                    "string": symbols_text,
                    "source": source,
                    "checkpoint": checkpoint,
                    "stamp": (cp / "weights.pt").stat().st_mtime_ns
                    if checkpoint_ready
                    else None,
                    "reference": reference.to_dict() if reference else None,
                    "reference_input": fingerprint(
                        {
                            "upload": upload.getvalue().decode(
                                "utf-8", errors="replace"
                            )
                            if upload is not None
                            else None,
                            "text": reference_text,
                            "error": reference_error,
                            "provenance": provenance,
                        }
                    ),
                    "budget": budget,
                }
            )
            action = st.button(
                "Predict & verify"
                if source in ("TheoryBERT checkpoint", "Rule-based baseline")
                else "Verify & prepare",
                type="primary",
                width="stretch",
                disabled=bool(blocked),
                key="verify_dfa",
            )
            if blocked:
                st.caption(blocked)
        else:
            with st.container(horizontal=True, gap="small"):
                for name in EXAMPLES:
                    st.button(
                        name, on_click=choose_cfg, args=(name,), key="example-" + name
                    )
            grammar = st.text_area(
                "Context-free grammar",
                key="cfg_grammar",
                height=180,
                placeholder="S -> 'a' S 'b' |",
            )
            st.caption(
                "One production per line. Quote terminals; use | for alternatives and a blank right-hand side for ε."
            )
            tokens_text = st.text_input(
                "Input tokens",
                key="cfg_string",
                placeholder="a a b b",
                help="Separate every token with whitespace. Blank input means ε.",
            )
            st.caption(
                "Source: NLTK Earley parser · independent production and terminal-yield checker."
            )
            signature = fingerprint(
                {
                    "mode": mode,
                    "grammar": grammar,
                    "tokens": tokens_text,
                    "limit": parse_limit,
                }
            )
            blocked = (
                None
                if grammar.strip()
                else "Choose a grammar example or write a grammar to begin."
            )
            action = st.button(
                "Parse & verify",
                type="primary",
                width="stretch",
                disabled=bool(blocked),
                key="verify_cfg",
            )
            if blocked:
                st.caption(blocked)

result_key = "dfa_result" if is_dfa else "cfg_result"
error_key = result_key + "_error"
if action:
    # Clear the prior success before any operation that might fail.
    st.session_state.pop(result_key, None)
    st.session_state.pop(error_key, None)
    progress_slot = right.empty()
    with progress_slot.container():
        with st.status("Predicting → Verifying → Rendering", expanded=True) as progress:
            try:
                started = time.perf_counter()
                if is_dfa:
                    st.write("1 · Predicting candidate structure")
                    if source == "Reference demonstration":
                        candidates = [DFA.from_dict(selected["dfa"].to_dict())]
                    elif source == "Incorrect candidate fixture":
                        candidate = DFA.from_dict(reference.to_dict())
                        candidate.accept_states = [
                            s
                            for s in candidate.states
                            if s not in candidate.accept_states
                        ]
                        candidates = [candidate]
                    elif source == "Rule-based baseline":
                        from theorybert.baselines.predictors import RuleBased

                        candidates = list(RuleBased().predict(description, int(budget)))
                    else:
                        predictor = load_model(
                            str(cp), (cp / "weights.pt").stat().st_mtime_ns
                        )
                        st.write("Checkpoint: " + predictor.source)
                        candidates = list(predictor.predict(description, int(budget)))
                    st.write("2 · Verifying structure and exact language equivalence")
                    result = cached_verification(
                        [d.to_dict() for d in candidates],
                        reference.to_dict() if reference else None,
                        provenance,
                        source,
                        int(budget),
                    )
                    execution = (
                        cached_trace(
                            canonicalise(result.verified.checked()).to_dict(),
                            list(symbols_text),
                        )
                        if result.verified
                        else None
                    )
                    stored = {
                        "signature": signature,
                        "result": result,
                        "trace": execution,
                        "video": None,
                        "elapsed": time.perf_counter() - started,
                        "source": predictor.source
                        if source == "TheoryBERT checkpoint"
                        else source,
                    }
                else:
                    st.write("1 · Parsing with the Earley algorithm")
                    spec, trees, truncated = parse(
                        grammar, tokens_text.split(), int(parse_limit)
                    )
                    st.write(
                        "2 · Checking each production, root and terminal yield independently"
                    )
                    stored = {
                        "signature": signature,
                        "spec": spec,
                        "trees": trees,
                        "truncated": truncated,
                        "video": None,
                        "source": "NLTK Earley + independent tree checker",
                        "elapsed": time.perf_counter() - started,
                    }
                st.session_state[result_key] = stored
                progress.update(
                    label=(
                        "Verification complete · render when ready"
                        if not is_dfa or result.verified
                        else "Checks complete · review verification evidence"
                    ),
                    state="complete",
                    expanded=False,
                )
            except Exception as exc:
                st.session_state[error_key] = {
                    "signature": signature,
                    "message": str(exc),
                    "kind": getattr(exc, "kind", "INPUT_OR_RUNTIME_ERROR"),
                }
                progress.update(
                    label="Unable to complete verification",
                    state="error",
                    expanded=False,
                )

    progress_slot.empty()

stored = st.session_state.get(result_key)
current = stored is not None and stored["signature"] == signature
err = st.session_state.get(error_key)
with right:
    with st.container(key="work-result"):
        section("02", "Explore the result")
        st.html(
            '<div class="tb-pipeline">Predicting <b>→</b> Verifying <b>→</b> Rendering</div>'
        )
        evidence = None
        execution = None
        tree = None
        tree_index = 0
        preview_error = None
        if err and err["signature"] == signature:
            status(
                "Verification could not complete",
                err["kind"].replace("_", " ").capitalize(),
                "failed",
            )
            st.error(err["message"])
            with left:
                st.error(err["message"])
        elif stored and not current:
            status(
                "Inputs changed · verify again",
                "The previous result is out of date. Run verification to update the evidence and animation.",
                "pending",
            )
        elif not current:
            status(
                "Ready when you are",
                "Animation unlocks after the applicable verification checks pass.",
            )
            st.html(
                '<div class="tb-empty"><div class="tb-symbol">q₀ → q₁</div><h3>Make the theory visible.</h3><p>Choose an example on the left, verify its structure, then follow every transition or derivation in a local animation.</p></div>'
            )
            st.caption(
                "DFA: exact equivalence to an independent reference. CFG: a legal derivation of the supplied tokens."
            )
        elif is_dfa:
            result = stored["result"]
            report = result.reports[-1] if result.reports else None
            if result.verified:
                evidence = result.verified
                execution = stored["trace"]
                d = canonicalise(evidence.checked())
                status(
                    "✓ Verified DFA; test string "
                    + ("accepted." if execution.accepted else "rejected."),
                    "Exact equivalence to the independent reference. "
                    + str(report.original_states)
                    + " states → "
                    + str(report.minimised_states)
                    + " minimal.",
                    "verified",
                )
                st.html(
                    f'<div class="tb-meta">Source: {html.escape(stored["source"])}<br>Scope: {html.escape(report.reference_provenance or "independent reference")}</div>'
                )
                if not stored.get("video") or stored.get("quality") != quality:
                    step = (
                        st.slider(
                            "Execution step",
                            0,
                            len(execution.steps),
                            0,
                            key="dfa_scrub_" + signature,
                        )
                        if execution.steps
                        else 0
                    )
                    active = (
                        execution.initial_state
                        if step == 0
                        else execution.steps[step - 1].destination
                    )
                    previous = execution.steps[step - 1] if step else None
                    try:
                        st.image(
                            dfa_svg(
                                d,
                                active,
                                (previous.source, previous.symbol)
                                if previous
                                else None,
                            ),
                            width="stretch",
                            alt=f"Verified minimal DFA, current state {active}. Double rings indicate accepting states.",
                        )
                    except ValueError as exc:
                        preview_error = str(exc)
                    if preview_error is None:
                        st.caption(
                            "Arrow: initial state · double ring: accepting state. Open the image fullscreen for a closer view."
                        )
                    if execution.symbols:
                        st.html(
                            "<div>"
                            + "".join(
                                f'<span class="tb-token {"current" if i == step - 1 else ""}">{html.escape(s)}</span>'
                                for i, s in enumerate(execution.symbols)
                            )
                            + "</div>"
                        )
                    st.caption(
                        "Minimal machine · BFS state names. Original prediction is available below."
                    )
                    st.caption(
                        f"Step {step} of {len(execution.steps)} · active state {active}"
                        + (" · empty input ε" if not execution.symbols else "")
                    )
                    explanation = (
                        f"Read {previous.symbol}: {previous.source} → {previous.destination}."
                        if previous
                        else f"Start in {execution.initial_state}. No symbols consumed yet."
                    )
                    if step == len(execution.steps):
                        explanation += (
                            f" {active} is an accepting state, so the input is ACCEPTED."
                            if execution.accepted
                            else f" {active} is not an accepting state, so the input is REJECTED."
                        )
                    elif execution.symbols:
                        explanation += f" Next symbol: {execution.symbols[step]}."
                    st.html(
                        '<div class="tb-explanation">'
                        + html.escape(explanation)
                        + "</div>"
                    )
            elif report:
                if report.status == Status.REFERENCE_UNAVAILABLE:
                    status(
                        "! Structure valid; semantic equivalence unverified.",
                        report.message,
                        "pending",
                    )
                elif report.status == Status.RESOURCE_LIMIT:
                    status(
                        "! Prediction or verification limit reached.",
                        report.message,
                        "pending",
                    )
                elif report.status == Status.INTERNAL_ERROR:
                    status(
                        "× Verification could not complete.", report.message, "failed"
                    )
                else:
                    status(
                        "× Candidate rejected by verifier.", report.message, "failed"
                    )
                st.caption("Source: " + stored["source"])
                if report.counterexample is not None:
                    witness = "".join(report.counterexample) or "ε (empty string)"
                    st.error("Shortest counterexample: " + witness)
                if report.structural_errors:
                    st.error(" ".join(report.structural_errors))
                st.html(
                    '<div class="tb-empty"><h3>Verification is the gate.</h3><p>Review the evidence below. A candidate can be animated only after exact equivalence has been established.</p></div>'
                )
        else:
            trees = stored["trees"]
            if len(trees) > 1:
                tree_index = st.selectbox(
                    "Verified parse tree",
                    range(len(trees)),
                    index=stored.get("selected_tree_index", 0),
                    format_func=lambda i: f"Tree {i + 1} of {len(trees)}",
                    key="tree-choice-" + signature,
                )
                stored["selected_tree_index"] = tree_index
            tree = trees[tree_index]
            evidence = seal_tree(stored["spec"], tree)
            status(
                "✓ Verified parse tree",
                "Root, productions and terminal yield checked independently.",
                "verified",
            )
            st.caption(
                f"{len(trees)} tree{'s' if len(trees) != 1 else ''} found"
                + (
                    " · enumeration capped; more may exist."
                    if stored["truncated"]
                    else ". Finding one tree does not prove the grammar is unambiguous."
                )
            )
            if (
                not stored.get("video")
                or stored.get("quality") != quality
                or stored.get("tree_index") != tree_index
            ):
                try:
                    st.image(
                        tree_svg(tree),
                        width="stretch",
                        alt="Verified parse tree. Every expansion belongs to the supplied grammar.",
                    )
                except ValueError as exc:
                    preview_error = str(exc)
                if preview_error is None:
                    branch_options = list(branches(tree))
                    if len(branch_options) > 1:
                        with st.expander("Inspect a branch"):
                            branch = st.selectbox(
                                "Subtree root",
                                range(len(branch_options)),
                                format_func=lambda i: (
                                    f"{branch_options[i].symbol} · {branch_options[i].node_id}"
                                ),
                                key=f"branch-{signature}-{tree_index}",
                            )
                            st.image(
                                tree_svg(branch_options[branch]),
                                width="stretch",
                                alt=f"Branch rooted at {branch_options[branch].symbol}, node {branch_options[branch].node_id}.",
                            )
                            st.caption(
                                "Choose a lower branch to read its labels at a larger size. Node IDs match the derivation evidence."
                            )
            st.caption(
                "Terminal yield: " + " ".join(stored["spec"].input_tokens or ["ε"])
            )
        # Old videos never survive an input or tree change.
        video_ready = bool(
            current
            and stored.get("video")
            and stored.get("quality") == quality
            and (is_dfa or stored.get("tree_index") == tree_index)
        )
        if video_ready:
            st.video(
                str(stored["video"]),
                alt="Manim animation of the verified execution or derivation. The same steps are available in the trace tab.",
            )
            st.caption(
                "Local Manim render · "
                + quality
                + " quality"
                + (
                    " · retrieved from cache"
                    if stored.get("cache_hit")
                    else f" · {stored.get('render_seconds', 0):.1f}s"
                )
            )
        render_error = preview_error
        if evidence is not None and render_error is None:
            try:
                from theorybert.rendering.renderer import payload_for

                payload_for(evidence, list(symbols_text) if is_dfa else None)
            except ValueError as exc:
                render_error = str(exc)
        if render_error:
            st.warning(render_error)
        available = importlib.util.find_spec("manim") is not None
        render_clicked = st.button(
            "Render animation" if not video_ready else "Render again",
            type="primary" if evidence is not None else "secondary",
            width="stretch",
            disabled=not bool(evidence) or not available or bool(render_error),
            key="render_animation",
        )
        if not current or evidence is None:
            st.caption(
                "Rendering is available after successful verification of the current inputs."
            )
        elif not available:
            st.caption(
                "Manim is missing. Install project dependencies using the README instructions."
            )
        if render_clicked:
            stored["video"] = None
            with st.status(
                "Rendering · building your verified animation", expanded=True
            ) as progress:
                st.write(
                    "3 · Rendering the checked execution trace with Manim. Preview usually takes a few seconds."
                )
                try:
                    path, seconds, hit = render(
                        evidence, list(symbols_text) if is_dfa else None, quality
                    )
                    stored.update(
                        video=str(path),
                        render_seconds=seconds,
                        cache_hit=hit,
                        quality=quality,
                        tree_index=tree_index,
                    )
                    progress.update(
                        label="Animation ready", state="complete", expanded=False
                    )
                    st.rerun()
                except (RuntimeError, ValueError, TypeError) as exc:
                    st.error(str(exc))
                    progress.update(label="Rendering could not complete", state="error")
        if video_ready:
            st.download_button(
                "Download video",
                Path(stored["video"]).read_bytes(),
                file_name="theorybert-animation.mp4",
                mime="video/mp4",
                width="stretch",
            )

if current:
    st.write("")
    evidence_tab, structure_tab, trace_tab, history_tab = st.tabs(
        [
            "Verification evidence",
            "Transition tables" if is_dfa else "Grammar & tree",
            "Execution trace" if is_dfa else "Derivation steps",
            "Candidate history" if is_dfa else "Parse details",
        ]
    )
    with evidence_tab:
        st.caption("Evidence for the current inputs · " + stored["source"])
        if is_dfa:
            reports = [r.to_dict() for r in stored["result"].reports]
            for r in stored["result"].reports:
                st.caption(f"Attempt {r.attempt} · {r.status.value}")
                for check in r.checks:
                    st.write("• " + check)
                st.write(r.message)
            if not reports:
                st.warning("No candidate was produced within the budget.")
            st.json(reports, expanded=False)
            export = {
                "description": description,
                "source": stored["source"],
                "candidate": stored["result"].candidate.to_dict()
                if stored["result"].candidate
                else None,
                "first_prediction": stored["result"].attempted_candidates[0].to_dict()
                if stored["result"].attempted_candidates
                else None,
                "candidate_history": [
                    d.to_dict() for d in stored["result"].attempted_candidates
                ],
                "reference": reference.to_dict() if reference else None,
                "reports": reports,
                "trace": stored["trace"].to_dict() if stored["trace"] else None,
            }
        else:
            errors, steps = check_tree(stored["spec"], tree)
            st.write(
                "✓ Root matches start symbol\n\n✓ Every production belongs to the supplied grammar\n\n✓ Terminal yield equals the input tokens\n\n✓ Stable node IDs are unique"
            )
            export = {
                "source": stored["source"],
                "grammar": stored["spec"].to_dict(),
                "tree": tree.to_dict(),
                "derivation": steps,
                "verification_errors": errors,
            }
        st.download_button(
            "Download verification evidence",
            json.dumps(export, indent=2, ensure_ascii=False),
            file_name="theorybert-evidence.json",
            mime="application/json",
        )
    with structure_tab:
        if is_dfa and stored["result"].candidate:
            d = stored["result"].candidate
            attempts = stored["result"].attempted_candidates
            st.markdown("**First prediction**")
            table(attempts[0])
            if len(attempts) > 1:
                st.markdown("**Last checked candidate**")
                table(d)
            if not validate(d):
                st.markdown("**Minimised checked candidate**")
                table(canonicalise(d))
        elif not is_dfa:
            st.code(grammar, language="text")
            st.json(tree.to_dict(), expanded=False)
    with trace_tab:
        if is_dfa:
            tr = stored["trace"]
            if tr:
                st.caption(
                    f"Initial state {tr.initial_state} · final state {tr.final_state} · "
                    + ("ACCEPT" if tr.accepted else "REJECT")
                )
                if tr.steps:
                    st.dataframe(
                        [
                            {
                                "Position": s.position + 1,
                                "Source": s.source,
                                "Symbol": s.symbol,
                                "Destination": s.destination,
                            }
                            for s in tr.steps
                        ],
                        hide_index=True,
                        width="stretch",
                    )
                else:
                    st.write("Empty input: no transitions are taken.")
            else:
                st.info(
                    "A verified execution trace is available after exact equivalence passes."
                )
        else:
            st.dataframe(steps, hide_index=True, width="stretch")
    with history_tab:
        if is_dfa:
            st.dataframe(
                [
                    {
                        "Attempt": r.attempt,
                        "Status": r.status.value,
                        "Counterexample": ("".join(r.counterexample) or "ε")
                        if r.counterexample is not None
                        else "—",
                        "Time (ms)": round(r.elapsed_seconds * 1000, 2),
                    }
                    for r in stored["result"].reports
                ],
                hide_index=True,
                width="stretch",
            )
            attempts = stored["result"].attempted_candidates
            if attempts:
                with st.expander("Inspect candidate structures"):
                    attempt = st.selectbox(
                        "Candidate attempt",
                        range(len(attempts)),
                        format_func=lambda i: f"Attempt {i + 1}",
                        key="candidate-choice-" + signature,
                    )
                    st.json(attempts[attempt].to_dict(), expanded=False)
        else:
            st.write(
                {
                    "trees_found": len(stored["trees"]),
                    "enumeration_capped": stored["truncated"],
                    "parse_and_check_seconds": round(stored["elapsed"], 3),
                    "tokenisation": "Whitespace-separated terminals; blank input is ε.",
                }
            )

st.html(
    '<div class="tb-foot">TheoryBERT · Local research prototype<br>Learned DFA inference requires a checkpoint. Reference demonstrations and deterministic CFG parsing work without training. Research accuracy and initialisation ablations have not been established.</div>'
)
