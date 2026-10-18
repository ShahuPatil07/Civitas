"""Disclosed, bounded composition policy. No private truth or artifact recipes."""
from copy import deepcopy
from itertools import permutations
from math import ceil, hypot

from .cognition import proposal
from .intents import compile_intent, parse_offline, crossings

# Published affordance costs (see affordances.py): effort J per primitive.
CONNECT_J, WORK_J, MEASURE_J = 5, 1, 1


def interpret(context):
    return compile_intent(parse_offline(context['project']['text'], context), context)


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
    goal = next((c for c in p['goals'] if c['measure'] in {'x', 'z'} and c['category'] == 'physical' and c['op'] in {'>=', '<=', '=='}), None)
    if not goal or goal['subject'] not in objects:
        return proposal('unresolved', 'Bounded planner cannot construct for these measurements.', requirements=['unsupported', 'supported positional goal'])
    target = goal['subject']
    obj = objects[target]['object']
    axis = 1 if goal['measure'] == 'z' else 0
    delta = goal['value'] - obj['position'][axis]
    crossing = next((c for c in p['goals'] if c['measure'] == 'crossings' and c['subject'] == target), None)
    motions = [delta] if delta else []
    if crossing:
        lower, upper = crossing['parameters']['lower'], crossing['parameters']['upper']
        remaining = max(0, int(crossing['value']) - crossings(obj, lower, upper))
        motions = []
        height = obj['position'][1]
        for _ in range(remaining):
            if height > lower:
                motions.append(lower - height)
                height = lower
            motions.append(upper - height)
            height = upper
    if not motions:
        if latest.get('experiment'):
            return proposal('unresolved', 'The position is reached, but other requirements remain unmet in this setup. ' + '; '.join(r['reason'] for r in latest.get('evaluations', []) if r['status'] != 'satisfied'), requirements=['not_found', 'unmet measured requirements'])
        return proposal('experiment_proposal', 'Measure the current state; the requested position may already be satisfied.')
    environmental = any(c['measure'] == 'human_work' and c['op'] == '<=' for c in p['goals'])
    human_only = any(c['measure'] == 'environment_work' and c['op'] == '<=' for c in p['goals'])
    caps = {i: {a['name'] for a in o['affordances']} for i, o in objects.items()}
    sources = [] if human_only else sorted(i for i in objects if i != target and 'supply_work' in caps[i])
    if not sources and environmental:
        if latest.get('experiment'):
            return proposal('unresolved', 'Not achievable with the observed setup: no environmental energy source is available.', requirements=['missing_resource', 'environmental source'])
        return proposal('experiment_proposal', 'Measure the unmet goal; no observed environmental source is available.')
    end = list(obj['position'])
    end[axis] = goal['value']
    span = max(hypot(end[0] - v['position'][0], end[1] - v['position'][1]),
               hypot(obj['position'][0] - v['position'][0], obj['position'][1] - v['position'][1]))
    # Human motion can be attempted directly before manufacturing any stock.
    human_tried = any(a['action']['kind'] == 'move' for a in p['attempts'])
    human_force_failed = any(a['action']['kind'] == 'move' and any(r['code'] in {'inadequate_force', 'inadequate_power', 'unavailable_resource'} for r in a['evaluations']) for a in p['attempts'] if not a['accepted'])
    if human_only and human_force_failed:
        return proposal('unresolved', 'Not achievable with the current human-only action capabilities: ' + '; '.join(r['reason'] for a in p['attempts'] if not a['accepted'] for r in a['evaluations']), requirements=['capability_limit', 'more human force/energy or permission for environmental work'])
    # A committed effort ceiling prunes candidates before any effort is spent.
    cap = next((c['value'] for c in p['goals'] if c['category'] == 'resource' and c['measure'] == 'effort_spent' and c['subject'] == v['id'] and c['op'] in {'<=', '=='}), None)
    remaining = None if cap is None else cap - v['effort_spent']
    too_costly = []
    shaped = [i for i, o in objects.items() if i != target and 'source' not in o['object'] and o['object']['length'] >= span]
    if not shaped and (environmental or human_tried) and not any(a['action']['kind'] == 'shape' for a in p['attempts']):
        known = {k['claim'] for k in v['knowledge'] if k['value'] is True and k['origin'] in {'initial', 'experiment'}}
        stocks = [i for i, m in v['materials'].items() if v['inventory'].get(i, 0) >= 2 and f'shape:{i}' in known and min(m['tensile_strength'], m['compressive_strength']) > 0]
        if stocks:
            material = min(stocks, key=lambda i: (v['materials'][i]['shape_energy'], i))
            # Shaping alone is useless: reserve two connections, a transfer and a measurement.
            cost = 2 * v['materials'][material]['shape_energy'] + 2 * CONNECT_J + WORK_J + MEASURE_J
            if remaining is None or cost <= remaining:
                return proposal('action_proposal', 'Shape available stock with reach covering the measured separation; strength still requires testing.', actions=[{'actor': v['id'], 'kind': 'shape', 'args': {'material': material, 'mass': 2, 'length': max(1, ceil(span)), 'radius': .5}}])
            too_costly.append(cost)
    installed = list(relations(v).values())
    queue = []
    failure_codes = {r['code'] for a in p['attempts'] if not a['accepted'] for r in a['evaluations']}
    if not environmental and not human_force_failed:
        queue.append(([target], 'human', None, None))
        if 'unsupported_load' in failure_codes:
            queue += [([target], 'human', i, None) for i in sorted(objects) if i != target and 'support' in caps[i]]
    # Prior measured graphs are hypotheses for transfer, never authoritative recipes.
    if p['use_knowledge'] and not human_only:
        for discovery in v['discoveries']:
            for principle in discovery['principles']:
                path = principle['path'][:-1] + [target]
                if len(set(path)) == len(path) and all(i in objects for i in path):
                    support = next((i for i in path[:-1] if objects[i]['object']['length'] >= span), None)
                    queue.append((path, principle['mode'], support, discovery['design']))
    for length in (2, 3):
        for source in sources:
            for middle in permutations(sorted(i for i in objects if i not in {source, target}), length - 2):
                path = [source, *middle, target]
                for mode in ('force', 'rotation'):
                    if all('connect_' + mode in caps[i] for i in path):
                        queue.append((path, mode, None, None))
                        if 'unsupported_load' in failure_codes:
                            queue += [(path, mode, i, None) for i in sorted(objects) if i != target and 'support' in caps[i]]
    # Power failures are diagnosed as too-short durations: spread the same work over longer time.
    slow = sum(1 for a in p['attempts'] if not a['accepted'] and any(r['code'] == 'inadequate_power' for r in a['evaluations']))
    duration = 10 * 4 ** min(slow, 3)
    tried = set()
    for identity in p['designs']:
        d = v['designs'][identity]['content']
        work = next((a for a in d['construction_steps'] if a['kind'] in {'work', 'move'}), None)
        if work is None:
            continue
        support = next((r['a'] for r in d['relationships'] if r['kind'] == 'support' and r['b'] == target), None)
        tried.add((tuple(work['args'].get('path', [target])), work['args'].get('mode', 'human'), support, work['args']['duration']))
    for path, mode, support, reuse in queue:
        if (tuple(path), mode, support, duration) in tried:
            continue
        wanted = [{'a': a, 'b': b, 'kind': mode} for a, b in zip(path, path[1:])]
        if support:
            wanted.append({'a': support, 'b': target, 'kind': 'support'})
        def same(a, b):
            return a['kind'] == b['kind'] and ({a['a'], a['b']} == {b['a'], b['b']} if a['kind'] in {'force', 'rotation'} else (a['a'], a['b']) == (b['a'], b['b']))
        steps = [{'actor': v['id'], 'kind': 'connect', 'args': r} for r in wanted if not any(same(r, i) for i in installed)]
        blocked = [a['action']['args'] for a in p['attempts'] if not a['accepted'] and a['action']['kind'] == 'connect'
                   and any(r['code'] == 'unsupported_connection' for r in a['evaluations'])]
        if any(same(step['args'], r) for step in steps for r in blocked):
            continue
        steps += [{'actor': v['id'], 'kind': 'move' if mode == 'human' else 'work',
                   'args': ({'target': target} if mode == 'human' else {'path': path, 'mode': mode}) |
                           {'dx': amount if axis == 0 else 0, 'dz': amount if axis == 1 else 0, 'duration': duration}} for amount in motions]
        cost = CONNECT_J * sum(step['kind'] == 'connect' for step in steps) + WORK_J * sum(step['kind'] == 'work' for step in steps) + MEASURE_J
        if remaining is not None and cost > remaining:
            too_costly.append(cost)
            continue
        parent = p['active_design']
        evidence = sorted({e for k in v['knowledge'] for e in k['evidence']})[-20:]
        design = {'title': 'Measured composition candidate', 'components': [{'key': i, 'requirements': []} for i in sorted(set(path) | ({support} if support else set()))],
                  'relationships': wanted, 'required_properties': [], 'intended_functions': ['satisfy recorded displacement and effort constraints'], 'constraints': deepcopy(p['goals']), 'construction_steps': steps,
                  'assumptions': ['Quasistatic transfer and separate support are kernel approximations.'] + ([f'Reuse measured design {reuse}; revalidation required.'] if reuse else []),
                  'failure_modes': sorted(failure_codes), 'evidence': evidence, 'version': v['designs'][parent]['content']['version'] + 1 if parent else 1, 'parent': parent}
        return proposal('design_revision' if parent else 'candidate_design', ('Reuse prior measured path; ' if reuse else 'Enumerate compatible path; ') + 'construct and test against frozen goals.', design=design)
    reasons = sorted({r['reason'] for a in p['attempts'] if not a['accepted'] for r in a['evaluations']})
    if too_costly:
        reasons.append(f'the cheapest remaining candidate needs at least {min(too_costly):g} J of effort but the limit leaves {remaining:g} J')
    return proposal('unresolved', 'I could not complete this task with the current setup and planner: ' + '; '.join(reasons or ['no compatible construction found']) + '. Search exhaustion is not proof of physical impossibility.', requirements=['not_found'] + (sorted(failure_codes) or ['broader composition search']))
