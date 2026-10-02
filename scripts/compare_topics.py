"""Controlled topic comparison: identical queries/settings, saved public results."""

import asyncio
import json
from pathlib import Path

from agents.retrieval import Retrieval

QUERIES = [
    'NVIDIA NVDA fiscal 2026 revenue 10-K January 25 2026',
    'Apple AAPL fiscal 2025 revenue 10-K September 27 2025',
    'Costco COST fiscal 2026 membership fees annual results',
    'Microsoft MSFT Q4 fiscal 2026 Azure guidance Q1 2027',
    'Walmart WMT Q2 fiscal 2027 operating income earnings release',
    'Novo Nordisk NVO 2025 sales constant exchange rates annual report',
    'Adobe ADBE Q2 fiscal 2025 revenue earnings',
    'JPMorgan JPM Q2 2026 net income earnings release',
]


async def main():
    retrieval = Retrieval('results/raw/topic_comparison', budget=32, project_id='eval-m4-topics')
    pairs = []
    try:
        for query in QUERIES:
            pair = {}
            for topic in ('general','finance'):
                response = await retrieval.call('search', query=query, topic=topic, search_depth='advanced',
                                                max_results=8, auto_parameters=False, include_answer=False, timeout=45)
                pair[topic] = [r['url'] for r in response.get('results') or []]
                pair[topic+'_error'] = response.get('error')
            pairs.append({'query': query, **pair})
            print('Compared', query.split()[0], flush=True)
    finally:
        await retrieval.close()
    data = {'pairs': pairs, 'credits': retrieval.used}
    Path('results/raw/topic_comparison.json').write_text(json.dumps(data,indent=2))
    print('Credits',retrieval.used,'identical URL rankings',sum(p['general']==p['finance'] for p in pairs),'of',len(pairs))


if __name__ == '__main__':
    asyncio.run(main())
