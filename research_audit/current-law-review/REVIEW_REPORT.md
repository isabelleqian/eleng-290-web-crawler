# Reconciliation, codebook restoration and continued legal review

The original four crawl CSVs contain **3,484 source records**, not 3,544: 2,868 state provisions, 380 federal provisions, 170 state bills and 66 federal bills. The later 3,455-record review cohort removed 15 already-indexed matches, four duplicates and ten earlier scope exclusions. The original export has records for 48 states plus federal sources; California was in a separate earlier index, and this export does not establish Tennessee or DC coverage. The unexplained difference from the recalled 3,544 count is 60; no records have been fabricated to fill it. See `crawl_reconciliation.json`.

The full six-category codebook, with all 35 original subclasses, is restored on the Overview. Defined subclasses remain visible even if their checked-entry count is zero.

**The nationwide legal review remains incomplete.** Four more current operative provisions were individually reviewed and reinstated: Alaska 13 AAC 02.080, Arizona A.R.S. § 28-728, Ohio Admin. Code 5537-2-05 and Pennsylvania 67 Pa. Code § 212.113. Their original crawl IDs remain traceable in the audit.

## Current checked collection

| Jurisdiction | Tier 1 | Tier 2 | Tier 3 | Total |
|---|---:|---:|---:|---:|
| Alaska | 0 | 1 | 0 | 1 |
| Arizona | 0 | 1 | 0 | 1 |
| California | 0 | 8 | 1 | 9 |
| Federal | 0 | 16 | 1 | 17 |
| Florida | 0 | 1 | 0 | 1 |
| Massachusetts | 0 | 1 | 0 | 1 |
| Minnesota | 0 | 1 | 0 | 1 |
| New Jersey | 1 | 0 | 0 | 1 |
| New York | 0 | 3 | 0 | 3 |
| Ohio | 0 | 1 | 0 | 1 |
| Oregon | 0 | 1 | 0 | 1 |
| Pennsylvania | 0 | 1 | 0 | 1 |
| Virginia | 0 | 1 | 0 | 1 |
| Washington | 0 | 2 | 0 | 2 |
| **Total** | **1** | **38** | **2** | **41** |

Types: 24 statutes, one enacted public law, 16 regulations. The 3,644 instrument-source rows remain separately accounted for: 45 consolidate into 41 current entries; 3,523 remain withheld for individual verification; 76 have explicit removal reasons. Withholding is not a finding of repeal or irrelevance. The original 3,455 cohort still has 3,439 withheld rows; reinstatement is continuing, not finished. All incomplete jurisdictions and next steps remain in `jurisdiction_tracker.csv`.

## Crosswalk preservation

At the user’s explicit instruction, the News–Law Crosswalk and related news-table links are restored exactly to their pre-cleanup content and functionality at commit 81321a1. Only the editorial color styling is retained. Its historical associations and counts are **not** being revised or represented as newly verified in this legal-review pass. The previous cleanup’s withdrawal of its content has been reversed. This instruction takes precedence over earlier requests to reconcile that page.

## Remaining issues

AB 2015 is not yet effective until 2027-01-01 and remains outside the current-law entries. The CFR 400-pound/statutory 550-pound idle-reduction discrepancy remains withheld pending reconciliation. California § 22358’s commencement qualification remains unresolved. Most other candidates still require individual official-current-text, status, scope and codebook review; no completed nationwide review or national prevalence conclusion is claimed.
