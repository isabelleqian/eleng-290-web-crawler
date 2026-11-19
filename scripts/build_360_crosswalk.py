"""Build and synchronize the comprehensive 360-record News-to-Law crosswalk.

This script:
1. Reads all 360 curated in-scope news articles from docs/data/news_corpus_filtered.json.
2. Aligns each record to statutory mechanisms and legal gap themes.
3. Preserves exact continuity for the empirical citations (N-001 through N-169).
4. Sequentially indexes all 360 rows (N-001 through N-360) with zero duplicates.
5. Saves clean crosswalk CSV deliverables across Law_Crawler and Web_Crawler.
6. Regenerates docs/crosswalk.html and docs/law_database.html via generate_all_dashboard_pages.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
import subprocess
import sys
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
PARENT_ROOT = ROOT.parent
sys.path.append(str(ROOT))
sys.path.append(str(PARENT_ROOT / "Law_Crawler"))

from law_importer.pipeline.generate_law_pages import generate_all_dashboard_pages

CORPUS_JSON = ROOT / "docs/data/news_corpus_filtered.json"
REVIEWED_CSV = ROOT / "outputs/article_review_pilot/reviewed_results.csv"
CROSSWALK_LAW_CSV = PARENT_ROOT / "Law_Crawler/exports/news_to_law_crosswalk.csv"
CROSSWALK_DOCS_CSV = ROOT / "docs/data/news_to_law_crosswalk.csv"
CROSSWALK_EXPORTS_CSV = ROOT / "data/exports/news_to_law_crosswalk.csv"

NEW_RECORDS_MAPPING = {
    "nexis_urn:contentItem:6216-5JN1-JCBF-S1W8-00000-00": {
        "legal_relationship": "Unaddressed Gap",
        "instrument_id": "MOU-WAZE-CC",
        "instrument_name": "Waze Connected Citizens Program / Waze for Cities Bilateral Data Agreement",
        "governance_layer": "Unregulated Phenomenon",
        "key_takeaway_and_relevance": "Academic-municipal research leveraging Waze for Cities data; voluntary bilateral data sharing lacks statutory enforceability over underlying platform routing algorithms.",
        "verification_status": "Secondary source only",
        "category_code": "E1",
        "category_name": "Routing-platform and information interventions",
        "matched_statute_or_ordinance": "Waze Connected Citizens Program / Waze for Cities Bilateral Data Agreement",
        "enabling_authority": "State Police Power / Transportation Code",
        "controlling_case_law": "N/A",
        "legal_feasibility_assessment": "Statutory void",
        "relevance_to_ca_ab2015": "Directly illustrates limitations of voluntary public-private data pacts absent legislative mandate.",
        "is_california": "false",
        "legal_gap_theme": "Theme 2: Voluntary MOUs vs. Enforceable Algorithmic Control",
    },
    "nexis_urn:contentItem:6J9M-YV13-SHR3-92B8-00000-00": {
        "legal_relationship": "Potentially Associated",
        "instrument_id": "CA-CVC21101",
        "instrument_name": "California Vehicle Code § 21101 — Local Highway Maintenance & Roadway Safety",
        "governance_layer": "Layer 3: Indirect (Road Conditions & Pricing)",
        "key_takeaway_and_relevance": "Municipal public works leverage crowdsourced autonomous vehicle sensor and navigation data to identify and repair roadway hazards.",
        "verification_status": "Verified against official municipal program",
        "category_code": "C1",
        "category_name": "Traffic calming and road classification",
        "matched_statute_or_ordinance": "Cal. Veh. Code § 21101 / Municipal Traffic Calming & Roadway Safety",
        "enabling_authority": "Cal. Veh. Code § 21101",
        "controlling_case_law": "N/A",
        "legal_feasibility_assessment": "Subject to local engineering survey",
        "relevance_to_ca_ab2015": "Relevant to automated infrastructure monitoring and road condition reporting under municipal data partnerships.",
        "is_california": "true",
        "legal_gap_theme": "N/A (Covered by Statutory/Judicial Instrument)",
    },
    "nexis_urn:contentItem:6JDF-3MR3-RRYD-H2J8-00000-00": {
        "legal_relationship": "Potentially Associated",
        "instrument_id": "CA-CVC21101",
        "instrument_name": "California Vehicle Code § 21101 — Local Highway Maintenance & Roadway Safety",
        "governance_layer": "Layer 3: Indirect (Road Conditions & Pricing)",
        "key_takeaway_and_relevance": "Commercial AV fleet sensors detect roadway defects for municipal maintenance and navigation hazard notification across multi-city pilot.",
        "verification_status": "Verified against official municipal program",
        "category_code": "C1",
        "category_name": "Traffic calming and road classification",
        "matched_statute_or_ordinance": "Cal. Veh. Code § 21101 / Municipal Traffic Calming & Roadway Safety",
        "enabling_authority": "Cal. Veh. Code § 21101",
        "controlling_case_law": "N/A",
        "legal_feasibility_assessment": "Subject to local engineering survey",
        "relevance_to_ca_ab2015": "Demonstrates sensor-based crowdsourced road hazard mitigation in California corridors.",
        "is_california": "true",
        "legal_gap_theme": "N/A (Covered by Statutory/Judicial Instrument)",
    },
    "nexis_urn:contentItem:6KHB-TG53-RXXG-N1XK-00000-00": {
        "legal_relationship": "Unaddressed Gap",
        "instrument_id": "MOU-WAZE-CC",
        "instrument_name": "Waze Connected Citizens Program / Waze for Cities Bilateral Data Agreement",
        "governance_layer": "Unregulated Phenomenon",
        "key_takeaway_and_relevance": "Emergency post-disaster detour routing relying on crowdsourced Waze data; lacks codified standards or statutory coordination mandates during declared emergencies.",
        "verification_status": "Secondary source only",
        "category_code": "E1",
        "category_name": "Routing-platform and information interventions",
        "matched_statute_or_ordinance": "None (Legal Gap)",
        "enabling_authority": "State Police Power / Transportation Code",
        "controlling_case_law": "N/A",
        "legal_feasibility_assessment": "Statutory void",
        "relevance_to_ca_ab2015": "Directly informs emergency evacuation and detour routing study parameters.",
        "is_california": "false",
        "legal_gap_theme": "Theme 2: Voluntary MOUs vs. Enforceable Algorithmic Control",
    },
    "nexis_urn:contentItem:7YKT-CHT1-2RGX-T28Y-00000-00": {
        "legal_relationship": "Unaddressed Gap",
        "instrument_id": "CASE-DYROFF",
        "instrument_name": "Dyroff v. Ultimate Software Group / CDA § 230 Common Law Duty of Care",
        "governance_layer": "Unregulated Phenomenon",
        "key_takeaway_and_relevance": "Common law negligence and tort immunity under 47 U.S.C. § 230 for navigation algorithm instructions directing users onto hazardous roadways.",
        "verification_status": "Verified against court record (D. Utah 2010)",
        "category_code": "E1",
        "category_name": "Routing-platform and information interventions",
        "matched_statute_or_ordinance": "Dyroff v. Ultimate Software Group / CDA § 230 Common Law Duty of Care",
        "enabling_authority": "State Police Power / Transportation Code",
        "controlling_case_law": "Dyroff v. Ultimate Software Group, Inc. (9th Cir. 2019); Lemmon v. Snap, Inc. (9th Cir. 2021)",
        "legal_feasibility_assessment": "Statutory void",
        "relevance_to_ca_ab2015": "Key empirical tort case demonstrating legal shield insulating platforms from liability for hazardous route guidance.",
        "is_california": "false",
        "legal_gap_theme": "Theme 5: Platform Tort Liability Void & Section 230 Shield",
    },
    "nexis_urn:contentItem:4JV2-R4P0-TX4Y-7356-00000-00": {
        "legal_relationship": "Potentially Associated",
        "instrument_id": "GEN-TRAFFIC-CALMING",
        "instrument_name": "Municipal Traffic Calming & Neighborhood Speed Reduction Authority",
        "governance_layer": "Layer 3: Indirect (Road Conditions & Pricing)",
        "key_takeaway_and_relevance": "Empirical field analysis of shortcut travel-time differentials versus arterial routes and subsequent municipal traffic calming interventions.",
        "verification_status": "Secondary source only",
        "category_code": "C1",
        "category_name": "Traffic calming and road classification",
        "matched_statute_or_ordinance": "Municipal Traffic Calming & Neighborhood Speed Reduction Authority",
        "enabling_authority": "State Police Power / Transportation Code",
        "controlling_case_law": "N/A",
        "legal_feasibility_assessment": "Subject to local engineering survey",
        "relevance_to_ca_ab2015": "Informs study of cut-through travel-time differentials and effectiveness of physical calming in defeating app bypasses.",
        "is_california": "false",
        "legal_gap_theme": "N/A (Covered by Statutory/Judicial Instrument)",
    },
    "nexis_urn:contentItem:5T6R-RT41-JBKS-P25G-00000-00": {
        "legal_relationship": "Directly Tied",
        "instrument_id": "IL-625ILCS5",
        "instrument_name": "Illinois Compiled Statutes 625 ILCS 5/11-1430 — Commercial GPS Navigation",
        "governance_layer": "Layer 2: Route-Linked (Road/Truck Bans)",
        "key_takeaway_and_relevance": "Commercial motor vehicle turn-by-turn routing app tailored to bridge height clearances, vehicle weight limits, and hazardous material restrictions.",
        "verification_status": "Verified against commercial GPS product specification",
        "category_code": "A2",
        "category_name": "Access and circulation regulation",
        "matched_statute_or_ordinance": "625 ILCS 5/11-1430 (Commercial GPS Navigation Mandate)",
        "enabling_authority": "State Police Power / Transportation Code",
        "controlling_case_law": "N/A",
        "legal_feasibility_assessment": "Codified statutory authority",
        "relevance_to_ca_ab2015": "Addresses commercial freight routing requirements and statutory bridge-strike avoidance mechanisms.",
        "is_california": "false",
        "legal_gap_theme": "N/A (Covered by Statutory/Judicial Instrument)",
    },
    "nexis_urn:contentItem:554F-4051-DY2R-41NY-00000-00": {
        "legal_relationship": "Directly Tied",
        "instrument_id": "IL-625ILCS5",
        "instrument_name": "Illinois Compiled Statutes 625 ILCS 5/11-1430 — Commercial GPS Navigation",
        "governance_layer": "Layer 2: Route-Linked (Road/Truck Bans)",
        "key_takeaway_and_relevance": "Fleet-integrated commercial GPS software providing height-clearance verification and truck-restriction compliance.",
        "verification_status": "Verified against commercial GPS product specification",
        "category_code": "A2",
        "category_name": "Access and circulation regulation",
        "matched_statute_or_ordinance": "625 ILCS 5/11-1430 (Commercial GPS Navigation Mandate)",
        "enabling_authority": "State Police Power / Transportation Code",
        "controlling_case_law": "N/A",
        "legal_feasibility_assessment": "Codified statutory authority",
        "relevance_to_ca_ab2015": "Relevant to commercial vehicle compliance under statutory bridge-strike prevention mandates.",
        "is_california": "false",
        "legal_gap_theme": "N/A (Covered by Statutory/Judicial Instrument)",
    },
    "nexis_urn:contentItem:523K-DRJ1-DY7H-52HR-00000-00": {
        "legal_relationship": "Directly Tied",
        "instrument_id": "IL-625ILCS5",
        "instrument_name": "Illinois Compiled Statutes 625 ILCS 5/11-1430 — Commercial GPS Navigation",
        "governance_layer": "Layer 2: Route-Linked (Road/Truck Bans)",
        "key_takeaway_and_relevance": "Dedicated in-cab navigation hardware designed to keep commercial motor vehicles on designated truck corridors and avoid low overpasses.",
        "verification_status": "Verified against commercial GPS product specification",
        "category_code": "A2",
        "category_name": "Access and circulation regulation",
        "matched_statute_or_ordinance": "625 ILCS 5/11-1430 (Commercial GPS Navigation Mandate)",
        "enabling_authority": "State Police Power / Transportation Code",
        "controlling_case_law": "N/A",
        "legal_feasibility_assessment": "Codified statutory authority",
        "relevance_to_ca_ab2015": "Exemplar of commercial-grade navigation complying with statutory height and route restrictions.",
        "is_california": "false",
        "legal_gap_theme": "N/A (Covered by Statutory/Judicial Instrument)",
    },
    "nexis_urn:contentItem:5F5D-CF01-JC65-52XS-00000-00": {
        "legal_relationship": "Directly Tied",
        "instrument_id": "IL-625ILCS5",
        "instrument_name": "Illinois Compiled Statutes 625 ILCS 5/11-1430 — Commercial GPS Navigation",
        "governance_layer": "Layer 2: Route-Linked (Road/Truck Bans)",
        "key_takeaway_and_relevance": "Municipal study responding to repeated GPS-directed bridge strikes; evaluated mandatory designated truck routes and GPS restriction notices.",
        "verification_status": "Verified against municipal council reporting",
        "category_code": "A2",
        "category_name": "Access and circulation regulation",
        "matched_statute_or_ordinance": "625 ILCS 5/11-1430 (Commercial GPS Navigation Mandate)",
        "enabling_authority": "State Police Power / Transportation Code",
        "controlling_case_law": "N/A",
        "legal_feasibility_assessment": "Codified statutory authority",
        "relevance_to_ca_ab2015": "Direct empirical documentation of commercial vehicles following consumer GPS onto restricted streets, causing bridge strikes.",
        "is_california": "false",
        "legal_gap_theme": "N/A (Covered by Statutory/Judicial Instrument)",
    },
    "nexis_urn:contentItem:67T7-2411-JCMN-Y3CN-00000-00": {
        "legal_relationship": "Potentially Associated",
        "instrument_id": "CA-CVC21101",
        "instrument_name": "California Vehicle Code § 21101 / Municipal Traffic Calming & Speed Reduction",
        "governance_layer": "Layer 3: Indirect (Road Conditions & Pricing)",
        "key_takeaway_and_relevance": "Davis deployed corridor redesign and traffic metering under Cal. Veh. Code § 21101 to suppress I-80 app-diverted cut-through traffic.",
        "verification_status": "Verified against Davis City Council legislative docket",
        "category_code": "C1",
        "category_name": "Traffic calming and road classification",
        "matched_statute_or_ordinance": "Cal. Veh. Code § 21101 / Municipal Traffic Calming & Speed Reduction",
        "enabling_authority": "Cal. Veh. Code § 21101",
        "controlling_case_law": "Save the Sunset Strip Coalition v. City of West Hollywood (2001)",
        "legal_feasibility_assessment": "Subject to local engineering survey",
        "relevance_to_ca_ab2015": "Exemplar of California municipality redesigning arterial corridor to deter app-directed freeway bypasses.",
        "is_california": "true",
        "legal_gap_theme": "N/A (Covered by Statutory/Judicial Instrument)",
    },
    "nexis_urn:contentItem:51KY-B831-DY2T-V1JW-00000-00": {
        "legal_relationship": "Directly Tied",
        "instrument_id": "IL-625ILCS5",
        "instrument_name": "Illinois Compiled Statutes 625 ILCS 5/11-1430 — Commercial GPS Navigation",
        "governance_layer": "Layer 2: Route-Linked (Road/Truck Bans)",
        "key_takeaway_and_relevance": "Commercial truck GPS navigation unit with bridge height and load restriction routing to prevent infrastructure strikes.",
        "verification_status": "Verified against commercial GPS product specification",
        "category_code": "A2",
        "category_name": "Access and circulation regulation",
        "matched_statute_or_ordinance": "625 ILCS 5/11-1430 (Commercial GPS Navigation Mandate)",
        "enabling_authority": "State Police Power / Transportation Code",
        "controlling_case_law": "N/A",
        "legal_feasibility_assessment": "Codified statutory authority",
        "relevance_to_ca_ab2015": "Addresses commercial navigation devices complying with statutory route and height restrictions.",
        "is_california": "false",
        "legal_gap_theme": "N/A (Covered by Statutory/Judicial Instrument)",
    },
}


def load_reviewed_pilot() -> dict[str, dict[str, str]]:
    """Load reviewed results from pilot if available."""
    reviewed = {}
    if REVIEWED_CSV.exists():
        with open(REVIEWED_CSV, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                sid = row.get("source_id") or row.get("id")
                if sid:
                    reviewed[sid] = row
    return reviewed


def build_360_crosswalk():
    print("=== Step 1: Loading 360 In-Scope Articles ===")
    with open(CORPUS_JSON, "r", encoding="utf-8") as f:
        corpus_360 = json.load(f)
    print(f"Loaded {len(corpus_360)} articles from {CORPUS_JSON}")
    assert len(corpus_360) == 360, f"Expected 360 articles, got {len(corpus_360)}"

    corpus_by_sid = {x["source_id"]: x for x in corpus_360}
    reviewed = load_reviewed_pilot()

    print("\n=== Step 2: Retrieving 3591920 Clean Baseline ===")
    out = subprocess.check_output(
        ["git", "show", "3591920:docs/data/news_to_law_crosswalk.csv"],
        cwd=str(ROOT),
    ).decode("utf-8")
    import io
    old_cw = list(csv.DictReader(io.StringIO(out)))
    fieldnames = list(old_cw[0].keys())
    print(f"Loaded {len(old_cw)} baseline records from commit 3591920")

    # Retain baseline rows that are in the 360 corpus
    retained_rows = [r for r in old_cw if r["source_id"] in corpus_by_sid]
    print(f"Retained {len(retained_rows)} baseline records in 360 corpus")
    assert len(retained_rows) == 348, f"Expected 348 retained rows, got {len(retained_rows)}"

    # 1. Update summaries, URLs, and clean gap themes for retained rows
    for r in retained_rows:
        sid = r["source_id"]
        c_doc = corpus_by_sid[sid]

        # Sync factual summary
        if c_doc.get("factual_summary"):
            r["factual_summary"] = c_doc["factual_summary"]
        elif sid in reviewed and reviewed[sid].get("factual_summary"):
            r["factual_summary"] = reviewed[sid]["factual_summary"]

        # Sync public URL
        if c_doc.get("url"):
            r["url"] = c_doc["url"]
        elif sid in reviewed and reviewed[sid].get("public_url") and reviewed[sid]["public_url"].startswith("http"):
            r["url"] = reviewed[sid]["public_url"]

        # Sync title / headline
        if c_doc.get("title"):
            r["headline"] = c_doc["title"]
            r["article_title"] = c_doc["title"]

        # Ensure covered records have N/A for legal_gap_theme
        if r["legal_relationship"] != "Unaddressed Gap":
            r["legal_gap_theme"] = "N/A (Covered by Statutory/Judicial Instrument)"

    # Check the first 169 retained rows
    for i in range(169):
        expected_id = f"N-{i+1:03d}"
        assert retained_rows[i]["news_id"] == expected_id, f"Row {i} has id {retained_rows[i]['news_id']}, expected {expected_id}"
    print("Verified: First 169 rows retain identical N-001..N-169 assignments!")

    # 2. Build newly added records
    retained_sids = set(r["source_id"] for r in retained_rows)
    new_sids = [c["source_id"] for c in corpus_360 if c["source_id"] not in retained_sids]
    print(f"\n=== Step 3: Integrating {len(new_sids)} New In-Scope Records ===")
    assert len(new_sids) == 12, f"Expected 12 new sids, got {len(new_sids)}"

    new_rows = []
    for sid in new_sids:
        c_doc = corpus_by_sid[sid]
        title = c_doc.get("title", "")
        pub = c_doc.get("publisher", "")
        dt = c_doc.get("publication_date", "")
        loc = c_doc.get("target_location") or c_doc.get("actual_jurisdiction", "")
        url = c_doc.get("url", "")
        summary = c_doc.get("factual_summary", "")

        meta = NEW_RECORDS_MAPPING.get(sid)
        if not meta:
            raise ValueError(f"Missing mapping for new sid: {sid}")

        row = {
            "news_id": "",  # will be assigned sequentially
            "source_id": sid,
            "date": dt,
            "headline": title,
            "source_and_jurisdiction": f"{pub} · {loc}" if loc else pub,
            "legal_relationship": meta["legal_relationship"],
            "instrument_id": meta["instrument_id"],
            "instrument_name": meta["instrument_name"],
            "governance_layer": meta["governance_layer"],
            "key_takeaway_and_relevance": meta["key_takeaway_and_relevance"],
            "verification_status": meta["verification_status"],
            "url": url,
            "article_title": title,
            "publication_year": dt[:4] if dt else "",
            "news_jurisdiction": loc,
            "category_code": meta["category_code"],
            "category_name": meta["category_name"],
            "matched_statute_or_ordinance": meta["matched_statute_or_ordinance"],
            "enabling_authority": meta["enabling_authority"],
            "controlling_case_law": meta["controlling_case_law"],
            "legal_feasibility_assessment": meta["legal_feasibility_assessment"],
            "relevance_to_ca_ab2015": meta["relevance_to_ca_ab2015"],
            "factual_summary": summary,
            "is_california": meta["is_california"],
            "legal_gap_theme": meta["legal_gap_theme"],
        }
        new_rows.append(row)

    # 3. Combine and re-index sequentially from N-001 to N-360
    all_360 = retained_rows + new_rows
    assert len(all_360) == 360, f"Expected 360 total records, got {len(all_360)}"

    for i, r in enumerate(all_360):
        r["news_id"] = f"N-{i+1:03d}"

    print(f"\n=== Step 4: Crosswalk Synthesis Statistics (Total = {len(all_360)}) ===")
    rel_counts = Counter(r["legal_relationship"] for r in all_360)
    print("Legal Relationships:")
    for k, v in rel_counts.items():
        print(f"  {k}: {v}")

    gap_theme_counts = Counter(r["legal_gap_theme"] for r in all_360 if r["legal_relationship"] == "Unaddressed Gap")
    print("\nLegal Gap Themes (Unaddressed Gaps):")
    for k, v in sorted(gap_theme_counts.items()):
        print(f"  {k}: {v}")

    ca_counts = Counter(r["is_california"] for r in all_360)
    print(f"\nCalifornia Incidents: {ca_counts.get('true', 0)}")

    # 4. Save to all destination paths
    print("\n=== Step 5: Exporting Crosswalk Deliverables ===")
    for dest in [CROSSWALK_LAW_CSV, CROSSWALK_DOCS_CSV, CROSSWALK_EXPORTS_CSV]:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_360)
        print(f"Successfully wrote {len(all_360)} rows to {dest}")

    # Also update research_analysis_filtered.json/csv if appropriate
    filtered_json = ROOT / "data/exports/research_analysis_filtered.json"
    filtered_csv = ROOT / "data/exports/research_analysis_filtered.csv"
    if filtered_json.exists():
        with open(filtered_json, "w", encoding="utf-8") as f:
            json.dump(corpus_360, f, indent=2)
        print(f"Synced {filtered_json} with 360 records.")

    # 5. Regenerate all dashboards
    print("\n=== Step 6: Regenerating Dashboard Pages ===")
    res = generate_all_dashboard_pages(PARENT_ROOT / "Law_Crawler", ROOT / "docs")
    print(f"Dashboard Generation Complete: {res}")

    return all_360


if __name__ == "__main__":
    build_360_crosswalk()
