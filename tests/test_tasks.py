"""Does the Engineer understand a specific free-text task and act on it honestly?"""
from itertools import product
import json
import os
from threading import Event
import unittest
from unittest.mock import patch

from benchmarks.engineer.tasks import CASES, run
from civitas.cognition import proposal
from civitas.intents import compile_intent, consistency, covered, intent, parse_offline
from civitas.language import render as canonical
from civitas.laboratory import Laboratory, scenario
from civitas.llm import FallbackBackend, OllamaBackend, OpenAIBackend, RateLimited, backend
from civitas.providers import ZERO_USAGE
from civitas.replies import render, render_task, reply


def started(text='Lift the selected object 1 m', spec=None):
    lab = Laboratory(spec)
    lab.start(text)
    return lab


def goals(text):
    lab = started(text)
    context = lab.context()
    return lab, compile_intent(parse_offline(text, context), context)


class TaskMatrixTests(unittest.TestCase):
    def test_offline_task_matrix(self):
        for case in CASES:
            with self.subTest(case=case['name']):
                result = run(case)
                self.assertEqual([r['category'] for r in result['replies']], case['expect'], result['replies'])
                self.assertTrue(result['state_ok'], 'measured world state does not match the request')
                self.assertEqual(result['invariant_violations'], [])


class InterpretationTests(unittest.TestCase):
    def measure(self, text, name):
        lab, artifact = goals(text)
        self.assertEqual(artifact['kind'], 'intent', artifact['summary'])
        return lab, {c['measure']: c for c in artifact['payload']['goals']}[name]

    def test_units_directions_and_references(self):
        for text, name, value in [('Lift the selected object 50 cm', 'z', .5), ('Raise the selected object 500 mm', 'z', .5),
                                  ('Lift the selected object two metres', 'z', 2), ('Move the selected object 1 m to the left', 'x', 1),
                                  # Regression: compound numbers once parsed as their fraction (0.5 m).
                                  ('Lift the selected object one and a half metres', 'z', 1.5),
                                  ('Lift the selected object two and a quarter metres', 'z', 2.25),
                                  ('Move the selected object 1 m to the right', 'x', 3), ('Raise the selected object to a height of 2 m', 'z', 2)]:
            with self.subTest(text=text):
                self.assertAlmostEqual(self.measure(text, name)[1]['value'], value)

    def test_repetition_energy_and_effort_constraints(self):
        _, crossing = self.measure('Lift the selected object 0.5 m 3 times using environmental energy', 'crossings')
        self.assertEqual(crossing['value'], 3)
        _, twice = self.measure('Lift the selected object 1 m twice', 'crossings')
        self.assertEqual(twice['value'], 2)
        self.assertEqual(self.measure('Lift the selected object 1 m using environmental energy', 'human_work')[1]['op'], '<=')
        self.assertEqual(self.measure('Lift the selected object 1 m by hand', 'environment_work')[1]['op'], '<=')
        lab, effort = self.measure('Lift the selected object 1 m using at most 40 joules', 'effort_spent')
        self.assertEqual((effort['op'], effort['value'], effort['subject']), ('<=', lab.project['initial_effort'] + 40, lab.actor))

    def test_any_energy_adds_no_hidden_work_constraint(self):
        _, artifact = goals('Move the selected object 1 m to the left')
        self.assertEqual([c['measure'] for c in artifact['payload']['goals']], ['x'])

    def test_refusals_are_deliberate_and_gaps_are_marked(self):
        lab = started()
        context = lab.context()
        for text in ('Do not move the selected object', 'Move the selected object 1 m right and then lift it 1 m',
                     'Move the 50 kg object 1 m to the right', 'Lift the selected object 1 m by hand using environmental energy'):
            parsed = parse_offline(text, context)
            self.assertEqual(parsed['status'], 'clarify', text)
            self.assertTrue(covered(parsed), text)
        for text in ('Build a ferris wheel', 'Nudge the rock a metre leftwards', 'Lift the selected object 1 m and paint it blue'):
            parsed = parse_offline(text, context)
            self.assertEqual(parsed['status'], 'clarify', text)
            self.assertFalse(covered(parsed), text)

    def test_world_boundaries_and_anchored_sources(self):
        lab = started('Lower the selected object 1 m')
        context = lab.context()
        self.assertEqual(compile_intent(parse_offline('Lower the selected object 1 m', context), context)['payload']['requirements'][0], 'boundary')
        source = next(i for i, o in context['view']['observations'].items() if 'source' in o['object'])
        context['project']['target'] = source
        self.assertEqual(compile_intent(intent(amount=1), context)['payload']['requirements'][0], 'unsupported')

    def test_consistency_catches_contradicted_model_readings(self):
        ok = intent(axis='x', amount=.3)
        self.assertEqual(consistency(ok, 'Slide the boulder 30 cm rightwards'), [])
        self.assertTrue(consistency(intent(axis='x', amount=.3, reference='absolute'), 'Slide the boulder 30 cm rightwards'))
        self.assertTrue(consistency(intent(axis='x', amount=-.3), 'Slide the boulder 30 cm rightwards'))
        self.assertTrue(consistency(intent(axis='x', amount=3), 'Slide the boulder 30 cm rightwards'))
        self.assertTrue(consistency(intent(axis='z', amount=.3), 'Slide the boulder 30 cm rightwards'))
        self.assertEqual(consistency(intent(axis='z', amount=2, reference='absolute'), 'Get the block two meters off the floor'), [])
        self.assertEqual(consistency(intent('unsupported'), 'Paint it blue'), [])
        self.assertEqual(consistency(intent(amount=1.5), 'Heave the stone upwards by about one and a half metres'), [])
        self.assertTrue(consistency(intent(amount=.5), 'Heave the stone upwards by about one and a half metres'))


class KernelGuardTests(unittest.TestCase):
    def test_effort_limit_is_a_hard_precondition(self):
        lab = started('Lift the selected object 1 m using at most 3 joules')
        lab.tick()
        before = lab.world.snapshot()
        other = next(i for i in lab.view['observations'] if i != lab.target() and 'source' not in lab.view['observations'][i]['object'])
        lab._accept({'proposal': proposal('action_proposal', 'Connect anyway', actions=[
            {'actor': lab.actor, 'kind': 'connect', 'args': {'a': other, 'b': lab.target(), 'kind': 'force'}}]), 'usage': ZERO_USAGE})
        event = lab.submit('step_project', {'project': lab.project_id})
        attempt = lab.project['attempts'][-1]
        self.assertFalse(attempt['accepted'])
        self.assertEqual(attempt['evaluations'][0]['code'], 'effort_limit')
        after = lab.world.snapshot()
        self.assertEqual(before['relations'], after['relations'])
        self.assertEqual(before['agents'][lab.actor]['effort_spent'], after['agents'][lab.actor]['effort_spent'])
        self.assertFalse(event['metadata']['operation_accepted'])

    def test_energy_certificate_not_issued_when_energy_suffices(self):
        lab = started('Lift the selected object 1 m', scenario(source_energy=500))
        lab.run()
        # 500 J source + 600 J agent exceeds 981 J: no proof exists, only search failure.
        self.assertEqual(reply(lab.project)['category'], 'not_found')
        self.assertNotEqual(lab.project['feasibility'], 'known_infeasible')


class Scripted:
    """Fake language backend: returns scripted public JSON and records turns."""
    name, label = 'scripted test model', 'scripted'

    def __init__(self, *answers):
        self.answers, self.calls = list(answers), []

    def complete(self, system, turns, schema, limit=1200):
        self.calls.append(list(turns))
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return (answer if isinstance(answer, str) else json.dumps(answer)), 40, 10, 'scripted/test'


def step(**values):
    return dict(target='selected', axis='z', amount=1., reference='relative', cycles=1, energy='any', effort_limit=None) | values


def plan(*steps, status='supported', reason='ok'):
    return {'status': status, 'reason': reason, 'steps': list(steps)}


def position(lab, name='load'):
    return lab.world.snapshot()['objects'][lab.target(name)]['position']


class TranslatorTests(unittest.TestCase):
    def test_grammar_covered_text_never_calls_a_model(self):
        words = Scripted()
        lab = Laboratory(translator=words)
        self.assertEqual(lab.instruct('Lift the selected object 1 m')['mode'], 'grammar')
        lab.run()
        self.assertEqual(reply(lab.project)['category'], 'succeeded')
        self.assertEqual(words.calls, [])

    def test_paraphrase_becomes_a_checked_canonical_plan(self):
        words = Scripted(plan(step(axis='x', amount=-1)))
        lab = Laboratory(translator=words)
        self.assertEqual(lab.instruct('Nudge the rock a metre leftwards')['mode'], 'plan')
        self.assertEqual([s['text'] for s in lab.agenda['steps']], ['Move the selected object 1 m to the left'])
        lab.run()
        self.assertEqual(reply(lab.project)['category'], 'succeeded')
        self.assertEqual(position(lab), [1, 0])
        idea = lab.world.snapshot()['ideas'][lab.agenda['idea']]['content']
        self.assertEqual(idea['purpose'], 'Nudge the rock a metre leftwards')
        self.assertIn('interpreter: scripted/test', idea['assumptions'])
        sent = json.loads(words.calls[0][0])
        self.assertTrue(any(o['selected'] and o['start_position_xz_m'] == [2, 0] for o in sent['objects'].values()))

    def test_multi_step_plan_runs_in_order(self):
        lab = Laboratory(translator=Scripted(plan(step(amount=.4), step(amount=0, reference='absolute'))))
        lab.instruct('Raise the stone by 40 cm and then drop it back down')
        lab.run()
        self.assertEqual(len(lab.agenda['projects']), 2)
        self.assertTrue(all(lab.view['projects'][i]['status'] == 'succeeded' for i in lab.agenda['projects']))
        load = lab.world.snapshot()['objects'][lab.target()]
        self.assertEqual(load['position'], [2, 0])
        self.assertAlmostEqual(max(m['to'][1] for m in load['motions']), .4)
        self.assertIn('2. Move the selected object to a height of 0 m [succeeded]', render_task(lab))

    def test_compound_requests_reach_the_translator_only_when_one_exists(self):
        text = 'Move the selected object 1 m right and then lift it 1 m'
        alone = Laboratory()
        self.assertEqual(alone.instruct(text)['mode'], 'grammar')
        alone.run()
        self.assertEqual(reply(alone.project)['category'], 'clarify')
        words = Scripted(plan(step(axis='x', amount=1), step(amount=1)))
        self.assertEqual(Laboratory(translator=words).instruct(text)['mode'], 'plan')
        negated = Scripted()
        self.assertEqual(Laboratory(translator=negated).instruct('Do not move the selected object')['mode'], 'grammar')
        self.assertEqual(negated.calls, [])

    def test_failed_step_stops_the_plan_honestly(self):
        lab = Laboratory(translator=Scripted(plan(step(axis='x', amount=-.5, energy='human'), step(amount=1))))
        lab.instruct('Drag the rock 50 cm left with your bare hands and then hoist it a metre')
        lab.run()
        self.assertEqual(len(lab.agenda['projects']), 1)
        self.assertEqual(reply(lab.project)['category'], 'capability_limit')
        self.assertIn('remaining steps were not attempted', render_task(lab))
        self.assertEqual(position(lab), [2, 0])

    def test_save_mid_plan_resumes_without_a_model(self):
        def two_step():
            lab = Laboratory(translator=Scripted(plan(step(amount=.4), step(amount=0, reference='absolute'))))
            lab.instruct('Raise the stone by 40 cm and then drop it back down')
            return lab
        whole = two_step()
        whole.run()
        lab = two_step()
        while lab.project['status'] != 'succeeded':
            lab.tick()
        record = json.loads(json.dumps(lab.record()))
        with patch('urllib.request.urlopen', side_effect=AssertionError('network')):
            resumed = Laboratory.restore(record)
            self.assertEqual(len(resumed.agenda['projects']), 1)
            resumed.run()
        self.assertEqual(resumed.world.state_hash, whole.world.state_hash)

    def test_inconsistent_and_malformed_output_get_bounded_repairs(self):
        words = Scripted('{not json', plan(step(axis='x', amount=.3, reference='absolute')), plan(step(axis='x', amount=.3)))
        lab = Laboratory(translator=words)
        lab.instruct('Slide the boulder 30 cm rightwards')
        lab.run()
        self.assertEqual(position(lab), [2.3, 0])
        self.assertIn('rejected', words.calls[1][-1])
        self.assertIn('set reference to "relative"', words.calls[2][-1])

    def test_unstated_restrictions_are_repaired_not_executed(self):
        # Observed live: a model read "heave" as "by hand", which the kernel then proved impossible.
        words = Scripted(plan(step(amount=1.5, energy='human', cycles=2)), plan(step(amount=1.5)))
        lab = Laboratory(translator=words)
        lab.instruct('Heave the stone upwards by about one and a half metres')
        lab.run()
        self.assertIn('never restricts energy', words.calls[1][-1])
        self.assertIn('never restricts cycles', words.calls[1][-1])
        self.assertEqual(reply(lab.project)['category'], 'succeeded')
        self.assertEqual(position(lab), [2, 1.5])
        sent = json.loads(words.calls[0][0])['objects']
        self.assertEqual(sorted(o['material'] for o in sent.values()), ['iron', 'stone', 'stone'])

    def test_multi_step_plan_may_not_drop_a_stated_distance(self):
        words = Scripted(plan(step(amount=1), step(amount=0, reference='absolute')),
                         plan(step(amount=1), step(axis='x', amount=-2)))
        lab = Laboratory(translator=words)
        lab.instruct('Hoist it a metre, then haul it 2 metres leftwards')
        self.assertIn('no step uses that distance', words.calls[1][-1])
        self.assertEqual(len(lab.agenda['steps']), 2)

    def test_every_outcome_step_round_trips_through_the_grammar(self):
        lab = Laboratory()
        context = lab.draft('', lab.target())
        for axis, reference, amount, cycles, energy, effort in product(
                'xz', ('relative', 'absolute'), (-1.5, .25, 2), (1, 3), ('any', 'environment', 'human'), (None, 40)):
            if axis == 'z' and reference == 'absolute' and amount < 0:
                continue
            s = step(axis=axis, reference=reference, amount=amount, cycles=cycles, energy=energy, effort_limit=effort)
            back = parse_offline(canonical(s), context)
            with self.subTest(sentence=canonical(s)):
                self.assertEqual(back['status'], 'supported')
                self.assertEqual({k: back[k] for k in s if k != 'target'}, {k: s[k] for k in s if k != 'target'})

    def test_repair_exhaustion_and_unreachable_backend_fail_visibly(self):
        for words in (Scripted(plan(step(target='o9')), '{}', '{"status": "maybe"}'), Scripted(OSError('unreachable'))):
            lab = Laboratory(translator=words)
            lab.instruct('Nudge the rock a metre leftwards')
            lab.run()
            r = reply(lab.project, lab.last_error)
            self.assertEqual(r['category'], 'provider_failed')
            self.assertFalse(lab.project['attempts'])
            self.assertIsNone(lab.agenda)
            self.assertEqual(position(lab), [2, 0])

    def test_model_refusal_is_recorded_and_labelled_as_judgement(self):
        lab = Laboratory(translator=Scripted(plan(status='unsupported', reason='Colour is not a movement.')))
        lab.instruct('Paint the rock blue')
        lab.run()
        r = reply(lab.project)
        self.assertEqual(r['category'], 'unsupported')
        self.assertIn('Language-model judgement', r['detail'])
        self.assertEqual(lab.project['usage']['input_tokens'], 40)
        self.assertFalse(lab.project['attempts'])

    def test_cancelled_translation_never_starts_steps(self):
        entered, release = Event(), Event()

        class Slow(Scripted):
            def complete(self, *args):
                entered.set()
                release.wait(5)
                return super().complete(*args)
        lab = Laboratory(translator=Slow(plan(step(amount=1))))
        self.assertEqual(lab.instruct('Hoist it a metre', asynchronous=True)['mode'], 'translating')
        self.assertTrue(entered.wait(2))
        self.assertFalse(lab.tick(asynchronous=True))
        pending = lab.pending_task[2]
        lab.stop('Cancelled by player')
        release.set()
        pending.result(timeout=5)
        lab.instruct('Lift the selected object 1 m')
        lab.run()
        self.assertFalse(lab.world.snapshot()['ideas'])
        self.assertIsNone(lab.agenda)
        lab.close()


class BackendTests(unittest.TestCase):
    def test_free_tier_guards(self):
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'k'}):
            with self.assertRaisesRegex(ValueError, ':free'):
                OpenAIBackend('openrouter', model='openai/gpt-5')
            OpenAIBackend('openrouter')
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, 'GROQ_API_KEY'):
                OpenAIBackend('groq')
            self.assertEqual(OpenAIBackend('ovh').key, '')
        with self.assertRaises(ValueError):
            OpenAIBackend('paid-service')

    def test_rate_limits_rotate_models_then_wait(self):
        slept = []
        ok = {'choices': [{'message': {'content': '{}'}, 'finish_reason': 'stop'}], 'usage': {'prompt_tokens': 7, 'completion_tokens': 3}}
        b = OpenAIBackend('ovh', sleep=slept.append)
        with patch.object(b, '_post', side_effect=[RateLimited('a', 30), ok]):
            self.assertEqual(b.complete('s', ['u'], {})[3], 'ovh/' + b.models[1])
        with patch.object(b, '_post', side_effect=[RateLimited(m, 20 + i) for i, m in enumerate(b.models)] + [ok]):
            self.assertEqual(b.complete('s', ['u'], {})[1:3], (7, 3))
        self.assertEqual(slept, [20])
        b.max_wait = 5
        with patch.object(b, '_post', side_effect=[RateLimited(m, 30) for m in b.models]):
            with self.assertRaisesRegex(OSError, 'rate limited'):
                b.complete('s', ['u'], {})

    def test_slow_models_rotate_instead_of_failing(self):
        ok = {'choices': [{'message': {'content': '{}'}, 'finish_reason': 'stop'}]}
        b = OpenAIBackend('ovh')
        with patch.object(b, '_post', side_effect=[TimeoutError('The read operation timed out'), ok]):
            self.assertEqual(b.complete('s', ['u'], {})[3], 'ovh/' + b.models[1])
        spent = {'choices': [{'message': {'content': ''}, 'finish_reason': 'length'}]}
        with patch.object(b, '_post', side_effect=[spent, ok]):
            self.assertEqual(b.complete('s', ['u'], {})[3], 'ovh/' + b.models[1])
        with patch.object(b, '_post', side_effect=[TimeoutError('slow')] * len(b.models)):
            with self.assertRaisesRegex(OSError, 'No ovh free model answered'):
                b.complete('s', ['u'], {})

    def test_unsupported_optional_parameters_are_dropped(self):
        ok = {'choices': [{'message': {'content': '{}'}, 'finish_reason': 'stop'}]}
        b = OpenAIBackend('ovh')
        with patch.object(b, '_post', side_effect=[OSError("HTTP 400 from ovh: feature 'reasoning_effort' not supported"),
                                                   OSError('HTTP 400 from ovh: response_format json_schema unsupported'), ok]) as post:
            b.complete('s', ['u'], {'type': 'object'})
        self.assertNotIn('reasoning_effort', post.call_args.args[0])
        self.assertEqual(post.call_args.args[0]['response_format'], {'type': 'json_object'})

    def test_request_shape_and_key_header(self):
        captured = {}

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return json.dumps({'choices': [{'message': {'content': '{"a":1}'}, 'finish_reason': 'stop'}]}).encode()

        def opener(request, timeout):
            captured['url'], captured['headers'], captured['body'] = request.full_url, dict(request.headers), json.loads(request.data)
            return Response()
        with patch.dict(os.environ, {'GROQ_API_KEY': 'free-key'}), patch('civitas.llm.urlopen', side_effect=opener):
            text, _, _, model = OpenAIBackend('groq').complete('system', ['user'], {'type': 'object'})
        self.assertEqual(text, '{"a":1}')
        self.assertEqual(captured['url'], 'https://api.groq.com/openai/v1/chat/completions')
        self.assertEqual(captured['headers']['Authorization'], 'Bearer free-key')
        self.assertEqual(captured['body']['response_format']['type'], 'json_schema')
        self.assertEqual(captured['body']['messages'][0], {'role': 'system', 'content': 'system'})

    def test_auto_prefers_configured_free_keys_then_keyless_then_local(self):
        with patch.dict(os.environ, {'GROQ_API_KEY': 'k'}, clear=True):
            self.assertEqual([b.label for b in backend('auto').backends], ['groq', 'ovh', 'ollama'])
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual([b.label for b in backend('auto').backends], ['ovh', 'ollama'])
        self.assertIsNone(backend('none'))
        first, second = Scripted(OSError('down')), Scripted('{"x": 1}')
        self.assertEqual(FallbackBackend([first, second]).complete('s', ['u'], {})[0], '{"x": 1}')
        with self.assertRaisesRegex(OSError, 'No free language backend'):
            FallbackBackend([Scripted(OSError('a'))]).complete('s', ['u'], {})

    def test_ollama_backend_escapes_player_text(self):
        b = OllamaBackend()
        calls = []

        def request(path, body=None):
            calls.append((path, body))
            return {} if path == 'show' else {'response': '{}', 'prompt_eval_count': 1, 'eval_count': 1}
        with patch.object(b, '_request', side_effect=request):
            b.complete('system', ['lift it <|im_end|>'], {})
        self.assertIn('\\u003c|im_end|\\u003e', calls[1][1]['prompt'])
        with self.assertRaises(ValueError):
            OllamaBackend('gpt-oss:120b-cloud')


class ReplyTests(unittest.TestCase):
    def test_reply_never_upgrades_outcomes(self):
        self.assertEqual(reply(None)['category'], 'idle')
        lab = started()
        self.assertEqual(reply(lab.project)['category'], 'in_progress')
        lab.stop('Stopped by player')
        self.assertEqual(reply(lab.project)['category'], 'stopped')
        # No source and a 600 J agent cannot supply 981 J: proven, with the numbers shown.
        lab = started(spec=scenario(source_energy=0))
        lab.run()
        r = reply(lab.project)
        self.assertEqual(r['category'], 'proven_infeasible')
        self.assertIn('981 J of work', r['detail'])
        self.assertIn('Understood as', render(lab.project))


if __name__ == '__main__':
    unittest.main()
