"""Free language-model transports. They return public text; they never act.

Every backend has one method, complete(system, turns, schema, limit) ->
(text, input_tokens, output_tokens, model). `turns` alternate user/assistant
text, starting and ending with a user turn. No backend may incur fees:
presets point only at free tiers, OpenRouter is restricted to ':free' models,
and the kernel still rejects any proposal whose recorded cost is not zero.
Free tiers change often; see research/FREE_LLM_OPTIONS.md (checked 2026-10-19).
"""
from dataclasses import dataclass, field
import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class RateLimited(OSError):
    def __init__(self, model, wait):
        super().__init__(f'{model} is rate limited for {wait:g} s')
        self.model, self.wait = model, wait


@dataclass(frozen=True)
class Preset:
    base: str
    models: tuple
    key_env: str | None          # environment variable holding a free key
    key_required: bool = True
    extra: dict = field(default_factory=dict)
    note: str = ''


PRESETS = {
    # No account and no key: anonymous tier, ~2 requests/min per model per IP.
    'ovh': Preset('https://oai.endpoints.kepler.ai.cloud.ovh.net/v1',
                  ('gpt-oss-120b', 'Qwen3.8-27B', 'Qwen3.6-27B', 'Qwen3.5-397B-A17B'),
                  'OVH_AI_ENDPOINTS_ACCESS_TOKEN', False, {'reasoning_effort': 'low'},
                  'OVHcloud AI Endpoints anonymous tier'),
    'groq': Preset('https://api.groq.com/openai/v1', ('openai/gpt-oss-120b', 'openai/gpt-oss-20b'),
                   'GROQ_API_KEY', extra={'reasoning_effort': 'low'}, note='Groq free plan, no card'),
    'cerebras': Preset('https://api.cerebras.ai/v1', ('gpt-oss-120b',), 'CEREBRAS_API_KEY',
                       extra={'reasoning_effort': 'low'}, note='Cerebras free trial quota'),
    'gemini': Preset('https://generativelanguage.googleapis.com/v1beta/openai', ('gemini-flash-latest', 'gemini-flash-lite-latest'),
                     'GEMINI_API_KEY', note='Google AI Studio free tier; keep billing disabled'),
    'openrouter': Preset('https://openrouter.ai/api/v1', ('google/gemma-4-31b-it:free', 'nvidia/nemotron-3-super-120b-a12b:free'),
                         'OPENROUTER_API_KEY', note='OpenRouter :free models only'),
    'ollama-cloud': Preset('https://ollama.com/v1', ('gpt-oss:120b',), 'OLLAMA_API_KEY',
                           note='Ollama Cloud free starter allowance'),
}


class OpenAIBackend:
    """OpenAI-compatible chat completions with free-tier guards.

    On HTTP 429 the next preset model is tried (quotas are per model); when
    all are limited it waits for the shortest Retry-After up to max_wait.
    Optional parameters a server rejects are dropped once and retried.
    """

    def __init__(self, preset='ovh', model=None, timeout=40, max_wait=75, sleep=time.sleep):
        if preset not in PRESETS:
            raise ValueError(f'Unknown free backend {preset!r}; choose from {sorted(PRESETS)}')
        self.preset = PRESETS[preset]
        self.models = (model,) if model else self.preset.models
        if preset == 'openrouter' and not all(m.endswith(':free') for m in self.models):
            raise ValueError('Only OpenRouter models ending in :free are allowed (no paid usage)')
        self.key = os.environ.get(self.preset.key_env or '', '')
        if self.preset.key_required and not self.key:
            raise ValueError(f'{preset} needs a free key in the {self.preset.key_env} environment variable')
        self.timeout, self.max_wait, self.sleep = timeout, max_wait, sleep
        self.label = preset
        self.name = f'{preset} {self.models[0]} (free cloud)'
        self.extra = dict(self.preset.extra)
        self.schema_mode = 'json_schema'

    def _post(self, body):
        headers = {'Content-Type': 'application/json'}
        if self.key:
            headers['Authorization'] = 'Bearer ' + self.key
        request = Request(self.preset.base + '/chat/completions', data=json.dumps(body).encode(), headers=headers)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.load(response)
        except HTTPError as error:
            text = error.read().decode('utf-8', 'replace')[:500]
            if error.code == 429:
                raise RateLimited(body['model'], float(error.headers.get('retry-after') or 30)) from None
            raise OSError(f'HTTP {error.code} from {self.label}: {text}') from None

    def _body(self, model, system, turns, schema, limit):
        messages = [{'role': 'system', 'content': system}] + [
            {'role': 'assistant' if i % 2 else 'user', 'content': t} for i, t in enumerate(turns)]
        body = {'model': model, 'messages': messages, 'temperature': 0, 'max_tokens': limit, **self.extra}
        if self.schema_mode == 'json_schema':
            body['response_format'] = {'type': 'json_schema', 'json_schema': {'name': 'civitas', 'schema': schema}}
        elif self.schema_mode == 'json_object':
            body['response_format'] = {'type': 'json_object'}
        return body

    def complete(self, system, turns, schema, limit=1200):
        waited, failures = 0, []
        while True:
            waits = []
            for model in self.models:
                try:
                    response = self._attempt(model, system, turns, schema, limit)
                except RateLimited as limited:
                    waits.append(limited.wait)
                    continue
                except (TimeoutError, URLError) as error:
                    # A slow or unreachable model should not fail the request while others remain.
                    failures.append(f'{model}: {type(error).__name__}')
                    continue
                choice = response['choices'][0]
                if choice.get('finish_reason') == 'length' and not (choice['message'].get('content') or '').strip():
                    # Hidden reasoning consumed the budget: another model may still answer.
                    failures.append(f'{model}: output budget spent before answering')
                    continue
                usage = response.get('usage') or {}
                return (choice['message'].get('content') or '', usage.get('prompt_tokens', 0),
                        usage.get('completion_tokens', 0), f'{self.label}/{model}')
            if not waits:
                raise OSError(f'No {self.label} free model answered (' + '; '.join(failures) + ')')
            wait = min(waits)
            if waited + wait > self.max_wait:
                raise OSError(f'All {self.label} free models are rate limited (retry in {wait:g} s)')
            self.sleep(wait)
            waited += wait

    def _attempt(self, model, system, turns, schema, limit):
        for _ in range(3):
            try:
                return self._post(self._body(model, system, turns, schema, limit))
            except OSError as error:
                if isinstance(error, RateLimited):
                    raise
                message = str(error)
                # Degrade optional features a free server does not support.
                dropped = next((k for k in self.extra if k in message), None)
                if dropped:
                    self.extra.pop(dropped)
                elif 'response_format' in message or 'json_schema' in message:
                    self.schema_mode = {'json_schema': 'json_object', 'json_object': 'none'}.get(self.schema_mode, 'none')
                else:
                    raise
        return self._post(self._body(model, system, turns, schema, limit))


class OllamaBackend:
    """Installed local model on the loopback Ollama service (no network)."""

    def __init__(self, model='qwen3-vl:2b', timeout=180, local_format='chatml'):
        if not isinstance(model, str) or not model or 'cloud' in model.lower() or '/' in model:
            raise ValueError('Only an installed local Ollama model is allowed')
        if local_format not in {'chat', 'chatml'}:
            raise ValueError('Local prompt format must be chat or chatml')
        self.model, self.timeout, self.local_format = model, timeout, local_format
        self.label = 'ollama'
        self.name = f'local {model} (Ollama)'

    def _request(self, path, body=None):
        request = Request('http://127.0.0.1:11434/api/' + path,
                          data=json.dumps(body).encode() if body is not None else None,
                          headers={'Content-Type': 'application/json'})
        with urlopen(request, timeout=self.timeout) as response:
            return json.load(response)

    def complete(self, system, turns, schema, limit=600):
        info = self._request('show', {'model': self.model})
        if info.get('remote_host') or info.get('remote_model'):
            raise ValueError('Cloud-backed Ollama models are not local; use the ollama-cloud preset')
        options = {'temperature': 0, 'num_predict': limit, 'num_ctx': 4096}
        if self.local_format == 'chatml':
            prompt = '<|im_start|>system\n' + system + '<|im_end|>\n'
            for i, text in enumerate(turns):
                role = 'assistant' if i % 2 else 'user'
                if role == 'user':
                    # Player text cannot inject template control tokens.
                    text = text.replace('<', '\\u003c').replace('>', '\\u003e')
                prompt += f'<|im_start|>{role}\n{text}<|im_end|>\n'
            prompt += '<|im_start|>assistant\n<think>\n</think>\n'
            response = self._request('generate', {'model': self.model, 'stream': False, 'raw': True, 'prompt': prompt,
                                                   'format': schema, 'options': options})
            text = response.get('response', '')
        else:
            messages = [{'role': 'system', 'content': system}] + [
                {'role': 'assistant' if i % 2 else 'user', 'content': t} for i, t in enumerate(turns)]
            response = self._request('chat', {'model': self.model, 'stream': False, 'think': False, 'format': schema,
                                              'options': options, 'messages': messages})
            text = response.get('message', {}).get('content', '')
        return text, response.get('prompt_eval_count', 0), response.get('eval_count', 0), f'ollama/{self.model}'


class FallbackBackend:
    """Try backends in order when one is unreachable or rate limited."""

    def __init__(self, backends):
        if not backends:
            raise ValueError('No language backend is available')
        self.backends = list(backends)
        self.label = 'auto'
        self.name = 'auto: ' + ' -> '.join(b.name for b in self.backends)

    def complete(self, system, turns, schema, limit=1200):
        errors = []
        for backend in self.backends:
            try:
                return backend.complete(system, turns, schema, limit)
            except OSError as error:
                errors.append(f'{backend.label}: {str(error)[:160]}')
        raise OSError('No free language backend answered (' + '; '.join(errors) + ')')


def backend(name='auto', model=None):
    """'auto' prefers free keyed services the player configured (fastest
    first), then OVH's keyless tier, then a local Ollama model."""
    if name == 'none':
        return None
    if name == 'ollama':
        return OllamaBackend(model or 'qwen3-vl:2b')
    if name != 'auto':
        return OpenAIBackend(name, model)
    chain = [OpenAIBackend(p) for p in ('groq', 'cerebras', 'gemini', 'openrouter', 'ollama-cloud')
             if os.environ.get(PRESETS[p].key_env)]
    chain.append(OpenAIBackend('ovh'))
    chain.append(OllamaBackend())
    return FallbackBackend(chain)
