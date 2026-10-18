"""Outcome-only language IR. No artifact names, recipes, or world writes."""
from copy import deepcopy
import re

from .cognition import proposal
from .model import keys, number

# First requirement of every unresolved artifact: why no task is executed.
REASONS = ('clarify', 'unsupported', 'boundary', 'missing_resource', 'capability_limit', 'not_found')
FIELDS = {'status', 'reason', 'target', 'axis', 'amount', 'reference', 'cycles', 'energy', 'effort_limit'}
SCHEMA = {'type': 'object', 'properties': {
    'status': {'type': 'string', 'enum': ['supported', 'unsupported', 'clarify']},
    'reason': {'type': 'string', 'maxLength': 240}, 'target': {'type': 'string'},
    'axis': {'type': 'string', 'enum': ['x', 'z']}, 'amount': {'type': 'number'},
    'reference': {'type': 'string', 'enum': ['relative', 'absolute']},
    'cycles': {'type': 'integer', 'minimum': 1, 'maximum': 8},
    'energy': {'type': 'string', 'enum': ['any', 'environment', 'human']},
    'effort_limit': {'type': ['number', 'null']}},
    'required': sorted(FIELDS), 'additionalProperties': False}


def aliases(context):
    names = {'selected': context['project']['target']}
    names.update({f'o{i}': identity for i, identity in enumerate(sorted(context['view']['observations']))})
    return names


def intent(status='supported', reason='', **values):
    return dict(status=status, reason=reason, target='selected', axis='z', amount=1.,
                reference='relative', cycles=1, energy='any', effort_limit=None) | values


def validate(data, context):
    keys(data, FIELDS)
    if data['status'] not in {'supported', 'unsupported', 'clarify'}:
        raise ValueError('status must be supported, unsupported or clarify')
    if not isinstance(data['reason'], str) or len(data['reason']) > 1000:
        raise ValueError('reason must be a concise explanation')
    if data['target'] not in aliases(context):
        raise ValueError('target must be selected or an observed object alias')
    if data['axis'] not in {'x', 'z'} or data['reference'] not in {'relative', 'absolute'} or data['energy'] not in {'any', 'environment', 'human'}:
        raise ValueError('invalid axis, reference or energy preference')
    number(data['amount'], 'amount')
    if type(data['cycles']) is not int or not 1 <= data['cycles'] <= 8:
        raise ValueError('cycles must be an integer from 1 to 8')
    if data['effort_limit'] is not None:
        number(data['effort_limit'], 'effort_limit', 0)
    return deepcopy(data)


def crossings(obj, lower, upper):
    armed, count = False, 0
    for m in obj['motions']:
        if m['from'][1] <= lower:
            armed = True
        if armed and m['to'][1] >= upper:
            count += 1
            armed = False
    return count


def compile_intent(data, context):
    d = validate(data, context)
    if d['status'] != 'supported':
        prefix = 'Not supported in this setup: ' if d['status'] == 'unsupported' else 'I need a clearer task: '
        return proposal('unresolved', prefix + (d['reason'] or 'describe one measurable movement of an observed object.'), requirements=[d['status']])
    v, p = context['view'], context['project']
    target = aliases(context)[d['target']]
    if target not in v['observations']:
        return proposal('unresolved', 'Select an observed object before giving a task.', requirements=['clarify', 'observed target'])
    obj = v['observations'][target]['object']
    if 'source' in obj:
        return proposal('unresolved', 'Not supported in this setup: environmental source boundaries are anchored.', requirements=['unsupported', 'movable target'])
    axis = 1 if d['axis'] == 'z' else 0
    start = obj['position'][axis]
    end = start + d['amount'] if d['reference'] == 'relative' else d['amount']
    if d['axis'] == 'z' and end < 0:
        return proposal('unresolved', 'Not feasible in this setup: the requested elevation is below the ground boundary.', requirements=['boundary', 'elevation >= 0'])
    if d['cycles'] > 1 and (d['axis'] != 'z' or end <= 0 or (d['reference'] == 'relative' and end <= start)):
        return proposal('unresolved', 'Not supported in this setup: repeated-task measurement currently counts upward elevation crossings only.', requirements=['unsupported', 'upward cycles'])
    def c(measure, value, op='>=', category='physical', subject=target, **extra):
        return dict(category=category, measure=measure, subject=subject, op=op, value=value, **extra)
    goals = [c(d['axis'], end, '==')]
    if d['cycles'] > 1:
        lower = start if d['reference'] == 'relative' else min(start, 0.)
        goals.append(c('crossings', crossings(obj, lower, end) + d['cycles'], parameters={'lower': lower, 'upper': end}))
    if d['energy'] == 'environment':
        goals.append(c('human_work', obj['human_work'], '<='))
        if end != start or d['cycles'] > 1:
            if d['axis'] == 'z' and end < start:
                return proposal('unresolved', 'Not supported in this setup: lowering dissipates potential energy; environmental useful-work attribution for lowering is not modeled.', requirements=['unsupported', 'controlled lowering with any energy source'])
            goals.append(c('environment_work', obj['environment_work'] + .001))
    elif d['energy'] == 'human':
        goals.append(c('environment_work', obj['environment_work'], '<='))
    if d['effort_limit'] is not None:
        goals.append(c('effort_spent', p['initial_effort'] + d['effort_limit'], '<=', 'resource', v['id']))
    detail = f'Interpretation: {obj["mass"]:g} kg object {target[:8]}, {d["axis"]}={end:g} m, {d["cycles"]} cycle(s); energy={d["energy"]}.'
    if d['effort_limit'] is not None:
        detail += f' Additional total human effort <= {d["effort_limit"]:g} J.'
    return proposal('intent', detail + ' ' + d['reason'], goals=goals)


# Grammar coverage gaps, as opposed to deliberate refusals (negation, several
# steps, conflicting energy, ambiguous mass). Only gaps justify asking a model.
GAPS = ('Describe one object displacement', 'Specify the displacement or destination', 'Specify an effort limit',
        'I cannot safely interpret the whole request offline')


# Single-outcome limits that a multi-step translator can resolve.
STEP_GAPS = ('Multiple distances or steps', 'One axis per project')


def covered(data, multistep=False):
    gaps = GAPS + STEP_GAPS if multistep else GAPS
    return not (data['status'] == 'clarify' and data['reason'].startswith(gaps))


HORIZONTAL = r'\b(?:left\w*|right\w*|sideways|horizontal\w*)\b'
VERTICAL = r'\b(?:up\w*|down\w*|lift\w*|raise\w*|hoist\w*|lower\w*|elevat\w*|height|high|floor|ground)\b'
NEGATIVE = r'\b(?:left\w*|down\w*|lower\w*)\b'
POSITIVE = r'\b(?:right\w*|up|upward\w*|raise\w*|lift\w*|hoist\w*|elevat\w*)\b'
DESTINATION = r'\b(?:to|at|until|height of|elevation of|position|coordinate|off the|above the)\b'


def stated(text):
    """Distances written in the request, in metres (after number words)."""
    t = numerals(text)
    scale = {'c': .01, 'm': 1}
    found = re.findall(r'(-?\d+(?:\.\d+)?|\.\d+)\s*(cm\b|centimet(?:er|re)s?\b|mm\b|millimet(?:er|re)s?\b|m\b|met(?:er|re)s?\b)', t)
    return t, [float(n) * (.001 if u.startswith(('mm', 'milli')) else scale['c'] if u.startswith(('cm', 'centi')) else 1) for n, u in found]


def consistency(data, text):
    """Problems where a model interpretation contradicts the literal request."""
    if data['status'] != 'supported':
        return []
    t, distances = stated(text)
    problems = []
    if len(distances) == 1 and abs(abs(data['amount']) - abs(distances[0])) > 1e-9:
        problems.append(f'the request states {distances[0]:g} m, so set amount to {distances[0]:g} or -{distances[0]:g}')
    horizontal, vertical = bool(re.search(HORIZONTAL, t)), bool(re.search(VERTICAL, t))
    if horizontal != vertical and data['axis'] != ('x' if horizontal else 'z'):
        problems.append('the direction words describe ' + ('horizontal motion: set axis to "x"' if horizontal else 'height: set axis to "z"'))
    negative, positive = bool(re.search(NEGATIVE, t)), bool(re.search(POSITIVE, t))
    if data['reference'] == 'relative' and negative != positive and (data['amount'] < 0) != negative and data['amount'] != 0:
        problems.append('the direction words require a ' + ('negative' if negative else 'positive') + ' amount')
    if data['reference'] == 'absolute' and (horizontal or negative or positive) and not re.search(DESTINATION, t):
        problems.append('this is a displacement, not a destination: keep status "supported", set reference to "relative" '
                        'and amount to the signed distance')
    return problems


WORDS = {'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5',
         'six': '6', 'seven': '7', 'eight': '8', 'nine': '9', 'ten': '10'}
FRACTIONS = {'half': .5, 'quarter': .25}


def numerals(text):
    """Lower-case text with number words as digits; "1 and a half" is 1.5, never 0.5."""
    t = text.lower().replace("don't", 'do not')
    for word, value in WORDS.items():
        t = re.sub(r'\b' + word + r'\b', value, t)
    for word, value in FRACTIONS.items():
        t = re.sub(r'\b(\d+) and an? ' + word + r'\b', lambda m: f'{int(m[1]) + value:g}', t)
        t = re.sub(r'\b' + word + r'\b', f'{value:g}', t)
    return t


def parse_offline(text, context):
    """Conservative grammar: refuse unknown clauses, rather than drop them.

    A local language model can interpret paraphrases outside this grammar. This
    parser only recognizes physical outcome vocabulary, never artifact recipes.
    """
    t = numerals(text).replace('twice', '2 times').replace('thrice', '3 times')
    if re.search(r'\b(?:do not|never)\s+(?:move|lift|raise|lower|push|pull)', t):
        return intent('clarify', 'The request says not to perform the movement; no movement will be attempted.')
    verbs = re.findall(r'\b(?:raise|raises|lift|lifting|elevate|hoist|lower|move|shift|slide|push|pull|transport|hold|support)\b', t)
    if not verbs:
        return intent('clarify', 'Describe one object displacement, elevation or support height.')
    # Parse one displacement plus optional explicit effort and mass constraints.
    effort = re.search(r'(?:at most|no more than|under|less than|within|<=)\s*(\d+(?:\.\d+)?)\s*(?:j\b|joules?\b)', t)
    if re.search(r'\b(?:j|joules?)\b', t) and not effort:
        return intent('clarify', 'Specify an effort limit as at most N joules.')
    target = 'selected'
    mass = re.search(r'(\d+(?:\.\d+)?)\s*(?:kg\b|kilograms?\b)', t)
    if mass:
        matches = [a for a, identity in aliases(context).items() if a != 'selected' and context['view']['observations'][identity]['object']['mass'] == float(mass[1])]
        if len(matches) != 1:
            return intent('clarify', 'That mass does not identify exactly one observed object. Select a target explicitly.')
        target = matches[0]
    distance = re.findall(r'(-?\d+(?:\.\d+)?|\.\d+)\s*(cm\b|centimet(?:er|re)s?\b|mm\b|millimet(?:er|re)s?\b|m\b|met(?:er|re)s?\b)', t)
    if len(distance) > 1:
        return intent('clarify', 'Multiple distances or steps need separate projects; I will not drop a step.')
    if not distance:
        return intent('clarify', 'Specify the displacement or destination in metres or centimetres.')
    amount = float(distance[0][0])
    if distance[0][1].startswith(('cm', 'centi')):
        amount /= 100
    elif distance[0][1].startswith(('mm', 'milli')):
        amount /= 1000
    # "to x = -1 m" names a horizontal destination coordinate, which may be negative.
    xabs = bool(re.search(r'\bto\s+(?:position\s+)?x\s*=\s*-?\d', t))
    if amount < 0 and not xabs:
        return intent('clarify', 'Use a positive distance with left/down, or an explicit absolute coordinate.')
    axis = 'x' if xabs else 'z' if re.search(r'\b(?:raise|raises|lift|lifting|elevate|hoist|lower|up|upward|upwards|down|downward|downwards|high|height|elevation|above)\b', t) else 'x'
    if re.search(r'\b(?:left|right|horizontally|horizontal)\b', t) and axis == 'z':
        return intent('clarify', 'One axis per project is supported; separate horizontal and vertical tasks.')
    if not xabs and re.search(r'\b(?:left|down|downward|downwards|lower)\b', t):
        amount = -amount
    absolute = xabs or bool(re.search(r'\b(?:to|at)\s+(?:a\s+)?(?:height\s+of\s+|elevation\s+of\s+)?\d', t) or re.search(r'\b(?:high|above the ground|above ground)\b', t))
    if absolute and not xabs:
        amount = abs(amount)
    repeat = re.search(r'(\d+)\s*(?:times|cycles)', t)
    count = int(repeat[1]) if repeat else (2 if re.search(r'\brepeated(?:ly)?\b', t) else 1)
    if not 1 <= count <= 8:
        return intent('unsupported', 'This planner has a limit of 8 finite repetitions per project.')
    environment = bool(re.search(r'\b(?:environmental|environment|source)\b|without (?:direct )?human (?:effort|work|lifting)', t))
    human = bool(re.search(r'\b(?:manually|human only|only human|by hand)\b|without (?:any )?(?:environmental|source)', t))
    if human and environment and not re.search(r'without (?:any )?(?:environmental|source)', t):
        return intent('clarify', 'The requested energy restrictions conflict.')
    # Unknown content is not silently reduced to the first recognized verb.
    allowed = set('please could can you i want would like to the a an this that it selected object body load stone rock heavy using use with without direct human effort work energy environmental environment source by from at of m meter meters metre metres cm centimeter centimeters centimetre centimetres mm millimeter millimeters millimetre millimetres kg kilogram kilograms j joule joules times cycles repeatedly repeated then and no more than at most under less within only manually hand do not requiring people continuously for us help something build create keeps keep hold holds support supports above ground height elevation up upward upwards down downward downwards left right horizontally horizontal once x position'.split()) | set(verbs)
    rest = set(re.findall(r'[a-z]+', t)) - allowed
    if rest:
        return intent('clarify', 'I cannot safely interpret the whole request offline (unrecognized terms: ' + ', '.join(sorted(rest)) + '). Use the local language interpreter or rephrase; no partial task will be executed.')
    return intent(target=target, axis=axis, amount=amount, reference='absolute' if absolute else 'relative', cycles=count,
                  energy='human' if human else 'environment' if environment else 'any',
                  effort_limit=float(effort[1]) if effort else None,
                  reason='Single selected-object outcome; any unspecified energy source may be used.' if not human and not environment else 'Energy restriction retained.')
