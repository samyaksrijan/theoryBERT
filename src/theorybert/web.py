"""Local React product API. The server owns every renderable verification object."""

import argparse
from collections import OrderedDict
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import importlib.util
import json
import os
from pathlib import Path
import re
import threading
import time
import uuid

from starlette.applications import Starlette
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Route

from theorybert.contracts import DFA, strict_json
from theorybert.data.generators import benchmark_examples
from theorybert.formal.cfg import EXAMPLES, check_tree, parse
from theorybert.formal.dfa import canonicalise, trace, validate
from theorybert.formal.analysis import machine_analysis, grammar_analysis, tokenize_input
from theorybert.pipeline import run_candidates
from theorybert.models.predictor import checkpoint_weights, load_predictor
from theorybert.rendering.layout import graph_layout, tree_layout
from theorybert.rendering.renderer import payload_for, render, seal_tree

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "frontend" / "dist"
VIDEO_CACHE = ROOT / "artifacts" / "videos"
workers = ThreadPoolExecutor(
    max_workers=max(1, int(os.environ.get("THEORYBERT_WORKERS", "2"))),
    thread_name_prefix="theorybert",
)
MAX_JOBS = max(1, int(os.environ.get("THEORYBERT_MAX_JOBS", "4")))
lock = threading.RLock()
jobs = OrderedDict()
results = OrderedDict()


def active_checkpoint():
    """Only an explicitly activated, evaluated real model becomes the default."""
    try:
        active = json.loads((ROOT / "artifacts" / "active-model.json").read_text())
        path = ROOT / active["checkpoint"]
        config = json.loads((path / "config.json").read_text())
        if not checkpoint_weights(path).is_file() or "smoke" in config.get("training_status", ""):
            return None
        return active
    except (OSError, ValueError, KeyError):
        return None


def graph_data(dfa):
    nodes, edges = graph_layout(dfa)
    return {"nodes": nodes, "edges": edges}


def active_grammar():
    pointer = ROOT / "artifacts/active-grammar.json"
    if pointer.is_file():
        try:
            active = json.loads(pointer.read_text())
            path = ROOT / active["checkpoint"]
        except (OSError, ValueError, KeyError):
            return None
    else:
        active = {"checkpoint": "artifacts/bert-grammar", "summary": "artifacts/bert-grammar/summary.json"}
        path = ROOT / active["checkpoint"]
    return active if (path / "head.pt").is_file() and (path / "config.json").is_file() else None


def tree_data(tree):
    nodes, links, positions = tree_layout(tree)
    return {
        "nodes": {k: v.to_dict() for k, v in nodes.items()},
        "links": links,
        "positions": positions,
    }


@lru_cache(maxsize=1)
def encoder_checkpoint(path, weights_stamp, config_stamp):
    import torch
    from theorybert.models.theorybert import load_checkpoint
    torch.set_num_threads(max(1, int(os.environ.get("THEORYBERT_TORCH_THREADS", "1" if os.environ.get("THEORYBERT_HOSTED") == "1" else "2"))))
    return load_checkpoint(path)[:2]


def shared_encoder(path):
    path = Path(path).resolve()
    return encoder_checkpoint(str(path), (path / "weights.pt").stat().st_mtime_ns,
                              (path / "config.json").stat().st_mtime_ns)


@lru_cache(maxsize=1)
def learned_checkpoint(path, weights_stamp, config_stamp):
    return load_predictor(path, shared_encoder)


def reference_for(data, selected):
    text = data.get("reference_json", "").strip()
    if text:
        if len(text) > 120000:
            raise ValueError("Use a reference JSON file smaller than 120 KB.")
        reference = DFA.from_dict(strict_json(text))
        errors = validate(reference)
        if errors:
            raise ValueError("Reference: " + " ".join(errors))
        if len(reference.states) > 64:
            raise ValueError("Use at most 64 reference states.")
        return reference, "User-supplied independent reference"
    return (
        (selected["dfa"], f"Benchmark · {selected['name']}")
        if selected
        else (None, None)
    )


@lru_cache(maxsize=1)
def learned_grammar(path, head_stamp, encoder_stamp):
    from theorybert.models.grammar import GrammarPredictor
    config = json.loads((Path(path) / "config.json").read_text())
    base = ROOT / config["encoder_checkpoint"]
    return GrammarPredictor(path, shared_encoder(base))


def solve_dfa(data, phase):
    description = data.get("description", "").strip()
    text = data.get("input", "")
    source = data.get("source", "learned")
    if source == "manual" and not description:
        description = "User-supplied DFA"
    budget = int(data.get("budget", 5))
    if not description or len(description) > 4000:
        raise ValueError("Describe your language in 1–4,000 characters.")
    if not isinstance(text, str) or set(text) - set("01"):
        raise ValueError(
            "The test string can contain only 0 and 1. Leave it blank for ε."
        )
    if len(text) > 40:
        raise ValueError("Use at most 40 input symbols for readable playback.")
    if not 1 <= budget <= 16:
        raise ValueError("Choose a candidate budget between 1 and 16.")
    selected = next(
        (
            e
            for e in benchmark_examples()
            if e["id"] == data.get("example_id") and e["description"] == description
        ),
        None,
    )
    reference, provenance = reference_for(data, None if source == "manual" else selected)
    prediction_budget = budget if reference is not None else 1
    phase("predicting")
    plans = []
    if source == "demo":
        if not selected:
            raise ValueError(
                "Choose a benchmark example for a reference demonstration, or switch prediction source."
            )
        candidates, identity = (
            [DFA.from_dict(selected["dfa"].to_dict())],
            "Reference demonstration · no learned inference",
        )
    elif source == "incorrect":
        if reference is None:
            raise ValueError(
                "Choose a benchmark or provide a reference for the incorrect-candidate fixture."
            )
        candidate = DFA.from_dict(reference.to_dict())
        candidate.accept_states = [
            s for s in candidate.states if s not in candidate.accept_states
        ]
        candidates, identity = (
            [candidate],
            "Deliberately incorrect fixture · complemented accepting states",
        )
    elif source == "manual":
        raw = data.get("candidate_json", "")
        if not isinstance(raw, str) or not raw.strip() or len(raw) > 120000:
            raise ValueError("Paste your DFA JSON, up to 120 KB.")
        candidate = DFA.from_dict(strict_json(raw))
        errors = validate(candidate)
        if errors:
            raise ValueError("Your DFA: " + " ".join(errors))
        if set(candidate.alphabet) != {"0", "1"} or len(candidate.states) > 64:
            raise ValueError("This studio supports alphabet [0, 1] and at most 64 states.")
        candidates, identity = [candidate], "User-supplied DFA · structural validation and simulation"
    elif source == "learned":
        active = active_checkpoint()
        requested = data.get("checkpoint", "") or (active["checkpoint"] if active else "")
        path = Path(requested).expanduser()
        if not path.is_absolute():
            path = ROOT / path
        if not (path / "config.json").is_file() or not checkpoint_weights(path).is_file():
            raise ValueError(
                "No checkpoint found. Choose a local checkpoint in Settings or use a reference demonstration."
            )
        config = json.loads((path / "config.json").read_text())
        if "smoke" in config.get("training_status", "") or "tiny-random" in config.get("backbone", ""):
            raise ValueError("This is a random-backbone smoke checkpoint, not a trained pretrained BERT model. Select the evaluated real model.")
        predictor = learned_checkpoint(
            str(path.resolve()),
            checkpoint_weights(path).stat().st_mtime_ns,
            (path / "config.json").stat().st_mtime_ns,
        )
        if hasattr(predictor, "predict_with_plans"):
            plans = predictor.predict_with_plans(description, prediction_budget)
            candidates = [p["dfa"] for p in plans]
        else:
            candidates = list(predictor.predict(description, prediction_budget))
        identity = predictor.source
    else:
        raise ValueError("Choose a supported prediction source.")
    phase("verifying")
    result = run_candidates(candidates, reference, provenance, identity, budget)
    public = {
        "mode": "dfa",
        "prediction_source": source,
        "source": identity,
        "description": description,
        "language_plan": next((p["plan"].to_dict() for p in plans if result.candidate and p["dfa"].to_dict() == result.candidate.to_dict()), None),
        "input": text,
        "reports": [r.to_dict() for r in result.reports],
        "status": result.reports[-1].status.value,
        "candidate": result.candidate.to_dict() if result.candidate else None,
        "attempted_candidates": [d.to_dict() for d in result.attempted_candidates],
        "reference": reference.to_dict() if reference else None,
        "provenance": provenance,
        "verified": result.verified is not None,
        "trace": None,
        "dfa": None,
        "graph": None,
        "renderable": False,
        "visual_error": None,
    }
    if result.candidate and not validate(result.candidate):
        public["minimised_candidate"] = canonicalise(result.candidate).to_dict()
    if result.verified:
        dfa = result.verified.checked() if source == "manual" else canonicalise(result.verified.checked())
        public["dfa"] = dfa.to_dict()
        public["trace"] = trace(dfa, list(text)).to_dict()
        try:
            public["graph"] = graph_data(dfa)
            payload_for(result.verified, list(text))
            public["renderable"] = importlib.util.find_spec("manim") is not None
        except ValueError as exc:
            public["visual_error"] = str(exc)
    elif result.candidate and not validate(result.candidate) and public["status"] == "REFERENCE_UNAVAILABLE":
        # Inspection and simulation do not constitute a proof against English.
        dfa = result.candidate if source == "manual" else canonicalise(result.candidate)
        public["dfa"] = dfa.to_dict()
        public["trace"] = trace(dfa, list(text)).to_dict()
        notice = "Your supplied DFA: structure checked; simulation follows your transitions. " if source == "manual" else "BERT candidate preview: structure checked. "
        public["visualization_notice"] = notice + "Equivalence to an independent reference has not been established."
        try:
            public["graph"] = graph_data(dfa)
        except ValueError as exc:
            public["visual_error"] = str(exc)
    if public["dfa"]:
        public["analysis"] = machine_analysis(DFA.from_dict(public["dfa"]), list(text))
    return public, {"evidence": result.verified, "symbols": list(text)}


def solve_cfg(data, phase):
    grammar, text = data.get("grammar", ""), data.get("input", "")
    grammar_source = data.get("grammar_source", "supplied")
    description = data.get("description", "")
    neural_source = None
    if grammar_source == "learned":
        with lock:
            previous = results.get(data.get("grammar_result_id"))
        active = active_grammar()
        if active is None:
            raise ValueError("No trained BERT grammar decoder is installed. Train the grammar model; no example grammar will be substituted.")
        path = ROOT / active["checkpoint"]
        revision = (path / "head.pt").stat().st_mtime_ns
        reusable = previous and previous["public"].get("grammar_source") == "learned" and previous["public"].get("description") == description and previous["public"].get("grammar_model_checkpoint") == active["checkpoint"] and previous["public"].get("grammar_model_revision") == revision
        config = json.loads((path / "config.json").read_text())
        base = ROOT / config["encoder_checkpoint"]
        if reusable:
            grammar = previous["public"]["grammar"]
            neural_source = previous["private"]["neural_source"]
        else:
            phase("predicting")
            predictor = learned_grammar(str(path), (path / "head.pt").stat().st_mtime_ns, (base / "weights.pt").stat().st_mtime_ns)
            grammar = predictor.predict(description)
            neural_source = predictor.source
    elif grammar_source != "supplied":
        raise ValueError("Choose BERT generation or a supplied formal CFG.")
    limit = int(data.get("limit", 5))
    phase("parsing")
    tokenization = data.get("tokenization", "literal")
    try:
        if tokenization == "expression":
            from theorybert.formal.compiler import ARITHMETIC_GRAMMAR, lex_expression
            from theorybert.models.grammar import grammar_identity
            if grammar_identity(grammar) != grammar_identity(ARITHMETIC_GRAMMAR):
                raise ValueError("The arithmetic compiler uses its displayed precedence grammar. Choose the Arithmetic compiler preset again, or select grammar-terminal tokenization for a custom grammar.")
            lexemes = lex_expression(text)
        else:
            lexemes = tokenize_input(grammar, text, tokenization)
        spec, trees, truncated = parse(
            grammar,
            [row["token"] for row in lexemes],
            limit,
            timeout=min(60, max(1, float(os.environ.get("THEORYBERT_PARSE_TIMEOUT", "8")))),
        )
    except ValueError as exc:
        if neural_source:
            exc.candidate_grammar = grammar
        raise
    phase("verifying")
    displays, steps, errors = [], [], []
    for tree in trees:
        issues, derivation = check_tree(spec, tree)
        if issues:
            raise ValueError(
                "Independent tree checker rejected the derivation: " + "; ".join(issues)
            )
        steps.append(derivation)
        try:
            displays.append(tree_data(tree))
            errors.append(None)
        except ValueError as exc:
            displays.append(None)
            errors.append(str(exc))
    public = {
        "mode": "cfg",
        "source": (neural_source + " → " if neural_source else "") + "NLTK Earley · independent derivation checker",
        "grammar_source": grammar_source,
        "grammar_model_checkpoint": active["checkpoint"] if neural_source else None,
        "grammar_model_revision": revision if neural_source else None,
        "description": description,
        "language_notice": "BERT generated these productions from your description. The selected derivation is independently checked; equivalence between the grammar and arbitrary English has not been proved." if neural_source else None,
        "status": "VERIFIED",
        "verified": True,
        "grammar": grammar,
        "input": text,
        "spec": spec.to_dict(),
        "lexemes": lexemes,
        "tokenization": tokenization,
        "analysis": grammar_analysis(spec),
        "trees": [t.to_dict() for t in trees],
        "layouts": displays,
        "steps": steps,
        "truncated": truncated,
        "visual_errors": errors,
        "renderable": importlib.util.find_spec("manim") is not None,
    }
    if tokenization == "expression":
        from theorybert.formal.compiler import compile_expression
        compiler, ast = compile_expression(trees[0], lexemes)
        try:
            compiler["layout"] = tree_data(ast)
        except ValueError as exc:
            compiler["visual_error"] = str(exc)
        public["compiler"] = compiler
    return public, {"spec": spec, "trees": trees, "neural_source": neural_source}


def run_job(job_id, kind, data):
    started = time.perf_counter()

    def phase(value):
        with lock:
            jobs[job_id]["phase"] = value

    try:
        if kind == "render":
            phase("rendering")
            with lock:
                item = results.get(data.get("result_id"))
            if item is None:
                raise ValueError(
                    "This session has expired. Verify the current inputs again before exporting a video."
                )
            tree_index = int(data.get("tree_index", 0))
            if item["public"]["mode"] == "dfa":
                evidence, symbols = (
                    item["private"]["evidence"],
                    item["private"]["symbols"],
                )
            else:
                trees = item["private"]["trees"]
                if not 0 <= tree_index < len(trees):
                    raise ValueError("Choose an available parse tree.")
                evidence, symbols = (
                    seal_tree(item["private"]["spec"], trees[tree_index]),
                    None,
                )
            path, seconds, hit = render(
                evidence, symbols, data.get("quality", "preview"), cache_dir=VIDEO_CACHE
            )
            response = {
                "url": f"/api/videos/{path.name}",
                "seconds": seconds,
                "cache_hit": hit,
                "quality": data.get("quality", "preview"),
                "tree_index": tree_index,
            }
        else:
            public, private = (
                solve_dfa(data, phase) if kind == "dfa" else solve_cfg(data, phase)
            )
            result_id = uuid.uuid4().hex
            public.update(
                id=result_id,
                elapsed_seconds=time.perf_counter() - started,
                created_at=time.time(),
            )
            with lock:
                results[result_id] = {"public": public, "private": private}
                while len(results) > 128:
                    results.popitem(last=False)
            response = public
        with lock:
            jobs[job_id].update(phase="complete", status="complete", result=response)
    except Exception as exc:
        with lock:
            jobs[job_id].update(
                phase="error",
                status="error",
                error=str(exc),
                error_kind=getattr(exc, "kind", "INPUT_OR_RUNTIME_ERROR"),
                candidate_grammar=getattr(exc, "candidate_grammar", None),
            )


async def submit(request):
    try:
        raw = await request.body()
        if len(raw) > 160000:
            return JSONResponse(
                {
                    "error": "Request too large. Keep reference and grammar inputs under 120 KB."
                },
                status_code=413,
            )
        data = strict_json(raw.decode())
        if not isinstance(data, dict) or data.get("kind") not in (
            "dfa",
            "cfg",
            "render",
        ):
            raise ValueError("Choose a DFA, grammar, or render task.")
        with lock:
            if sum(j["status"] == "running" for j in jobs.values()) >= MAX_JOBS:
                return JSONResponse(
                    {
                        "error": "The local engine is busy. Wait for the current task to finish."
                    },
                    status_code=429,
                )
            job_id = uuid.uuid4().hex
            jobs[job_id] = {"id": job_id, "status": "running", "phase": "queued"}
            while len(jobs) > 256:
                completed = next(
                    (k for k, j in jobs.items() if j["status"] != "running"), None
                )
                if completed is None:
                    break
                del jobs[completed]
        workers.submit(run_job, job_id, data["kind"], data)
        return JSONResponse({"job_id": job_id}, status_code=202)
    except (ValueError, UnicodeDecodeError) as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


async def job_status(request):
    with lock:
        job = jobs.get(request.path_params["job_id"])
        return (
            JSONResponse(dict(job))
            if job
            else JSONResponse(
                {"error": "Task not found. Please try again."}, status_code=404
            )
        )


async def simulate(request):
    """Reuse the checked machine when only the test string changes."""
    try:
        raw = await request.body()
        if len(raw) > 2048:
            raise ValueError("Simulation request is too large.")
        data = strict_json(raw.decode())
        text = data.get("input", "")
        if not isinstance(text, str) or len(text) > 40 or set(text) - set("01"):
            raise ValueError("Use at most 40 binary input symbols.")
        with lock:
            item = results.get(data.get("result_id"))
            if item is None or item["public"]["mode"] != "dfa" or not item["public"].get("dfa"):
                raise ValueError("Build this machine again before simulating it.")
            public = {**item["public"], "id": uuid.uuid4().hex, "input": text, "created_at": time.time()}
            dfa = DFA.from_dict(public["dfa"])
            public["trace"] = trace(dfa, list(text)).to_dict()
            public["analysis"] = machine_analysis(dfa, list(text))
            private = {**item["private"], "symbols": list(text)}
            results[public["id"]] = {"public": public, "private": private}
            while len(results) > 128:
                results.popitem(last=False)
        return JSONResponse(public)
    except (ValueError, UnicodeDecodeError, AttributeError) as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)


async def catalog(request):
    from theorybert.formal.compiler import ARITHMETIC_GRAMMAR
    grammar_descriptions = {
        "Balanced a / b": "Build a context-free grammar for strings of the form a^n b^n for n >= 0.",
        "Arithmetic": "Arithmetic expressions with identifiers, plus and multiplication, using standard precedence.",
        "Ambiguous expression": "Ambiguous expressions with id and addition and no operator associativity.",
    }
    checkpoints = []
    for path in sorted((ROOT / "artifacts").glob("*/best/config.json")):
        try:
            if not checkpoint_weights(path.parent).is_file():
                continue
            config = json.loads(path.read_text())
            checkpoints.append(
                {
                    "path": str(path.parent.relative_to(ROOT)),
                    "variant": config.get("variant"),
                    "backbone": config.get("backbone"),
                    "status": config.get("training_status", "untrained"),
                }
            )
        except (OSError, ValueError):
            continue
    return JSONResponse(
        {
            "dfa": [
                {
                    **{k: v for k, v in e.items() if k != "dfa"},
                    "preview": {
                        "dfa": e["dfa"].to_dict(),
                        "graph": graph_data(e["dfa"]),
                    },
                }
                for e in benchmark_examples()
            ],
            "cfg": [
                {"id": name, "name": name, "grammar": grammar, "input": text, "description": grammar_descriptions[name]}
                for name, (grammar, text) in EXAMPLES.items()
            ],
            "compiler": {"grammar": ARITHMETIC_GRAMMAR, "input": "(total + 3) * scale - 4 / 2", "description": "Arithmetic expressions with identifiers and numbers, plus, minus, multiplication, division, parentheses, and unary signs; use standard precedence and left associativity."},
            "grammar_model": active_grammar() is not None,
            "active_grammar": active_grammar(),
            "checkpoints": checkpoints,
            "active_model": active_checkpoint(),
        }
    )


async def health(request):
    return JSONResponse(
        {
            "status": "ready",
            "engine": "TheoryBERT",
            "active_model": active_checkpoint(),
            "hosted": os.environ.get("THEORYBERT_HOSTED") == "1",
            "rendering": importlib.util.find_spec("manim") is not None,
            "runtime": os.environ.get("THEORYBERT_RUNTIME", "local"),
            "commit": os.environ.get("RENDER_GIT_COMMIT", "local"),
            "active_grammar": active_grammar(),
            "model_ready": bool(getattr(request.app.state, "model_ready", False)),
        }
    )


async def research(request):
    def read_json(path):
        for candidate in (
            ROOT / path,
            ROOT / "data" / "research" / Path(path).relative_to("artifacts"),
        ):
            try:
                return json.loads(candidate.read_text())
            except (ValueError, OSError):
                continue
        return None

    active = active_checkpoint()
    evaluation = active.get("evaluation", "artifacts/bert-engine-evaluation") if active else "artifacts/bert-engine-evaluation"
    training = active.get("training_summary", "artifacts/bert-engine/summary.json") if active else "artifacts/bert-engine/summary.json"
    grammar_active = active_grammar()
    learned = read_json(evaluation + "/summary.json")
    if active and active.get("kind") == "semantic_plan" and learned:
        measured = learned["test"]["candidate"]["original"]
        learned = {"semantic": {**measured, "raw_equivalence": measured["first_equivalence"], "first_candidate_accuracy": measured["first_equivalence"], "success_within_budget": measured["within_five"], "prediction_seconds": measured["mean_prediction_seconds"], "supported": 1.0, "unique_languages": 74}}
    return JSONResponse(
        {
            "baseline": read_json("artifacts/evaluation/summary.json"),
            "baseline_metadata": read_json("artifacts/evaluation/metadata.json"),
            "smoke": read_json("artifacts/smoke/summary.json"),
            "ablations": read_json("artifacts/ablations/aggregate.json"),
            "environment": read_json("artifacts/environment.json"),
            "learned": learned,
            "plan_comparison": read_json("artifacts/plan-comparison/summary.json"),
            "learned_training": read_json(training),
            "grammar_model": read_json(grammar_active.get("summary", "artifacts/bert-grammar/summary.json")) if grammar_active else None,
            "challenge": read_json("artifacts/challenge-comparison.json"),
            "comparison": read_json("artifacts/v3-comparison.json"),
            "active_model": active,
        }
    )


async def video(request):
    name = request.path_params["name"]
    if (
        not re.fullmatch(r"[a-f0-9]{64}\.mp4", name)
        or not (VIDEO_CACHE / name).is_file()
    ):
        return JSONResponse(
            {"error": "Video not found. Render it again."}, status_code=404
        )
    return FileResponse(
        VIDEO_CACHE / name,
        media_type="video/mp4",
        filename="theorybert-animation.mp4",
        content_disposition_type="inline",
    )


async def frontend(request):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"error": "Endpoint not found."}, status_code=404)
    path = (DIST / request.path_params.get("path", "")).resolve()
    if path.is_relative_to(DIST.resolve()) and path.is_file():
        return FileResponse(path)
    if (DIST / "index.html").is_file():
        return FileResponse(DIST / "index.html")
    return JSONResponse(
        {
            "error": "Build the React frontend first: cd frontend && npm install && npm run build"
        },
        status_code=503,
    )


@asynccontextmanager
async def lifespan(application):
    application.state.model_ready = False
    if os.environ.get("THEORYBERT_RUNTIME") == "bert":
        active, grammar = active_checkpoint(), active_grammar()
        if active is None or grammar is None:
            raise RuntimeError("BERT deployment requires both evaluated active checkpoints.")
        path = ROOT / active["checkpoint"]
        learned_checkpoint(str(path), checkpoint_weights(path).stat().st_mtime_ns,
                           (path / "config.json").stat().st_mtime_ns)
        path = ROOT / grammar["checkpoint"]
        base = ROOT / json.loads((path / "config.json").read_text())["encoder_checkpoint"]
        learned_grammar(str(path), (path / "head.pt").stat().st_mtime_ns,
                        (base / "weights.pt").stat().st_mtime_ns)
        application.state.model_ready = True
    yield


app = Starlette(
    lifespan=lifespan,
    routes=[
        Route("/api/health", health),
        Route("/api/catalog", catalog),
        Route("/api/research", research),
        Route("/api/jobs", submit, methods=["POST"]),
        Route("/api/jobs/{job_id}", job_status),
        Route("/api/simulate", simulate, methods=["POST"]),
        Route("/api/videos/{name}", video),
        Route("/{path:path}", frontend),
    ]
)


def main():
    import uvicorn

    parser = argparse.ArgumentParser(
        description="Run the TheoryBERT React product locally."
    )
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8501")))
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()
    uvicorn.run(
        "theorybert.web:app", host=args.host, port=args.port, reload=args.reload
    )


if __name__ == "__main__":
    main()
