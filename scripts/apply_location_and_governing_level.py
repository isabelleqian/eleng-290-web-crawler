"""Apply persistent location normalization and factual summary-based governing level classification.

This script updates:
1. data/news.sqlite (crawled_documents)
2. docs/news_database_archive.html (ROWS)
3. docs/news_database.html (ROWS)
4. docs/index.html (DATA['database'] and DATA['metadata'])
5. docs/data/news_corpus_archive_all.json
6. docs/data/news_corpus_filtered.json
7. docs/data/news_to_law_crosswalk.csv (and Law_Crawler/exports/ if present)
8. scripts/enrich_news_database.py (LOCATION_NORM dictionary)
9. news_importer/generate_infographics.py (format_location and dynamic pill counts)
"""

from __future__ import annotations

import csv
import json
import re
import sqlite3
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARENT_ROOT = ROOT.parent

DB_PATH = ROOT / "data/news.sqlite"
ARCHIVE_HTML = ROOT / "docs/news_database_archive.html"
FILTERED_HTML = ROOT / "docs/news_database.html"
INDEX_HTML = ROOT / "docs/index.html"
CROSSWALK_CSV = ROOT / "docs/data/news_to_law_crosswalk.csv"
LAW_CROSSWALK_CSV = PARENT_ROOT / "Law_Crawler/exports/news_to_law_crosswalk.csv"
CORPUS_ARCHIVE_JSON = ROOT / "docs/data/news_corpus_archive_all.json"
CORPUS_FILTERED_JSON = ROOT / "docs/data/news_corpus_filtered.json"

# Complete location normalization dictionary
LOCATION_NORM = {
    # Single-word cities missing state abbreviations
    "Detroit": "Detroit, MI",
    "Houston": "Houston, TX",
    "Tampa": "Tampa, FL",
    "New York City": "New York, NY",
    "Boston": "Boston, MA",
    "Chicago": "Chicago, IL",
    "Los Angeles": "Los Angeles, CA",
    "San Francisco": "San Francisco, CA",
    "Seattle": "Seattle, WA",
    "Columbus": "Columbus, OH",
    "Leonia": "Leonia, NJ",
    "Mantoloking": "Mantoloking, NJ",
    "Torrance": "Torrance, CA",
    "Albany, Ny": "Albany, NY",
    "Anchorage, Ak": "Anchorage, AK",
    "Asheville, Nc": "Asheville, NC",
    "Atlanta, Ga": "Atlanta, GA",
    "Austin, Tx": "Austin, TX",
    "Carson City, Nv": "Carson City, NV",
    "Charlotte, Nc": "Charlotte, NC",
    "Chicago, Il": "Chicago, IL",
    "Dallas, Tx": "Dallas, TX",
    "Des Moines, Ia": "Des Moines, IA",
    "Fort Worth, Tx": "Fort Worth, TX",
    "Lancaster, Pa": "Lancaster, PA",
    "Lincoln, Ne": "Lincoln, NE",
    "Los Angeles, Ca": "Los Angeles, CA",
    "Louisville, Ky": "Louisville, KY",
    "Miami, Fl": "Miami, FL",
    "Montgomery, Al": "Montgomery, AL",
    "New Haven, Ct": "New Haven, CT",
    "New York, Ny": "New York, NY",
    "New York, New York": "New York, NY",
    "Portland, Or": "Portland, OR",
    "Providence, Ri": "Providence, RI",
    "Raleigh, Nc": "Raleigh, NC",
    "Richmond, Va": "Richmond, VA",
    "Saint Louis, MO": "St. Louis, MO",
    "Salt Lake City, Ut": "Salt Lake City, UT",
    "San Francisco, Ca": "San Francisco, CA",
    "San Francisco Bay Area, Ca": "San Francisco Bay Area, CA",
    "San Francisco County": "San Francisco, CA",
    "San Jose, Ca": "San Jose, CA",
    "Spokane, Wa": "Spokane, WA",
    "Tampa, Fl": "Tampa, FL",
    "Virginia Beach, Va": "Virginia Beach, VA",
    "Washington Dc": "Washington, DC",
    "Washington, Washington": "Washington, DC",

    # Syntax and semantic corrections
    "San Jose, UT": "San Jose, CA",
    "New York, District of Columbia": "Washington, DC",

    # State label cleanups (removing '(State)')
    "California (State)": "California",
    "Virginia (State)": "Virginia",
    "Connecticut (State)": "Connecticut",
    "New York (State)": "New York",
    "Illinois (State)": "Illinois",
    "Maryland (State)": "Maryland",
    "Pennsylvania (State)": "Pennsylvania",

    # Multi-city regional clusters mapped to clean canonical label
    "Atlanta, Boston, Chicago, Los Angeles, Miami, New York, Philadelphia, Salt Lake City, San Francisco, Seattle": "United States (Multi-City)",
    "Boston, Los Angeles County, Miami, New York City, Pittsburgh; Florida, Utah, Kentucky": "United States (Multi-City)",
    "Las Vegas, NV (Southern Nevada), Tampa, FL, Delaware": "United States (Multi-City)",
    "San Francisco Bay Area, Los Angeles, Phoenix, Austin, Atlanta": "United States (Multi-City)",
    "San Francisco, Los Angeles, Phoenix, Austin, Atlanta": "United States (Multi-City)",
}

def normalize_location(loc: str) -> str:
    if not loc:
        return "United States"
    clean = re.sub(r"\s+", " ", loc).strip()
    clean = LOCATION_NORM.get(clean, clean)
    # Check case variations with strip
    clean = LOCATION_NORM.get(clean.title(), clean)
    # Remove any trailing '(State)'
    clean = re.sub(r"\s*\(state\)$", "", clean, flags=re.I).strip()
    # Normalize 2-letter state code capitalization: 'City, ca' -> 'City, CA'
    clean = re.sub(r",\s*([A-Za-z]{2})$", lambda m: f", {m.group(1).upper()}", clean)
    return LOCATION_NORM.get(clean, clean)


# Regex patterns for extracting actor from opening clause of factual summary
RE_INTRO = re.compile(
    r"^(On\s+[^,]+,\s*|In\s+[^,]+,\s*|At\s+[^,]+,\s*|Following\s+[^,]+,\s*|After\s+[^,]+,\s*|"
    r"According to\s+[^,]+,\s*|During\s+[^,]+,\s*)",
    re.I
)

RE_FED = re.compile(
    r"\b(usdot|u\.s\.\s*department of transportation|fhwa|federal highway administration|"
    r"nhtsa|national highway traffic safety administration|congress|u\.s\.\s*senate|"
    r"house of representatives|senate|federal communications commission|fcc|ftc|federal trade commission|"
    r"environmental protection agency|epa|white house|dhs|homeland security|"
    r"federal court|federal judge|u\.s\.\s*district court|court of appeals for the.*circuit|"
    r"47 u\.s\.c\.|senate environment and public works|house committee on homeland security|"
    r"marco rubio|pete hegseth|biden administration|trump administration)\b",
    re.I
)

RE_COUNTY = re.compile(
    r"\b(county board|county commission|county commissioners|county council|"
    r"county department|county executive|county public works|county supervisors|"
    r"board of supervisors|county sheriff|county road commission|county jury|"
    r"howard county|kerr county|king county|fairfax county|fulton county|dekalb county|"
    r"los angeles county board|cook county|bernalillo county)\b",
    re.I
)

RE_STATE = re.compile(
    r"\b(state legislature|general assembly|state senate|assemblymember|state senator|"
    r"governor|gov\.\s+[a-z]+|caltrans|massdot|vdot|penndot|txdot|gdot|nysdot|idot|fdot|mdot|modot|"
    r"colorado department of transportation|colorado dot|"
    r"state department of transportation|state transportation department|state dot|"
    r"state police|highway patrol|state supreme court|appellate division|assembly bill|"
    r"senate bill|ab\s*2015|a-4222|hb\s*6709|scotts law|scott's law|state law|state statute|"
    r"california legislature|new jersey legislature|connecticut general assembly|"
    r"illinois general assembly|pennsylvania turnpike commission|state officials|"
    r"state highway department|state office of traffic safety)\b",
    re.I
)

RE_CITY = re.compile(
    r"\b(city council|town council|borough council|village board|board of aldermen|"
    r"alderman|alderwoman|alderperson|mayor|city department of transportation|"
    r"city transportation department|ladot|sdot|sfmta|nyc dot|ddot|"
    r"chicago department of transportation|chicago’s transportation department|"
    r"seattle’s transportation department|boston mayor|los angeles city council|"
    r"leonia borough|borough of leonia|leonia, new jersey|leonia officials|"
    r"city manager|public works director|city officials|boston’s analytics team|"
    r"neighborhood council|silver lake neighborhood council|"
    r"municipal ordinance|city ordinance|city government|township|"
    r"police department|police chief|select board|town board|public works)\b",
    re.I
)

RE_COMPANY = re.compile(
    r"\b(waze|google|google maps|alphabet|apple|apple maps|here technologies|inrix|"
    r"tomtom|mapquest|alk technologies|copilot|trimble|cavnue|waymo|uber|lyft|"
    r"navteq|decarta|pharos|tiger telematics|teqlo|smartdraw|xora|earthlink|spacelink|"
    r"mentor engineering|telematics|roadnet technologies|cygnus capital|amundi|"
    r"empirical finance|hightower advisors|virginia retirement systems|microsoft|garmin)\b",
    re.I
)

RE_NGO = re.compile(
    r"\b(neighborhood association|homeowners association|residents of|residents seeking|"
    r"advocacy group|community coalition|aaa |aarp|ghsa|urban planning commentary|"
    r"community petition|petition signed by)\b",
    re.I
)

KNOWN_CITIES = {
    "Boston", "Seattle", "Chicago", "Leonia", "Davis", "Mantoloking",
    "Somerville", "Abington", "Godfrey", "Detroit", "Wheaton", "Houston",
    "Torrance", "Austin", "Turner", "Beaumont", "Niskayuna", "East Lampeter",
    "St. Louis", "Los Angeles", "San Francisco", "New York", "Philadelphia",
    "Portland", "San Jose", "Dallas", "Atlanta", "Grand Junction"
}

def classify_governing_level(summary: str, title: str, loc: str, old_gov: str) -> str:
    s_clean = RE_INTRO.sub("", (summary or "").strip()).strip()
    s_clean = RE_INTRO.sub("", s_clean).strip()

    first_sentence = s_clean.split(".")[0] if "." in s_clean else s_clean
    subject_clause = first_sentence[:120].lower()

    # 1. Subject clause exact actor checks
    if RE_FED.search(subject_clause):
        return "Government: Federal"
    if RE_COUNTY.search(subject_clause):
        return "Government: County"
    if RE_STATE.search(subject_clause):
        return "Government: State"
    if RE_CITY.search(subject_clause):
        return "Government: City"

    # Check known cities as subject
    words = s_clean.split()
    if len(words) >= 1:
        w0 = re.sub(r"['’]s?$", "", words[0]).strip().title()
        if w0 in KNOWN_CITIES:
            w_next = " ".join(words[1:4]).lower() if len(words) > 1 else ""
            if any(k in w_next for k in ["announced", "began", "closed", "banned", "converted", "planned", "partnered", "adopted", "voted", "approved", "mayor", "police", "officials", "department", "select", "council", "analytics", "transportation", "public works"]):
                return "Government: City"

    if RE_COMPANY.search(subject_clause):
        return "Company"

    if RE_NGO.search(subject_clause):
        if any(c in subject_clause for c in ["city council", "ordinance", "sdot", "ladot", "city", "street"]):
            return "Government: City"
        return "Non-Government Organization"

    # 2. Check full first sentence
    s_full_first = first_sentence.lower()
    if RE_FED.search(s_full_first):
        return "Government: Federal"
    if RE_COUNTY.search(s_full_first):
        return "Government: County"
    if RE_STATE.search(s_full_first):
        return "Government: State"
    if RE_CITY.search(s_full_first):
        return "Government: City"
    if RE_COMPANY.search(s_full_first):
        return "Company"
    if RE_NGO.search(s_full_first):
        return "Non-Government Organization"

    # 3. Fallback based on location and old gov
    if old_gov in ["Government: City", "Government: State", "Government: County", "Government: Federal", "Company", "Non-Government Organization"]:
        return old_gov
    if "," in loc:
        return "Government: City"
    return "Government: State"


def process_all():
    print("=== Processing Location Normalization & Governing Level Classification ===")

    # 1. Update docs/news_database_archive.html
    print(f"Reading {ARCHIVE_HTML}...")
    with open(ARCHIVE_HTML, "r", encoding="utf-8") as f:
        archive_content = f.read()

    m_archive = re.search(r"const ROWS = (\[.*?\]);", archive_content, re.DOTALL)
    if not m_archive:
        raise ValueError("Could not find const ROWS in archive HTML")

    archive_rows = json.loads(m_archive.group(1))
    print(f"Loaded {len(archive_rows)} rows from archive HTML")

    loc_changes = 0
    gov_changes = 0
    row_map = {}

    for r in archive_rows:
        sid = r["id"]
        old_loc = r.get("location", "")
        new_loc = normalize_location(old_loc)
        if new_loc != old_loc:
            loc_changes += 1
            r["location"] = new_loc

        old_gov = r.get("governing_level", "")
        new_gov = classify_governing_level(r.get("summary", ""), r.get("title", ""), r.get("location", ""), old_gov)
        if new_gov != old_gov:
            gov_changes += 1
            r["governing_level"] = new_gov

        row_map[sid] = r

    print(f"Archive HTML: {loc_changes} locations normalized, {gov_changes} governing levels updated.")

    # Re-serialize ROWS into archive HTML
    new_rows_json = json.dumps(archive_rows, ensure_ascii=False)
    # In archive HTML, update const ROWS
    archive_content = archive_content[:m_archive.start(1)] + new_rows_json + archive_content[m_archive.end(1):]
    with open(ARCHIVE_HTML, "w", encoding="utf-8") as f:
        f.write(archive_content)
    print(f"Saved updated {ARCHIVE_HTML}")

    # 2. Update docs/news_database.html
    print(f"\nUpdating {FILTERED_HTML}...")
    with open(FILTERED_HTML, "r", encoding="utf-8") as f:
        filtered_content = f.read()

    m_filt = re.search(r"const ROWS = (\[.*?\]);", filtered_content, re.DOTALL)
    if m_filt:
        filtered_rows = json.loads(m_filt.group(1))
        for r in filtered_rows:
            sid = r["id"]
            if sid in row_map:
                r["location"] = row_map[sid]["location"]
                r["governing_level"] = row_map[sid]["governing_level"]
        new_filt_json = json.dumps(filtered_rows, ensure_ascii=False)
        filtered_content = filtered_content[:m_filt.start(1)] + new_filt_json + filtered_content[m_filt.end(1):]
        with open(FILTERED_HTML, "w", encoding="utf-8") as f:
            f.write(filtered_content)
        print(f"Saved updated {FILTERED_HTML} ({len(filtered_rows)} records)")

    # 3. Update SQLite database (data/news.sqlite)
    print(f"\nUpdating SQLite database {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # Ensure schema has all columns
    cur.execute("PRAGMA table_info(crawled_documents)")
    cols = {row[1] for row in cur.fetchall()}
    for c_name in ["is_project_relevant", "relevance_tier", "exclusion_reason", "relevance_score", "relevance_rationale", "topic_category", "crosswalk_instrument_id", "crosswalk_instrument_name"]:
        if c_name not in cols:
            cur.execute(f"ALTER TABLE crawled_documents ADD COLUMN {c_name} TEXT DEFAULT NULL")

    for sid, r in row_map.items():
        cur.execute(
            """
            UPDATE crawled_documents
            SET location = ?,
                governing_level = ?,
                is_project_relevant = ?,
                relevance_tier = ?,
                exclusion_reason = ?,
                relevance_score = ?,
                relevance_rationale = ?
            WHERE id = ?
            """,
            (
                r["location"],
                r["governing_level"],
                r["is_relevant"],
                r.get("tier", "In-Scope"),
                r.get("exclusion_reason", ""),
                r.get("relevance_score", 85),
                r.get("relevance_rationale", ""),
                sid,
            ),
        )
    conn.commit()
    conn.close()
    print("Updated SQLite crawled_documents table.")

    # 4. Update docs/data/news_to_law_crosswalk.csv
    print(f"\nUpdating Crosswalk CSV {CROSSWALK_CSV}...")
    if CROSSWALK_CSV.exists():
        with open(CROSSWALK_CSV, "r", encoding="utf-8") as f:
            cw_rows = list(csv.DictReader(f))
        cw_fields = list(cw_rows[0].keys())

        cw_loc_changes = 0
        for r in cw_rows:
            sid = r["source_id"]
            if sid in row_map:
                norm_loc = row_map[sid]["location"]
                if r.get("news_jurisdiction") != norm_loc:
                    r["news_jurisdiction"] = norm_loc
                    cw_loc_changes += 1
                pub = r.get("source_and_jurisdiction", "").split("·")[0].strip()
                r["source_and_jurisdiction"] = f"{pub} · {norm_loc}" if norm_loc else pub
                r["factual_summary"] = row_map[sid]["summary"]

        with open(CROSSWALK_CSV, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=cw_fields)
            writer.writeheader()
            writer.writerows(cw_rows)
        print(f"Updated {CROSSWALK_CSV} ({cw_loc_changes} jurisdictions normalized).")

        if LAW_CROSSWALK_CSV.exists():
            with open(LAW_CROSSWALK_CSV, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=cw_fields)
                writer.writeheader()
                writer.writerows(cw_rows)
            print(f"Synced {LAW_CROSSWALK_CSV}")

    # 5. Update docs/data/news_corpus_archive_all.json
    print(f"\nUpdating {CORPUS_ARCHIVE_JSON}...")
    if CORPUS_ARCHIVE_JSON.exists():
        with open(CORPUS_ARCHIVE_JSON, "r", encoding="utf-8") as f:
            archive_json_docs = json.load(f)
        for doc in archive_json_docs:
            sid = doc.get("source_id")
            if sid in row_map:
                doc["target_location"] = row_map[sid]["location"]
                doc["governing_level"] = row_map[sid]["governing_level"]
                doc["factual_summary"] = row_map[sid]["summary"]
                doc["is_project_relevant"] = row_map[sid]["is_relevant"]
        with open(CORPUS_ARCHIVE_JSON, "w", encoding="utf-8") as f:
            json.dump(archive_json_docs, f, indent=2, ensure_ascii=False)
        print(f"Updated {CORPUS_ARCHIVE_JSON}")

    # 6. Update docs/data/news_corpus_filtered.json with all 373 filtered docs
    print(f"\nUpdating {CORPUS_FILTERED_JSON}...")
    filtered_sids = {r["id"] for r in archive_rows if r.get("is_relevant") == 1}
    filtered_json_docs = [doc for doc in archive_json_docs if doc.get("source_id") in filtered_sids]
    with open(CORPUS_FILTERED_JSON, "w", encoding="utf-8") as f:
        json.dump(filtered_json_docs, f, indent=2, ensure_ascii=False)
    print(f"Updated {CORPUS_FILTERED_JSON} ({len(filtered_json_docs)} filtered records)")

    # 7. Update docs/index.html (DATA object and metadata)
    print(f"\nUpdating {INDEX_HTML}...")
    with open(INDEX_HTML, "r", encoding="utf-8") as f:
        index_content = f.read()

    m_data = re.search(r"let DATA = ({.*?});\s*(?:window\.DATA|\n)", index_content, re.DOTALL)
    if m_data:
        data_obj = json.loads(m_data.group(1))
        # Update database rows inside DATA
        db_rows = data_obj.get("database", [])
        for r in db_rows:
            sid = r.get("source_id")
            if sid in row_map:
                r["location"] = row_map[sid]["location"]
                r["gov"] = row_map[sid]["governing_level"]
                r["summary"] = row_map[sid]["summary"]
                r["is_relevant"] = row_map[sid]["is_relevant"]

        # Recalculate metadata
        filtered_db = [r for r in db_rows if r.get("is_relevant") == 1]
        gov_counts = Counter(r.get("gov") for r in filtered_db)
        locs = set(r.get("location") for r in filtered_db)
        nationwide = sum(1 for r in filtered_db if r.get("location") == "United States")
        localized = len(filtered_db) - nationwide

        data_obj["metadata"]["total_sources"] = len(filtered_db)
        data_obj["metadata"]["archive_total_sources"] = len(db_rows)
        data_obj["metadata"]["unique_locations"] = len(locs)
        data_obj["metadata"]["nationwide_sources"] = nationwide
        data_obj["metadata"]["localized_sources"] = localized
        data_obj["metadata"]["gov_counts"] = dict(gov_counts)

        new_data_json = json.dumps(data_obj, ensure_ascii=False)
        index_content = index_content[:m_data.start(1)] + new_data_json + index_content[m_data.end(1):]

        # Fix hardcoded number "Filtered Project Corpus (189)" in index HTML markup
        index_content = re.sub(
            r"Filtered Project Corpus \(\d+\)",
            f"Filtered Project Corpus ({len(filtered_db)})",
            index_content
        )
        # Fix All Topics pill count
        index_content = re.sub(
            r"All Topics \(\d+\)",
            f"All Topics ({len(filtered_db)})",
            index_content
        )

        with open(INDEX_HTML, "w", encoding="utf-8") as f:
            f.write(index_content)
        print(f"Updated {INDEX_HTML} (metadata total_sources: {len(filtered_db)})")

    print("\n=== All persistent updates completed successfully! ===")


if __name__ == "__main__":
    process_all()
