"""Task-understanding matrix: free text -> expected reply and measured world state.

python -m benchmarks.engineer.tasks                       # offline grammar matrix
python -m benchmarks.engineer.tasks --language-cases --backend ovh   # live free model

Each case states the reply category a careful Engineer should give and an
independent check over named world objects. The checks never read the
Engineer's interpretation, so a misunderstood task cannot pass by succeeding
at the wrong thing. Global invariants are verified for every task.
"""
import argparse
import json
from pathlib import Path
import time

from civitas.laboratory import Laboratory, scenario
from civitas.llm import backend
from civitas.providers import provider
from civitas.replies import reply
from civitas.simulation import save

REFUSALS = {'clarify', 'unsupported', 'boundary'}


def at(name, x=None, z=None):
    def check(o):
        p = o[name]['position']
        return (x is None or abs(p[0] - x) < 1e-9) and (z is None or abs(p[1] - z) < 1e-9)
    return check


def unmoved(o):
    return at('load', 2, 0)(o) and at('other_load', 2.5, 0)(o)


# Offline grammar cases: deterministic, part of the unit suite.
CASES = [
    # Supported outcomes, units, directions, references.
    dict(name='left_1m', tasks=['Move the selected object 1 m to the left'], expect=['succeeded'], check=at('load', 1, 0)),
    dict(name='right_cm', tasks=['Push the load 50 cm right'], expect=['succeeded'], check=at('load', 2.5, 0)),
    dict(name='lift_words', tasks=['Lift the selected object two metres'], expect=['succeeded'], check=at('load', 2, 2)),
    dict(name='lift_mm', tasks=['Raise the selected object 500 mm'], expect=['succeeded'], check=at('load', 2, .5)),
    dict(name='absolute_height', tasks=['Raise the selected object to a height of 2 m'], expect=['succeeded'], check=at('load', 2, 2)),
    dict(name='tall_lift_power', tasks=['Lift the selected object 10 m'], expect=['succeeded'], check=at('load', 2, 10)),
    dict(name='by_mass', tasks=['Move the 80 kg object 1 m to the right'], expect=['succeeded'],
         check=lambda o: at('other_load', 3.5, 0)(o) and at('load', 2, 0)(o)),
    dict(name='repeat_env', tasks=['Lift the selected object 0.5 m, 3 times, using environmental energy'], expect=['succeeded'],
         check=lambda o: at('load', 2, .5)(o) and o['load']['human_work'] == 0 and sum(m['to'][1] >= .5 > m['from'][1] for m in o['load']['motions']) >= 3),
    dict(name='already_there', tasks=['Raise the object 0 m'], expect=['succeeded'], check=unmoved),
    dict(name='effort_ok', tasks=['Lift the selected object 1 m using at most 100 joules'], expect=['succeeded'], check=at('load', 2, 1)),
    # Sequential tasks in one world: stale relations and measured-knowledge reuse.
    dict(name='lift_then_lower', tasks=['Lift the selected object 1 m', 'Lower the selected object 1 m'], expect=['succeeded'] * 2, check=at('load', 2, 0)),
    dict(name='lift_twice', tasks=['Lift the selected object 1 m', 'Lift the selected object 1 m'], expect=['succeeded'] * 2, check=at('load', 2, 2)),
    dict(name='right_left_lift', tasks=['Move the selected object 1 m to the right', 'Move the selected object 2 m to the left', 'Lift the selected object 1 m'],
         expect=['succeeded'] * 3, check=at('load', 1, 1)),
    dict(name='absolute_down', tasks=['Raise the selected object to a height of 2 m', 'Lower the selected object to a height of 1 m'],
         expect=['succeeded'] * 2, check=at('load', 2, 1)),
    # Honest failures, each with a distinct reason.
    dict(name='effort_too_low', tasks=['Move the selected object 1 m to the left using at most 20 joules'], expect=['not_found'], check=unmoved),
    # 981 J needed, agent holds 600 J: a conservation proof, not a planner limit.
    dict(name='human_only_energy', tasks=['Lift the selected object 1 m manually'], expect=['proven_infeasible'],
         check=lambda o: unmoved(o) and o['load']['environment_work'] == 0),
    # 343 J is affordable but needs 687 N against a 100 N limit: no proof, a capability limit.
    dict(name='human_only_force', tasks=['Move the selected object 50 cm to the right by hand'], expect=['capability_limit'],
         check=lambda o: unmoved(o) and o['load']['environment_work'] == 0),
    dict(name='below_ground', tasks=['Lower the selected object 1 m'], expect=['boundary'], check=unmoved),
    dict(name='no_energy', tasks=['Lift the selected object 1 m 2 times using environmental energy'], spec={'source_energy': 0},
         expect=['proven_infeasible'], check=unmoved),
    dict(name='energy_bound', tasks=['Lift the selected object 1 m 3 times using environmental energy'], spec={'source_energy': 2500},
         expect=['proven_infeasible'], check=lambda o: o['load']['position'][1] <= 1),
    dict(name='elevated_sideways', tasks=['Lift the selected object 1 m', 'Move the selected object 1 m to the right'],
         expect=['succeeded', 'not_found'], check=at('load', 2, 1)),
    # Requests the Engineer must not act on.
    dict(name='negation', tasks=['Do not move the selected object'], expect=['clarify'], check=unmoved),
    dict(name='compound', tasks=['Move the selected object 1 m right and then lift it 1 m'], expect=['clarify'], check=unmoved),
    dict(name='invention_name', tasks=['Build a ferris wheel'], expect=['clarify'], check=unmoved),
    dict(name='unknown_physics', tasks=['Make the stone fly to the moon'], expect=['clarify'], check=unmoved),
    dict(name='unknown_words', tasks=['Lift the selected object 1 m and paint it blue'], expect=['clarify'], check=unmoved),
    dict(name='mass_ambiguous', tasks=['Move the 50 kg object 1 m to the right'], expect=['clarify'], check=unmoved),
    dict(name='energy_conflict', tasks=['Lift the selected object 1 m by hand using environmental energy'], expect=['clarify'], check=unmoved),
    dict(name='two_axes', tasks=['Move the selected object 1 m up and to the left'], expect=['clarify'], check=unmoved),
]

# Paraphrases outside the offline grammar: need a language backend.
# Run live with --language-cases --backend NAME; never part of the unit suite.
LANGUAGE_CASES = [
    dict(name='nudge_a_metre', tasks=['Could you nudge the big rock a metre towards the left?'], expect=['succeeded'], check=at('load', 1, 0)),
    dict(name='rightwards', tasks=['Slide the boulder 30 cm rightwards please'], expect=['succeeded'], check=at('load', 2.3, 0)),
    dict(name='off_the_floor', tasks=['Get the heavy block two meters off the floor'], expect=['succeeded'], check=at('load', 2, 2)),
    dict(name='no_muscles', tasks=['Could you shove the rock 40 centimetres to the right without using your own muscles'],
         expect=['succeeded'], check=lambda o: at('load', 2.4, 0)(o) and o['load']['human_work'] == 0),
    dict(name='heave_up', tasks=['Heave the stone upwards by about one and a half metres'], expect=['succeeded', 'clarify'], check=lambda o: True),
    dict(name='paint', tasks=['Paint the rock blue'], expect=['unsupported', 'clarify'], check=unmoved),
    dict(name='bridge', tasks=['Build a bridge across the river'], expect=['unsupported', 'clarify'], check=unmoved),
    dict(name='moon', tasks=['Carry the rock to the moon'], expect=['unsupported', 'clarify'], check=unmoved),
    dict(name='teleport', tasks=['Teleport the boulder behind the workshop'], expect=['unsupported', 'clarify'], check=unmoved),
    # Multi-step requests and references the single-outcome grammar cannot express.
    dict(name='raise_and_drop', tasks=['Raise the stone by 40 cm and then drop it back down'], expect=['succeeded'],
         check=lambda o: at('load', 2, 0)(o) and max((m['to'][1] for m in o['load']['motions']), default=0) >= .4 - 1e-9),
    dict(name='two_moves', tasks=['Shuffle the rock 1 m to the left, then another 50 cm to the left'], expect=['succeeded'], check=at('load', .5, 0)),
    dict(name='lighter_rock', tasks=['Please hoist the lighter rock up by a metre'], expect=['succeeded'],
         check=lambda o: at('other_load', 2.5, 1)(o) and at('load', 2, 0)(o)),
    dict(name='to_the_mark', tasks=['Shove the boulder over to the 4 metre mark'], expect=['succeeded'], check=at('load', 4, 0)),
    dict(name='back_to_start', tasks=['Push the load 50 cm right', 'Now put the rock back where it started'], expect=['succeeded', 'succeeded'],
         check=at('load', 2, 0)),
    dict(name='spin', tasks=['Spin the rock around three times'], expect=['unsupported', 'clarify'], check=unmoved),
    dict(name='ramp', tasks=['Build a ramp so the rock can roll up onto it'], expect=['unsupported', 'clarify'], check=unmoved),
    dict(name='vague', tasks=['Shift the boulder somewhere nicer'], expect=['clarify', 'unsupported'], check=unmoved),
]


def invariants(lab, project, final=True):
    """Violations of rules that hold for every task, whatever its text.

    An earlier plan step is judged by the kernel's measurement when it
    succeeded; later steps may legitimately move the object again.
    """
    problems = []
    said = reply(project, lab.last_error)['category']
    measured = (lab.world.evaluate(c) for c in project['goals']) if final else (project['latest'] or {}).get('evaluations', [])
    if said == 'succeeded' and not (project['goals'] and all(r['status'] == 'satisfied' for r in measured)):
        problems.append('success reported while a frozen goal is unmet')
    caps = [c['value'] for c in project['goals'] if c['measure'] == 'effort_spent' and c['op'] == '<=']
    effort = lab.world.snapshot()['agents'][lab.actor]['effort_spent']
    if caps and effort > min(caps) + 1e-9:
        problems.append(f'effort cap exceeded: {effort} > {min(caps)}')
    if said in REFUSALS and project['attempts']:
        problems.append('physical action attempted for a refused request')
    if said == 'proven_infeasible' and not (project['latest'] or {}).get('certificate'):
        problems.append('impossibility claimed without a kernel certificate')
    return problems


def run(case, engine=None, translator=None):
    lab = Laboratory(scenario(**case.get('spec', {})), engine or provider('offline'), translator)
    said, problems = [], []
    for text in case['tasks']:
        lab.instruct(text)
        lab.run()
        steps = lab.agenda['projects'] if lab.agenda else [lab.project_id]
        for identity in steps:
            problems += invariants(lab, lab.view['projects'][identity], identity == steps[-1])
        r = reply(lab.project, lab.last_error)
        said.append(r | {'text': text, 'actions': sum(lab.view['projects'][i]['counts']['actions'] for i in steps),
                         'usage': lab.project['usage'], 'plan': [s['text'] for s in lab.agenda['steps']] if lab.agenda else None,
                         'read_by': lab.agenda['model'] if lab.agenda else None})
    names = {n: lab.target(n) for n in lab.spec['objects']}
    objects = {n: lab.world.snapshot()['objects'][i] for n, i in names.items()}
    expected = case['expect']
    # A single expected entry may list acceptable alternatives (language cases).
    if len(expected) == len(case['tasks']):
        categories_ok = all(s['category'] == e for s, e in zip(said, expected))
    else:
        categories_ok = len(said) == 1 and said[0]['category'] in expected
    state_ok = case['check'](objects)
    return {'name': case['name'], 'passed': categories_ok and state_ok and not problems, 'categories_ok': categories_ok,
            'state_ok': state_ok, 'invariant_violations': problems, 'replies': said, 'world_hash': lab.world.state_hash, 'lab': lab}


def main():
    parser = argparse.ArgumentParser(description='Can the Engineer understand and perform a specific task?')
    parser.add_argument('--backend', default='none', help='Language backend: none, auto, ovh, groq, ollama, ...')
    parser.add_argument('--model', help='Override the backend model')
    parser.add_argument('--language-cases', action='store_true', help='Run grammar-external paraphrases (needs --backend)')
    parser.add_argument('--cases', nargs='*', help='Only run these case names')
    parser.add_argument('--output', default='runs/engineer-tasks')
    args = parser.parse_args()
    folder = Path(args.output)
    folder.mkdir(parents=True, exist_ok=True)
    cases = LANGUAGE_CASES if args.language_cases else CASES
    cases = [c for c in cases if not args.cases or c['name'] in args.cases]
    words = backend(args.backend, args.model)
    summary = {}
    for case in cases:
        engine = provider('offline')
        started = time.time()
        result = run(case, engine, words)
        result['seconds'] = round(time.time() - started, 2)
        lab = result.pop('lab')
        restored = Laboratory.restore(json.loads(json.dumps(lab.record())))
        result['replay_verified'] = restored.world.state_hash == lab.world.state_hash
        result['provider'] = words.name if words else 'grammar only'
        summary[case['name']] = result
        mark = 'PASS' if result['passed'] and result['replay_verified'] else 'FAIL'
        print(f'{mark} {case["name"]:18} {result["seconds"]:6.1f}s ' + ' | '.join(f'{s["category"]} ({s["actions"]} actions)' for s in result['replies']))
        for s in result['replies']:
            if s['plan']:
                print('     plan by', s['read_by'], '->', ' / '.join(s['plan']))
        for problem in result['invariant_violations']:
            print('     invariant:', problem)
        if not result['state_ok']:
            print('     world state check failed')
    passed = sum(r['passed'] and r['replay_verified'] for r in summary.values())
    print(f'{passed}/{len(summary)} cases passed with {next(iter(summary.values()))["provider"]}')
    save(summary, folder / ('language-summary.json' if args.language_cases else 'summary.json'))


if __name__ == '__main__':
    main()
