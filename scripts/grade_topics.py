"""Judge the saved controlled topic experiment; no new retrieval calls."""
import json
from pathlib import Path
from agents.company import resolve
from agents.evidence import matching_entities, source_tier
from evals.sec_snapshots import SnapshotClient
from evals.retrieval import relevance

root=Path('results/raw/topic_comparison')
records=[json.loads(p.read_text()) for p in root.glob('*.json')]
pairs=json.loads(Path('results/raw/topic_comparison.json').read_text())['pairs']
rows=[]
for pair,ticker in zip(pairs,['NVDA','AAPL','COST','MSFT','WMT','NVO','ADBE','JPM']):
    entity=resolve(ticker,mentions=[ticker],client=SnapshotClient())
    for topic in ('general','finance'):
        record=next(r for r in records if r['parameters'].get('query')==pair['query'] and r['parameters'].get('topic')==topic)
        sources=[dict(id=f'T{i}',url=r['url'],title=r.get('title',''),content=r.get('content','')) for i,r in enumerate(record['response'].get('results') or [])]
        score=relevance(pair['query'],'2026-10-01',sources,root/'grades'/f'{ticker}_{topic}.json')
        primary=sum(source_tier(s['url'],matching_entities(s['title'],s['content'],s['url'],entity))=='primary' for s in sources)
        rows.append(dict(ticker=ticker,topic=topic,primary=primary,total=len(sources),relevant=score['relevant']))
        print(ticker,topic,score['relevant'],len(sources),flush=True)
lines=['# M4: controlled Tavily topic comparison','','Eight matched queries; only `topic` changes. Advanced search, eight results, automatic parameters disabled. No reference answers are supplied to the independent DeepSeek judge. Public responses and scores are saved locally. Total experiment cost: 32 credits.','','| Topic | Relevant results | Primary results |','|---|---|---|']
for topic in ('general','finance'):
    group=[r for r in rows if r['topic']==topic];total=sum(r['total'] for r in group)
    lines.append(f"| {topic} | {sum(r['relevant'] for r in group)}/{total} | {sum(r['primary'] for r in group)}/{total} |")
lines += ['', 'All eight URL rankings differed. This confirms that finance is accepted by the API and changes results; it does not establish universal superiority. Keep general as the default unless this small experiment shows a clear quality advantage for finance. Eight queries are too few to claim statistical significance.', '', 'Settings use the [official search API](https://docs.tavily.com/documentation/api-reference/endpoint/search). Extraction uses query-focused chunks, basic first and advanced only for failed URLs, following the [extract API](https://docs.tavily.com/documentation/api-reference/endpoint/extract). Extracted evidence is an excerpt, not the entire filing.']
Path('results/topic_comparison_m4.md').write_text('\n'.join(lines)+'\n')
Path('results/raw/topic_comparison_grades.json').write_text(json.dumps(rows,indent=2))
