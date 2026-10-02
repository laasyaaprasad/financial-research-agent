"""Budgeted Tavily calls, public response recording and zero-network replay."""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
from pathlib import Path

from dotenv import load_dotenv

from agents import tracing

load_dotenv()


def key_for(operation: str, parameters: dict) -> str:
    return hashlib.sha256(json.dumps([operation, parameters], sort_keys=True).encode()).hexdigest()


def clean(value):
    """Server errors/pages cannot accidentally persist one of our credentials."""
    secrets = [os.getenv(n) for n in ('TAVILY_API_KEY','NEBIUS_API_KEY','LANGFUSE_SECRET_KEY') if os.getenv(n)]
    if isinstance(value, str):
        for secret in secrets:
            value = value.replace(secret, '[redacted]')
        return value
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items() if k.lower() not in {'authorization','api_key','headers'}}
    if isinstance(value, list):
        return [clean(v) for v in value]
    return value


class Retrieval:
    def __init__(self, directory: Path | str, *, budget: float = 25, project_id: str = 'dev', replay: bool = False, client=None):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.budget, self.replay, self.client = budget, replay, client
        self.used = 0.0
        self.records = {}
        self._lock = asyncio.Lock()
        self._inflight = {}
        self._owns_client = client is None and not replay
        if not replay:
            # Resume an interrupted question without buying the same retrieval
            # again; all historical receipts still count against its budget.
            for path in self.directory.glob('*.json'):
                record=json.loads(path.read_text())
                self.records[path.stem]=record
                self.used+=record['credits']
        if self._owns_client:
            from tavily import AsyncTavilyClient
            if not os.getenv('TAVILY_API_KEY'):
                raise ValueError('Set TAVILY_API_KEY in .env')
            self.client = AsyncTavilyClient(project_id=project_id)

    async def close(self):
        if self._owns_client:
            await self.client.close()

    @staticmethod
    def maximum_cost(operation: str, p: dict) -> float:
        if operation == 'search':
            return 2 if p.get('search_depth') == 'advanced' else 1
        if operation == 'extract':
            return math.ceil(len(p['urls']) / 5) * (2 if p.get('extract_depth') == 'advanced' else 1)
        if operation == 'map':
            return math.ceil(p.get('limit', 10)/10) * (2 if p.get('instructions') else 1)
        raise ValueError('Unsupported retrieval operation')

    async def call(self, operation: str, **parameters) -> dict:
        if operation == 'search' and not 0 < len(parameters['query']) < 400:
            raise ValueError('Search queries must be below 400 characters')
        parameters = {**parameters, 'include_usage': True}
        identity = key_for(operation, parameters)
        path = self.directory / f'{identity}.json'
        async with self._lock:
            if identity in self.records:
                return self.records[identity]['response']
            if self.replay:
                if not path.exists():
                    raise ValueError(f'Missing recorded {operation} response')
                record = json.loads(path.read_text())
                if record['operation'] != operation or record['parameters'] != parameters:
                    raise ValueError('Retrieval replay parameters differ')
                self.records[identity] = record
                self.used += record['credits']
                return record['response']
            if identity in self._inflight:
                future = self._inflight[identity]
                owner = False
            else:
                future = asyncio.get_running_loop().create_future()
                self._inflight[identity] = future
                owner = True
                maximum = self.maximum_cost(operation, parameters)
                allowed = self.used + maximum <= self.budget
                if allowed:
                    self.used += maximum
        if not owner:
            return await future
        credits = 0.0
        if not allowed:
            response = {'results': [], 'budget_exhausted': True}
        else:
            try:
                with tracing.tool_span(f'tavily_{operation}', parameters) as span:
                    response = clean(await getattr(self.client, operation)(**parameters))
                    reported = (response.get('usage') or {}).get('credits')
                    credits = float(reported) if reported is not None else maximum
                    span.finish({'request_id': response.get('request_id'), 'credits': credits,
                                 'results': len(response.get('results') or [])})
            except Exception as exc:
                # A failed request may have reached the server. Reserve its upper
                # bound rather than retry blindly or persist HTTP diagnostics.
                credits = maximum
                response = {'results': [], 'error': type(exc).__name__}
        record = {'operation': operation, 'parameters': parameters, 'response': response, 'credits': credits}
        async with self._lock:
            if allowed:
                self.used += credits - maximum
            self.records[identity] = record
            path.write_text(json.dumps(record, ensure_ascii=False))
            future.set_result(response)
            del self._inflight[identity]
        return response
