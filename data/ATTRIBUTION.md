# Data attribution

- Original: Thought Vector / Stuart Axelbrooke, *Customer Support on Twitter*, Kaggle dataset `thoughtvector/customer-support-on-twitter`, version 10 on the accessed page.
- Source page: https://www.kaggle.com/datasets/thoughtvector/customer-support-on-twitter
- Sample mirror: https://github.com/naman-tiwari/Customer-Support-on-Twitter/blob/main/sample.csv
- Mirror blob SHA: `98f195e1f9652c59b978b89d45cadcfd59fa8b40`
- Local sample SHA-256: `302aaa20f7dcebe602d143c615b0c4575e7937a396439bb1521b84c838e91b68`
- Retrieved: 2026-09-09.
- Dataset license as displayed on Kaggle: [Creative Commons Attribution-NonCommercial-ShareAlike 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). The original page directs commercial/full-dataset licensing questions to the dataset creator. No commercial-use rights are asserted here.

The raw sample contains 93 CSV records (quoted multiline text means physical line count differs). The derived demo pairs use AppleSupport direct replies only. Transformations: HTML entity decoding, removal of mentions/URLs/agent signatures, basic email and long-number redaction, conversation context reconstruction, group splitting, and weak intent suggestions. Dates and anonymized customer IDs are retained for audit. Basic redaction is not a complete PII detector.

Original data and derived subsets remain under the data license. The MIT code license does not relicense these tweets. This is a research/take-home demonstration, not an endorsed Apple service.
