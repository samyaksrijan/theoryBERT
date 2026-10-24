import argparse, importlib, json, platform, shutil, subprocess, sys, tempfile
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--render", action="store_true")
a = p.parse_args()
report = {
    "python": sys.version,
    "platform": platform.platform(),
    "ffmpeg": shutil.which("ffmpeg"),
}
for name in ["torch", "transformers", "streamlit", "nltk", "manim"]:
    try:
        module = importlib.import_module(name)
        report[name] = module.__version__
    except Exception as exc:
        report[name] = str(exc)
import torch

report["compute"] = {
    "cuda": torch.cuda.is_available(),
    "mps": torch.backends.mps.is_available(),
    "cpu": True,
}
report["minimal_text_render"] = "not run; use --render"
if a.render:
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "minimal.py"
        path.write_text(
            'from manim import *\nclass Minimal(Scene):\n def construct(self):\n  self.add(Text("TheoryBERT · verified",font_size=30));self.wait(.3)\n'
        )
        try:
            r = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "manim",
                    "-ql",
                    "--media_dir",
                    str(Path(temp) / "media"),
                    str(path),
                    "Minimal",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            report["minimal_text_render"] = (
                "passed"
                if r.returncode == 0 and list(Path(temp).rglob("*.mp4"))
                else (r.stderr + r.stdout)[-2000:]
            )
        except Exception as exc:
            report["minimal_text_render"] = str(exc)
print(json.dumps(report, indent=2))
