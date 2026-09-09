# Submission handoff

Form: https://intelligent-bar-256.notion.site/39492cbf0da2800682cfc78a600a745f

The live form was checked on 2026-09-09. It contains four fields and a Submit button, with no separate report-upload field.

| Form field | What to enter | Current status |
|---|---|---|
| Github Url | The published repository URL, not your profile URL or a local ZIP | Repository not yet published |
| Email | Your application/contact email | Needed from you |
| LinkedIn Url | Your LinkedIn profile URL | Needed from you |
| Phone | Your phone number including country code | Needed from you |

Connected GitHub account: `Vishwateja-123`. Suggested repository name: `hiver-support-agent`. This name is a proposal, not an existing verified repository URL.

## Finish before submitting

1. Supply the original `twcs.csv` to prepare the 200-example held-out pool.
2. Complete the human labels and actual local LLM/human judge ratings using the README commands. These cannot be represented by AI-written labels or mocked tests.
3. Recompute the evaluation, update `docs/REPORT.md` with the real results, and verify the final reproduction time.
4. Publish the project repository. The browser currently requires GitHub sign-in; the local GitHub CLI also could not authenticate. Do not share passwords or tokens in chat.
5. Keep `docs/REPORT.md`, `docs/DECISIONS.md`, bounded evaluation data, human labels, and evaluation evidence accessible through the repository. Ensure the README links to them.
6. Enter the repository URL and your three contact fields in the Notion form, then submit and retain the confirmation.

If publishing manually, create a repository on your own GitHub account, unzip the provided archive, and upload the contents of its `hiver-support-agent` folder preserving subfolders. Do not upload only the ZIP: reviewers need a browsable, runnable repository. Public access permits review; a private repository needs access explicitly granted to the reviewers identified by the hiring team.

## Current deliverable status

The prototype, report, decision log, two baselines, annotation tools, evaluation harness, and 15 passing tests are present. The bundled real sample contains only 13 AppleSupport pairs and a 3-example test split. The required golden set and human–LLM agreement remain missing. Neither publishing nor submission has occurred. Do not present this bundle as satisfying every assignment requirement yet.
