#!/usr/bin/env python3
"""Run the research analysis pass 1, validate passages, and generate exports."""

from pathlib import Path
import sys

from news_importer.analysis import (
    build_all_analyses,
    build_pass1_analyses,
    export_analysis_csv,
    export_analysis_json,
    export_inventory_csv,
    inventory_archived_sources,
)


def main() -> None:
    base_dir = Path(__file__).resolve().parent
    db_path = base_dir / "data" / "news.sqlite"
    archive_base = base_dir / "data" / "archive"
    exports_dir = base_dir / "data" / "exports"

    print("=" * 70)
    print("STEP 1: INVENTORYING ARCHIVED SOURCES & QUALITY FLAGS")
    print("=" * 70)
    inventory = inventory_archived_sources(db_path, archive_base)
    inv_csv_path = exports_dir / "archived_sources_inventory.csv"
    export_inventory_csv(inventory, inv_csv_path)
    print(f"Total fetch attempts inventoried: {len(inventory)}")
    
    # Outcomes tally
    outcomes: dict[str, int] = {}
    flag_tally: dict[str, int] = {}
    for item in inventory:
        out = item["outcome"]
        outcomes[out] = outcomes.get(out, 0) + 1
        for code in item["quality_flag_codes"]:
            flag_tally[code] = flag_tally.get(code, 0) + 1
    
    print("\nAttempt Outcomes:")
    for out, cnt in sorted(outcomes.items()):
        print(f"  - {out}: {cnt}")
        
    print("\nQuality Flag Counts:")
    for code, cnt in sorted(flag_tally.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {code}: {cnt}")
    print(f"\nInventory exported to: {inv_csv_path}")

    print("\n" + "=" * 70)
    print("STEP 2: EXECUTING RESEARCH ANALYSIS PASS 1 (6 CORE SOURCES)")
    print("=" * 70)
    p1_entries = build_pass1_analyses(db_path, base_dir)

    all_verified = True
    for i, e in enumerate(p1_entries, 1):
        print(f"\n--- Pass 1 Source {i}: {e.source_id} ---")
        print(f"Title: {e.title}")
        print(f"Publisher: {e.publisher} | Pub Date: {e.publication_date}")
        print(f"Jurisdiction: {e.actual_jurisdiction}")
        print(f"Governance: {e.governing_level} | Authority: {e.authority_names}")
        print(f"Target: [{e.target_location_type}] {e.target_location}")
        print(f"Type: {e.source_type} | Category: {e.category}")
        for idx, p in enumerate(e.supporting_passages, 1):
            status_str = "VERIFIED" if p.verified else "FAILED"
            if not p.verified:
                all_verified = False
            print(f"  [{status_str}] Passage {idx} ({p.verification_note}): \"{p.verbatim_text[:80]}...\"")

    json_path = exports_dir / "research_analysis_pass1.json"
    csv_path = exports_dir / "research_analysis_pass1.csv"
    export_analysis_json(p1_entries, json_path)
    export_analysis_csv(p1_entries, csv_path)
    print(f"\nExported Pass 1 JSON: {json_path}")
    print(f"Exported Pass 1 CSV:  {csv_path}")

    print("\n" + "=" * 70)
    print("STEP 3: EXECUTING FULL RESEARCH ANALYSIS (ALL 43 RETRIEVED SOURCES)")
    print("=" * 70)
    all_entries = build_all_analyses(db_path, base_dir)
    print(f"Total retrieved sources analyzed: {len(all_entries)}")

    unverified_count = 0
    cat_tally: dict[str, int] = {}
    gov_tally: dict[str, int] = {}
    loc_type_tally: dict[str, int] = {}
    for e in all_entries:
        cat_tally[e.category] = cat_tally.get(e.category, 0) + 1
        gov_tally[e.governing_level] = gov_tally.get(e.governing_level, 0) + 1
        loc_type_tally[e.target_location_type] = loc_type_tally.get(e.target_location_type, 0) + 1
        for p in e.supporting_passages:
            if not p.verified:
                unverified_count += 1
                all_verified = False
                print(f"  FAILED in {e.source_id}: {p.claim_topic}")

    print("\nCategory Distribution:")
    for cat, cnt in sorted(cat_tally.items()):
        print(f"  - {cat}: {cnt}")

    print("\nGoverning Level Distribution:")
    for lvl, cnt in sorted(gov_tally.items()):
        print(f"  - {lvl}: {cnt}")

    print("\nTarget Location Type Distribution:")
    for tlt, cnt in sorted(loc_type_tally.items()):
        print(f"  - {tlt}: {cnt}")

    all_json_path = exports_dir / "research_analysis_all_sources.json"
    all_csv_path = exports_dir / "research_analysis_all_sources.csv"
    export_analysis_json(all_entries, all_json_path)
    export_analysis_csv(all_entries, all_csv_path)
    print(f"\nExported All Sources JSON: {all_json_path}")
    print(f"Exported All Sources CSV:  {all_csv_path}")

    if all_verified and unverified_count == 0:
        print("\nAll supporting evidence passages verified verbatim across all 43 sources!")
    else:
        print(f"\nWARNING: {unverified_count} supporting passages could not be verified.")
        sys.exit(1)


if __name__ == "__main__":
    main()

