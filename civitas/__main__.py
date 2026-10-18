import argparse
import json
from pathlib import Path

from .benchmarks import available, load
from .simulation import replay, run, save, trace


def main() -> int:
    parser = argparse.ArgumentParser(description="CIVITAS deterministic research environment")
    commands = parser.add_subparsers(dest="command", required=True)
    bench = commands.add_parser("benchmark").add_subparsers(dest="operation", required=True)
    bench.add_parser("list")
    inspect = bench.add_parser("inspect")
    inspect.add_argument("benchmark")
    execute = bench.add_parser("run")
    execute.add_argument("benchmark")
    execute.add_argument("--solver", choices=["baseline", "composition"], default="baseline")
    execute.add_argument("--seed", type=int)
    execute.add_argument("--output", type=Path)
    playback = commands.add_parser("replay")
    playback.add_argument("run", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "replay":
            record = json.loads(args.run.read_text(encoding="utf-8"))
            world = replay(record)
            print(trace(record))
            print(f"Replay verified: {len(world.history)} events, {world.state_hash}")
        elif args.operation == "list":
            for name in available():
                print(f"{name}: {load(name)['description']}")
        elif args.operation == "inspect":
            print(json.dumps(load(args.benchmark), indent=2))
        else:
            record = run(load(args.benchmark), args.seed, args.solver)
            path = args.output or Path("runs") / f"{args.benchmark}-{record['task']['seed']}.json"
            save(record, path)
            print(trace(record))
            print(f"Run saved: {path}")
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f"civitas: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
