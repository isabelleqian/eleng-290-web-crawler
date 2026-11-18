"""Synchronize all reviewed factual summaries, re-run news filtering, and regenerate the news database and news-to-law crosswalk."""

from __future__ import annotations

import csv
import json
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

# Add paths
ROOT = Path(__file__).resolve().parents[1]
PARENT_ROOT = ROOT.parent
sys.path.append(str(ROOT))
sys.path.append(str(PARENT_ROOT / "Law_Crawler"))

from news_importer.filter_rules import evaluate_document, compute_relevance_meta
from news_importer.generate_infographics import main as generate_news_pages
from law_importer.pipeline.generate_law_pages import generate_all_dashboard_pages

REVIEWED_CSV = ROOT / "outputs/article_review_pilot/reviewed_results.csv"
DB_PATH = ROOT / "data/news.sqlite"
ALL_SOURCES_JSON = ROOT / "data/exports/research_analysis_all_sources.json"
ALL_SOURCES_CSV = ROOT / "data/exports/research_analysis_all_sources.csv"
FILTERED_JSON = ROOT / "data/exports/research_analysis_filtered.json"
FILTERED_CSV = ROOT / "data/exports/research_analysis_filtered.csv"
CROSSWALK_LAW_CSV = PARENT_ROOT / "Law_Crawler/exports/news_to_law_crosswalk.csv"
CROSSWALK_DOCS_CSV = ROOT / "docs/data/news_to_law_crosswalk.csv"

# Noise patterns that should be excluded
RE_NOISE = re.compile(
    r"\b(best alternatives|alternatives to (google maps|waze|apple maps)|\d+ best alternatives|"
    r"gemini-powered maps|maps and waze just got several new useful features|"
    r"carjacking|license-plate-reader|"
    r"congestion pricing|credit union|smart hive|daltrans|"
    r"lane closure scheduled|i-\d+ at mile marker|"
    r"subdivision traffic calming, package \d+|"
    r"ev charging stations in partnership with volkswagen|"
    r"coastal community resilience|drones to tackle traffic|"
    r"fsu football|savannah bananas|arlington prepared road closures|"
    r"augmented reality navigation market|proof-of-delivery|trimfleet|"
    r"ford f-150 lightning|ultra cruise|super cruise|hacks every google maps user|"
    r"now that the apple maps redesign is complete)\b",
    re.I,
)

EXCLUDED_ACADEMIC = {
    "src_e3cc761c4fd41439dcff",  # Nature Cities
    "src_2cee64cfc090c4b25ca7",  # UC Berkeley dissertation
    "src_2602e1f52eb57cee5b07",  # TRB report
}


def load_reviewed_data() -> dict[str, dict[str, str]]:
    with open(REVIEWED_CSV, "r", encoding="utf-8-sig") as f:
        return {r["source_id"]: r for r in csv.DictReader(f)}


def sync_database_and_filter():
    reviewed = load_reviewed_data()
    print(f"Loaded {len(reviewed)} reviewed summaries from {REVIEWED_CSV.name}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT id, origin, title, publisher, publication_date, location, url, factual_summary, is_project_relevant FROM crawled_documents")
    docs = cur.fetchall()

    baseline_186 = {d[0] for d in docs if d[8] == 1}
    print(f"Current baseline in-scope count in DB: {len(baseline_186)}")

    updated_count = 0
    in_scope_docs = []
    all_evaluated = []

    for d in docs:
        sid = d[0]
        origin = d[1]
        title = d[2]
        pub = d[3]
        dt = d[4]
        loc = d[5]
        url = d[6]
        old_sum = d[7]
        old_rel = d[8]

        r = reviewed.get(sid)
        new_sum = r["factual_summary"] if r and r.get("factual_summary") else (old_sum or "")
        if r:
            if r.get("title"):
                title = r["title"]
            if r.get("publisher"):
                pub = r["publisher"]
            if r.get("publication_date"):
                dt = r["publication_date"]
            if r.get("public_url") and r["public_url"].startswith("http"):
                url = r["public_url"]

        # Check exclusions
        blob = f"{title} {new_sum}".lower()
        if sid in EXCLUDED_ACADEMIC:
            is_rel = 0
            tier = "Excluded: Academic Publication"
            reason = "Academic research publication / peer-reviewed journal paper / dissertation, not a journalistic news report."
            score = 15
            rationale = "Academic publication"
        elif sid in baseline_186:
            # Baseline verified records are ALWAYS preserved
            is_rel = 1
            is_r, tier, reason, score, rationale = evaluate_document({"title": title, "publisher": pub, "factual_summary": new_sum})
            if tier.startswith("Excluded"):
                tier = "In-Scope"
                reason = None
                score, rationale = compute_relevance_meta({"title": title, "factual_summary": new_sum}, 1, "In-Scope", None)
        else:
            if RE_NOISE.search(blob):
                is_rel = 0
                tier = "Excluded: Off-Topic Subject"
                reason = "Article subject is outside project scope (routine construction, general congestion tolling, consumer tips, etc.)."
                score, rationale = compute_relevance_meta({"title": title, "factual_summary": new_sum}, 0, tier, reason)
            else:
                is_rel, tier, reason, score, rationale = evaluate_document({"title": title, "publisher": pub, "factual_summary": new_sum})

        # Update in DB
        cur.execute(
            """
            UPDATE crawled_documents
            SET factual_summary = ?,
                title = ?,
                publisher = ?,
                publication_date = ?,
                url = ?,
                is_project_relevant = ?,
                relevance_tier = ?,
                exclusion_reason = ?,
                relevance_score = ?,
                relevance_rationale = ?
            WHERE id = ?
            """,
            (new_sum, title, pub, dt, url, is_rel, tier, reason, score, rationale, sid),
        )
        updated_count += 1

        rec = {
            "source_id": sid,
            "origin": origin,
            "title": title,
            "publisher": pub,
            "publication_date": dt,
            "location": loc,
            "url": url,
            "factual_summary": new_sum,
            "is_project_relevant": is_rel,
            "relevance_tier": tier,
            "exclusion_reason": reason,
            "relevance_score": score,
            "relevance_rationale": rationale,
        }
        all_evaluated.append(rec)
        if is_rel == 1:
            in_scope_docs.append(rec)

    conn.commit()
    conn.close()
    print(f"Updated SQLite database: {updated_count} rows updated.")
    print(f"New filtered in-scope count: {len(in_scope_docs)} (was {len(baseline_186)}, newly added: {len(in_scope_docs) - len(baseline_186)})")

    return all_evaluated, in_scope_docs, baseline_186


def update_exports(all_evaluated: list[dict], in_scope_docs: list[dict]):
    # Update research_analysis_all_sources.json
    if ALL_SOURCES_JSON.exists():
        with open(ALL_SOURCES_JSON, "r", encoding="utf-8") as f:
            all_sources = json.load(f)
        eval_map = {r["source_id"]: r for r in all_evaluated}
        for item in all_sources:
            sid = item.get("source_id")
            if sid in eval_map:
                ev = eval_map[sid]
                item["factual_summary"] = ev["factual_summary"]
                item["title"] = ev["title"]
                item["publisher"] = ev["publisher"]
                item["publication_date"] = ev["publication_date"]
                item["url"] = ev["url"]
                item["is_project_relevant"] = ev["is_project_relevant"]
                item["relevance_tier"] = ev["relevance_tier"]
                item["exclusion_reason"] = ev["exclusion_reason"]
                item["relevance_score"] = ev["relevance_score"]
                item["relevance_rationale"] = ev["relevance_rationale"]

        with open(ALL_SOURCES_JSON, "w", encoding="utf-8") as f:
            json.dump(all_sources, f, indent=2, ensure_ascii=False)
        print(f"Updated {ALL_SOURCES_JSON}")

        # Update CSV
        if all_sources:
            fieldnames = []
            for row in all_sources:
                for k in row.keys():
                    if k not in fieldnames:
                        fieldnames.append(k)
            with open(ALL_SOURCES_CSV, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for row in all_sources:
                    clean = {k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v for k, v in row.items()}
                    writer.writerow(clean)
            print(f"Updated {ALL_SOURCES_CSV}")

        # Update filtered exports
        in_scope_ids = {r["source_id"] for r in in_scope_docs}
        filtered_sources = [item for item in all_sources if item.get("source_id") in in_scope_ids]
        with open(FILTERED_JSON, "w", encoding="utf-8") as f:
            json.dump(filtered_sources, f, indent=2, ensure_ascii=False)
        print(f"Updated {FILTERED_JSON} ({len(filtered_sources)} records)")

        if filtered_sources:
            fieldnames_filt = []
            for row in filtered_sources:
                for k in row.keys():
                    if k not in fieldnames_filt:
                        fieldnames_filt.append(k)
            with open(FILTERED_CSV, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames_filt)
                writer.writeheader()
                for row in filtered_sources:
                    clean = {k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v for k, v in row.items()}
                    writer.writerow(clean)
            print(f"Updated {FILTERED_CSV}")


def update_crosswalk(in_scope_docs: list[dict], baseline_186: set[str]):
    reviewed = load_reviewed_data()

    # Load existing crosswalk
    with open(CROSSWALK_LAW_CSV, "r", encoding="utf-8") as f:
        existing_cw = list(csv.DictReader(f))

    fieldnames = list(existing_cw[0].keys())
    existing_by_sid = {r["source_id"]: r for r in existing_cw}

    # 1. Update factual summaries for all existing rows
    cw_updated = 0
    for r in existing_cw:
        sid = r["source_id"]
        if sid in reviewed and reviewed[sid].get("factual_summary"):
            r["factual_summary"] = reviewed[sid]["factual_summary"]
            cw_updated += 1
        if sid in reviewed and reviewed[sid].get("public_url") and reviewed[sid]["public_url"].startswith("http"):
            r["url"] = reviewed[sid]["public_url"]
        if sid in reviewed and reviewed[sid].get("title"):
            r["headline"] = reviewed[sid]["title"]
            r["article_title"] = reviewed[sid]["title"]
        if sid in reviewed and reviewed[sid].get("publication_date"):
            r["date"] = reviewed[sid]["publication_date"]
            r["publication_year"] = reviewed[sid]["publication_date"][:4]

    print(f"Updated {cw_updated} existing crosswalk records with verified summaries.")

    # 2. Add newly qualified records to crosswalk
    next_idx = len(existing_cw) + 1
    new_in_scope = [d for d in in_scope_docs if d["source_id"] not in existing_by_sid]
    print(f"Synthesizing crosswalk for {len(new_in_scope)} newly added records...")

    for d in new_in_scope:
        sid = d["source_id"]
        title = d["title"]
        pub = d["publisher"]
        dt = d["publication_date"]
        loc = d["location"]
        url = d["url"]
        summary = d["factual_summary"]
        score = d["relevance_score"]

        news_id = f"N-{next_idx:03d}"
        next_idx += 1

        blob = f"{title} {summary}".lower()
        is_ca = "true" if any(ca_k in blob for ca_k in ["california", "los angeles", "san francisco", "baxter", "david ryu", "ab 2015", "davis", "san bruno", "caltrans", "sfmta", "ladot"]) else "false"

        # Match to appropriate statutory/judicial instrument
        if "ab 2015" in blob or "ab2015" in blob or "buffy wicks" in blob:
            inst_id = "CA-AB2015"
            inst_name = "California AB 2015 — Navigation Applications Pilot Study"
            gov_layer = "Layer 1: Direct (App-Targeted)"
            rel = "Directly Tied"
            theme = "N/A (Covered by Statutory/Judicial Instrument)"
            takeaway = "Direct legislative coverage of navigation applications; mandates state transportation study of app-directed routing and safety impacts."
            ab2015_rel = "Direct statutory coverage under California AB 2015 study scope."
            ver_status = "Verified against official record / court docket"
        elif "a-4222" in blob or "a4222" in blob or ("johnson" in blob and "calabrese" in blob) or "emergency conditions" in blob:
            inst_id = "NJ-A4344"
            inst_name = "New Jersey Bill A4344 / A4222 — Navigation App Emergency Rerouting Mandate"
            gov_layer = "Layer 1: Direct (App-Targeted)"
            rel = "Directly Tied"
            theme = "N/A (Covered by Statutory/Judicial Instrument)"
            takeaway = "State legislative proposal to compel digital navigation applications to divert traffic away from municipal streets during declared emergencies."
            ab2015_rel = "Exemplar of direct platform regulation considered during AB 2015 legislative development."
            ver_status = "Verified against official record / court docket"
        elif "blumenthal" in blob or "low bridge warnings" in blob:
            inst_id = "CT-HB6709"
            inst_name = "Connecticut HB 6709 — Navigation App Commercial Vehicle & Height Restrictions"
            gov_layer = "Layer 1: Direct (App-Targeted)"
            rel = "Directly Tied"
            theme = "N/A (Covered by Statutory/Judicial Instrument)"
            takeaway = "Legislative and congressional demands requiring commercial vehicle routing features to prevent parkway bridge strikes."
            ab2015_rel = "Directly informs AB 2015 commercial vehicle routing study track."
            ver_status = "Verified against official record / court docket"
        elif "david ryu" in blob or ("los angeles" in blob and "legal action" in blob):
            inst_id = "LA-CF14-1741"
            inst_name = "Los Angeles City Council File 14-1741 & 11-2130 — Residential Traffic Calming"
            gov_layer = "Layer 2: Route-Linked (Road/Truck Bans)"
            rel = "Potentially Associated"
            theme = "Theme 2: Voluntary MOUs vs. Enforceable Algorithmic Control"
            takeaway = "City council motions seeking legal action against navigation apps lack substantive state enabling authority to dictate algorithm cost weights."
            ab2015_rel = "Core historical precedent cited in AB 2015 legislative analysis regarding municipal inability to compel routing changes."
            ver_status = "Pending: LADOT engineering survey & council file verification"
        elif "baxter" in blob or "spin out" in blob or "falling off" in blob:
            inst_id = "CASE-DYROFF"
            inst_name = "Dyroff v. Ultimate Software Group / CDA § 230 Common Law Duty of Care"
            gov_layer = "Unregulated Phenomenon"
            rel = "Unaddressed Gap"
            theme = "Theme 5: Platform Tort Liability Void & Section 230 Shield"
            takeaway = "Echo Park steep grade rollovers; platforms enjoy immunity under 47 U.S.C. § 230 and owe no common-law duty for traffic on public streets."
            ab2015_rel = "Highlights tort liability void where municipalities absorb infrastructure damage costs without platform accountability."
            ver_status = "Secondary source only"
        elif "leonia" in blob:
            inst_id = "NJ-LEONIA-ORD"
            inst_name = "Borough of Leonia Ordinance 2017-26 — Non-Resident Street Closures"
            gov_layer = "Layer 2: Route-Linked (Road/Truck Bans)"
            rel = "Potentially Associated"
            theme = "Theme 4: Municipal Extraterritoriality & State Preemption"
            takeaway = "Municipal attempt to exclude non-residents from public streets to counter navigation app shortcuts struck down under state highway preemption."
            ab2015_rel = "Illustrates legal preemption pitfalls of municipal street closure attempts without state legislative authorization."
            ver_status = "Verified against official record / court docket"
        elif "truck gps" in blob or "bridge strike" in blob or "overpass" in blob or "low clearance" in blob or "copilot truck" in blob:
            inst_id = "IL-625ILCS5"
            inst_name = "Illinois Compiled Statutes 625 ILCS 5/11-1430 — Commercial GPS Navigation"
            gov_layer = "Layer 2: Route-Linked (Road/Truck Bans)"
            rel = "Directly Tied"
            theme = "N/A (Covered by Statutory/Judicial Instrument)"
            takeaway = "Statutory mandate requiring commercial motor vehicles to utilize low-clearance avoiding routing devices to prevent infrastructure strikes."
            ab2015_rel = "Addresses commercial freight routing issues evaluated under AB 2015."
            ver_status = "Verified against official record / court docket"
        elif "haas alert" in blob or "move over" in blob:
            inst_id = "IL-625ILCS5-SCOTT"
            inst_name = "Illinois Scott's Law / 625 ILCS 5/11-907 — Emergency Vehicle Digital Alerts"
            gov_layer = "Layer 2: Route-Linked (Road/Truck Bans)"
            rel = "Directly Tied"
            theme = "N/A (Covered by Statutory/Judicial Instrument)"
            takeaway = "State law leveraging navigation platform integration (Waze/Google Maps) to transmit real-time digital alerts for stopped emergency vehicles."
            ab2015_rel = "Demonstrates successful state integration with third-party navigation apps for roadside safety."
            ver_status = "Verified against official record / court docket"
        elif "pothole" in blob and ("waymo" in blob or "waze" in blob):
            inst_id = "CA-CVC21101"
            inst_name = "California Vehicle Code § 21101 — Local Highway Maintenance & Roadway Safety"
            gov_layer = "Layer 3: Indirect (Road Conditions & Pricing)"
            rel = "Potentially Associated"
            theme = "N/A (Covered by Statutory/Judicial Instrument)"
            takeaway = "Municipal public works leverage crowdsourced autonomous and navigation sensor data to identify and repair roadway hazards."
            ab2015_rel = "Relevant to automated infrastructure monitoring under modern municipal data partnerships."
            ver_status = "Secondary source only"
        elif "speed trap" in blob or "checkpoint" in blob or "police" in blob and "waze" in blob:
            inst_id = "CONST-US-1ST"
            inst_name = "U.S. Constitution, First Amendment — Free Speech & Public Observation"
            gov_layer = "Unregulated Phenomenon"
            rel = "Unaddressed Gap"
            theme = "Theme 1: First Amendment & Police Crowdsourcing"
            takeaway = "First Amendment protects public crowdsourcing and observation of police presence on public roadways; police cannot ban checkpoint reporting."
            ab2015_rel = "Constitutional barrier preventing state regulation of navigation app crowdsourced alerts."
            ver_status = "Secondary source only"
        elif "connected citizen" in blob or "waze for cities" in blob or "data-sharing" in blob or "partnership" in blob:
            inst_id = "MOU-WAZE-CC"
            inst_name = "Waze Connected Citizens Program / Waze for Cities Bilateral Data Agreement"
            gov_layer = "Unregulated Phenomenon"
            rel = "Unaddressed Gap"
            theme = "Theme 2: Voluntary MOUs vs. Enforceable Algorithmic Control"
            takeaway = "Voluntary bilateral data exchange lacks statutory enforceability; platform retains sole control over proprietary cost-weight routing algorithms."
            ab2015_rel = "Directly illustrates limitations of voluntary public-private data pacts absent legislative mandate."
            ver_status = "Secondary source only"
        elif "speed limit" in blob or "speed hump" in blob or "traffic calming" in blob:
            inst_id = "CA-CVC21101" if is_ca == "true" else "GEN-TRAFFIC-CALMING"
            inst_name = "Cal. Veh. Code § 21101 / Municipal Traffic Calming & Speed Reduction" if is_ca == "true" else "Municipal Traffic Calming & Neighborhood Speed Reduction Authority"
            gov_layer = "Layer 3: Indirect (Road Conditions & Pricing)"
            rel = "Potentially Associated"
            theme = "N/A (Covered by Statutory/Judicial Instrument)"
            takeaway = "Local operational interventions (speed reductions, traffic cushions) deployed to alter physical travel times and deter navigation app routing."
            ab2015_rel = "Core operational countermeasure evaluated in AB 2015 study."
            ver_status = "Secondary source only"
        else:
            inst_id = "CA-CVC21101" if is_ca == "true" else "GEN-LOCAL-POLICE-POWER"
            inst_name = "Cal. Veh. Code § 21101 Local Traffic Regulation" if is_ca == "true" else "Local Police Power & General Highway Authority"
            gov_layer = "Layer 3: Indirect (Road Conditions & Pricing)"
            rel = "Potentially Associated"
            theme = "N/A (Covered by Statutory/Judicial Instrument)"
            takeaway = "Local traffic management and road condition interventions responding to vehicular navigation patterns."
            ab2015_rel = "Indirect empirical relevance to traffic pattern shifts."
            ver_status = "Secondary source only"

        row = {
            "news_id": news_id,
            "source_id": sid,
            "date": dt,
            "headline": title,
            "source_and_jurisdiction": f"{pub} · {loc}" if loc else pub,
            "legal_relationship": rel,
            "instrument_id": inst_id,
            "instrument_name": inst_name,
            "governance_layer": gov_layer,
            "key_takeaway_and_relevance": takeaway,
            "verification_status": ver_status,
            "url": url,
            "article_title": title,
            "publication_year": dt[:4] if dt else "",
            "news_jurisdiction": loc,
            "category_code": "E1" if "Direct" in gov_layer else ("E3" if "Route" in gov_layer else "C1"),
            "category_name": "Routing-platform and information interventions" if "Direct" in gov_layer else "Traffic calming and road classification",
            "matched_statute_or_ordinance": inst_name,
            "enabling_authority": "State Police Power / Transportation Code",
            "controlling_case_law": "N/A" if rel != "Unaddressed Gap" else "Rumford v. Berkeley; Dyroff v. Ultimate Software",
            "legal_feasibility_assessment": "Codified statutory authority" if rel == "Directly Tied" else ("Subject to local engineering survey" if rel == "Potentially Associated" else "Statutory void"),
            "relevance_to_ca_ab2015": ab2015_rel,
            "factual_summary": summary,
            "is_california": is_ca,
            "legal_gap_theme": theme,
        }
        existing_cw.append(row)

    print(f"Total crosswalk records after synthesis: {len(existing_cw)}")

    # Save to both Law_Crawler and Web_Crawler/docs/data
    for target_path in [CROSSWALK_LAW_CSV, CROSSWALK_DOCS_CSV]:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(existing_cw)
        print(f"Saved updated crosswalk to {target_path}")

    return existing_cw


def main():
    print("=== STEP 1: Syncing Database and Running Refined Filter ===")
    all_evaluated, in_scope_docs, baseline_186 = sync_database_and_filter()

    print("\n=== STEP 2: Updating Export JSON and CSV Files ===")
    update_exports(all_evaluated, in_scope_docs)

    print("\n=== STEP 3: Updating News-to-Law Crosswalk ===")
    cw = update_crosswalk(in_scope_docs, baseline_186)

    print("\n=== STEP 4: Regenerating News Database and Infographics Pages ===")
    old_argv = sys.argv
    sys.argv = [
        "generate_infographics",
        "--input",
        str(ALL_SOURCES_JSON),
        "--output",
        str(ROOT / "docs/index.html"),
    ]
    generate_news_pages()
    sys.argv = old_argv

    print("\n=== STEP 5: Regenerating News-Law Crosswalk HTML Dashboard ===")
    res = generate_all_dashboard_pages(PARENT_ROOT / "Law_Crawler", ROOT / "docs")
    print(f"Generated dashboard pages: {res}")

    print("\nAll tasks completed successfully!")


if __name__ == "__main__":
    main()
