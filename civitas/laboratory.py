"""Shared playable/headless scene, Engineer controller, verified save/load."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path

from .benchmarks import instantiate
from .model import Action, OPERATIONS, uid
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
                       'parameters': {'lower': 0, 'upper': 1}}]}


class Laboratory:
    def __init__(self, spec=None, provider=None):
        self.spec = deepcopy(spec or scenario())
        self.world, task = instantiate(self.spec)
        self.actor = task['actor']
        self.provider = provider or OfflineProvider()
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

    def start(self, text, target=None, use_knowledge=True, budgets=None):
        event = self.submit('start_project', {'text': text, 'target': target or self.target(),
                            'use_knowledge': use_knowledge, 'budgets': budgets or {'actions': 120, 'experiments': 20, 'reasoning': 60}})
        if event['accepted']:
            self.project_id = event['metadata']['created']
            self.last_error = None
        return event

    def context(self):
        v = self.view
        p = deepcopy(v['projects'][self.project_id])
        # Cold transfer retains current observations and construction evidence,
        # but cannot access earlier projects, designs or discovery conclusions.
        v.pop('projects')
        if not p['use_knowledge']:
            v['discoveries'] = []
            v['designs'] = {i: d for i, d in v['designs'].items() if i in p['designs']}
            v['knowledge'] = [k for k in v['knowledge'] if k['origin'] not in {'discovery', 'experiment', 'record'} or k['value'] in p['designs']]
        return {'view': v, 'project': p}

    def stop(self, reason):
        if self.project and self.project['status'] not in TERMINAL:
            self.submit('stop_project', {'project': self.project_id, 'reason': reason[:1000]})

    def _accept(self, response):
        event = self.submit('reason_project', {'project': self.project_id, **response})
        if not event['accepted']:
            self.last_error = 'Invalid reasoning proposal: ' + event['evaluations'][0]['reason']
            self.stop(self.last_error)
        return event

    def tick(self, asynchronous=False):
        p = self.project
        if not p or p['status'] in TERMINAL:
            return False
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
        while self.project and self.project['status'] not in TERMINAL:
            self.tick()
        return self.project

    def metrics(self):
        p, v = self.project, self.view
        if not p:
            return {}
        effort = sum(k['value'] for k in [])  # effort comes from authoritative researcher metrics below
        effort = self.world.snapshot()['agents'][self.actor]['effort_spent'] - p['initial_effort']
        return {'status': p['status'], 'feasibility': p['feasibility'], **p['counts'],
                'design_attempts': len(p['designs']), 'failed_actions': sum(not a['accepted'] for a in p['attempts']),
                'simulated_seconds': v['time'] - p['started'], 'human_effort_J': effort,
                'reused_knowledge': any(a['summary'].startswith('Reuse prior') for a in p['artifacts']), **p['usage']}

    def record(self):
        return {'format': 'civitas-lab-1', 'scenario': deepcopy(self.spec), 'actor': self.actor,
                'project_id': self.project_id, 'provider': self.provider.name,
                'genesis': self.world.genesis, 'events': self.world.history, 'final_hash': self.world.state_hash}

    def save(self, path='runs/laboratory.json'):
        return save(self.record(), path)

    @classmethod
    def restore(cls, record, provider=None):
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
        lab.worker = lab.pending = lab.last_error = None
        return lab

    @classmethod
    def load(cls, path, provider=None):
        return cls.restore(json.loads(Path(path).read_text(encoding='utf-8')), provider)

    def close(self):
        if self.worker:
            self.worker.shutdown(wait=False, cancel_futures=True)


def trace(lab):
    lines = [f'CIVITAS laboratory | {lab.provider.name}']
    for e in lab.world.history:
        lines.append(f'{e["sequence"]:03d} {"ACCEPT" if e["accepted"] else "REJECT"} {e["action"]["kind"]}: {json.dumps(e["metadata"], sort_keys=True)}')
        lines += ['    ' + r['code'] + ': ' + r['reason'] for r in e['evaluations'] if r['code'] != 'action_valid']
    lines.append(json.dumps(lab.metrics(), sort_keys=True))
    lines.append('FINAL ' + lab.world.state_hash)
    return '\n'.join(lines)
