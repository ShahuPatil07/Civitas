"""Run the unnamed assembly task, insufficient-energy control and gravity transfer."""
import argparse
from copy import deepcopy
from importlib.resources import files
import json
from pathlib import Path

from civitas.simulation import replay, run, save, trace


def scenarios():
    task = json.loads(files("benchmarks.composition").joinpath("task.json").read_text(encoding="utf-8"))
    impossible = deepcopy(task)
    impossible["id"] = "insufficient_energy_control"
    impossible["objects"]["a"]["source"]["energy"] = 50
    transfer = deepcopy(task)
    transfer["id"] = "gravity_transfer"
    transfer["universe"]["gravity"] = 12
    return {"feasible": task, "insufficient_energy": impossible, "gravity_transfer": transfer}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("runs/composition"))
    args = parser.parse_args()
    rows = []
    for label, spec in scenarios().items():
        for solver in ("baseline", "composition"):
            record = run(spec, args.seed, solver)
            path = save(record, args.output / f"{label}-{solver}.json")
            reconstructed = replay(json.loads(path.read_text(encoding="utf-8")))
            path.with_suffix(".txt").write_text(trace(record) + "\n", encoding="utf-8")
            state = reconstructed.snapshot()
            row = {"case": label, "solver": solver, "seed": args.seed, **record["outcome"],
                   "design_versions": len(state["designs"]), "final_hash": record["final_hash"], "replay_verified": True}
            rows.append(row)
            print(f"{label} / {solver}: success={row['success']}, actions={row['attempts']}, experiments={row['experiments']}, design_versions={row['design_versions']}, replay=verified")
    (args.output / "summary.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
