"""Download only the pinned BERT files and small public corpus needed locally."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BERT_REVISION = "86b5e0934494bd15c9632b12f734a8a67f723594"
BERT_WEIGHTS_SHA256 = "68d45e234eb4a928074dfd868cead0219ab85354cc53d20e772753c6bb9169d3"


def fetch(url, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_file():
        if shutil.disk_usage(ROOT).free < 3.5 * 2**30:
            raise RuntimeError("At least 3.5 GiB of free space is required before a download")
        temporary = path.with_name(path.name + ".partial")
        subprocess.run(["curl", "-fsSL", "--retry", "3", "--connect-timeout", "30", url, "-o", str(temporary)], check=True)
        temporary.replace(path)
    with path.open("rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
    return {"url": url, "bytes": path.stat().st_size, "sha256": digest}


def main():
    model = ROOT / "artifacts/pretrained/bert-base-uncased"
    files = ["config.json", "tokenizer.json", "tokenizer_config.json", "vocab.txt", "model.safetensors", "LICENSE", "README.md"]
    manifest = {"source": "google-bert/bert-base-uncased", "revision": BERT_REVISION, "files": {}}
    for name in files:
        manifest["files"][name] = fetch(f"https://huggingface.co/google-bert/bert-base-uncased/resolve/{BERT_REVISION}/{name}", model / name)
        if name == "model.safetensors" and manifest["files"][name]["sha256"] != BERT_WEIGHTS_SHA256:
            raise ValueError("BERT weights do not match the source repository's published SHA-256")
        print("Ready:", name, flush=True)
    (model / "source.json").write_text(json.dumps(manifest, indent=2))
    external = ROOT / "data/generated/external"
    source = external / "source-commit.json"
    fetch("https://api.github.com/repos/nicholaslocascio/deep-regex/commits/master", source)
    revision = json.loads(source.read_text())["sha"]
    public = {"source": "nicholaslocascio/deep-regex", "revision": revision, "license": "MIT", "files": {}}
    for remote, local in [("datasets/KB13/src.txt", "kb13-descriptions.txt"), ("datasets/KB13/targ.txt", "kb13-regex.txt"), ("datasets/license.md", "LICENSE.md")]:
        public["files"][local] = fetch(f"https://raw.githubusercontent.com/nicholaslocascio/deep-regex/{revision}/{remote}", external / local)
    (external / "source.json").write_text(json.dumps(public, indent=2))
    print("Public corpus and BERT source manifests written. No project data uploaded.")


if __name__ == "__main__":
    main()
