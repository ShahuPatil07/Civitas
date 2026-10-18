"""Human-readable Engineer replies derived only from kernel project records.

A reply never upgrades an outcome: success requires a passed kernel experiment,
and "impossible" requires a kernel certificate. Everything else says what was
missing, so a planner search limit is never presented as a law of physics.
"""
from .intents import REASONS
from .projects import TERMINAL

HEADLINES = {
    'succeeded': 'Done. The world measured the result; I did not just claim it.',
    'proven_infeasible': 'That is physically impossible in this setup.',
    'clarify': 'I need a clearer task before I act.',
    'unsupported': 'This world cannot represent that request yet.',
    'boundary': 'That conflicts with a fixed boundary of this world.',
    'missing_resource': 'A required resource is not present here.',
    'capability_limit': 'That is beyond the physical capabilities I am allowed to use.',
    'not_found': 'I could not find a way within my search and limits.',
    'budget_exhausted': 'I ran out of this project\'s budget before finishing.',
    'provider_failed': 'My reasoning model failed, so no proposal from it was executed.',
    'stopped': 'The project was stopped.',
    'in_progress': 'Working on it.',
    'idle': 'No task yet.',
}


def category(project):
    if not project:
        return 'idle'
    if project['status'] == 'succeeded':
        return 'succeeded'
    if project['feasibility'] == 'known_infeasible':
        return 'proven_infeasible'
    if project['status'] not in TERMINAL:
        return 'in_progress'
    latest = project['latest'] or {}
    if latest.get('code') == 'stopped':
        reason = latest['reason']
        if reason.startswith(('Provider failed', 'Invalid reasoning proposal', 'Language backend failed')):
            return 'provider_failed'
        return 'budget_exhausted' if project['status'] == 'exhausted' or 'budget' in reason.lower() else 'stopped'
    if project['status'] == 'exhausted':
        return 'budget_exhausted'
    final = project['artifacts'][-1] if project['artifacts'] else None
    if final and final['kind'] == 'unresolved':
        first = (final['payload']['requirements'] or ['not_found'])[0]
        return first if first in REASONS else 'not_found'
    return 'not_found'


def reply(project, error=None):
    """{'category', 'headline', 'detail', 'interpretation'} for UI and CLI."""
    kind = category(project)
    detail = ''
    interpretation = ''
    if project:
        intent = next((a for a in project['artifacts'] if a['kind'] == 'intent'), None)
        interpretation = intent['summary'] if intent else ''
        latest = project['latest'] or {}
        final = project['artifacts'][-1] if project['artifacts'] else None
        if kind == 'succeeded':
            detail = 'Kernel measurement: ' + '; '.join(r['reason'] for r in latest.get('evaluations', []))
        elif kind == 'proven_infeasible':
            c = latest.get('certificate', {})
            detail = (f'Needs at least {c.get("required_J", 0):g} J of work but only {c.get("available_J", 0):g} J exists in the '
                      'energy channels this task permits. ' + c.get('basis', 'Conservation of energy bound.'))
        elif kind in {'provider_failed', 'stopped', 'budget_exhausted'} and latest.get('code') == 'stopped':
            detail = latest['reason']
        elif kind == 'budget_exhausted':
            detail = 'Used ' + ', '.join(f'{k} {project["counts"][k]}/{project["budgets"][k]}' for k in project['counts']) + '.'
        elif kind == 'in_progress':
            detail = f'{project["status"]}: ' + (final['summary'] if final else 'interpreting the request')
        elif final:
            detail = final['summary']
    if error and kind != 'succeeded' and error not in detail:
        detail = (detail + ' ' + error).strip()
    return {'category': kind, 'headline': HEADLINES[kind], 'detail': detail, 'interpretation': interpretation}


def plan_lines(agenda, projects):
    """The translated plan, each step with its kernel-recorded status."""
    if not agenda:
        return []
    lines = [f'PLAN for "{agenda["text"]}" (read by {agenda["model"]}):']
    for i, step in enumerate(agenda['steps']):
        identity = agenda['projects'][i] if i < len(agenda['projects']) else None
        status = projects[identity]['status'] if identity in projects else 'not started'
        lines.append(f'  {i + 1}. {step["text"]} [{status}]')
    started = [projects[i] for i in agenda['projects'] if i in projects]
    if started and started[-1]['status'] in TERMINAL and started[-1]['status'] != 'succeeded' and len(started) < len(agenda['steps']):
        lines.append(f'  Step {len(started)} did not succeed, so the remaining steps were not attempted.')
    return lines


def render_task(lab):
    """CLI summary: the plan (if any) followed by the latest project's reply."""
    lines = plan_lines(lab.agenda, lab.view['projects'])
    return '\n'.join(lines + [render(lab.project, lab.last_error)])


def render(project, error=None):
    r = reply(project, error)
    lines = [f'ENGINEER [{r["category"]}]: {r["headline"]}']
    if r['interpretation']:
        lines.append('  Understood as: ' + r['interpretation'])
    if r['detail']:
        lines.append('  ' + r['detail'])
    return '\n'.join(lines)
