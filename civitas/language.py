"""Free text -> ordered canonical steps. Models translate; the grammar compiles.

A language model returns outcome steps in a closed JSON schema. Each step is
rendered as a canonical sentence of the offline grammar and must parse back to
the same outcome, so the deterministic grammar stays the only compiler from
language to measurable goals, and the player can read exactly what will be
attempted. Literal checks (stated distances, direction words) catch readings
that contradict the request; rejected output gets a bounded repair.
"""
from copy import deepcopy
import json
import re

from .intents import aliases, consistency, intent, numerals, parse_offline, stated, validate
from .model import keys

TASK_TAG = 'civitas-task-1'
STEP_FIELDS = ('target', 'axis', 'amount', 'reference', 'cycles', 'energy', 'effort_limit')
MAX_STEPS = 6
STEP_SCHEMA = {'type': 'object', 'properties': {
    'target': {'type': 'string'}, 'axis': {'type': 'string', 'enum': ['x', 'z']}, 'amount': {'type': 'number'},
    'reference': {'type': 'string', 'enum': ['relative', 'absolute']}, 'cycles': {'type': 'integer'},
    'energy': {'type': 'string', 'enum': ['any', 'environment', 'human']}, 'effort_limit': {'type': ['number', 'null']}},
    'required': list(STEP_FIELDS), 'additionalProperties': False}
SCHEMA = {'type': 'object', 'properties': {
    'status': {'type': 'string', 'enum': ['supported', 'unsupported', 'clarify']},
    'reason': {'type': 'string'}, 'steps': {'type': 'array', 'items': STEP_SCHEMA}},
    'required': ['status', 'reason', 'steps'], 'additionalProperties': False}

SYSTEM = '''You translate a player's request into ordered movement steps for a 2-D physics sandbox.
Coordinates: x is horizontal in metres (right is +x, left is -x); z is height above the ground in metres (ground is z = 0).
Listed objects have an alias, mass, current position, start position, and flags for selected and for anchored energy sources (sources cannot move).
Return JSON {"status", "reason", "steps"}:
- "supported": the WHOLE request is one or more movements of listed objects. Give every movement as a step, in order.
- "unsupported": some part is not a movement (colour, shape, building or naming machines, teleporting, leaving the map). steps = [].
- "clarify": the request is ambiguous (which object, how far, which way). Put one short question in reason. steps = [].
Step fields: target (alias or "selected"); axis ("x" or "z"); amount in metres; reference ("relative" = signed displacement,
left and down negative; "absolute" = destination coordinate); cycles (repeated upward lifts, usually 1); energy ("environment"
when told to use the environmental source or avoid human work, "human" when only by hand, otherwise "any"); effort_limit
(maximum human effort in joules, or null).
Rules: convert units (1 cm = 0.01 m, 1 mm = 0.001 m, "a metre" = 1 m, "half a metre" = 0.5 m). "the rock", "the stone", "it" and
"the object" without other identification mean "selected". Heavier, lighter, left-most and similar words choose among the
movable listed objects; an anchored energy source is never a rock, stone or load. Set energy and effort_limit only when
the request itself restricts them; set cycles above 1 only when it asks for repetition. "back where it started" is an absolute destination at its start position. "put it back down", "drop it", "onto the
ground" mean absolute z = 0. "off the floor", "above the ground" and "height" describe z. Never invent steps, objects or
distances the request does not state. Keep reason under 25 words.
Examples:
"nudge the rock a metre leftwards" -> {"status":"supported","reason":"Move the rock 1 m left.","steps":[{"target":"selected",
"axis":"x","amount":-1,"reference":"relative","cycles":1,"energy":"any","effort_limit":null}]}
"hike the crate up 3 m and let the reservoir do the work, then set it back on the ground" -> {"status":"supported",
"reason":"Lift 3 m with environmental energy, then lower to the ground.","steps":[{"target":"selected","axis":"z","amount":3,
"reference":"relative","cycles":1,"energy":"environment","effort_limit":null},{"target":"selected","axis":"z","amount":0,
"reference":"absolute","cycles":1,"energy":"any","effort_limit":null}]}
"melt the crate" -> {"status":"unsupported","reason":"Melting is not a movement.","steps":[]}
"move it a bit" -> {"status":"clarify","reason":"How far, and in which direction?","steps":[]}'''


# A model may not add restrictions the player never stated (e.g. "heave" is not "by hand").
CUES = {
    'energy': (lambda s: s['energy'] != 'any',
               r'\b(?:hands?|manual\w*|muscles?|yourself|human|people|person|effort|environment\w*|source|reservoir|'
               r'engine|machine\w*|motor|powered|energy|mechanical)\b', 'set energy to "any"'),
    'effort_limit': (lambda s: s['effort_limit'] is not None, r'\b(?:j|joules?|kj|effort)\b', 'set effort_limit to null'),
    'cycles': (lambda s: s['cycles'] > 1, r'\b(?:times|twice|thrice|repeat\w*|again|cycles?)\b', 'set cycles to 1'),
}


def unstated(steps, text):
    words = numerals(text)
    return [f'the request never restricts {name.replace("_", " ")}: {fix}'
            for name, (used, cue, fix) in CUES.items() if any(used(s) for s in steps) and not re.search(cue, words)]


def number(value):
    return format(round(value, 4), '.10g')


def render(step):
    """Canonical grammar sentence for one validated outcome step."""
    a, absolute = round(step['amount'], 4), step['reference'] == 'absolute'
    if step['axis'] == 'z':
        s = (f'Move the selected object to a height of {number(a)} m' if absolute else
             f'Lift the selected object {number(a)} m' if a >= 0 else f'Lower the selected object {number(-a)} m')
    else:
        s = (f'Move the selected object to x = {number(a)} m' if absolute else
             f'Move the selected object {number(abs(a))} m to the {"right" if a >= 0 else "left"}')
    if step['cycles'] > 1:
        s += f', {step["cycles"]} times'
    if step['energy'] == 'environment':
        s += ', using environmental energy'
    elif step['energy'] == 'human':
        s += ', by hand'
    if step['effort_limit'] is not None:
        s += f', using at most {number(step["effort_limit"])} joules'
    return s


def describe(context):
    names = aliases(context)
    objects = {}
    for alias, identity in names.items():
        if alias == 'selected':
            continue
        o = context['view']['observations'][identity]['object']
        objects[alias] = {'material': context['view']['observations'][identity]['material']['label'],
                          'mass_kg': o['mass'], 'position_xz_m': o['position'],
                          'start_position_xz_m': o['motions'][0]['from'] if o['motions'] else o['position'],
                          'selected': identity == names['selected'], 'anchored_energy_source': 'source' in o}
    return objects


def check(data, text, context):
    """Validated plan or ValueError explaining what to repair."""
    keys(data, {'status', 'reason', 'steps'})
    if data['status'] not in {'supported', 'unsupported', 'clarify'} or not isinstance(data['reason'], str):
        raise ValueError('status must be supported, unsupported or clarify, with a text reason')
    reason = data['reason'].strip()[:400]
    if not isinstance(data['steps'], list):
        raise ValueError('steps must be a list')
    if data['status'] != 'supported':
        return {'status': data['status'], 'reason': reason or 'Describe one or more measurable movements.', 'steps': []}
    if not 1 <= len(data['steps']) <= MAX_STEPS:
        raise ValueError(f'a supported request needs 1 to {MAX_STEPS} steps')
    names, steps, full = aliases(context), [], []
    for i, raw in enumerate(data['steps'], 1):
        keys(raw, set(STEP_FIELDS))
        if isinstance(raw.get('cycles'), float) and raw['cycles'].is_integer():
            raw = raw | {'cycles': int(raw['cycles'])}
        step = validate(intent(**raw), context)
        step['amount'] = round(step['amount'], 4)
        if step['axis'] == 'z' and step['reference'] == 'absolute' and step['amount'] < 0:
            return {'status': 'boundary', 'reason': 'Heights below the ground (z < 0) are a fixed boundary of this world.', 'steps': []}
        sentence = render(step)
        scoped = deepcopy(context)
        scoped['project']['target'] = names[step['target']]
        back = parse_offline(sentence, scoped)
        if back['status'] != 'supported' or any(back[k] != step[k] for k in ('axis', 'reference', 'cycles', 'energy', 'effort_limit')) \
                or abs(back['amount'] - step['amount']) > 1e-9:
            raise ValueError(f'step {i} cannot be expressed as one supported movement: {back["reason"] or sentence}')
        full.append(step)
        steps.append({'text': sentence, 'target': names[step['target']], 'alias': step['target']})
    if len(full) == 1:
        problems = consistency(full[0], text)
    else:
        _, distances = stated(text)
        problems = [f'the request states {d:g} m but no step uses that distance' for d in distances
                    if not any(abs(abs(s['amount']) - abs(d)) < 1e-9 for s in full)]
    problems += unstated(full, text)
    if problems:
        raise ValueError('; '.join(problems))
    return {'status': 'supported', 'reason': reason, 'steps': steps}


def translate(text, context, backend, repairs=2):
    """{'status', 'reason', 'steps', 'model', 'usage', 'attempts'}; raises on failure."""
    turns = [json.dumps({'request': text, 'objects': describe(context)}, separators=(',', ':'))]
    usage, error, model = {'input_tokens': 0, 'output_tokens': 0, 'cost': 0}, None, backend.name
    for attempt in range(1, repairs + 2):
        public, used_in, used_out, model = backend.complete(SYSTEM, turns, SCHEMA, 1200)
        usage['input_tokens'] += int(used_in or 0)
        usage['output_tokens'] += int(used_out or 0)
        try:
            plan = check(json.loads(public), text, context)
            return plan | {'model': model, 'usage': usage, 'attempts': attempt}
        except (ValueError, TypeError, KeyError) as e:
            error = str(e)[:300] or type(e).__name__
            turns += [public or '{}', f'That JSON was rejected: {error}. Return one corrected JSON object only.']
    raise ValueError(f'{model} returned no valid plan after {repairs + 1} attempts (last error: {error}); nothing was executed')
