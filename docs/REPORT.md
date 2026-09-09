# Hiver project report: AppleSupport

## 1. Framing and completion status

The agent drafts the next response to a customer asking AppleSupport for help. Good behavior means identifying the main intent, giving a relevant historically supported next step, and deferring when account access, risk, ambiguity, or insufficient evidence requires a person. It must never pretend to have changed an account, issued a refund, or resolved a problem.

This is an **offline prototype with verified software behavior, not a completed trust evaluation**. Only a 93-tweet public sample was available. It yields 13 paired AppleSupport messages. The full dataset requires access not available during this build, the hand-labelled gold set has not been created, and no real LLM or human judge ratings were collected. These are blocking deliverables, not cosmetic improvements.

The scope excludes account actions, customer messaging, live Apple policy, links to unverified 2017 resources, free-form LLM generation, and autonomous deployment. Auto eligibility is limited to supported low-risk clarifications or acknowledgements. Historical conversations show support steps, usually moving to DM; they rarely establish a verified resolution.

## 2. Data, method, and intended gold set

The importer joins each inbound tweet to a direct AppleSupport reply by ID. If several replies exist, it deterministically selects one by reply ID; this is reproducible but not guaranteed to be the earliest or best reply. Previous context is recovered through parent links; future turns are excluded. We group related ancestors, repeated customers, and normalized exact duplicate messages before splitting, reducing conversation leakage and user memorisation.

The seed is 41. The demo has 8 train messages from 6 groups, 2 development messages from 2 groups, and 3 test messages from 3 groups. Similarity fitting uses training text only. The full-data recipe targets 4,000 pairs with a soft group-preserving cap, reserving 200 test examples and up to 100 development examples. Exact and near-duplicate paraphrase leakage are different: only the former is handled automatically.

The initial taxonomy is battery/power, connectivity, software/performance, apps/media, account/billing, hardware/repair, thanks, and other. Battery, update, and app issues are visible in the sample. Account/billing captures access problems; hardware and thanks are provisional coverage categories requiring full-data validation. Training labels currently come from keyword rules, so overlapping and indirect intents will be unreliable.

The intended gold set is 200 real, held-out messages manually labelled for primary intent and whether a safe next reply requires a human. Annotators see past context but no model labels or future response. They provide an alias and rationale; ambiguous messages go to `other` and human review. A second annotator should independently label at least 40 cases, with disagreements adjudicated and the original judgements retained. The CLI supports separate annotation files; this second review has not occurred.

## 3. Systems and observed results

The trivial baseline predicts the training majority intent and escalates everything. The simple baseline uses top-1 TF-IDF retrieval and copies its reply with no safety gate. The proposed agent uses a top-3 similarity-weighted intent vote and requires cosine similarity ≥0.4, vote share ≥0.7, no detected risk/incomplete history, and a supported approved draft. Thresholds are presets, not calibrated probabilities.

| System | Demo test messages | Auto eligible | Coverage | Human intent/reply metrics |
|---|---:|---:|---:|---|
| Majority + always escalate | 3 | 0 | 0% | Unavailable |
| Nearest historical reply | 3 | 3 | 100% | Unavailable |
| Retrieval + routing gate | 3 | 0 | 0% | Unavailable |

These are executable smoke results, reproduced in `results/demo`. The automated test suite passes 15 tests covering past-only history, group isolation, duplicate leakage, safety overrides, missing context, unsupported replies, absent gold labels, uncertainty, strict judge output, and recorded judge failure. Mocked judge tests check the adapter; they are not model evaluations.

For a real run, the harness reports accuracy, fixed-taxonomy macro-F1, supported-class macro-F1, confusion matrix, per-intent support, coverage, unsafe-auto count/rate, escalation recall, selective intent accuracy, and a Wilson interval for unsafe-auto rate. A zero denominator yields unavailable rather than a perfect score. The input hashes and policy threshold accompany every run. Development labels must be used to choose thresholds before test evaluation.

## 4. Reply judge and human agreement

The optional local Ollama judge scores groundedness, relevance, safety, actionability, and tone from 0 to 2 using a fixed rubric. It sees retrieved evidence and historical context but not the held-out reference reply or system identity. Failures are saved and stop the run; missing scores are never replaced by heuristics. The model tag, prompt hash, request hash, raw response, and prediction hash permit audit.

A human rates the same deterministic prediction sample without seeing LLM scores. The agreement tool reports per-dimension exact agreement, mean absolute error, Cohen's kappa, and agreement on an all-dimensions-pass decision. No agreement number is available yet. The proposed 60-prediction sample is exploratory; repeated systems for the same message create dependence, so simple binomial intervals are optimistic. A larger group-bootstrap analysis and a second human are appropriate before making trust claims.

## 5. Five observed failure patterns with real examples

These cases are drawn from the available sample; training/development observations are explicitly separated from held-out errors. They are diagnostic hypotheses, not ranked failure frequencies from a gold evaluation.

1. **Context-dependent wording (development, 119249).** “Me too am suffering” refers to an earlier iOS complaint. Message-only retrieval predicts battery/power. Hypothesis: including a bounded representation of previous customer turns would improve intent recognition. Context is already retained for review and safety, but not used in retrieval.
2. **Multiple intents (training, 119263).** The customer reports broken apps and frequent Wi-Fi disconnections after an update. Keyword priority chooses connectivity. Hypothesis: a primary-plus-secondary label scheme or multi-intent abstention would better represent the complaint. This case informed diagnosis, not test accuracy.
3. **Indirect account vocabulary (test, 119299).** The customer asks for a new “I-store” code after a too-many-sent message. Retrieval predicts apps/media rather than recognising an access issue. The gate escalates. Hypothesis: additional account-access examples and spelling-aware representations would help; a correct route does not excuse wrong intent classification.
4. **Vague complaint retrieves the wrong issue (test, 119301).** “fix this update. It’s horrible” retrieves battery-related history and predicts battery/power. The gate escalates. Hypothesis: insufficient-information detection and a learned out-of-distribution score could improve the label. Cosine similarity is not confidence.
5. **Private handoff is mistaken for resolution evidence (test, 119253).** A slow-phone complaint receives a historical invitation to DM, not a verified fix. The nearest baseline copies a reply from a different case and marks it auto-eligible; the conservative agent abstains. Hypothesis: source replies need action-type and outcome annotations before broader drafting is defensible.

## 6. What is misleading about my headline number?

“0% auto coverage” is not a safety achievement. An agent that escalates everything cannot make an unsafe automated reply but may offer little value. The nearest baseline's 100% coverage says nothing about reply correctness. Three cases cannot establish generalisation, and zero observed errors would still leave a very wide uncertainty interval.

Weak-label agreement is circular because the training labels and diagnostic reference labels share rules. It is saved only for debugging, never presented here as accuracy. Eight taxonomy classes are not all represented in the demo; aggregate scores can hide complete failure on missing classes. Group sampling differs from a production traffic distribution and can overrepresent large conversations. The tweets are from 2017; old steps and device versions are not current policy. Public reply availability creates selection bias, and private resolutions are missing. High LLM-human agreement would still not prove correctness if both share a bias.

## 7. One more week

First obtain the full CSV and validate the taxonomy on development data. Independently label the 200-case gold set plus development cases; double-label and adjudicate a subset. Improve context-aware intent recognition and account-access coverage using only development evidence. Calibrate a coverage/risk tradeoff, retaining an explicit abstention policy if evidence is insufficient. Run the real judge and human rating protocol, examine disagreements and intent slices, then replace this smoke table with genuine held-out results. Finally, measure cached-result reproduction time, publish the bounded bundle, and prepare to explain and modify each component live.
