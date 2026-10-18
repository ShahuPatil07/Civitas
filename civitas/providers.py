"""Zero-fee reasoning adapters. Only a loopback Ollama endpoint is supported."""
from copy import deepcopy
import json
from urllib.request import Request, urlopen

from .cognition import validate_proposal
from .planner import propose

ZERO_USAGE = {'input_tokens': 0, 'output_tokens': 0, 'cost': 0}


class OfflineProvider:
    name = 'offline bounded planner (no LLM)'

    def propose(self, context):
        return {'proposal': propose(deepcopy(context)), 'usage': dict(ZERO_USAGE)}


class ReplayProvider:
    name = 'recorded responses (no LLM)'

    def __init__(self, responses):
        self.responses = iter(deepcopy(responses))

    def propose(self, context):
        response = next(self.responses)
        validate_proposal(response['proposal'])
        return response


DECISION_SYSTEM = '''You are an Engineer proposing experiments in a physical sandbox.
Evaluate the advisory proposal using the goal, observations and failure evidence.
Return JSON: {"decision":"adopt"|"replace"|"unresolved","summary":"brief public conclusion"}.
For replace, also include "replacement": a complete proposal with exactly kind,summary,payload,
following the advisory's schema. For unresolved give the missing physical requirement.
Adopt proposes the advisory unchanged for independent kernel validation; it does NOT claim success.
You may change a proposed design or action, but may not change already frozen project goals.
There are no named artifact recipes or generated code. Known objects expose only generic properties.
Energy sources are finite mechanical-energy boundaries; fluid harvesting is not simulated.
All physical outcomes and success are determined by the kernel. Decide only the NEXT proposal,
not the entire task. For an intent proposal, interpret the requested outcome; do not require
a solution to exist before recording the goal. An unproven hypothesis is allowed.
Keep your conclusion concise.'''

DECISION_SCHEMA = {'oneOf': [
    {'type': 'object', 'properties': {'decision': {'const': decision}, 'summary': {'type': 'string'}},
     'required': ['decision', 'summary'], 'additionalProperties': False}
    for decision in ('adopt', 'unresolved')
] + [{'type': 'object', 'properties': {'decision': {'const': 'replace'}, 'summary': {'type': 'string'},
                                      'replacement': {'type': 'object'}},
      'required': ['decision', 'summary', 'replacement'], 'additionalProperties': False}]}


class LocalProvider:
    """Local model selects structured proposals with disclosed search assistance.

    No fallback substitutes mock output for invalid model responses. Responses
    are journaled by the controller. No downloads, keys, cloud endpoints or SDKs.
    """
    name = 'local Ollama + advisory bounded planner'

    def __init__(self, model='qwen3-vl:2b', timeout=180, local_format='chat'):
        if not isinstance(model, str) or not model or 'cloud' in model.lower() or '/' in model:
            raise ValueError('Only an installed local Ollama model is allowed')
        self.model, self.timeout = model, timeout
        if local_format not in {'chat', 'chatml'}:
            raise ValueError('Local prompt format must be chat or chatml')
        self.local_format = local_format
        self.name = f'local {model} ({local_format}) + advisory planner'

    def _request(self, path, body=None):
        request = Request('http://127.0.0.1:11434/api/' + path,
                          data=json.dumps(body).encode() if body is not None else None,
                          headers={'Content-Type': 'application/json'})
        with urlopen(request, timeout=self.timeout) as response:
            return json.load(response)

    def check(self):
        info = self._request('show', {'model': self.model})
        if info.get('remote_host') or info.get('remote_model'):
            raise ValueError('Cloud-backed models are disabled; choose an installed local model')

    def propose(self, context):
        self.check()
        advisory = propose(context)
        # Keep local inference small; no full event journal, truth or chain of thought.
        v, p = deepcopy(context['view']), deepcopy(context['project'])
        v['knowledge'] = [k for k in v['knowledge'] if k['origin'] in {'initial', 'discovery'}][-8:]
        v.pop('projects', None)
        v.pop('neighbors', None)
        v['observations'] = {i: {'object': {k: value for k, value in o['object'].items() if k != 'motions'},
                                     'properties': o['properties'], 'affordances': [a['name'] for a in o['affordances']]}
                             for i, o in v['observations'].items()}
        v['designs'] = {i: d for i, d in v['designs'].items() if i == p['active_design']}
        v.pop('ideas', None)
        p['artifacts'] = p['artifacts'][-2:]
        p['attempts'] = p['attempts'][-2:]
        if not p['goals']:
            # Goal interpretation needs the selected observation, not every
            # construction affordance and stock property in the laboratory.
            v = {'id': v['id'], 'target': p['target'], 'observation': v['observations'].get(p['target']), 'energy': v['energy'],
                 'observed_sources': {i: o['object']['source'] for i, o in v['observations'].items() if 'source' in o['object']}}
        # Keep the local decision prompt bounded on CPU. The deterministic
        # policy can inspect the full permitted context; the model gets this
        # observation-only digest plus the concrete proposal it can replace.
        if p['goals']:
            v = {'id': v['id'], 'inventory': v['inventory'], 'materials': v['materials'],
                 'observations': {i: {'object': o['object'], 'affordances': o['affordances']} for i, o in v['observations'].items()},
                 'discoveries': v['discoveries'][-2:]}
        compact = {'goal_text': p['text'], 'frozen_goals': p['goals'], 'observed_world': v,
                   'latest_failure': next((a for a in reversed(p['attempts']) if not a['accepted']), None),
                   'advisory_proposal': advisory}
        request = {'model': self.model, 'stream': False, 'think': False, 'format': 'json',
                   'options': {'temperature': 0, 'num_predict': 1536, 'num_ctx': 8192},
                   'messages': [{'role': 'system', 'content': DECISION_SYSTEM},
                                {'role': 'user', 'content': json.dumps(compact, separators=(',', ':'))}]}
        if self.local_format == 'chatml':
            # Explicit opt-in transport for ChatML-compatible local models.
            # Closing an empty thinking section requests public output directly;
            # no private reasoning text is read, synthesized or replayed.
            content = request['messages'][1]['content'].replace('<', '\\u003c').replace('>', '\\u003e')
            prompt = '<|im_start|>system\n' + DECISION_SYSTEM + '<|im_end|>\n<|im_start|>user\n' + content + '<|im_end|>\n<|im_start|>assistant\n<think>\n</think>\n'
            raw = {k: v for k, v in request.items() if k not in {'messages', 'think'}}
            raw.update(raw=True, prompt=prompt, format=DECISION_SCHEMA)
            response = self._request('generate', raw)
            public_text = response.get('response', '')
        else:
            response = self._request('chat', request)
            public_text = response['message']['content']
        if not public_text.strip():
            raise ValueError('Local model returned no public JSON within its generation budget; no proposal was applied')
        output = json.loads(public_text)
        if isinstance(output, dict) and 'decision' in output:
            if set(output) - {'decision', 'summary', 'replacement'} or not isinstance(output.get('summary'), str) or not 0 < len(output['summary']) <= 1000:
                raise ValueError('Invalid local model decision')
            if output['decision'] == 'adopt' and 'replacement' not in output:
                output = {'adopt_advisory': True, 'summary': output['summary']}
            elif output['decision'] == 'unresolved' and 'replacement' not in output:
                output = {'kind': 'unresolved', 'summary': output['summary'], 'payload': {'requirements': [output['summary']]}}
            elif output['decision'] == 'replace' and 'replacement' in output:
                output = output['replacement']
            else:
                raise ValueError('Invalid local model decision/replacement combination')
        if isinstance(output, dict) and set(output) == {'adopt_advisory', 'summary'} and output['adopt_advisory'] is True:
            if not isinstance(output['summary'], str) or not 0 < len(output['summary']) <= 1000:
                raise ValueError('Advisory adoption requires a concise model explanation')
            artifact = deepcopy(advisory)
            artifact['summary'] += ' Local model: ' + output['summary']
            artifact = validate_proposal(artifact)
        else:
            artifact = validate_proposal(output)
        return {'proposal': artifact, 'usage': {'input_tokens': response.get('prompt_eval_count', 0), 'output_tokens': response.get('eval_count', 0), 'cost': 0}}


def provider(name='offline', model='qwen3-vl:2b', local_format='chatml'):
    """Engineer reasoning inside projects. Free-text translation is separate:
    see civitas.llm.backend and Laboratory(translator=...)."""
    if name == 'offline':
        return OfflineProvider()
    if name == 'local':
        return LocalProvider(model, local_format=local_format)
    raise ValueError('Provider must be offline or local')
