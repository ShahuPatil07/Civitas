import argparse
import json
from pathlib import Path

from .benchmarks import available, load
from .simulation import replay, run, save, trace


def main() -> int:
    parser = argparse.ArgumentParser(description="CIVITAS deterministic research environment")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ('play', 'laboratory'):
        lab = commands.add_parser(name)
        lab.add_argument('--provider', choices=['offline', 'local'], default='offline',
                         help='Engineer reasoning inside projects (local = experimental Ollama decision mode)')
        lab.add_argument('--language', default='auto',
                         choices=['auto', 'none', 'ovh', 'groq', 'cerebras', 'gemini', 'openrouter', 'ollama-cloud', 'ollama'],
                         help='Free backend for text the grammar cannot parse. auto: your free keys (GROQ_API_KEY, ...), '
                              'then keyless OVHcloud, then local Ollama. none: grammar only, no network.')
        lab.add_argument('--language-model', help='Override the backend model name')
        lab.add_argument('--model', default='qwen3-vl:2b')
        lab.add_argument('--local-format', choices=['chat', 'chatml'], default='chatml')
        lab.add_argument('--load', type=Path)
        lab.add_argument('--output', type=Path, default=Path('runs/laboratory.json'))
        lab.add_argument('--goal')
        lab.add_argument('--gravity', type=float, default=9.81)
        lab.add_argument('--source-energy', type=float, default=15000)
        lab.add_argument('--seed', type=int, default=42)
        if name == 'play':
            lab.add_argument('--smoke-frames', type=int, default=0, help='Close after N frames (client verification)')
            lab.add_argument('--screenshot', type=Path)
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
        if args.command in {'play', 'laboratory'}:
            from .laboratory import Laboratory, DEFAULT_GOAL, scenario, trace as lab_trace
            from .providers import provider
            from .llm import backend
            engine = provider(args.provider, args.model, args.local_format)
            words = backend(args.language, args.language_model)
            lab = (Laboratory.load(args.load, engine, words) if args.load else
                   Laboratory(scenario(args.gravity, args.source_energy, args.seed), engine, words))
            if args.command == 'play':
                from .client import play
                if args.goal:
                    lab.instruct(args.goal)
                play(lab, args.output, args.smoke_frames, args.screenshot)
            else:
                if args.goal or not lab.project:
                    lab.instruct(args.goal or DEFAULT_GOAL)
                lab.run()
                lab.save(args.output)
                print(lab_trace(lab))
                print('Saved:', args.output)
                from .replies import render_task
                print('Reasoning:', lab.provider.name, '| language:', words.name if words else 'grammar only (no network)')
                print(render_task(lab))
            return 0
        if args.command == "replay":
            record = json.loads(args.run.read_text(encoding="utf-8"))
            if record.get('format') == 'civitas-lab-1':
                from .laboratory import Laboratory, trace as lab_trace
                lab = Laboratory.restore(record)
                world = lab.world
                print(lab_trace(lab))
            else:
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
