"""Disclosed, bounded composition policy. No private truth or artifact recipes."""
from copy import deepcopy
from itertools import permutations
from math import ceil, hypot
import re

from .cognition import proposal


def interpret(context):
    p, v = context['project'], context['view']
    text = p['text'].lower()
    objects = v['observations']
    target = p['target']
    if target not in objects:
        return proposal('unresolved', 'Select an observed object for this task.', requirements=['observed target'])
    if not re.search(r'\b(raise|lift|elevate|move|transport)\b', text):
        return proposal('unresolved', 'The offline interpreter supports measurable lifting and horizontal movement only.', requirements=['modeled displacement goal or local model interpretation'])
    vertical = bool(re.search(r'\b(raise|lift|elevate)\b', text))
    amount = re.search(r'(\d+(?:\.\d+)?)\s*(?:m\b|met(?:er|re)s?\b)', text)
    amount = float(amount.group(1)) if amount else 1.0
    repeats = re.search(r'(\d+)\s*(?:times|cycles)', text)
    count = int(repeats.group(1)) if repeats else (2 if 'repeat' in text else 1)
    if count > 8 or amount <= 0:
        return proposal('unresolved', 'Requested motion is outside the bounded planner range.', requirements=['1-8 repetitions and positive distance'])
    obj = objects[target]['object']
    def c(measure, value, op='>=', category='physical', subject=target, **extra):
        return dict(category=category, measure=measure, subject=subject, op=op, value=value, **extra)
    lower = obj['position'][1]
    goals = [c('z' if vertical else 'x', obj['position'][1 if vertical else 0] + amount)]
    if vertical and count > 1:
        goals.append(c('crossings', count, parameters={'lower': lower, 'upper': lower + amount}))
    # These are outcome requirements, not a construction or technology selection.
    goals += [c('human_work', obj['human_work'], '<='), c('environment_work', obj['environment_work'] + .001)]
    return proposal('intent', f'Interpretation: move selected {obj["mass"]:g} kg body {amount:g} m {"up" if vertical else "horizontally"}, {count} time(s), using environmental work and no added direct human work. Defaults are explicit.', goals=goals)


def relations(view):
    result = {}
    for k in view['knowledge']:
        if k['origin'] != 'construction':
            continue
        if k['claim'].startswith('relation:'):
            result[k['claim'].split(':', 1)[1]] = k['value']
        elif k['claim'].startswith('removed_relation:'):
            result.pop(k['claim'].split(':', 1)[1], None)
    return result


def propose(context):
    p, v = context['project'], context['view']
    if not p['goals']:
        return interpret(context)
    if not any(a['kind'] == 'hypothesis' for a in p['artifacts']):
        return proposal('hypothesis', 'Test compatible paths between observed energy sources and the target. Treat reach, force and load support as separately validated requirements.', requirements=['compatible path', 'sufficient energy and force', 'supported elevated load'])
    latest = p['latest'] or {}
    if latest.get('experiment') and not latest.get('passed') and p['artifacts'][-1]['kind'] != 'diagnosis':
        failures = [r['code'] for a in p['attempts'] if not a['accepted'] for r in a['evaluations']]
        return proposal('diagnosis', 'The measured candidate failed. Next candidate will use the recorded blocking requirements: ' + ', '.join(sorted(set(failures)) or ['goal unmet']), requirements=sorted(set(failures)))
    objects = v['observations']
    goal = next((c for c in p['goals'] if c['measure'] in {'x', 'z'} and c['category'] == 'physical' and c['op'] == '>='), None)
    if not goal or goal['subject'] not in objects:
        return proposal('unresolved', 'Bounded planner cannot construct for these measurements.', requirements=['supported positional goal'])
    target = goal['subject']
    caps = {i: {a['name'] for a in o['affordances']} for i, o in objects.items()}
    sources = sorted(i for i in objects if i != target and 'supply_work' in caps[i])
    if not sources:
        return proposal('experiment_proposal', 'Measure the unmet goal; no observed environmental source is available.')
    span = hypot(objects[target]['object']['position'][0] - v['position'][0], max(goal['value'] if goal['measure'] == 'z' else 0, 1))
    shaped = [i for i, o in objects.items() if i != target and 'source' not in o['object'] and o['object']['length'] >= span]
    if not shaped and not any(a['action']['kind'] == 'shape' for a in p['attempts']):
        known = {k['claim'] for k in v['knowledge'] if k['value'] is True and k['origin'] in {'initial', 'experiment'}}
        stocks = [i for i, m in v['materials'].items() if v['inventory'].get(i, 0) >= 2 and f'shape:{i}' in known and min(m['tensile_strength'], m['compressive_strength']) > 0]
        if stocks:
            material = min(stocks, key=lambda i: (v['materials'][i]['shape_energy'], i))
            return proposal('action_proposal', 'Shape available stock with reach covering the measured separation; strength still requires testing.', actions=[{'actor': v['id'], 'kind': 'shape', 'args': {'material': material, 'mass': 2, 'length': max(1, ceil(span)), 'radius': .5}}])
    installed = list(relations(v).values())
    queue = []
    # Prior measured graphs are hypotheses for transfer, never authoritative recipes.
    if p['use_knowledge']:
        for discovery in v['discoveries']:
            for principle in discovery['principles']:
                path = principle['path'][:-1] + [target]
                if len(set(path)) == len(path) and all(i in objects for i in path):
                    support = next((i for i in path[:-1] if objects[i]['object']['length'] >= span), None)
                    queue.append((path, principle['mode'], support, discovery['design']))
    failure_codes = {r['code'] for a in p['attempts'] if not a['accepted'] for r in a['evaluations']}
    for length in (2, 3):
        for source in sources:
            for middle in permutations(sorted(i for i in objects if i not in {source, target}), length - 2):
                path = [source, *middle, target]
                for mode in ('force', 'rotation'):
                    if all('connect_' + mode in caps[i] for i in path):
                        queue.append((path, mode, None, None))
                        if 'unsupported_load' in failure_codes:
                            queue += [(path, mode, i, None) for i in sorted(objects) if i != target and 'support' in caps[i]]
    tried = set()
    for identity in p['designs']:
        d = v['designs'][identity]['content']
        work = next(a for a in d['construction_steps'] if a['kind'] == 'work')
        support = next((r['a'] for r in d['relationships'] if r['kind'] == 'support' and r['b'] == target), None)
        tried.add((tuple(work['args']['path']), work['args']['mode'], support))
    for path, mode, support, reuse in queue:
        if (tuple(path), mode, support) in tried:
            continue
        wanted = [{'a': a, 'b': b, 'kind': mode} for a, b in zip(path, path[1:])]
        if support:
            wanted.append({'a': support, 'b': target, 'kind': 'support'})
        def same(a, b):
            return a['kind'] == b['kind'] and ({a['a'], a['b']} == {b['a'], b['b']} if a['kind'] in {'force', 'rotation'} else (a['a'], a['b']) == (b['a'], b['b']))
        steps = [{'actor': v['id'], 'kind': 'connect', 'args': r} for r in wanted if not any(same(r, i) for i in installed)]
        obj = objects[target]['object']
        axis = 1 if goal['measure'] == 'z' else 0
        delta = goal['value'] - obj['position'][axis]
        crossing = next((c for c in p['goals'] if c['measure'] == 'crossings' and c['subject'] == target), None)
        motions = [delta] if delta > 0 else []
        if crossing:
            # Re-test the full bounded cycle; earlier motion stays in world history.
            height = crossing['parameters']['upper'] - crossing['parameters']['lower']
            if not motions:
                motions = [-height, height]
            for _ in range(int(crossing['value']) - 1):
                motions += [-height, height]
        if not motions:
            return proposal('experiment_proposal', 'Measure the current outcome before claiming success.')
        steps += [{'actor': v['id'], 'kind': 'work', 'args': {'path': path, 'mode': mode, 'dx': amount if axis == 0 else 0, 'dz': amount if axis == 1 else 0, 'duration': 10}} for amount in motions]
        parent = p['active_design']
        evidence = sorted({e for k in v['knowledge'] for e in k['evidence']})[-20:]
        design = {'title': 'Measured composition candidate', 'components': [{'key': i, 'requirements': []} for i in sorted(set(path) | ({support} if support else set()))],
                  'relationships': wanted, 'required_properties': [], 'intended_functions': ['satisfy recorded displacement and effort constraints'], 'constraints': deepcopy(p['goals']), 'construction_steps': steps,
                  'assumptions': ['Quasistatic transfer and separate support are kernel approximations.'] + ([f'Reuse measured design {reuse}; revalidation required.'] if reuse else []),
                  'failure_modes': sorted(failure_codes), 'evidence': evidence, 'version': v['designs'][parent]['content']['version'] + 1 if parent else 1, 'parent': parent}
        return proposal('design_revision' if parent else 'candidate_design', ('Reuse prior measured path; ' if reuse else 'Enumerate compatible path; ') + 'construct and test against frozen goals.', design=design)
    return proposal('unresolved', 'Bounded path and support search exhausted; this is not a proof of impossibility.', requirements=sorted(failure_codes) or ['broader composition search'])
