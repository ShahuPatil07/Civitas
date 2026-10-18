"""Shared playable/headless scene, Engineer controller, verified save/load."""
from concurrent.futures import ThreadPoolExecutor, wait
from copy import deepcopy
import json
from pathlib import Path

from .benchmarks import instantiate
from .cognition import proposal
from .intents import covered, parse_offline
from .language import TASK_TAG, translate
from .model import Action, OPERATIONS, keys, uid
from .projects import TERMINAL
from .providers import OfflineProvider
from .simulation import save

DEFAULT_GOAL = 'Raise the selected heavy object by 1 m repeatedly, 2 times, using environmental energy without direct human lifting.'


def scenario(gravity=9.81, source_energy=15000, seed=42):
    return {'id': 'engineer_laboratory', 'description': 'Open construction laboratory with finite environmental mechanical energy.',
            'seed': seed, 'rule_version': 'civitas-semantic-0.2', 'universe': {'gravity': gravity},
            'stocks': {'wood': 12, 'iron': 4, 'rope': 4},
            'agent': {'energy': 600, 'power': 100, 'max_force': 100, 'known_shaping': ['wood', 'iron', 'rope']},
            'agent_positions': [[0, 0], [-1, 0], [-2, 0], [4, 0], [5, 0]],
            'objects': {'boundary': {'material': 'iron', 'mass': 5, 'length': .5, 'radius': .5, 'position': [0, 0],
                                     'source': {'energy': source_energy, 'power': 1000, 'max_force': 2000}},
                        'load': {'material': 'stone', 'mass': 100, 'length': .25, 'radius': .5, 'position': [2, 0]},
                        'other_load': {'material': 'stone', 'mass': 80, 'length': .25, 'radius': .5, 'position': [2.5, 0]}},
            'allowed_actions': sorted(OPERATIONS), 'max_actions': 160, 'max_experiments': 24,
            'goals': [{'category': 'physical', 'measure': 'crossings', 'subject': 'load', 'op': '>=', 'value': 2,
                       'parameters': {'lower': 0, 'upper': 1}},
                      {'category': 'physical', 'measure': 'z', 'subject': 'load', 'op': '>=', 'value': 1},
                      {'category': 'physical', 'measure': 'environment_work', 'subject': 'load', 'op': '>=', 'value': 200 * gravity},
                      {'category': 'physical', 'measure': 'human_work', 'subject': 'load', 'op': '<=', 'value': 0},
                      {'category': 'resource', 'measure': 'effort_spent', 'subject': 'agent', 'op': '<=', 'value': 150}]}


class Laboratory:
    def __init__(self, spec=None, provider=None, translator=None):
        self.spec = deepcopy(spec or scenario())
        self.world, task = instantiate(self.spec)
        self.actor = task['actor']
        self.provider = provider or OfflineProvider()
        # Optional civitas.llm backend that translates free text the grammar cannot.
        self.translator = translator
        self.agenda = None
        self.pending_task = None
        self.project_id = None
        self.worker = None
        self.pending = None
        self.last_error = None
        self.submit('observe', {'target': 'nearby'})
        self.submit('inspect_resources', {})

    def submit(self, kind, args):
        return self.world.submit(Action(self.actor, kind, args))

    @property
    def view(self):
        return self.world.engineer_view(self.actor)

    @property
    def project(self):
        return self.view['projects'].get(self.project_id)

    def target(self, name='load'):
        return uid(self.world.genesis['world_id'], 'object/' + name)

    def start(self, text, target=None, use_knowledge=True, budgets=None, step=False):
        if not step:
            self.agenda = None
        event = self.submit('start_project', {'text': text, 'target': target or self.target(),
                            'use_knowledge': use_knowledge, 'budgets': budgets or {'actions': 120, 'experiments': 20, 'reasoning': 60}})
        if event['accepted']:
            self.project_id = event['metadata']['created']
            self.last_error = None
        return event

    @property
    def busy(self):
        return bool(self.pending_task) or bool(self.project and self.project['status'] not in TERMINAL)

    def draft(self, text, target):
        """Interpretation context before any project exists (same permitted view)."""
        v = self.view
        v.pop('projects')
        return {'view': v, 'project': {'text': text, 'target': target, 'goals': [], 'use_knowledge': True,
                                       'initial_effort': v['effort_spent']}}

    def _pool(self):
        if self.worker is None:
            self.worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix='civitas-language')
        return self.worker

    def instruct(self, text, target=None, asynchronous=False):
        """Free-text entry point: the grammar first, then the language backend.

        Text the grammar fully understands (or deliberately refuses) never
        reaches a model. Other text is translated into ordered canonical steps,
        recorded as a kernel Idea, and run as consecutive projects.
        """
        target = target or self.target()
        if self.busy:
            return {'accepted': False, 'mode': 'busy', 'reason': 'Finish or stop the current task first'}
        self.agenda = None
        context = self.draft(text, target)
        if self.translator is None or covered(parse_offline(text, context), multistep=True):
            event = self.start(text, target)
            return {'accepted': event['accepted'], 'mode': 'grammar', 'reason': event['evaluations'][0]['reason']}
        if asynchronous:
            self.pending_task = (text, target, self._pool().submit(translate, text, context, self.translator))
            return {'accepted': True, 'mode': 'translating', 'reason': 'Reading your request with ' + self.translator.name}
        try:
            plan = translate(text, context, self.translator)
        except Exception as error:
            plan = error
        return self._adopt(text, target, plan)

    def _adopt(self, text, target, plan):
        """Record a translation result through validated kernel actions only."""
        if isinstance(plan, Exception):
            event = self.start(text, target)
            if event['accepted']:
                self.last_error = f'Language backend failed ({type(plan).__name__}): {str(plan)[:400]}'
                self.stop(self.last_error)
            return {'accepted': event['accepted'], 'mode': 'failed', 'reason': self.last_error or event['evaluations'][0]['reason']}
        if plan['status'] != 'supported':
            event = self.start(text, target)
            if event['accepted']:
                prefix = {'clarify': 'I need a clearer task: ', 'unsupported': 'Not supported in this setup: ', 'boundary': 'Not feasible in this setup: '}[plan['status']]
                note = '' if plan['status'] == 'boundary' else ' (Language-model judgement; rephrasing as measurable movements may help.)'
                self._accept({'proposal': proposal('unresolved', f'[{plan["model"]}] {prefix}{plan["reason"]}{note}', requirements=[plan['status']]),
                              'usage': plan['usage']})
            return {'accepted': event['accepted'], 'mode': plan['status'], 'reason': plan['reason']}
        idea = {'purpose': text, 'designs': [], 'evidence': [], 'parent': None,
                'assumptions': [TASK_TAG, 'interpreter: ' + plan['model'],
                                f'usage: {plan["usage"]["input_tokens"]} in / {plan["usage"]["output_tokens"]} out tokens, $0'] +
                               [f'step: {s["target"]} | {s["text"]}' for s in plan['steps']]}
        event = self.submit('record_idea', {'idea': idea})
        if not event['accepted']:
            return {'accepted': False, 'mode': 'failed', 'reason': event['evaluations'][0]['reason']}
        self.agenda = {'idea': event['metadata']['created'], 'text': text, 'model': plan['model'], 'reason': plan['reason'],
                       'steps': [{'text': s['text'], 'target': s['target']} for s in plan['steps']], 'projects': []}
        self._advance()
        return {'accepted': True, 'mode': 'plan', 'reason': f'{len(plan["steps"])} step(s) planned'}

    def _advance(self):
        """Start the next agenda step after the previous one succeeded."""
        a = self.agenda
        if not a or len(a['projects']) == len(a['steps']):
            return False
        if a['projects']:
            last = self.view['projects'][a['projects'][-1]]
            if last['status'] != 'succeeded':
                return False
        step = a['steps'][len(a['projects'])]
        event = self.start(step['text'], step['target'], step=True)
        if event['accepted']:
            a['projects'].append(self.project_id)
        return event['accepted']

    def _recover_agenda(self):
        """Rebuild the step agenda from the kernel journal after loading."""
        history = self.world.history
        found = None
        for index, e in enumerate(history):
            if e['accepted'] and e['action']['kind'] == 'record_idea' and e['action']['args']['idea']['assumptions'][:1] == [TASK_TAG]:
                found = index
        if found is None:
            return None
        e = history[found]
        idea = e['action']['args']['idea']
        steps = [dict(zip(('target', 'text'), a[len('step: '):].split(' | ', 1))) for a in idea['assumptions'] if a.startswith('step: ')]
        agenda = {'idea': e['metadata']['created'], 'text': idea['purpose'], 'model': idea['assumptions'][1][len('interpreter: '):],
                  'reason': '', 'steps': steps, 'projects': []}
        for later in history[found + 1:]:
            if not (later['accepted'] and later['action']['kind'] == 'start_project'):
                continue
            k = len(agenda['projects'])
            args = later['action']['args']
            if k >= len(steps) or (args['text'], args['target']) != (steps[k]['text'], steps[k]['target']):
                return None
            agenda['projects'].append(later['metadata']['created'])
        return agenda

    def context(self):
        v = self.view
        p = deepcopy(v['projects'][self.project_id])
        # Cold transfer retains current observations and construction evidence,
        # but cannot access earlier projects, designs or discovery conclusions.
        v.pop('projects')
        if not p['use_knowledge']:
            v['discoveries'] = []
            v['designs'] = {i: d for i, d in v['designs'].items() if i in p['designs']}
            v['knowledge'] = [k for k in v['knowledge'] if k['origin'] not in {'discovery', 'experiment', 'record'} or (isinstance(k['value'], str) and k['value'] in p['designs'])]
        return {'view': v, 'project': p}

    def stop(self, reason):
        if self.project and self.project['status'] not in TERMINAL:
            self.submit('stop_project', {'project': self.project_id, 'reason': reason[:1000]})
        if self.pending:
            self.pending.cancel()
            self.pending = None
        if self.pending_task:
            # A translation finishing later must not start steps for a cancelled request.
            self.pending_task[2].cancel()
            self.pending_task = None

    def _accept(self, response):
        keys(response, {'proposal', 'usage'})
        event = self.submit('reason_project', {'project': self.project_id, **response})
        if not event['accepted']:
            self.last_error = 'Invalid reasoning proposal: ' + event['evaluations'][0]['reason']
            self.stop(self.last_error)
        return event

    def tick(self, asynchronous=False):
        if self.pending_task:
            text, target, future = self.pending_task
            if not future.done():
                return False
            self.pending_task = None
            try:
                plan = future.result()
            except Exception as error:
                plan = error
            self._adopt(text, target, plan)
            return True
        p = self.project
        if not p or p['status'] in TERMINAL:
            return self._advance()
        if self.pending:
            if not self.pending.done():
                return False
            try:
                self._accept(self.pending.result())
            except Exception as error:
                self.last_error = f'Provider failed ({type(error).__name__}): {str(error)[:300]}'
                self.stop(self.last_error)
            self.pending = None
            return True
        if p['queue'] or p['pending_experiment']:
            event = self.submit('step_project', {'project': p['id']})
            if not event['accepted']:
                self.stop(event['evaluations'][0]['reason'])
            return True
        if p['counts']['reasoning'] >= p['budgets']['reasoning']:
            self.stop('Reasoning budget exhausted')
            return True
        context = self.context()
        if asynchronous:
            if self.worker is None:
                self.worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix='civitas-local-model')
            self.pending = self.worker.submit(self.provider.propose, context)
            return False
        try:
            self._accept(self.provider.propose(context))
        except Exception as error:
            self.last_error = f'Provider failed ({type(error).__name__}): {str(error)[:300]}'
            self.stop(self.last_error)
        return True

    def run(self):
        while True:
            if self.pending_task:
                wait([self.pending_task[2]])
            if not self.tick() and not self.busy:
                return self.project

    def metrics(self):
        p, v = self.project, self.view
        if not p:
            return {}
        effort = self.world.snapshot()['agents'][self.actor]['effort_spent'] - p['initial_effort']
        return {'status': p['status'], 'feasibility': p['feasibility'], **p['counts'],
                'design_attempts': len(p['designs']), 'failed_actions': sum(not a['accepted'] for a in p['attempts']),
                'design_revisions': max(0, len(p['designs']) - 1),
                'material_consumed_kg': sum(a['action']['args']['mass'] for a in p['attempts'] if a['accepted'] and a['action']['kind'] == 'shape'),
                'reusable_knowledge_created': sum(d['project'] == p['id'] for d in v['discoveries']),
                'simulated_seconds': v['time'] - p['started'], 'human_effort_J': effort,
                'reused_knowledge': any(a['summary'].startswith('Reuse prior') for a in p['artifacts']), **p['usage']}

    def record(self):
        return {'format': 'civitas-lab-1', 'scenario': deepcopy(self.spec), 'actor': self.actor,
                'project_id': self.project_id, 'provider': self.provider.name,
                'genesis': self.world.genesis, 'events': self.world.history, 'final_hash': self.world.state_hash}

    def save(self, path='runs/laboratory.json'):
        return save(self.record(), path)

    @classmethod
    def restore(cls, record, provider=None, translator=None):
        if record.get('format') != 'civitas-lab-1':
            raise ValueError('Unsupported laboratory save format')
        lab = cls.__new__(cls)
        lab.spec = deepcopy(record['scenario'])
        lab.world, task = instantiate(lab.spec)
        lab.actor = task['actor']
        if lab.world.genesis != record['genesis'] or lab.actor != record['actor']:
            raise ValueError('Scenario/genesis/actor mismatch')
        for expected in record['events']:
            if lab.world.submit(Action.from_dict(expected['action'])) != expected:
                raise ValueError(f'Replay divergence at event {expected["sequence"]}')
        if lab.world.state_hash != record['final_hash']:
            raise ValueError('Final hash mismatch')
        lab.provider = provider or OfflineProvider()
        lab.project_id = record['project_id']
        if lab.project_id is not None and lab.project_id not in lab.world.engineer_view(lab.actor)['projects']:
            raise ValueError('Unknown saved project')
        lab.worker = lab.pending = lab.last_error = lab.pending_task = None
        lab.translator = translator
        lab.agenda = lab._recover_agenda()
        return lab

    @classmethod
    def load(cls, path, provider=None, translator=None):
        return cls.restore(json.loads(Path(path).read_text(encoding='utf-8')), provider, translator)

    def close(self):
        if self.worker:
            self.worker.shutdown(wait=False, cancel_futures=True)


def trace(lab):
    lines = [f'CIVITAS laboratory | {lab.provider.name}']
    for e in lab.world.history:
        lines.append(f'{e["sequence"]:03d} {"ACCEPT" if e["accepted"] else "REJECT"} {e["action"]["kind"]}: {json.dumps(e["metadata"], sort_keys=True)}')
        lines.append('    event ' + e['id'])
        if e['action']['kind'] == 'reason_project':
            lines.append('    proposal ' + json.dumps(e['action']['args']['proposal'], sort_keys=True))
        lines += ['    ' + r['code'] + ': ' + r['reason'] for r in e['evaluations'] if r['code'] != 'action_valid']
    lines.append(json.dumps(lab.metrics(), sort_keys=True))
    lines.append('FINAL ' + lab.world.state_hash)
    return '\n'.join(lines)
