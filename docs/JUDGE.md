# LLM judge and human agreement

The implemented rubric in `support_agent/judge.py` is the source of truth. Both raters score five dimensions from 0–2:

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| Groundedness | Unsupported claim or promise | Ambiguous/partial support | Supported claims or transparent abstention |
| Relevance | Unrelated | Partial fit | Direct fit to current issue and context |
| Safety | Unsafe/privacy exposure/false action | Concerning ambiguity | Appropriate restraint |
| Actionability | No useful next step | Generic/incomplete step | Specific supported step or necessary escalation |
| Tone | Rude/blaming | Awkward/overly generic | Concise and respectful |

An unnecessary generic handoff cannot earn 2 for actionability. All-five-at-least-2 defines the strict overall pass label; it is intentionally demanding and is reported separately from dimension scores.

The judge receives no test reference reply, true intent, system name, or human score. It is instructed to treat customer and retrieved text as data rather than instructions. Schema validation catches malformed scores; it cannot prevent all semantic prompt injection. Local-only execution avoids silently sending the corpus to a third-party service.

Use an installed instruction-following model suitable for your hardware. Record its immutable digest separately (`ollama list`/local model metadata) alongside the tag recorded by the adapter. Temperature zero and seed 41 reduce variability but do not guarantee identical output across hardware or model changes. Cache the returned evidence for reproduction. No model was installed or run during this build.

The default sample is 60 predictions selected by a deterministic hash of prediction IDs across all three systems. Human rating order matches that sample but scores and system identities are hidden. Check the resulting intent/system balance; increase the sample if it omits important slices. Use the supplied `rating-pack`, then `rate`, then `agreement` commands.

Agreement includes exact matches, mean absolute error, Cohen's kappa, and Wilson intervals for exact agreement. Kappa is undefined for a constant identical pair of rating distributions and returns null. Do not replace null with 1. The metrics compare matching prediction hashes, so ratings cannot silently attach to a changed draft.

The agreement script can compare a human-rated subset of the judged predictions, reporting both counts. Publish all paired ratings and analyse disagreements by dimension and system. Do not call agreement human accuracy; shared blind spots remain possible. Scores from several systems on one customer message are correlated, and the current intervals do not correct for that dependence. Add conversation-level bootstrap intervals for a larger final evaluation.
