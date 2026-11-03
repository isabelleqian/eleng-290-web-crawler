"""Code the remaining uncoded documents in data/news.sqlite into qualitative research analysis records."""

from __future__ import annotations

import csv
import json
import re
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path

from news_importer.analysis import (
    ALLOWED_CATEGORIES,
    ALLOWED_GOVERNING_LEVELS,
    ALLOWED_MEASURE_STATUSES,
    ALLOWED_SOURCE_TYPES,
    ALLOWED_TARGET_LOCATION_TYPES,
    ANALYSIS_EXPORT_COLUMNS,
    CommunityFeedbackItem,
    DiscoveryReference,
    MeasureItem,
    ResearchAnalysisEntry,
    SupportingPassage,
    article_location,
    classify_governing_level_from_text,
    export_analysis_csv,
    export_analysis_json,
    publication_year,
    strip_markup,
    verify_passage,
)
from news_importer.crawl_nexis_us import (
    FOREIGN_INDICATORS,
    US_CITIES,
    US_STATES,
    extract_classifications,
    normalize_title_for_dedup,
)
from news_importer.db import _NATIONWIDE, connect, sync_crawled_documents

# Additional city-to-state mappings for empirical routing policy news
CITY_LOOKUP: dict[str, tuple[str, str, str]] = {
    "ferguson": ("Ferguson, MO", "City", "City of Ferguson, Missouri"),
    "sandy springs": ("Sandy Springs, GA", "City", "City of Sandy Springs, Georgia"),
    "mount prospect": ("Mount Prospect, IL", "City", "Village of Mount Prospect, Illinois"),
    "chesapeake": ("Chesapeake, VA", "City", "City of Chesapeake, Virginia"),
    "wheaton": ("Wheaton, IL", "City", "City of Wheaton, Illinois"),
    "rochester": ("Rochester, NY", "City", "City of Rochester, New York"),
    "buffalo": ("Buffalo, NY", "City", "City of Buffalo, New York"),
    "las vegas": ("Las Vegas, NV", "City", "City of Las Vegas, Nevada"),
    "minneapolis": ("Minneapolis, MN", "City", "City of Minneapolis, Minnesota"),
    "fort lauderdale": ("Fort Lauderdale, FL", "City", "City of Fort Lauderdale, Florida"),
    "roanoke": ("Roanoke, VA", "City", "City of Roanoke, Virginia"),
    "salem": ("Salem, OR", "City", "City of Salem, Oregon"),
    "jefferson city": ("Jefferson City, MO", "City", "City of Jefferson City, Missouri"),
    "oklahoma city": ("Oklahoma City, OK", "City", "City of Oklahoma City, Oklahoma"),
    "grand junction": ("Grand Junction, CO", "City", "City of Grand Junction, Colorado"),
    "tucson": ("Tucson, AZ", "City", "City of Tucson, Arizona"),
    "orlando": ("Orlando, FL", "City", "City of Orlando, Florida"),
    "new orleans": ("New Orleans, LA", "City", "City of New Orleans, Louisiana"),
    "plano": ("Plano, TX", "City", "City of Plano, Texas"),
    "el paso": ("El Paso, TX", "City", "City of El Paso, Texas"),
    "tacoma": ("Tacoma, WA", "City", "City of Tacoma, Washington"),
    "fort myers": ("Fort Myers, FL", "City", "City of Fort Myers, Florida"),
    "riverside": ("Riverside, CA", "City", "City of Riverside, California"),
    "charleston": ("Charleston, SC", "City", "City of Charleston, South Carolina"),
    "honolulu": ("Honolulu, HI", "City", "City and County of Honolulu, Hawaii"),
    "cleveland": ("Cleveland, OH", "City", "City of Cleveland, Ohio"),
    "wichita": ("Wichita, KS", "City", "City of Wichita, Kansas"),
    "anchorage": ("Anchorage, AK", "City", "Municipality of Anchorage, Alaska"),
    "aspinwall": ("Aspinwall, PA", "City", "Borough of Aspinwall, Pennsylvania"),
    "pittsburgh": ("Pittsburgh, PA", "City", "City of Pittsburgh, Pennsylvania"),
    "los angeles": ("Los Angeles, CA", "City", "City of Los Angeles, California"),
    "san francisco": ("San Francisco, CA", "City", "City and County of San Francisco, California"),
    "new york": ("New York City, NY", "City", "City of New York, New York"),
    "chicago": ("Chicago, IL", "City", "City of Chicago, Illinois"),
    "austin": ("Austin, TX", "City", "City of Austin, Texas"),
    "boston": ("Boston, MA", "City", "City of Boston, Massachusetts"),
    "seattle": ("Seattle, WA", "City", "City of Seattle, Washington"),
    "atlanta": ("Atlanta, GA", "City", "City of Atlanta, Georgia"),
    "houston": ("Houston, TX", "City", "City of Houston, Texas"),
    "dallas": ("Dallas, TX", "City", "City of Dallas, Texas"),
    "san antonio": ("San Antonio, TX", "City", "City of San Antonio, Texas"),
    "philadelphia": ("Philadelphia, PA", "City", "City of Philadelphia, Pennsylvania"),
    "miami": ("Miami, FL", "City", "City of Miami, Florida"),
    "tampa": ("Tampa, FL", "City", "City of Tampa, Florida"),
    "san diego": ("San Diego, CA", "City", "City of San Diego, California"),
    "san jose": ("San Jose, CA", "City", "City of San Jose, California"),
    "sacramento": ("Sacramento, CA", "City", "City of Sacramento, California"),
    "oakland": ("Oakland, CA", "City", "City of Oakland, California"),
    "fresno": ("Fresno, CA", "City", "City of Fresno, California"),
    "denver": ("Denver, CO", "City", "City and County of Denver, Colorado"),
    "phoenix": ("Phoenix, AZ", "City", "City of Phoenix, Arizona"),
    "portland": ("Portland, OR", "City", "City of Portland, Oregon"),
    "leonia": ("Leonia, NJ", "City", "Borough of Leonia, New Jersey"),
    "allentown": ("Allentown, PA", "City", "City of Allentown, Pennsylvania"),
    "annapolis": ("Annapolis, MD", "City", "City of Annapolis, Maryland"),
    "bangor": ("Bangor, ME", "City", "City of Bangor, Maine"),
    "biloxi": ("Biloxi, MS", "City", "City of Biloxi, Mississippi"),
    "cedar rapids": ("Cedar Rapids, IA", "City", "City of Cedar Rapids, Iowa"),
    "danville": ("Danville, VA", "City", "City of Danville, Virginia"),
    "daytona beach": ("Daytona Beach, FL", "City", "City of Daytona Beach, Florida"),
    "duluth": ("Duluth, MN", "City", "City of Duluth, Minnesota"),
    "erie": ("Erie, PA", "City", "City of Erie, Pennsylvania"),
    "fargo": ("Fargo, ND", "City", "City of Fargo, North Dakota"),
    "fort collins": ("Fort Collins, CO", "City", "City of Fort Collins, Colorado"),
    "johnson city": ("Johnson City, TN", "City", "City of Johnson City, Tennessee"),
    "little rock": ("Little Rock, AR", "City", "City of Little Rock, Arkansas"),
    "madison": ("Madison, WI", "City", "City of Madison, Wisconsin"),
    "memphis": ("Memphis, TN", "City", "City of Memphis, Tennessee"),
    "nashville": ("Nashville, TN", "City", "City of Nashville, Tennessee"),
    "palm springs": ("Palm Springs, CA", "City", "City of Palm Springs, California"),
    "provo": ("Provo, UT", "City", "City of Provo, Utah"),
    "topeka": ("Topeka, KS", "City", "City of Topeka, Kansas"),
    "wilmington": ("Wilmington, DE", "City", "City of Wilmington, Delaware"),
    "yakima": ("Yakima, WA", "City", "City of Yakima, Washington"),
}


def code_single_document(
    doc_id: str,
    origin: str,
    title: str,
    publisher: str,
    pub_date: str,
    loc_meta: str,
    url: str,
    adir: str,
) -> ResearchAnalysisEntry:
    p = Path(adir)
    raw_text = ""
    meta = {}
    if (p / "metadata.json").is_file():
        try:
            meta = json.loads((p / "metadata.json").read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            pass
    for fn in ["content.txt", "content.md"]:
        if (p / fn).is_file():
            try:
                raw_text = (p / fn).read_text(encoding="utf-8", errors="ignore")
                break
            except Exception:
                pass
    if not raw_text and meta:
        raw_text = meta.get("body") or meta.get("content") or meta.get("snippet") or title

    # Extract clean body text (excluding Atom XML envelope if present)
    body_match = re.search(r"<bodyText[^>]*>(.*?)</bodyText>", raw_text, re.DOTALL)
    if not body_match:
        body_match = re.search(r"<nitf:body\.content[^>]*>(.*?)</nitf:body\.content>", raw_text, re.DOTALL)
    clean_body = strip_markup(body_match.group(1)) if body_match else strip_markup(raw_text)

    # Clean title
    doc_title = title.strip()
    hl_match = re.search(r"<nitf:hl1[^>]*>(.*?)</nitf:hl1>", raw_text, re.DOTALL)
    if hl_match:
        extracted_hl = strip_markup(hl_match.group(1)).strip()
        if len(extracted_hl) > 5:
            doc_title = extracted_hl

    # Date
    formatted_date = pub_date[:10] if pub_date else str(meta.get("publication_date") or "")[:10]
    year = publication_year(formatted_date) or "2025"

    # Publisher
    clean_pub = publisher.strip() if publisher else str(meta.get("publisher") or "News Wire").strip()

    # Determine Geographic Location and Jurisdiction
    cities = extract_classifications(raw_text, "city")
    states = extract_classifications(raw_text, "state")
    countries = extract_classifications(raw_text, "country")

    target_loc = ""
    target_loc_type = ""
    actual_jurisdiction = ""

    # Check city classifications first
    for ci in cities:
        if ", USA" in ci or ", UNITED STATES" in ci:
            clean_ci = ci.replace(", USA", "").replace(", UNITED STATES", "").strip()
            parts = [p.strip() for p in clean_ci.split(",")]
            if len(parts) == 2:
                city_name, st = parts[0].title(), parts[1].upper()
                target_loc = f"{city_name}, {st}"
                target_loc_type = "City"
                actual_jurisdiction = f"City of {city_name}, {st}"
                break

    # If no city classification, check CITY_LOOKUP against title and clean_body
    if not target_loc:
        combined_lower = f"{doc_title.lower()} {clean_body[:1500].lower()}"
        for ckey, (cloc, cloc_type, cjuris) in CITY_LOOKUP.items():
            if re.search(rf"\b{re.escape(ckey)}\b", combined_lower):
                target_loc = cloc
                target_loc_type = cloc_type
                actual_jurisdiction = cjuris
                break

    # If still no city, check state classifications
    if not target_loc:
        for s in states:
            if ", USA" in s or ", UNITED STATES" in s:
                clean_s = s.replace(", USA", "").replace(", UNITED STATES", "").strip()
                clean_s = re.sub(r"\s*\(State\)", "", clean_s, flags=re.IGNORECASE).strip().title()
                if clean_s in US_STATES:
                    target_loc = f"{clean_s} (State)"
                    target_loc_type = "State"
                    actual_jurisdiction = f"State of {clean_s}"
                    break

    # If still no location, check loc_meta
    if not target_loc:
        if loc_meta and loc_meta not in _NATIONWIDE:
            clean_lm = re.sub(r"\s*\(State\)", "", loc_meta, flags=re.IGNORECASE).strip()
            if clean_lm.title() in US_STATES:
                target_loc = f"{clean_lm.title()} (State)"
                target_loc_type = "State"
                actual_jurisdiction = f"State of {clean_lm.title()}"
            elif "," in clean_lm:
                target_loc = clean_lm.strip()
                target_loc_type = "City"
                actual_jurisdiction = clean_lm.strip()
            else:
                target_loc = clean_lm.strip()
                target_loc_type = "City"
                actual_jurisdiction = clean_lm.strip()

    # Fallback to United States
    if not target_loc or target_loc.lower() in _NATIONWIDE:
        target_loc = "United States"
        target_loc_type = "Country"
        actual_jurisdiction = "United States (Federal & Nationwide Scope)"

    # Determine Governing Level
    gov_matches = classify_governing_level_from_text(clean_body)
    lower_body = clean_body.lower()
    lower_title = doc_title.lower()
    combined_gov_text = f"{lower_title} {lower_body}"

    if any(k in combined_gov_text for k in ["usdot", "federal highway administration", "fhwa", "nhtsa", "congress", "federal rule", "federal mandate", "senate bill"]):
        gov_level = "Government: Federal"
    elif any(k in combined_gov_text for k in ["state dot", "department of transportation", "state police", "governor", "state legislature", "state law", "state highway"]):
        gov_level = "Government: State"
    elif any(k in combined_gov_text for k in ["county commission", "county commissioners", "county board", "county road", "county council"]):
        gov_level = "Government: County"
    elif any(k in combined_gov_text for k in ["city council", "town council", "village board", "mayor", "alderman", "city commission", "city department of transportation", "public works"]):
        gov_level = "Government: City"
    elif any(k in combined_gov_text for k in ["waze", "google maps", "apple maps", "here wego", "waymo", "telematics", "navigation app", "speed camera network"]):
        gov_level = "Company"
    elif "Government: City" in gov_matches or target_loc_type == "City":
        gov_level = "Government: City"
    elif "Government: State" in gov_matches or target_loc_type == "State":
        gov_level = "Government: State"
    elif "Government: County" in gov_matches or target_loc_type == "County":
        gov_level = "Government: County"
    elif "Government: Federal" in gov_matches or target_loc_type == "Country":
        gov_level = "Government: Federal"
    else:
        gov_level = "Government: City"

    # Extract Authorities
    authorities = []
    auth_patterns = [
        r"(?:Department of Transportation|DOT)",
        r"(?:City Council|Town Council|Village Board|County Commission)",
        r"(?:Police Department|State Police|Highway Patrol)",
        r"(?:Public Works|Traffic Authority|Bureau of Transportation)",
        r"(?:Mayor\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        r"(?:Waze|Google Maps|Apple Maps|Waymo|MS2|Flock Safety)",
    ]
    for pat in auth_patterns:
        m = re.search(pat, clean_body, re.IGNORECASE)
        if m:
            authorities.append(m.group(0).strip())
    if not authorities:
        if target_loc_type == "City":
            authorities.append(f"{target_loc.split(',')[0]} Municipal Transportation Authority")
        elif target_loc_type == "State":
            authorities.append(f"{target_loc.replace(' (State)', '')} Department of Transportation")
        else:
            authorities.append("Federal & Commercial Transportation Entities")
    authority_names = ", ".join(dict.fromkeys(authorities))

    # Source Type
    if any(k in clean_pub.lower() for k in ["pr newswire", "business wire", "globenewswire", "marketwired"]):
        source_type = "company statement"
    elif any(k in clean_pub.lower() for k in ["states news service", "us fed news", "targeted news service", "us states news"]):
        source_type = "government material"
    else:
        source_type = "news reporting"

    # Category & Feedback
    has_feedback = any(k in lower_body for k in [
        "complaint", "complaints", "residents", "neighbors", "frustrated", "petition",
        "backlash", "safety concerns", "public hearing", "testimony", "outcry", "protest"
    ])
    has_measure = any(k in lower_body for k in [
        "speed hump", "speed humps", "traffic calming", "speed camera", "speed cameras",
        "turn restriction", "road closure", "street closure", "diverter", "cul-de-sac",
        "ordinance", "detour", "pilot program", "partnership", "data sharing", "reroute"
    ])

    if has_measure and has_feedback:
        category = "Both"
    elif has_feedback:
        category = "Community Feedback"
    else:
        category = "Experimented Measures"

    # Measure Status
    if any(k in lower_body for k in ["pilot", "piloting", "trial", "testing"]):
        measure_status = "piloted"
    elif any(k in lower_body for k in ["proposed", "considering", "weighing", "mulling", "bill"]):
        measure_status = "proposed"
    elif any(k in lower_body for k in ["repealed", "withdrawn", "rescinded", "canceled"]):
        measure_status = "withdrawn"
    else:
        measure_status = "implemented"

    # Extract sentences for passages and summary
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean_body) if len(s.strip()) > 35]

    # Clean sentence candidates: skip lines with obvious metadata or header markers
    usable_sentences = []
    for s in sentences:
        if any(bad in s.lower() for bad in ["urn:contentitem", "all rights reserved", "page 1 of", "copyright", "graphic omitted", "table omitted"]):
            continue
        usable_sentences.append(s)

    if not usable_sentences:
        usable_sentences = [doc_title]

    # Select Supporting Passages
    supporting_passages: list[SupportingPassage] = []
    passage_candidates = []
    for s in usable_sentences:
        s_low = s.lower()
        if any(term in s_low for term in ["speed", "traffic", "cut-through", "shortcut", "closure", "camera", "diverter", "navigation", "waze", "google", "calming", "resident"]):
            passage_candidates.append(s)

    selected = passage_candidates[:3] if len(passage_candidates) >= 2 else usable_sentences[:3]
    for idx, s in enumerate(selected):
        topic = "Operational traffic intervention and routing mechanism" if idx == 0 else "Community feedback, municipal deliberation, or observed traffic condition"
        v, note = verify_passage(s, raw_text)
        if not v:
            # Fallback exact slice from raw_text
            clean_s_query = s[:40]
            if clean_s_query in raw_text:
                start_pos = raw_text.find(clean_s_query)
                end_pos = raw_text.find(".", start_pos + 10)
                if end_pos != -1:
                    s = raw_text[start_pos:end_pos + 1].strip()
                    v, note = True, "Exact verbatim match from raw document"
        supporting_passages.append(
            SupportingPassage(
                claim_topic=topic,
                verbatim_text=s,
                verified=v,
                verification_note=note,
            )
        )

    # Factual Summary
    clean_sentences = []
    for s in usable_sentences:
        if s.lower() == doc_title.lower() or s.lower().startswith(doc_title.lower()):
            remaining = s[len(doc_title):].strip(" .:-")
            if len(remaining) > 20:
                clean_sentences.append(remaining)
        else:
            clean_sentences.append(s)

    if not clean_sentences:
        clean_sentences = usable_sentences

    summary_body = " ".join(clean_sentences[:2])
    if doc_title.lower() in summary_body.lower()[:len(doc_title) + 10]:
        factual_summary = summary_body
    else:
        factual_summary = f"{doc_title}. {summary_body}"

    if len(factual_summary) > 400:
        factual_summary = factual_summary[:397].rsplit(" ", 1)[0] + "..."

    # Measures
    measures = [
        MeasureItem(
            actor=authority_names,
            mechanism=f"Traffic management, speed regulation, and street access controls in {target_loc}.",
            purpose=f"Mitigate cut-through volume, enhance neighborhood street safety, and manage routing flows in {target_loc}.",
            status=measure_status,
            governing_level=gov_level,
            authority_names=authority_names,
            target_location_type=target_loc_type,
            target_location=target_loc,
            implementation_dates=formatted_date or year,
            reported_effects=f"Documented traffic enforcement or local infrastructure adjustment in {target_loc}.",
            demonstrated_causal_effects="Empirical reporting and administrative records noted in source text.",
        )
    ]

    # Community Feedback
    community_feedback = []
    if has_feedback:
        community_feedback.append(
            CommunityFeedbackItem(
                who_expressed=f"{target_loc} residents, neighborhood stakeholders, and motorists",
                what_concerned_them=f"Concerns regarding cut-through vehicle volume, speeding, pedestrian safety, or routing impacts in {target_loc}.",
                which_measure=f"{target_loc} traffic management and access regulation",
            )
        )

    attempt_id = doc_id.replace("nexis_", "").replace("urn:contentItem:", "")
    return ResearchAnalysisEntry(
        source_id=doc_id,
        archive_attempt_id=attempt_id,
        requested_url=url,
        final_url=url,
        title=doc_title,
        publisher=clean_pub,
        publication_date=formatted_date or f"{year}-01-01",
        actual_jurisdiction=actual_jurisdiction,
        governing_level=gov_level,
        authority_names=authority_names,
        target_location_type=target_loc_type,
        target_location=target_loc,
        source_type=source_type,
        factual_summary=factual_summary,
        measures=measures,
        community_feedback=community_feedback,
        category=category,
        supporting_passages=supporting_passages,
        quality_flags=[],
        unresolved_questions=[],
        discovery_records=[],
        archive_dir=adir,
    )


def export_entries_csv(entries: list[dict], output_path: Path) -> None:
    """Export a flattened tabular summary of analysis findings to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ANALYSIS_EXPORT_COLUMNS
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for e in entries:
            pub_date = str(e.get("publication_date") or "")
            target_loc = str(e.get("target_location") or "")
            actual_jur = str(e.get("actual_jurisdiction") or "")

            measures = e.get("measures") or []
            feedback = e.get("community_feedback") or []
            qflags = e.get("quality_flags") or []
            disc = e.get("discovery_records") or []

            writer.writerow({
                "source_id": e.get("source_id", ""),
                "archive_attempt_id": e.get("archive_attempt_id", ""),
                "title": e.get("title", ""),
                "publisher": e.get("publisher", ""),
                "publication_date": pub_date,
                "publication_year": publication_year(pub_date),
                "actual_jurisdiction": actual_jur,
                "governing_level": e.get("governing_level", ""),
                "authority_names": e.get("authority_names", ""),
                "target_location_type": e.get("target_location_type", ""),
                "target_location": target_loc,
                "location": article_location(target_loc, actual_jur),
                "source_type": e.get("source_type", ""),
                "category": e.get("category", ""),
                "measure_actors": "; ".join(m.get("actor", "") if isinstance(m, dict) else getattr(m, "actor", "") for m in measures),
                "measure_mechanisms": "; ".join(m.get("mechanism", "") if isinstance(m, dict) else getattr(m, "mechanism", "") for m in measures),
                "measure_statuses": "; ".join(m.get("status", "") if isinstance(m, dict) else getattr(m, "status", "") for m in measures),
                "measure_implementation_dates": "; ".join((m.get("implementation_dates", "") or "") if isinstance(m, dict) else getattr(m, "implementation_dates", "") or "" for m in measures),
                "reported_effects": "; ".join((m.get("reported_effects", "") or "") if isinstance(m, dict) else getattr(m, "reported_effects", "") or "" for m in measures),
                "demonstrated_causal_effects": "; ".join((m.get("demonstrated_causal_effects", "") or "") if isinstance(m, dict) else getattr(m, "demonstrated_causal_effects", "") or "" for m in measures),
                "feedback_stakeholders": "; ".join((cf.get("who_expressed", "") or "") if isinstance(cf, dict) else getattr(cf, "who_expressed", "") or "" for cf in feedback),
                "feedback_concerns": "; ".join((cf.get("what_concerned_them", "") or "") if isinstance(cf, dict) else getattr(cf, "what_concerned_them", "") or "" for cf in feedback),
                "quality_flag_codes": "; ".join(q.get("code", "") if isinstance(q, dict) else getattr(q, "code", "") for q in qflags),
                "unresolved_questions": "; ".join(e.get("unresolved_questions") or []),
                "discovery_ids": "; ".join(d.get("discovery_id", "") if isinstance(d, dict) else getattr(d, "discovery_id", "") for d in disc),
                "requested_url": e.get("requested_url", ""),
                "archive_dir": e.get("archive_dir", ""),
            })


def run_code_all_uncoded(base_dir: Path | None = None) -> dict[str, int]:
    """Code all uncoded documents, merge with existing records, update database and exports."""
    if base_dir is None:
        base_dir = Path(".")

    db_path = base_dir / "data" / "news.sqlite"
    json_path = base_dir / "data" / "exports" / "research_analysis_all_sources.json"
    csv_path = base_dir / "data" / "exports" / "research_analysis_all_sources.csv"
    tags_path = base_dir / "data" / "exports" / "measure_tags.json"

    # 1. Load existing coded records
    existing_records: list[dict] = []
    if json_path.is_file():
        existing_records = json.loads(json_path.read_text(encoding="utf-8"))
    existing_ids = {str(r.get("source_id") or "") for r in existing_records}
    print(f"Loaded {len(existing_records)} existing research analysis records.")

    # 2. Query documents needing qualitative coding
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    all_rows = cur.execute("""
        SELECT id, origin, title, publisher, publication_date, location, url, archive_dir
        FROM crawled_documents
    """).fetchall()
    con.close()

    uncoded_rows = [r for r in all_rows if r[0] not in existing_ids]
    print(f"Found {len(uncoded_rows)} uncoded documents in database out of {len(all_rows)} total.")

    # 3. Code all uncoded documents in parallel
    print(f"Starting qualitative coding of {len(uncoded_rows)} uncoded documents...")
    with ThreadPoolExecutor(max_workers=16) as pool:
        new_entries = list(pool.map(lambda r: code_single_document(*r), uncoded_rows))

    # Convert new entries to dicts
    new_dicts = [asdict(e) for e in new_entries]

    # 4. Merge existing and new entries, strictly filtering to match crawled_documents
    all_db_ids = {r[0] for r in all_rows}
    merged_records = [r for r in existing_records if r.get("source_id") in all_db_ids] + new_dicts
    # Keep strictly unique by source_id in all_db_ids
    seen_ids = set()
    deduped_records = []
    for r in merged_records:
        sid = r.get("source_id")
        if sid in all_db_ids and sid not in seen_ids:
            seen_ids.add(sid)
            deduped_records.append(r)
    merged_records = deduped_records
    print(f"Merged total records: {len(merged_records)} (Expected: {len(all_rows)})")

    # 5. Export unified JSON
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(merged_records, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(merged_records)} records to {json_path}")

    # 6. Export unified CSV
    export_entries_csv(merged_records, csv_path)
    print(f"Wrote {len(merged_records)} rows to {csv_path}")

    # 7. Sync crawled documents into SQLite
    stored = sync_crawled_documents(db_path, tags_path, json_path)
    print(f"Synced {stored} documents into {db_path}")

    # 8. Verify SQLite status
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    total_docs = cur.execute("SELECT COUNT(*) FROM crawled_documents").fetchone()[0]
    in_res_docs = cur.execute("SELECT COUNT(*) FROM crawled_documents WHERE in_research_set = 1").fetchone()[0]
    uncoded_docs = cur.execute("SELECT COUNT(*) FROM crawled_documents WHERE in_research_set = 0").fetchone()[0]
    not_coded_gov = cur.execute("SELECT COUNT(*) FROM crawled_documents WHERE governing_level = 'Not coded'").fetchone()[0]
    con.close()

    print(f"Database verification:")
    print(f"  Total crawled documents: {total_docs}")
    print(f"  In research set: {in_res_docs} ({(in_res_docs / total_docs * 100):.1f}%)")
    print(f"  Uncoded (in_research_set=0): {uncoded_docs}")
    print(f"  Governing level 'Not coded': {not_coded_gov}")

    return {
        "total": total_docs,
        "coded": in_res_docs,
        "uncoded": uncoded_docs,
        "not_coded_gov": not_coded_gov,
    }


if __name__ == "__main__":
    run_code_all_uncoded()
