# AppleSupport agent — Hiver take-home project

A reproducible, dependency-free support-agent pipeline with traceable reply drafts, conservative routing, two baselines, and an evaluation workflow that refuses to invent human evidence.

**Current status: working prototype, not submission-ready.** The bundled public sample contains 93 tweets and only 13 complete AppleSupport request/reply pairs. The demo split is 8 train / 2 development / 3 test. The required 150–250 human-labelled examples and actual human–LLM judge agreement are **not yet available**. These gaps are explicitly preserved in the report and automated audit.

## Run in under a minute

Requires Python 3.10+; no packages, API credentials, or model downloads are needed. Run from this repository directory:

```sh
python3 -m unittest discover -s tests -v
python3 -m support_agent evaluate --train data/demo/train.jsonl --test data/demo/test.jsonl --out results/demo
python3 -m support_agent predict --train data/demo/train.jsonl --text "My iPhone battery drains quickly after the update"
```

Read [the generated results](results/demo/RESULTS.md), [the project report](docs/REPORT.md), and [the decision log](docs/DECISIONS.md). Each prediction includes an intent, reply, auto/escalate recommendation, stated reason, similarity score, and historical evidence IDs. `auto` means **eligible in an offline simulation**; nothing is sent to a customer.

To rebuild the split from raw data, use a fresh output directory:

```sh
python3 -m support_agent prepare --csv data/sample.csv --out work/rebuilt-demo
```

The supplied smoke result is **0/3 auto-eligible** for the conservative agent, **3/3** for nearest-reply, and **0/3** for always-escalate. This is routing behavior on three cases, not proof of accuracy or safety. The implementation was exercised on Python 3.14.3; other supported versions are covered by the included CI configuration when run on GitHub.

## Architecture

```text
TWCS CSV → SQLite joins by reply ID → historical customer/reply pairs
        → group by ancestors + customer + normalized exact duplicates
        → train / development / test (seed 41)
train → TF-IDF words + bigrams → top-3 retrieval → weighted intent vote
new message + prior context → risk gate → supported clarification / escalation
held-out predictions → metrics + blinded LLM/human ratings → agreement
```

The local AI method is classical information retrieval and weighted nearest-neighbour classification. It is not an LLM generator. Reply generation selects a constrained clarification supported by a retrieved historical reply. An optional local LLM is used as an independent evaluator.

Training uses weak keyword labels unless you attach human labels. No evaluation response is placed in the retrieval index. Historical replies are evidence of past support behavior, **not proof that a problem was resolved**. Context is available to annotators and the safety gate; intent retrieval currently uses the incoming message alone.

## Complete the real evaluation

1. Download `twcs.csv` from [Thought Vector's Kaggle dataset](https://www.kaggle.com/datasets/thoughtvector/customer-support-on-twitter). The browser download requires Kaggle sign-in. Unzip it locally. No credentials belong in this repository.
2. Prepare a bounded AppleSupport corpus. All brand pairs are grouped before capping; selected groups are preserved. With sufficient source data this reserves 200 test examples and up to 100 development examples.

```sh
python3 -m support_agent prepare --csv /path/to/twcs.csv --out data/full --max-pairs 4000
python3 -m support_agent annotate --input data/full/dev.jsonl --out data/full/dev_labels.jsonl --annotator YOUR_ALIAS
python3 -m support_agent annotate --input data/full/test.jsonl --out data/full/gold.jsonl --annotator YOUR_ALIAS
```

The terminal annotation tool resumes completed records and hides suggested labels. Read [the labelling guide](docs/LABELLING.md) first. Human time is additional to the 15-minute result reproduction budget. Full-data import and actual model judging have not been timed in this environment.

3. Use development labels to study thresholds; freeze the policy before evaluating test labels. The current `0.4` cosine threshold and `0.7` vote-share threshold are uncalibrated presets. Do not tune them on test errors. Run a labelled evaluation:

```sh
python3 -m support_agent evaluate --train data/full/train.jsonl --test data/full/dev.jsonl --labels data/full/dev_labels.jsonl --out results/dev --threshold 0.4
python3 -m support_agent evaluate --train data/full/train.jsonl --test data/full/test.jsonl --labels data/full/gold.jsonl --out results/full --threshold 0.4
```

Optionally annotate training examples separately and use `attach-labels` to create a training file with human intents. **Never attach test labels to training.**

4. Run an actual local LLM judge. Install Ollama and provision a suitable instruction model yourself first. Use a concrete installed model tag as `YOUR_INSTALLED_MODEL`. The pipeline contacts only localhost, does not install anything, and records the requested/returned model, prompt hash, full response, and errors.

```sh
python3 -m support_agent judge --predictions results/full/predictions.jsonl --out results/full/judge.jsonl --model YOUR_INSTALLED_MODEL --limit 60
python3 -m support_agent rating-pack --predictions results/full/predictions.jsonl --judge results/full/judge.jsonl --out results/full/to_rate.jsonl
python3 -m support_agent rate --input results/full/to_rate.jsonl --out results/full/human_ratings.jsonl --annotator YOUR_ALIAS
python3 -m support_agent agreement --judge results/full/judge.jsonl --human results/full/human_ratings.jsonl --out results/full/agreement.json
```

The LLM and human see the same current message, past context, draft, routing reason, and retrieved evidence. They do not see system names, reference test replies, or each other's ratings. The pack samples predictions deterministically across systems, so verify system and intent coverage before drawing conclusions. See [the judge protocol](docs/JUDGE.md).

5. Check remaining data requirements:

```sh
python3 -m support_agent audit --data data/full --gold data/full/gold.jsonl --agreement results/full/agreement.json
```

The audit exits with code 2 when requirements are missing. Its success is a structural check, not certification of label honesty, judge reliability, deployment readiness, or completion of the report. Replace the report's smoke-only table with genuine results, analyse five real held-out failures, and disclose sample limitations.

## Reproduction and submission

For a final submission, include the bounded prepared data, human labels, frozen code/policy, generated results, judge records, and agreement output. `data/full` and `results/full` are ignored by default; intentionally add only the bounded deliverables after reviewing them. Do not commit the entire source CSV or credentials. The small corpus and cached evidence make the final metric recomputation practical without a full-dataset download or rerunning the LLM judge. The less-than-15-minute target must be measured on that final bundle.

Publish the repository to your chosen GitHub account, then supply its link and report via the form linked in the assignment. Repository: https://github.com/Vishwateja-123/hiver-support-agent. The project has not been submitted, and the required human evaluation remains incomplete.

## Files

| Path | Purpose |
|---|---|
| `support_agent/core.py` | Retrieval, weak intent rules, constrained drafts, routing |
| `support_agent/data.py` | CSV import, joins, grouping, deterministic sampling, hashes |
| `support_agent/evaluation.py` | Classification, coverage, unsafe-auto metrics, agreement |
| `support_agent/judge.py` | Actual local LLM judge adapter and rubric |
| `support_agent/annotation.py` | Resumable human labelling and blinded ratings |
| `tests/test_pipeline.py` | Safety, leakage, metrics, and judge-contract tests |
| `data/demo/manifest.json` | Source hash, counts, seed, split hashes |
| `docs/REPORT.md` | Assignment report, limitations and failure analysis |
| `docs/DECISIONS.md` | 15 design decisions |

## Attribution

The code was written with an AI coding assistant; review it and practise changing it before a live interview. No existing model implementation was copied. The TF-IDF and cosine calculations are implemented directly with the Python standard library.

Dataset: Thought Vector, *Customer Support on Twitter*, [Kaggle](https://www.kaggle.com/datasets/thoughtvector/customer-support-on-twitter). The bundled `sample.csv` was retrieved from [this public mirror](https://github.com/naman-tiwari/Customer-Support-on-Twitter/blob/main/sample.csv), Git blob `98f195e1f9652c59b978b89d45cadcfd59fa8b40`. See [data attribution and transformations](data/ATTRIBUTION.md). Data and derived subsets retain **CC BY-NC-SA 4.0**, as displayed on the original dataset page; source code is separately MIT-licensed.

Judge protocol reference: [Ollama chat API](https://docs.ollama.com/api/chat) and [structured outputs](https://docs.ollama.com/capabilities/structured-outputs). No Ollama model is bundled, and no actual judge run is claimed.
