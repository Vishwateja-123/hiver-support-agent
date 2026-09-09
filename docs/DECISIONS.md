# Decision log

1. **AppleSupport**: it has the largest brand reply count in the accessible sample and concrete device-support concerns. Brand choice is provisional until full-data inspection.
2. **Offline classical AI first**: TF-IDF retrieval runs immediately with no paid service or model download; the tradeoff is weaker semantic understanding.
3. **A direct reply is evidence, not a resolution**: private DM handoffs dominate the sample, so successful outcomes cannot be inferred.
4. **Join by parent tweet ID**: CSV row proximity is not a reliable conversation relationship.
5. **Deterministic reply selection**: use one direct reply per customer message to avoid counting the same request multiple times; acknowledge that ID order is not chronological preference.
6. **Group before capping**: related users, ancestors, and normalized exact duplicates must remain isolated before sampling, otherwise a bounded corpus can hide leakage.
7. **SQLite import**: the large CSV does not have to live entirely in Python memory. Selected brand pairs and ancestor chains still consume memory.
8. **Soft cap**: preserve complete selected groups rather than silently severing conversations at exactly 4,000 rows.
9. **Primary intent plus abstention**: keep the initial label set understandable for an interview; document multi-intent ambiguity instead of concealing it.
10. **Weak training labels are explicit**: the code can run before human annotation, but weak-label agreement is never human evaluation.
11. **Bounded reply templates**: only historical evidence supporting an iOS clarification or courtesy acknowledgement can yield auto eligibility. Arbitrary historical replies are never copied by the proposed agent.
12. **Scores are not probabilities**: cosine and vote share remain named as such; uncalibrated presets are not confidence claims.
13. **Safety uses prior context**: account or physical risk in a previous turn can still make a superficially harmless follow-up unsafe to automate.
14. **Judge failure is visible**: malformed output and connection failure stop the judge stage; mocked contract tests remain distinct from real model evidence.
15. **Human work is an explicit dependency**: do not fabricate 200 hand labels, ratings, agreement statistics, a repository URL, or a completed submission. The structural audit exposes remaining requirements.
