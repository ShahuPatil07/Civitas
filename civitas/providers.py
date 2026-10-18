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


SYSTEM = '''You are an experimental Engineer in a deterministic physical sandbox.
Return exactly one JSON object: {"kind":...,"summary":...,"payload":...}.
Never report success yourself. The kernel evaluates all experiments. No code execution.
You see only observations and known records. Give concise conclusions, not hidden reasoning.
Kinds:
intent: payload {"goals":[constraint,...]}; only when goals are empty.
hypothesis, diagnosis, unresolved: payload {"requirements":[string,...]}.
experiment_proposal: payload {}. This tests frozen project goals.
action_proposal or plan: payload {"actions":[{"actor":actor_id,"kind":primitive,"args":...}]}.
candidate_design or design_revision: payload {"design":design}, using the exact schema of the advisory candidate if present.
Constraints: {"category":"physical"|"resource","measure":string,"subject":observed_id|actor_id,"op":">="|"<="|"==","value":number}.
Physical measures x,z (metres), environment_work,human_work (joules), mass, length, crossings.
crossings also needs parameters:{"lower":number,"upper":number}; counts completed upward crossings after return.
Resource measure energy or effort_spent. Unknown physics must be unresolved, never relabelled as modeled.
Primitive actions: shape(material,mass,length,radius), connect(a,b,kind:force|rotation|support|contain), work(path,dx,dz,duration,mode:force|rotation), move(target,dx,dz,duration), observe(target), disconnect(relation).
Materials are property based. There are no named artifact classes. Sources provide finite mechanical energy already; fluid conversion is NOT modeled.
Default ambiguous displacement is 1 metre and repeated means 2 cycles; clearly state assumptions.
Preserve human intent: environmental work requires environment_work increase and no added human_work on target.
An advisory proposal from a bounded planner is provided. You may adopt, revise or decline it. Its feasibility is unproven.
Return only the proposal object, not usage, project state, or world state.'''


class LocalProvider:
    """Local model selects structured proposals with disclosed search assistance.

    No fallback substitutes mock output for invalid model responses. Responses
    are journaled by the controller. No downloads, keys, cloud endpoints or SDKs.
    """
    name = 'local Ollama + advisory bounded planner'

    def __init__(self, model='qwen3-vl:2b', timeout=120):
        if not isinstance(model, str) or not model or 'cloud' in model.lower() or '/' in model:
            raise ValueError('Only an installed local Ollama model is allowed')
        self.model, self.timeout = model, timeout

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
        v['knowledge'] = [k for k in v['knowledge'] if k['origin'] not in {'observation', 'record'}][-24:]
        v.pop('projects', None)
        v.pop('neighbors', None)
        p['artifacts'] = p['artifacts'][-2:]
        p['attempts'] = p['attempts'][-2:]
        request = {'model': self.model, 'stream': False, 'think': False, 'format': 'json',
                   'options': {'temperature': 0, 'num_predict': 4096, 'num_ctx': 16384},
                   'messages': [{'role': 'system', 'content': SYSTEM},
                                {'role': 'user', 'content': json.dumps({'project': p, 'observed_world': v, 'advisory_proposal': advisory})}]}
        response = self._request('chat', request)
        artifact = validate_proposal(json.loads(response['message']['content']))
        return {'proposal': artifact, 'usage': {'input_tokens': response.get('prompt_eval_count', 0), 'output_tokens': response.get('eval_count', 0), 'cost': 0}}


def provider(name='offline', model='qwen3-vl:2b'):
    if name == 'offline':
        return OfflineProvider()
    if name == 'local':
        return LocalProvider(model)
    if name == 'auto':
        local = LocalProvider(model, timeout=120)
        try:
            local.check()
            return local
        except (OSError, ValueError):
            return OfflineProvider()
    raise ValueError('Provider must be offline, local or auto')
