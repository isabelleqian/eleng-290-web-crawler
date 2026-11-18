# Article review files

Start with [reviewed_results.csv](reviewed_results.csv): the single current review table, keyed by source_id. It contains 36 non-Nexis records and 1,592 Nexis records (1,628 total). The initial 386 summaries received the factual-content style correction; subsequent summaries follow the corrected instructions. All Nexis factual summaries are complete; no summaries remain pending. Public-link and independent title/publisher/date verification remain incomplete for rows marked `partial_verification`, and the existing `needs_attention` record remains flagged.

[methodology.md](methodology.md) records the method, source evidence, decisions and limitations. Its summary-style correction supersedes earlier instructions about evaluative caveats.

- `support/`: corpus inventory, original ten-record Nexis selection, non-Nexis scope, and current progress and validation.
- `scripts/`: active save and validation helpers. Run from the repository root: `python outputs/article_review_pilot/scripts/checkpoint_review.py`.

The CSV path is unchanged. Databases, source archives, reviewed source metadata and filtering decisions are outside this folderâ€™s cleanup.
