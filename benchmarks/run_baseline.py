"""Reproduce the baseline report and retain complete JSON runs plus readable traces."""
import argparse
from collections import Counter
import json
from pathlib import Path

from civitas.benchmarks import available, load
from civitas.simulation import replay, run, save, trace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    folder = args.output or Path("runs") / f"baseline-{args.seed}"
    folder.mkdir(parents=True, exist_ok=True)
    summary = []
    for name in available():
        record = run(load(name), args.seed)
        path = save(record, folder / f"{name}.json")
        # Verify the actual persisted artifact, not only the in-memory object.
        replay(json.loads(path.read_text(encoding="utf-8")))
        (folder / f"{name}.txt").write_text(trace(record) + "\n", encoding="utf-8")
        row = {"benchmark": name, **record["outcome"], "seed": args.seed,
               "accepted": sum(e["accepted"] for e in record["events"]),
               "failure_codes": dict(sorted(Counter(e["evaluations"][0]["code"] for e in record["events"] if not e["accepted"]).items())),
               "final_hash": record["final_hash"], "replay_verified": True}
        summary.append(row)
        print(f"{name}: success={row['success']}, attempts={row['attempts']}, accepted={row['accepted']}, experiments={row['experiments']}, replay=verified")
    (folder / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Artifacts: {folder}")


if __name__ == "__main__":
    main()
