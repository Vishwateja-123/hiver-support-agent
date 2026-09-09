# Human labelling protocol

## Sampling and separation

The full-data preparation recipe selects AppleSupport request/reply pairs with a deterministic random group order (seed 41), then reserves a 200-message test pool and up to 100 development messages. Group identity connects historical ancestors, customer identity, and normalized exact duplicates. The evaluation pool is group-sampled, not perfectly representative traffic sampling. Larger groups can affect representation. Inspect counts in the manifest and publish per-intent supports.

The included demo has only 3 evaluation candidates. **It is not the requested golden set.** Do not duplicate these cases or create synthetic tweets to reach 200. Do not call AI-suggested labels human labels. A human must read and decide each case.

Freeze the test pool before modelling. Read and refine guidelines using development messages. Run `annotate` independently on development and test files. The tool displays previous context and the current message, hides suggested labels and future replies, and saves after every completed item. Ctrl-C leaves previous items saved; rerun with the same output to resume.

## Intent labels

| Label | Include | Boundary |
|---|---|---|
| battery_power | drain, charging, device power | Physical danger/repair takes precedence |
| connectivity | Wi-Fi, cellular, Bluetooth connection | Media-only failures go to apps_media |
| software_performance | overall slowness, freezing, operating-system update | A specific app symptom goes to apps_media |
| apps_media | app behavior, keyboard/notifications, playback | Authentication/billing takes precedence |
| account_billing | Apple ID, access codes, login, charges, refunds | Never imply account access is available |
| hardware_repair | physical damage, repair, swollen battery | Escalate potentially dangerous cases |
| thanks | unambiguous acknowledgement without a new issue | “Thanks, but it still fails” is not thanks |
| other | insufficient context, unrelated or unsupported intent | Explain what is missing |

For multiple issues, choose the one requiring the highest-risk intervention: account or physical safety first, then the principal explicit request. If no principal request is identifiable, choose `other` and record the ambiguity. Add detail in the rationale; do not silently invent extra labels after seeing test results.

## Routing label

`should_escalate=yes` means a safe next response requires human review under this prototype's scope: account transactions/access, danger, personal information, unclear context, unverifiable policies, or actions outside a supported clarification. `no` means a low-risk clarification or acknowledgement is appropriate; it does not mean the underlying issue is solved.

Label routing from the message and available past context, not from whether this particular model happened to find a matching reply. This permits measuring missed opportunities to assist. Do not infer resolution from a support reply, silence, or a DM request.

Each saved label includes `id`, `intent`, `should_escalate`, `label_source=human`, `annotator`, and `rationale`. Use your real name or stable alias. Software can verify fields but cannot verify that someone actually performed the work.

## Quality control

Have a second person independently annotate at least 40 held-out cases using a separate output file. Calculate and report intent and routing disagreements, keep original labels, and write an adjudicated final file with a short resolution record. Do not discard hard examples after scoring. This step is recommended and not performed in the supplied bundle.
