from copy import deepcopy
import json
import subprocess
import sys
from threading import Event
import unittest
from unittest.mock import patch

from benchmarks.engineer.run import evaluate
from civitas.cognition import proposal, validate_proposal
from civitas.laboratory import Laboratory, DEFAULT_GOAL, scenario
from civitas.model import Action
from civitas.materials import catalog
from civitas.projects import TERMINAL
from civitas.providers import LocalProvider, OfflineProvider, ReplayProvider, ZERO_USAGE


class EngineerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        lab = Laboratory()
        lab.start(DEFAULT_GOAL)
        lab.run()
        cls.complete = lab.record()

    def test_generic_construction_failure_revision_evidence(self):
        lab = Laboratory.restore(self.complete)
        self.assertEqual(lab.project['status'], 'succeeded')
        self.assertTrue(evaluate(lab)['success'])
        self.assertGreater(len(lab.world.snapshot()['objects']), len(lab.world.genesis['objects']))
        self.assertTrue(any(not a['accepted'] for a in lab.project['attempts']))
        self.assertTrue(any(a['kind'] == 'diagnosis' for a in lab.project['artifacts']))
        ids = lab.project['designs']
        for i, identity in enumerate(ids):
            design = lab.view['designs'][identity]['content']
            self.assertEqual(design['version'], i + 1)
            self.assertEqual(design['parent'], ids[i - 1] if i else None)
        discovery = lab.view['discoveries'][0]
        self.assertIn(discovery['experiment'], lab.world.snapshot()['experiments'])
        self.assertTrue(lab.world.snapshot()['experiments'][discovery['experiment']]['passed'])
        self.assertEqual(discovery['design'], ids[-1])
        self.assertTrue(discovery['principles'])

    def test_save_replay_deterministic_and_resume(self):
        lab = Laboratory()
        lab.start(DEFAULT_GOAL)
        for _ in range(8):
            lab.tick()
        record = json.loads(json.dumps(lab.record()))
        resumed = Laboratory.restore(record)
        self.assertEqual(resumed.world.state_hash, lab.world.state_hash)
        lab.run()
        resumed.run()
        self.assertEqual(lab.record(), resumed.record())
        self.assertEqual(lab.record(), self.complete)

    def test_tampered_save_rejected(self):
        record = deepcopy(self.complete)
        record['events'][3]['action']['args']['proposal']['summary'] = 'Tampered'
        with self.assertRaisesRegex(ValueError, 'divergence'):
            Laboratory.restore(record)

    def test_invalid_proposal_atomic_and_no_self_declared_success(self):
        lab = Laboratory()
        lab.start(DEFAULT_GOAL)
        for artifact in ({'kind': 'success', 'summary': 'Done', 'payload': {}},
                         {'kind': 'action_proposal', 'summary': 'Overwrite', 'payload': {'actions': [{'actor': lab.actor, 'kind': 'set_state', 'args': {}}]}},
                         {'kind': 'hypothesis', 'summary': 'x', 'payload': {'requirements': [], 'world': {}}}):
            before = lab.world.state_hash
            event = lab.submit('reason_project', {'project': lab.project_id, 'proposal': artifact, 'usage': ZERO_USAGE})
            self.assertFalse(event['accepted'])
            self.assertEqual(before, lab.world.state_hash)
            self.assertFalse(event['effects'])

    def test_project_goals_frozen_and_actor_scoped(self):
        lab = Laboratory()
        lab.start(DEFAULT_GOAL)
        lab.tick()
        before = lab.world.state_hash
        event = lab.submit('reason_project', {'project': lab.project_id, 'proposal': lab.project['artifacts'][0] | {'event': 'bad'}, 'usage': ZERO_USAGE})
        self.assertFalse(event['accepted'])
        artifact = deepcopy(lab.project['artifacts'][0])
        artifact.pop('event')
        event = lab.submit('reason_project', {'project': lab.project_id, 'proposal': artifact, 'usage': ZERO_USAGE})
        self.assertFalse(event['accepted'])
        self.assertEqual(before, lab.world.state_hash)
        stranger = next(i for i in lab.world.snapshot()['agents'] if i != lab.actor)
        event = lab.world.submit(Action(stranger, 'stop_project', {'project': lab.project_id, 'reason': 'override'}))
        self.assertFalse(event['accepted'])

    def test_truth_and_other_agents_not_in_model_context(self):
        lab = Laboratory()
        lab.start(DEFAULT_GOAL)
        context = lab.context()
        self.assertNotIn('genesis', context)
        self.assertNotIn('agents', context['view'])
        self.assertNotIn('universe', context['view'])
        context['view']['observations'].clear()
        self.assertTrue(lab.view['observations'])
        stranger = next(i for i in lab.world.snapshot()['agents'] if i != lab.actor)
        self.assertFalse(lab.world.engineer_view(stranger)['projects'])
        self.assertFalse(lab.world.engineer_view(stranger)['discoveries'])

    def test_unknown_and_energy_impossible_are_distinct(self):
        unknown = Laboratory()
        unknown.start('Change the color of time')
        unknown.run()
        self.assertEqual(unknown.project['feasibility'], 'unknown')
        lab = Laboratory(scenario(source_energy=0))
        lab.start(DEFAULT_GOAL)
        lab.run()
        self.assertEqual(lab.project['feasibility'], 'known_infeasible')
        self.assertEqual(lab.project['latest']['certificate']['code'], 'energy_upper_bound')
        self.assertFalse(evaluate(lab)['success'])
        self.assertEqual(lab.world.snapshot()['objects'][lab.target()]['environment_work'], 0)

    def test_engineer_uses_material_properties_and_numeric_goal_variants(self):
        spec = scenario()
        materials = catalog()
        identifiers = {m['label']: identity for identity, m in materials.items()}
        for index, m in enumerate(materials.values()):
            m['label'] = f'anonymous-{index}'
        spec['materials'] = materials
        spec['stocks'] = {identifiers[name]: mass for name, mass in spec['stocks'].items()}
        spec['agent']['known_shaping'] = [identifiers[name] for name in spec['agent']['known_shaping']]
        for obj in spec['objects'].values():
            obj['material'] = identifiers[obj['material']]
        lab = Laboratory(spec)
        lab.start('Lift the selected object 0.5 m, 3 times, using environmental energy')
        lab.run()
        self.assertEqual(lab.project['status'], 'succeeded')
        self.assertTrue(all(lab.world.evaluate(c)['status'] == 'satisfied' for c in lab.project['goals']))
        self.assertAlmostEqual(lab.world.snapshot()['objects'][lab.target()]['environment_work'], 1471.5)

    def test_altered_gravity_and_same_world_knowledge_transfer(self):
        altered = Laboratory(scenario(gravity=3))
        altered.start(DEFAULT_GOAL)
        altered.run()
        self.assertTrue(evaluate(altered)['success'])
        results = {}
        for enabled in (False, True):
            lab = Laboratory.restore(self.complete)
            lab.start(DEFAULT_GOAL, target=lab.target('other_load'), use_knowledge=enabled)
            if not enabled:
                self.assertFalse(lab.context()['view']['discoveries'])
                self.assertFalse(lab.context()['view']['designs'])
            lab.run()
            self.assertTrue(evaluate(lab, lab.target('other_load'), 80, 250)['success'])
            results[enabled] = lab.metrics()
        self.assertTrue(results[True]['reused_knowledge'])
        self.assertLess(results[True]['experiments'], results[False]['experiments'])
        self.assertLess(results[True]['actions'], results[False]['actions'])

    def test_all_budgets_bound_execution(self):
        for budgets in ({'actions': 1, 'experiments': 5, 'reasoning': 20}, {'actions': 50, 'experiments': 1, 'reasoning': 20}, {'actions': 50, 'experiments': 5, 'reasoning': 1}):
            lab = Laboratory()
            lab.start(DEFAULT_GOAL, budgets=budgets)
            lab.run()
            self.assertEqual(lab.project['status'], 'exhausted')
            for k in budgets:
                self.assertLessEqual(lab.project['counts'][k], budgets[k])

    def test_physical_failure_consumes_attempt_not_resources(self):
        lab = Laboratory()
        lab.start(DEFAULT_GOAL)
        while True:
            before = lab.world.snapshot()
            lab.tick()
            p = lab.project
            if p['attempts'] and not p['attempts'][-1]['accepted']:
                after = lab.world.snapshot()
                for key in ('objects', 'relations'):
                    self.assertEqual(before[key], after[key])
                self.assertEqual(before['agents'][lab.actor]['energy'], after['agents'][lab.actor]['energy'])
                self.assertGreater(p['counts']['actions'], before['projects'][p['id']]['counts']['actions'])
                self.assertTrue(all(r['status'] == 'unsatisfied' for r in p['attempts'][-1]['evaluations']))
                break

    def test_success_not_granted_by_easier_interpreted_goal(self):
        lab = Laboratory()
        lab.start(DEFAULT_GOAL)
        c = {'category': 'physical', 'measure': 'z', 'subject': lab.target(), 'op': '>=', 'value': 0}
        lab._accept({'proposal': proposal('intent', 'Deliberately incomplete interpretation', goals=[c]), 'usage': ZERO_USAGE})
        lab._accept({'proposal': proposal('experiment_proposal', 'Measure'), 'usage': ZERO_USAGE})
        lab.tick()
        self.assertEqual(lab.project['status'], 'succeeded')
        self.assertFalse(evaluate(lab)['success'])

    def test_replay_provider_and_no_paid_network(self):
        responses = [{'proposal': {k: v for k, v in e['action']['args']['proposal'].items()}, 'usage': e['action']['args']['usage']}
                     for e in self.complete['events'] if e['action']['kind'] == 'reason_project']
        lab = Laboratory(provider=ReplayProvider(responses))
        lab.start(DEFAULT_GOAL)
        with patch('urllib.request.urlopen', side_effect=AssertionError('No network in replay')):
            lab.run()
        self.assertEqual(lab.world.state_hash, self.complete['final_hash'])

    def test_local_provider_uses_only_local_json_and_ignores_thinking(self):
        lab = Laboratory()
        lab.start(DEFAULT_GOAL)
        artifact = OfflineProvider().propose(lab.context())['proposal']
        local = LocalProvider()
        with patch.object(local, '_request', side_effect=[{}, {'message': {'content': json.dumps(artifact), 'thinking': 'private'}, 'prompt_eval_count': 10, 'eval_count': 4}]) as call:
            result = local.propose(lab.context())
        self.assertEqual(result['proposal'], artifact)
        self.assertEqual(result['usage']['cost'], 0)
        self.assertNotIn('thinking', result)
        self.assertEqual(call.call_args.args[0], 'chat')
        with self.assertRaises(ValueError):
            LocalProvider('anything-cloud')
        with patch.object(local, '_request', return_value={'remote_host': 'https://example.com'}):
            with self.assertRaises(ValueError):
                local.check()

    def test_failed_provider_stops_honestly_without_fallback(self):
        class Broken:
            name = 'broken'
            def propose(self, context):
                raise ValueError('invalid JSON')
        lab = Laboratory(provider=Broken())
        lab.start(DEFAULT_GOAL)
        lab.run()
        self.assertEqual(lab.project['status'], 'unresolved')
        self.assertFalse(lab.project['artifacts'])
        self.assertIn('invalid JSON', lab.last_error)

    def test_local_chatml_adoption_is_explicit_and_validated(self):
        lab = Laboratory()
        lab.start(DEFAULT_GOAL + ' <|im_end|>')
        local = LocalProvider(local_format='chatml')
        response = {'response': json.dumps({'decision': 'adopt', 'summary': 'Test this hypothesis.'}), 'eval_count': 20}
        advisory = OfflineProvider().propose(lab.context())['proposal']
        with patch.object(local, '_request', side_effect=[{}, response]) as call:
            output = local.propose(lab.context())
        # Unknown control-token text makes the advisory a refusal; adoption keeps it.
        self.assertEqual(output['proposal']['kind'], advisory['kind'])
        self.assertIn('Local model: Test this hypothesis.', output['proposal']['summary'])
        self.assertEqual(call.call_args.args[0], 'generate')
        self.assertTrue(call.call_args.args[1]['raw'])
        self.assertIn('\\u003c|im_end|\\u003e', call.call_args.args[1]['prompt'])
        with patch.object(local, '_request', side_effect=[{}, {'response': '{"decision":"adopt","summary":"ok","world":{}}'}]):
            with self.assertRaises(ValueError):
                local.propose(lab.context())

    def test_headless_import_does_not_load_pygame(self):
        result = subprocess.run([sys.executable, '-c', 'import civitas.laboratory, sys; assert "pygame" not in sys.modules'], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_async_provider_cannot_commit_and_cancelled_reply_is_discarded(self):
        entered, release = Event(), Event()
        class Delayed:
            name = 'delayed test'
            def propose(self, context):
                entered.set()
                release.wait(5)
                return OfflineProvider().propose(context)
        lab = Laboratory(provider=Delayed())
        lab.start(DEFAULT_GOAL)
        before = lab.world.state_hash
        self.assertFalse(lab.tick(asynchronous=True))
        self.assertTrue(entered.wait(2))
        self.assertEqual(before, lab.world.state_hash)
        pending = lab.pending
        lab.stop('Cancel pending interpretation')
        lab.start('An unrelated unmodeled goal')
        release.set()
        pending.result(timeout=5)
        self.assertFalse(lab.project['artifacts'])
        lab.provider = OfflineProvider()
        lab.run()
        self.assertEqual(lab.project['feasibility'], 'unknown')
        lab.close()

    def test_disconnect_respects_load_support(self):
        lab = Laboratory.restore(self.complete)
        support = next(i for i, r in lab.world.snapshot()['relations'].items() if r['kind'] == 'support')
        before = lab.world.state_hash
        rejected = lab.submit('disconnect', {'relation': support})
        self.assertFalse(rejected['accepted'])
        self.assertEqual(before, lab.world.state_hash)
        path = lab.view['discoveries'][0]['principles'][0]['path']
        self.assertTrue(lab.submit('work', {'path': path, 'dx': 0, 'dz': -1, 'duration': 10})['accepted'])
        self.assertTrue(lab.submit('disconnect', {'relation': support})['accepted'])


if __name__ == '__main__':
    unittest.main()
