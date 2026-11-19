# Article review files

Start with [reviewed_results.csv](reviewed_results.csv): the single current review table, keyed by source_id. It contains 36 non-Nexis records and 1,592 Nexis records (1,628 total). The initial 386 summaries received the factual-content style correction; subsequent summaries follow the corrected instructions. All Nexis factual summaries are complete; no summaries remain pending. Public-link and independent title/publisher/date verification remain incomplete for rows marked `partial_verification`, and the existing `needs_attention` record remains flagged.

[methodology.md](methodology.md) records the method, source evidence, decisions and limitations. Its summary-style correction supersedes earlier instructions about evaluative caveats.

- `support/`: corpus inventory, original ten-record Nexis selection, non-Nexis scope, and current progress and validation.
- `scripts/`: active save and validation helpers. Run from the repository root: `python outputs/article_review_pilot/scripts/checkpoint_review.py`.

The CSV path is unchanged. Databases, source archives, reviewed source metadata and filtering decisions are outside this folderâ€™s cleanup.

## Dashboard connection

The published-page sources `docs/index.html` and `docs/news_database.html` now use full reviewed factual summaries joined by exact `source_id`. Run `python -m news_importer.review_summaries` from the repository root to refresh their embedded summaries without database access, regeneration, or filtering. The page generator also applies this overlay on future builds. Keep `reviewed_results.csv` available when generating pages.

The current filtered dashboard has 186 records; 185 match the review sheet. `src_472865dc84294b0bd125` (Waze and LA City Council Will Work Together to Reduce Growing Traffic on Residential Streets) has no reviewed row and retains its previous summary. The overview's map cards and embedded database also receive matching summaries; no records, metadata, links, labels, scores, or filter decisions are changed. Database-row summaries are displayed in full rather than clamped to two lines. The separate archive HTML page was not regenerated.

Validation compared embedded payloads before and after and confirmed that only summary values changed, with every match equal to the complete reviewed text. Targeted overlay and generated-navigation tests passed. The broader published-navigation test finds existing label differences in untouched law and crosswalk pages. Browser policy blocked a local-file preview, so visual rendering was not verified. Deployment is separate from these local page updates.
