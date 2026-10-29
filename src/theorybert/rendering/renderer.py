import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from theorybert.contracts import CFGSpec, Production, TreeNode
from theorybert.pipeline import VerifiedDFA
from theorybert.formal.dfa import canonicalise, trace
from theorybert.formal.cfg import check_tree
from theorybert.rendering.layout import VERSION, graph_layout, tree_layout


@dataclass(frozen=True)
class VerifiedTree:
    spec_json: str
    tree_json: str

    def checked(self):
        data = json.loads(self.spec_json)
        data["productions"] = [Production(**p) for p in data["productions"]]
        spec = CFGSpec(**data)
        tree = TreeNode.from_dict(json.loads(self.tree_json))
        errors, steps = check_tree(spec, tree)
        if errors:
            raise ValueError("; ".join(errors))
        return spec, tree, steps


def seal_tree(spec, tree):
    seal = VerifiedTree(json.dumps(spec.to_dict()), json.dumps(tree.to_dict()))
    seal.checked()
    return seal


def render_key(payload, quality="preview"):
    return hashlib.sha256(
        json.dumps(
            {
                "payload": payload,
                "quality": quality,
                "renderer": VERSION,
                "style": "pink-ink",
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()


def payload_for(evidence, symbols=None):
    if isinstance(evidence, VerifiedDFA):
        d = canonicalise(evidence.checked())
        if len(d.states) > 8:
            raise ValueError("Video export supports at most 8 states. The interactive canvas and transition table support up to 64.")
        graph_layout(d)
        symbols = list(symbols or [])
        if len(symbols) > 40:
            raise ValueError("Use at most 40 symbols for a readable animation.")
        return {"mode": "dfa", "dfa": d.to_dict(), "trace": trace(d, symbols).to_dict()}
    if isinstance(evidence, VerifiedTree):
        spec, tree, steps = evidence.checked()
        tree_layout(tree)
        return {
            "mode": "cfg",
            "spec": spec.to_dict(),
            "tree": tree.to_dict(),
            "steps": steps,
        }
    raise TypeError(
        "Renderer requires a VerifiedDFA or VerifiedTree; raw candidates cannot be rendered."
    )


def render(
    evidence, symbols=None, quality="preview", cache_dir="artifacts/videos", timeout=180
):
    if quality not in ("preview", "high"):
        raise ValueError("Quality must be preview or high.")
    payload = payload_for(evidence, symbols)
    key = render_key(payload, quality)
    cache = Path(cache_dir).resolve()
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / f"{key}.mp4"
    if target.exists() and target.stat().st_size > 1000:
        return target, 0.0, True
    start = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="render-", dir=cache) as tmp:
        tmp = Path(tmp)
        (tmp / "input.json").write_text(json.dumps(payload))
        env = {**os.environ, "THEORYBERT_PAYLOAD": str(tmp / "input.json")}
        command = [
            sys.executable,
            "-m",
            "manim",
            "-ql" if quality == "preview" else "-qh",
            "--disable_caching",
            "--media_dir",
            str(tmp / "media"),
            "-o",
            "result.mp4",
            str(Path(__file__).with_name("scenes.py")),
            "TheoryScene",
        ]
        try:
            p = subprocess.run(
                command, capture_output=True, text=True, timeout=timeout, env=env
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"Rendering exceeded {timeout}s. Try preview quality or a shorter input."
            ) from exc
        if p.returncode:
            raise RuntimeError(
                "Manim could not render. Check cairo, pango and ffmpeg.\n"
                + (p.stderr or p.stdout)[-3500:]
            )
        videos = list((tmp / "media" / "videos").rglob("result.mp4"))
        if not videos:
            raise RuntimeError("Manim completed without an output video.")
        os.replace(videos[0], target)
    return target, time.perf_counter() - start, False
