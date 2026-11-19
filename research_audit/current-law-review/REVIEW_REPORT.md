# Current-law review and publication report

Reviewed 2026-11-18 (Pacific). **This is a verified subset, not a completed nationwide legal review.** No revised nationwide legal-gap, prevalence or policy-effectiveness conclusion is published. All original IDs have a publication disposition; most withheld sources still require individual legal verification.

## Current public collection

37 nonoverlapping legal entries: Tier 1 **1**, Tier 2 **34**, Tier 3 **2**. The public database contains no pending/draft, excluded or unverified groups. Tier and codebook counts derive from the same allowlisted dataset.

| Jurisdiction | Tier 1 | Tier 2 | Tier 3 | Total |
|---|---:|---:|---:|---:|
| California | 0 | 8 | 1 | 9 |
| Federal | 0 | 16 | 1 | 17 |
| Florida | 0 | 1 | 0 | 1 |
| Massachusetts | 0 | 1 | 0 | 1 |
| Minnesota | 0 | 1 | 0 | 1 |
| New Jersey | 1 | 0 | 0 | 1 |
| New York | 0 | 3 | 0 | 3 |
| Oregon | 0 | 1 | 0 | 1 |
| Virginia | 0 | 1 | 0 | 1 |
| Washington | 0 | 2 | 0 | 2 |
| **Total** | **1** | **34** | **2** | **37** |

Instrument types: **23 statutes**, **1 enacted public law**, **13 regulations**. All retained entries have current operative-text verification and a supported primary tier/subclass. The original commencement date is not invented when the official current page does not independently establish it.

## Source accounting and remaining review

The initial 3,455 candidate records and 189 earlier-index entries total 3,644 source rows. **41 source rows** are represented by **37 current entries**, after consolidation. **3,527 source rows are withheld pending individual verification**, and **76 are removed** as non-specific placeholders, advisory content, a superseded companion draft or a not-yet-effective act. These are source-row counts, not counts of repealed laws.

For the original 3,455 cohort alone: 11 source rows consolidate into checked current entries, one advisory section is removed, and 3,443 await individual current-law/enactment verification. No conclusion that the withheld records are invalid or irrelevant is warranted.

All 52 jurisdictions are listed in `jurisdiction_tracker.csv`. All remain Partial or Not yet searched; no jurisdiction has been certified complete. The next step is individual operative-text, commencement, amendment and applicability review of withheld records, starting with federal sources and then California under the established order. California local placeholders require identifiable enacted sections, not homepage links. District of Columbia and Tennessee have no entries in the fixed candidate cohort establishing coverage.

Ten earlier court-decision references are separately preserved in `case_law_reference_audit.csv` and withheld from the current statutory/regulatory collection pending precedential-status and applicability checks. They are outside the 3,644 instrument-source accounting.

## Material corrections and unresolved conflicts

- **AB 2015:** official chaptered text approved/filed 2026-09-14; ordinary effective date 2027-01-01 under California Constitution art. IV, § 8(c). Withheld until effective, retaining Tier 2/F3 only in the research audit.
- **New Jersey SAFER APP:** final P.L.2025, c.347 approved 2026-01-20. Section 8 effective immediately, remainder effective 2026-04-20. The enacted law is Tier 1/E1; the substituted S756 draft is not counted again. Final-law daily fine is $1,000–$5,000, with the stated waiver/reduction grounds and hospital/police-station exception.
- **HOV access:** expired low-emission exemptions are excluded from the retained § 166 scope; no continuing EV-only HOV entitlement is asserted.
- **Weight allowance conflict:** current CFR § 658.17(n) says 400 pounds for idle-reduction equipment; later 23 U.S.C. § 127(a)(12) specifies up to 550 pounds. The CFR candidate is withheld pending precise reconciliation, and the current statute’s qualifications are retained.
- **California § 22358:** the cross-referenced director notice determining operative commencement was not independently established, so the candidate remains withheld.
- **Crosswalk:** all 373 previous associations are archived. No article-to-current-provision edge has passed individual verification in this release; no article is labeled a proven legal gap. The news factual corpus is preserved without the prior unverified feasibility, precedent or authority claims.

## Website changes

The Overview has a short screening paragraph and no separate federal/Minnesota/Ohio/Washington examples. Only the three current-law tiers appear, separated by gold, blue and neutral rules with explicit labels. The searchable database, jurisdiction/category tables, downloads and crosswalk current-law total share one data source. Stale 3,455-candidate totals, earlier-index counts, court-case cards and legacy legal-gap rankings no longer define the current public collection. News-table links show crosswalk review status rather than unverified instrument codes.

## Deliverables

- `docs/data/current_law_database.json` and `.csv`: checked public entries.
- `record_disposition_audit.csv`: every original instrument-source ID and its reasoned publication disposition.
- `removal_and_verification_log.csv`: the complete list of source rows not approved for public-law inclusion, with next steps.
- `reviewed_official_texts.json`: official text captures, currency and fingerprints.
- `source_access_log.csv`: all 3,316 distinct original URL attempts, distinct from legal verification.
- `jurisdiction_tracker.csv`, `legacy_crosswalk_audit.csv`, `case_law_reference_audit.csv`, `review_summary.json`: coverage, withdrawn associations, separate case references and reconciled counts.
