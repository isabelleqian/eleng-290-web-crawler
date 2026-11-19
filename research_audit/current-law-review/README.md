# Current-law publication review — 2026-11-18

The public law collection contains only the individually approved current instruments in `docs/data/current_law_database.json`. The 3,455 candidate source records and 189 supplementary earlier-index records are separate audit populations, not 3,644 unique laws.

**Review is not complete nationwide.** Every original ID has a publication disposition, but most withheld records still need substantive current-law verification. Withholding does not mean repeal, invalidity or irrelevance. HTTP success, retrieved text, an older layer assignment and an official-looking URL are not legal verification. No withheld record is silently assigned to Tier 3.

## Files

- `record_disposition_audit.csv`: all 3,644 input IDs, original collection and reference, disposition, reason and next step.
- `removal_and_verification_log.csv`: sources not approved as current public entries, including unverified proposals, non-specific placeholders, future commencement and evidence conflicts.
- `source_access_log.csv`: access attempts to 3,316 distinct original URLs; access/challenge pages do not count as operative text.
- `reviewed_official_texts.json`: the retained instruments’ official text captures, currency and fingerprints, plus AB 2015 withholding evidence.
- `jurisdiction_tracker.csv`: federal, all 50 states and DC; no uncompleted jurisdiction is marked Complete.
- `legacy_crosswalk_audit.csv`: all 373 previous news-law associations, preserved separately and withdrawn from current legal conclusions.
- `review_summary.json`: reconciled public counts and separate source-accounting counts.

Original unverified source datasets remain recoverable in repository history at commit `81321a186c552c520a1c0584595c7da245df3f51` (`docs/data/cohort_3455_analysis.json` and the prior law/crosswalk HTML). They are not the current verified database and must not be reimported automatically. The publication allowlist is explicit; reinstatement requires a recorded operative-text, currency, applicability and codebook decision.

## Material corrections

AB 2015 remains Tier 2/F3 in research scope but is not yet effective on this review date; ordinary commencement is 2027-01-01 under California Constitution art. IV, § 8(c). New Jersey A3036 is represented by the final P.L.2025, c.347, not an amended bill reprint or a separately counted S756 draft. Expired HOV low-emission exceptions are excluded from the retained § 166 scope. CFR § 658.17 is withheld because its 400-pound idle-reduction text needs reconciliation with the later 550-pound statutory ceiling. A current compilation can contain expired subparts; presence on a page alone is insufficient.

Historical commencement dates not independently re-established are identified as such in retained metadata; no historical date is invented. Retained status rests on the checked current official operative compilation, with its stated currency. eCFR’s latest available edition was 2026-11-17, and the U.S. Code’s was current through Public Law 119-142 (2026-11-10). These publication lags limit the as-of claim.

No nationwide prevalence, legal-gap count, causal policy effectiveness or validated article-to-provision relationship is inferred from this selective collection. Existing news and policy corpora are distinct research collections.

Additional evidence: `reviewed_source_register.csv` lists every retained entry’s source and currency; `supplementary_source_access.json` records the official API/current-code fetches. Current New Jersey §§ 39:4-215.4–215.5 were also opened in the official compilation through P.L.2026, c.70 and J.R.2; those browser snapshots are in `reviewed_official_texts.json`.
