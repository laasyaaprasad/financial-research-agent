# M4: controlled Tavily topic comparison

Eight matched queries; only `topic` changes. Advanced search, eight results, automatic parameters disabled. No reference answers are supplied to the independent DeepSeek judge. Public responses and scores are saved locally. Total experiment cost: 32 credits.

| Topic | Relevant results | Primary results |
|---|---|---|
| general | 37/64 | 25/64 |
| finance | 15/62 | 0/62 |

All eight URL rankings differed. This confirms that finance is accepted by the API and changes results; it does not establish universal superiority. Keep general as the default unless this small experiment shows a clear quality advantage for finance. Eight queries are too few to claim statistical significance.

Settings use the [official search API](https://docs.tavily.com/documentation/api-reference/endpoint/search). Extraction uses query-focused chunks, basic first and advanced only for failed URLs, following the [extract API](https://docs.tavily.com/documentation/api-reference/endpoint/extract). Extracted evidence is an excerpt, not the entire filing.
