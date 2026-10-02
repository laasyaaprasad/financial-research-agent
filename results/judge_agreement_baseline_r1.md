# Judge agreement: baseline_r1

Judge (`deepseek-ai/DeepSeek-V4-Pro`) agreed with the human grade on **8 of 9** user-graded answers, and **9 of 10** including G29 (graded by Claude at the user's request).

| ID | Judge | Grade | Graded by | Agree |
|---|---|---|---|---|
| G01 | correct | correct | user | ✓ |
| G04 | correct | partial | user | ✗ |
| G05 | partial | partial | user | ✓ |
| G06 | partial | partial | user | ✓ |
| G14 | partial | partial | user | ✓ |
| G16 | partial | partial | user | ✓ |
| G18 | correct | correct | user | ✓ |
| G24 | incorrect | incorrect | user | ✓ |
| G25 | partial | partial | user | ✓ |
| G29 | partial | partial | claude (delegated by user) | ✓ |

## Disagreement

- **G04 (Oracle RPO):** the judge marked it correct because both numbers match the reference. The user graded it partial because the ~13% figure was cited to a Reddit post. Correctness is scored separately from source quality: that weakness shows up in the scorecard's primary-source and claim-support columns, not in the correctness verdict.
