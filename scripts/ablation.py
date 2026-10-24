"""Full runs are opt-in. Completed runs alone enter aggregate statistics."""

import argparse, json, subprocess, sys, csv, statistics
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--run", action="store_true")
p.add_argument("--seeds", nargs="+", type=int, default=[13, 42, 123])
a = p.parse_args()
root = Path("artifacts/ablations")
root.mkdir(parents=True, exist_ok=True)
rows = []
for variant, strategy in [
    ("vanilla", "none"),
    ("theorybert", "random"),
    ("theorybert", "subword_mean"),
    ("theorybert", "subword_mean_plus_one"),
]:
    for seed in a.seeds:
        config = json.loads(
            Path(
                f"configs/{'vanilla' if variant == 'vanilla' else 'theorybert'}.json"
            ).read_text()
        )
        name = f"{variant}-{strategy}-{seed}"
        out = root / name
        out.mkdir(exist_ok=True)
        config.update(seed=seed, initialisation=strategy, output=str(out))
        path = out / "experiment.json"
        path.write_text(json.dumps(config, indent=2))
        row = {
            "variant": variant,
            "initialisation": strategy,
            "seed": seed,
            "status": "not run",
            "semantic_equivalence": None,
            "structural_equivalence": None,
        }
        if a.run:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "theorybert.training.train",
                    "--config",
                    str(path),
                ],
                check=True,
            )
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "theorybert.evaluation.evaluate",
                    "--dataset",
                    config["dataset"],
                    "--checkpoint",
                    str(out / "best"),
                    "--output",
                    str(out / "evaluation"),
                ],
                check=True,
            )
            result = json.loads((out / "evaluation/summary.json").read_text())
            row.update(
                status="completed",
                semantic_equivalence=result.get("semantic", {}).get("raw_equivalence"),
                structural_equivalence=result.get("structural", {}).get(
                    "raw_equivalence"
                ),
            )
        rows.append(row)
with (root / "runs.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
summary = []
for v, s in sorted({(r["variant"], r["initialisation"]) for r in rows}):
    for category in ("semantic", "structural"):
        vals = [
            r[category + "_equivalence"]
            for r in rows
            if r["variant"] == v
            and r["initialisation"] == s
            and r["status"] == "completed"
            and r[category + "_equivalence"] is not None
        ]
        summary.append(
            {
                "variant": v,
                "initialisation": s,
                "category": category,
                "completed": len(vals),
                "mean": statistics.mean(vals) if vals else None,
                "std": statistics.stdev(vals) if len(vals) > 1 else None,
                "status": "completed" if vals else "not run",
            }
        )
(root / "aggregate.json").write_text(json.dumps(summary, indent=2))
print(root / "runs.csv")
