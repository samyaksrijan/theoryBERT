"""Build and serve the React product with the local Python research engine."""

import argparse
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8501)
    parser.add_argument("--skip-build", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    frontend = root / "frontend"
    if not args.skip_build:
        if shutil.which("npm") is None:
            raise SystemExit(
                "Install Node.js 22.12+ to build the React frontend, or use --skip-build with an existing frontend/dist."
            )
        if not (frontend / "node_modules").is_dir():
            subprocess.run(
                ["npm", "ci", "--no-audit", "--no-fund"], cwd=frontend, check=True
            )
        subprocess.run(["npm", "run", "build"], cwd=frontend, check=True)
    if not (frontend / "dist" / "index.html").is_file():
        raise SystemExit(
            "No frontend build found. Run this command without --skip-build first."
        )
    print(f"\nTheoryBERT → http://localhost:{args.port}\n", flush=True)
    subprocess.run(
        [sys.executable, "-m", "theorybert.web", "--port", str(args.port)],
        cwd=root,
        check=True,
    )


if __name__ == "__main__":
    main()
