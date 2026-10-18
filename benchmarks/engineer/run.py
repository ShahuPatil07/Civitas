"""python -m benchmarks.engineer.run [--output runs/engineer-42]."""
import argparse
from copy import deepcopy
import json
from pathlib import Path

from civitas.benchmarks import instantiate
from civitas.laboratory import Laboratory, DEFAULT_GOAL, scenario, trace
from civitas.providers import provider
from civitas.simulation import save


def evaluate(lab, target=None, mass=100, max_effort=150):
    """Private evaluator: does not trust a model's interpretation or status."""
    _, task = instantiate(lab.spec)
    goals = deepcopy(task['goals'])
    for c in goals:
        if c['subject'] != lab.actor and target:
            c['subject'] = target
        if c['measure'] == 'environment_work':
            c['value'] = 2 * mass * lab.spec['universe']['gravity']
        if c['measure'] == 'effort_spent':
            c['value'] = max_effort
    checks = [lab.world.evaluate(c) for c in goals]
    return {'success': all(r['status'] == 'satisfied' for r in checks), 'constraints': checks}


def suite(output='runs/engineer-42', provider_name='offline', model='qwen3-vl:2b'):
    folder = Path(output)
    folder.mkdir(parents=True, exist_ok=True)
    results = {}

    def record(name, lab, target=None, mass=100, max_effort=150):
        path = lab.save(folder / (name + '.json'))
        restored = Laboratory.load(path)
        assert restored.world.state_hash == lab.world.state_hash
        (folder / (name + '.txt')).write_text(trace(lab) + '\n', encoding='utf-8')
        results[name] = {**lab.metrics(), 'evaluation': evaluate(lab, target, mass, max_effort),
                         'world_hash': lab.world.state_hash, 'replay_verified': True,
                         'discoveries': len(lab.view['discoveries'])}

    for name, spec in [('feasible', scenario()), ('no_energy', scenario(source_energy=0)), ('gravity_3', scenario(gravity=3))]:
        lab = Laboratory(spec, provider(provider_name, model))
        lab.start(DEFAULT_GOAL)
        lab.run()
        record(name, lab)
        if name == 'feasible' and lab.project['status'] == 'succeeded':
            initial = lab.record()
    if 'initial' in locals():
        for enabled in (False, True):
            lab = Laboratory.restore(initial, provider(provider_name, model))
            lab.start(DEFAULT_GOAL, target=lab.target('other_load'), use_knowledge=enabled)
            lab.run()
            record('transfer_warm' if enabled else 'transfer_cold', lab, lab.target('other_load'), 80, 250)
    save(results, folder / 'summary.json')
    return results


def main():
    parser = argparse.ArgumentParser(description='Same-world Engineer experiments, including matched transfer forks')
    parser.add_argument('--output', default='runs/engineer-42')
    parser.add_argument('--provider', choices=['offline', 'local'], default='offline')
    parser.add_argument('--model', default='qwen3-vl:2b')
    args = parser.parse_args()
    results = suite(args.output, args.provider, args.model)
    for name, result in results.items():
        print(name, json.dumps({k: v for k, v in result.items() if k != 'evaluation'}), 'measured_success=', result['evaluation']['success'])


if __name__ == '__main__':
    main()
