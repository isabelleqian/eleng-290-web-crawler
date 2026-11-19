# Fixed 3,455-record content analysis

As of November 18, 2026. Professional review draft.

This release analyzes exactly the 3,455 stable source IDs in the pre-existing content-review cohort. It does not add the earlier 189-instrument index or its 171 Layer 2 entries. Source records are not a deduplicated count of enacted laws. Separate sections of the same law, companion bills, historical proposals, repeated captures and district-specific template provisions can each have a source ID. Identical retrieved bill texts are flagged, not silently removed from the fixed base.

## Accounting

| Outcome | Source records |
|---|---:|
| Layer 1 | 5 |
| Layer 2 | 2,936 |
| Layer 3 | 52 |
| Excluded | 436 |
| Pending text/source conflict | 26 |
| Total | 3,455 |

All 3,455 IDs receive a recorded content-analysis outcome. This is not a claim that every record has a defensible layer or that individual current-law verification is complete. Excluded and insufficient-evidence candidates are not forced into Layer 3.

## Framework

Layers 1 and 2 use the user's AB 2015 research scope. Layer 1 requires an express routing-app/provider right, obligation, exemption or liability. Layer 2 principally regulates another actor and indirectly affects routing through road access, traffic intervention, pricing, road data or planning. Layer 3 covers other applicable law outside those two groups. AB 2015's Caltrans study/report duties remain Layer 2 F3; the earlier index is supplementary, outside this fixed denominator.

## Method and evidence

Archived provision payloads were analyzed with category passage rules and contextual overrides. 441 decisions have explicit contextual overrides/exclusion rationales; other assignments remain automated text-assisted drafts. The process retrieved 163 state-bill texts and 62 federal-bill texts. PA HB2635 PN3601 was additionally opened through the research browser for its classification clause. Headings, annotations, truncated sections and contaminated register extracts are flagged as inadequate text. Source/status metadata is retained; retrieval is not proof of enactment or current effect.

Five provider-subject proposals are supported within this cohort: CT HB5071, CT HB6709, MA HD4949, HI SB2839 and HI HB2025. The introduced/retrieved text, not a claim of current pending status, supplies their Layer 1 basis. CT and MA local-road routing prohibitions use E1; the Hawaii police-location-alert proposals use F6, with proposed injunction/penalty notes. The Hawaii proposal fine amount is blank and is not fabricated.

The category codebook is independent of layer. Exactly one primary subclass is assigned where supported. 54 assigned records have no defensible exact intervention subclass, principally general privacy/driver-conduct laws plus broad traffic-calming authority. They are shown explicitly, not assigned an invented category. Omnibus bills are one source record each; their primary code describes the identified research-relevant operative anchor, not every provision in the instrument. Supporting titles, definitions, purpose clauses and cross-references do not create independent app duties.

## Limits and files

The crawl cohort covers federal and 49-state sources; California and DC are not supplied by this cohort. Earlier California/index examples remain separate. This is not proof of exhaustive federal or 50-state coverage. No causal policy-effectiveness or app-behavior finding is inferred from law counts. No new news-law match is asserted solely from sharing a code.

- cohort_3455_analysis.json / .csv: the same 3,455 records and classifications used on the webpage.
- cohort_3455_unverified.csv: the 26 content-blocked records and next steps. Every assigned record also retains legal-status/currency verification qualifications.
- cohort_3455_excluded.csv: all 436 exclusions with reasons.
- cohort_3455_jurisdiction_counts.csv: jurisdiction/layer/outcome accounting.
- cohort_3455_codebook_counts.csv: all 35 codebook subclasses, including zero-count subclasses and the no-exact-subclass group.
- cohort_3455_summary.json: current counts; all row/outcome totals must reconcile to 3,455.

Current status, amendments, official citations, effective dates, liability, penalties and cross-references still require jurisdiction-by-jurisdiction official verification. Downloaded text alone is not labeled a completed legal review.
