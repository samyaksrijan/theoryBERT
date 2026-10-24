"""Local React product API. The server owns every renderable verification object."""

import argparse
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import importlib.util
import json
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
from theorybert.pipeline import run_candidates
from theorybert.rendering.layout import graph_layout, tree_layout
from theorybert.rendering.renderer import payload_for, render, seal_tree

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "frontend" / "dist"
VIDEO_CACHE = ROOT / "artifacts" / "videos"
workers = ThreadPoolExecutor(max_workers=2, thread_name_prefix="theorybert")
lock = threading.RLock()
jobs = OrderedDict()
results = OrderedDict()


def graph_data(dfa):
    nodes, edges = graph_layout(dfa)
    return {"nodes": nodes, "edges": edges}


def tree_data(tree):
    nodes, links, positions = tree_layout(tree)
    return {
        "nodes": {k: v.to_dict() for k, v in nodes.items()},
        "links": links,
        "positions": positions,
    }


@lru_cache(maxsize=3)
def learned_checkpoint(path, weights_stamp, config_stamp):
    from theorybert.baselines.predictors import Learned
    from theorybert.models.theorybert import load_checkpoint

    return Learned(*load_checkpoint(path))


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


def solve_dfa(data, phase):
    description = data.get("description", "").strip()
    text = data.get("input", "")
    source = data.get("source", "demo")
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
    reference, provenance = reference_for(data, selected)
    phase("predicting")
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
    elif source == "rule":
        from theorybert.baselines.predictors import RuleBased

        predictor = RuleBased()
        candidates, identity = (
            list(predictor.predict(description, budget)),
            predictor.source,
        )
    elif source == "learned":
        path = Path(data.get("checkpoint", "")).expanduser()
        if not path.is_absolute():
            path = ROOT / path
        if not (path / "weights.pt").is_file() or not (path / "config.json").is_file():
            raise ValueError(
                "No checkpoint found. Choose a local checkpoint in Settings or use a reference demonstration."
            )
        predictor = learned_checkpoint(
            str(path.resolve()),
            (path / "weights.pt").stat().st_mtime_ns,
            (path / "config.json").stat().st_mtime_ns,
        )
        candidates, identity = (
            list(predictor.predict(description, budget)),
            predictor.source,
        )
    else:
        raise ValueError("Choose a supported prediction source.")
    phase("verifying")
    result = run_candidates(candidates, reference, provenance, identity, budget)
    public = {
        "mode": "dfa",
        "source": identity,
        "description": description,
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
        dfa = canonicalise(result.verified.checked())
        public["dfa"] = dfa.to_dict()
        public["trace"] = trace(dfa, list(text)).to_dict()
        try:
            public["graph"] = graph_data(dfa)
            payload_for(result.verified, list(text))
            public["renderable"] = importlib.util.find_spec("manim") is not None
        except ValueError as exc:
            public["visual_error"] = str(exc)
    return public, {"evidence": result.verified, "symbols": list(text)}


def solve_cfg(data, phase):
    grammar, text = data.get("grammar", ""), data.get("input", "")
    limit = int(data.get("limit", 5))
    phase("parsing")
    spec, trees, truncated = parse(grammar, text.split(), limit)
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
    return {
        "mode": "cfg",
        "source": "NLTK Earley · independent derivation checker",
        "status": "VERIFIED",
        "verified": True,
        "grammar": grammar,
        "input": text,
        "spec": spec.to_dict(),
        "trees": [t.to_dict() for t in trees],
        "layouts": displays,
        "steps": steps,
        "truncated": truncated,
        "visual_errors": errors,
        "renderable": importlib.util.find_spec("manim") is not None,
    }, {"spec": spec, "trees": trees}


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
            if sum(j["status"] == "running" for j in jobs.values()) >= 4:
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


async def catalog(request):
    checkpoints = []
    for path in sorted((ROOT / "artifacts").glob("*/best/config.json")):
        if not (path.parent / "weights.pt").is_file():
            continue
        try:
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
                {"id": name, "name": name, "grammar": grammar, "input": text}
                for name, (grammar, text) in EXAMPLES.items()
            ],
            "checkpoints": checkpoints,
        }
    )


async def health(request):
    return JSONResponse(
        {
            "status": "ready",
            "engine": "TheoryBERT",
            "rendering": importlib.util.find_spec("manim") is not None,
        }
    )


async def research(request):
    def read_json(path):
        try:
            return json.loads((ROOT / path).read_text())
        except (ValueError, OSError):
            return None

    return JSONResponse(
        {
            "baseline": read_json("artifacts/evaluation/summary.json"),
            "baseline_metadata": read_json("artifacts/evaluation/metadata.json"),
            "smoke": read_json("artifacts/smoke/summary.json"),
            "ablations": read_json("artifacts/ablations/aggregate.json"),
            "environment": read_json("artifacts/environment.json"),
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


app = Starlette(
    routes=[
        Route("/api/health", health),
        Route("/api/catalog", catalog),
        Route("/api/research", research),
        Route("/api/jobs", submit, methods=["POST"]),
        Route("/api/jobs/{job_id}", job_status),
        Route("/api/videos/{name}", video),
        Route("/{path:path}", frontend),
    ]
)


def main():
    import uvicorn

    parser = argparse.ArgumentParser(
        description="Run the TheoryBERT React product locally."
    )
    parser.add_argument("--port", type=int, default=8501)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()
    uvicorn.run(
        "theorybert.web:app", host="127.0.0.1", port=args.port, reload=args.reload
    )


if __name__ == "__main__":
    main()
