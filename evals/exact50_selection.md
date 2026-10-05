# Exact50: how the 50 questions were chosen

Exact50 is a 50-question benchmark drawn only from the held-out sets (`test_heldout`, `test_hard`, `test_tables`,
`test_edge`, `test_web`; 74 questions). The dev sets (`golden`, `dev_tables`, `edge_dev`, `web_dev`) are excluded,
because they were inspected and used while the agent was built.

## Why a new set

In the end-to-end run of 2026-10-05 both agents scored near the ceiling on `test_heldout`, `test_hard` and
`test_tables`. Most of those questions ask for one figure from an earnings release or a filing, with at most a
period-label trap, and a search agent finds the figure in its first results. Such questions say little about what an
analyst tool has to get right. Exact50 keeps the questions that test those things.

## Rules (written before the set was built; applied once, in this order)

Each held-out question belongs to the first class whose description fits it, judged from the question, its
`failure_mode` and its grading rule (not from any agent's answers). Classes are taken whole, in priority order,
until 50 questions are reached; the class that overflows is cut in ID order.

1. **Edge cases and ambiguous requests** (all of `test_edge`): terse or ambiguous wording, missing company or period,
   share classes, out-of-scope asks, unreported periods, private or non-SEC companies, malformed input.
2. **Web-dependent questions** (all of `test_web`): call commentary, recent events, foreign issuers, private
   companies and multi-hop questions whose facts are not in SEC filings.
3. **Traps**: questions whose obvious answer is wrong because of the date: point-in-time questions where later
   results exist, superseded guidance, "latest" or "recent" questions, and figures that are unreported, undisclosed
   or from a company that no longer files.
4. **Actual versus guidance**: beat-or-miss questions against the company's own earlier guidance.
5. **Comparisons across fiscal calendars**: several companies whose fiscal quarters must each be mapped to the
   requested window.
6. Everything else: single figures, segment figures, management drivers, single-company calculations and trends.

## Result

| Class | Questions | Taken |
|---|---|---|
| 1. Edge and ambiguous | E02, E06, E09, E10, E13, E14, E17, E19, E21, E25, E27, E29, E32, E33, E37, E39 | 16 |
| 2. Web-dependent | W01, W02, W05, W06, W10, W11, W13, W14, W18, W19 | 10 |
| 3. Traps | T10, T15, T16, T17, T18, T19, H01, H02, H03, H04, H05, H14, H15, H16, H19, H20 | 16 |
| 4. Actual versus guidance | T11, T12, H17, H18 | 4 |
| 5. Comparisons across fiscal calendars | T20, X01, X03, X04 (X07 cut by the ID-order rule) | 4 of 5 |
| 6. Everything else | T01-T09, T13, T14, H06-H13, X02, X05, X06, X08 | 0 |

## Caveat

The rules were written after the 2026-10-05 run, so their author had seen both agents' results on these questions.
The rules use only question content, and the questions, references and grading rules are copied unchanged from the
held-out sets. Still, Exact50 is not a fresh held-out set: read it as a harder, more discriminating benchmark, and
read the full held-out sets (reported alongside it) for the unselected picture.
