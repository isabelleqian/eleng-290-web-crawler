import json
import csv
import re
from pathlib import Path

def run():
    root = Path(__file__).resolve().parent.parent
    repo_root = root.parent
    news_json_path = root / "docs" / "data" / "news_corpus_filtered.json"
    law_cross_path = repo_root / "Law_Crawler" / "exports" / "news_to_law_crosswalk.csv"
    web_cross_path = root / "docs" / "data" / "news_to_law_crosswalk.csv"

    with open(news_json_path, "r", encoding="utf-8") as f:
        docs = {d["source_id"]: d for d in json.load(f)}

    rows = []
    with open(law_cross_path, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(r)

    print(f"Loaded {len(docs)} news docs and {len(rows)} crosswalk rows.")

    THEMES = {
        'SPEECH': 'Theme 1: First Amendment & Police Crowdsourcing',
        'VOLUNTARY': 'Theme 2: Voluntary MOUs vs. Enforceable Algorithmic Control',
        'SPOOFING': 'Theme 3: Algorithmic Manipulation & Phantom Congestion',
        'PREEMPTION': 'Theme 4: Municipal Extraterritoriality & State Preemption',
        'TORT_230': 'Theme 5: Platform Tort Liability Void & Section 230 Shield',
        'FREIGHT': 'Theme 6: Commercial Freight Routing & FAAAA Preemption',
        'COVERED': 'N/A (Covered by Statutory/Judicial Instrument)'
    }

    for r in rows:
        sid = r["source_id"]
        d = docs.get(sid, {})
        
        # Exact verified URL
        r["url"] = d.get("url") or r.get("url") or ""
        r["factual_summary"] = d.get("factual_summary") or ""
        
        # California jurisdiction tagging
        loc_text = (
            str(r.get("headline", "")) + " " +
            str(r.get("source_and_jurisdiction", "")) + " " +
            str(d.get("actual_jurisdiction", "")) + " " +
            str(d.get("location", ""))
        ).lower()
        r["is_california"] = "true" if (
            "california" in loc_text or
            "los angeles" in loc_text or
            "san francisco" in loc_text or
            "fremont" in loc_text or
            "torrance" in loc_text or
            ", ca" in loc_text
        ) else "false"

        # Refine takeaways and themes for Unaddressed Gaps
        if r.get("legal_relationship") == "Unaddressed Gap":
            text = (
                str(r.get("headline", "")) + " " +
                str(r.get("factual_summary", "")) + " " +
                str(r.get("key_takeaway_and_relevance", ""))
            ).lower()

            if any(k in text for k in ["police", "cop", "nypd", "lapd", "checkpoint", "speed trap", "speed camera", "dwi", "dui", "warning"]):
                r["legal_gap_theme"] = THEMES['SPEECH']
                r["key_takeaway_and_relevance"] = (
                    "LEGAL GAP: Crowdsourced speed trap & police officer location reporting. "
                    "Law enforcement demands removal of officer-tracking features, but reporting public police presence "
                    "is constitutionally protected speech under the First Amendment (Fields v. City of Philadelphia) "
                    "and platforms are shielded by Section 230 CDA."
                )
            elif any(k in text for k in ["99 phone", "fake", "trick", "phantom", "spoof", "manipulat", "accident to trick", "simon weckert"]):
                r["legal_gap_theme"] = THEMES['SPOOFING']
                r["key_takeaway_and_relevance"] = (
                    "LEGAL GAP: Computational traffic spoofing & false reporting. "
                    "No federal, state, or municipal statute prohibits residents or third parties from fabricating "
                    "fake accident reports or clustering smartphones to generate artificial 'phantom jams' to deter through traffic."
                )
            elif any(k in text for k in ["leonia", "close street", "resident-only", "permit", "turnpike", "maine", "overflow", "bypass", "nursery road", "non-resident"]):
                r["legal_gap_theme"] = THEMES['PREEMPTION']
                r["key_takeaway_and_relevance"] = (
                    "LEGAL GAP: Municipal street closure preemption & right to travel. "
                    "Municipalities inundated with regional cut-through traffic face strict state vehicle code preemption "
                    "(e.g., Rumford v. Berkeley, CVC § 21101.6; Higgins v. Borough of Leonia); "
                    "cities cannot legally close public roads to non-residents."
                )
            elif any(k in text for k in ["hijack", "baxter", "rollover", "absolute chaos", "steep", "narrow", "damage", "pothole", "hazard", "rollovers"]):
                r["legal_gap_theme"] = THEMES['TORT_230']
                r["key_takeaway_and_relevance"] = (
                    "LEGAL GAP: Platform tort immunity & lack of common-law duty. "
                    "Section 230 CDA and common-law negligence doctrines hold that digital mapping developers "
                    "owe no duty of care to municipalities or property owners for vehicle traffic directed onto steep or hazardous public streets."
                )
            elif any(k in text for k in ["truck", "freight", "bridge", "clearance", "overpass", "bus", "dirt road", "commercial"]):
                r["legal_gap_theme"] = THEMES['FREIGHT']
                r["key_takeaway_and_relevance"] = (
                    "LEGAL GAP: Federal Aviation Administration Authorization Act (FAAAA) preemption. "
                    "Federal law (49 U.S.C. § 14501(c)) broadly preempts state and municipal laws relating to "
                    "commercial motor carrier routes, leaving local governments unable to enforce local GPS routing restrictions without federal legislation."
                )
            else:
                r["legal_gap_theme"] = THEMES['VOLUNTARY']
                r["key_takeaway_and_relevance"] = (
                    "LEGAL GAP: Non-enforceability of voluntary municipal data agreements. "
                    "Municipalities entering Waze CCP / Waze for Cities agreements lack statutory authority to compel "
                    "platforms to adjust cost-weight routing algorithms or honor municipal requests to de-prioritize residential corridors."
                )
        else:
            r["legal_gap_theme"] = THEMES['COVERED']

    fieldnames = list(rows[0].keys())
    for p in [law_cross_path, web_cross_path]:
        with open(p, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Updated CSV at {p}")

if __name__ == "__main__":
    run()
