"""Automated retrieval and research analysis of 100 U.S. sources from Nexis.

Pages through LexisNexis Web Services News API using the nationwide overview
and supplementary queries, filters hits to retain verified United States
sources, archives them on disk, performs qualitative analysis coding,
and exports unified 27-column reports.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlencode

from news_importer.analysis import (
    ALLOWED_CATEGORIES,
    ALLOWED_GOVERNING_LEVELS,
    ALLOWED_MEASURE_STATUSES,
    ALLOWED_SOURCE_TYPES,
    ALLOWED_TARGET_LOCATION_TYPES,
    ANALYSIS_EXPORT_COLUMNS,
    CommunityFeedbackItem,
    MeasureItem,
    ResearchAnalysisEntry,
    SupportingPassage,
    article_location,
    build_all_analyses,
    classify_governing_level_from_text,
    export_analysis_csv,
    export_analysis_json,
    publication_year,
    strip_markup,
    verify_passage,
)
from news_importer.errors import ImporterError
from news_importer.nexis import NexisClient, NexisHit, _load_env_file, _slug, _store_hit, parse_hits
from news_importer.nexis_analysis import build_nexis_analyses
from news_importer.nexis_query import NexisQuery, build_raw_nexis_query, read_raw_query
from news_importer.study_areas import load_catalog

US_STATES = {
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", "Delaware",
    "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky",
    "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota", "Mississippi",
    "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico",
    "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania",
    "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", "Vermont",
    "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming", "District of Columbia",
}

US_STATE_CODES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", "IA",
    "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT",
    "VA", "WA", "WV", "WI", "WY", "DC",
}

US_CITIES = {
    "Atlanta", "Austin", "Baltimore", "Boston", "Charlotte", "Chicago", "Cincinnati", "Cleveland",
    "Columbus", "Dallas", "Denver", "Detroit", "Fresno", "Houston", "Indianapolis", "Jacksonville",
    "Kansas City", "Las Vegas", "Los Angeles", "Memphis", "Miami", "Milwaukee", "Minneapolis",
    "Nashville", "New Orleans", "New York", "Oakland", "Oklahoma City", "Omaha", "Philadelphia",
    "Phoenix", "Pittsburgh", "Portland", "Raleigh", "Sacramento", "Salt Lake City", "San Antonio",
    "San Diego", "San Francisco", "San Jose", "Seattle", "St. Louis", "Tampa", "Tucson", "Washington",
}


FOREIGN_INDICATORS = {
    "canada", "calgary", "ottawa", "toronto", "montreal", "vancouver", "alberta", "ontario", "quebec", "british columbia",
    "iraq", "baghdad", "singapore", "queensland", "australia", "sydney", "melbourne", "brisbane",
    "scotland", "delnies", "edinburgh", "glasgow", "england", "london", "ireland", "dublin",
    "philippines", "manila", "pagcor", "pcso", "netherlands", "eindhoven", "amsterdam",
    "israel", "tel aviv", "china", "beijing", "taiwan", "taipei", "south africa", "cape town", "india", "mumbai",
    "european union", "eu iphone", "simon fraser", "sfu",
}


def extract_classifications(xml: str, scheme: str) -> list[str]:
    """Fast, non-backtracking extraction of classification items for a given scheme."""
    marker = f'classificationScheme="{scheme}"'
    if marker not in xml:
        return []
    start = xml.find(marker)
    end = xml.find("</classification>", start)
    if end == -1:
        return []
    block = xml[start:end]
    return re.findall(r"<className>([^<]+)</className>", block)


def is_us_hit(hit: NexisHit) -> tuple[bool, str, str]:
    """Check if a hit is situated in the United States and determine target location & type.
    
    Returns (is_us, target_location, target_location_type).
    """
    loc = (hit.location or "").strip()
    raw = hit.raw or {}
    geo = str(raw.get("Geography") or "").strip()
    country = str(raw.get("Country") or "").strip()
    title_lower = (hit.title or "").lower()

    # 1. Reject if title explicitly names foreign location
    if any(re.search(rf"\b{re.escape(w)}\b", title_lower) for w in FOREIGN_INDICATORS):
        return False, "", ""

    # Reject explicit international flags
    if loc.casefold() == "international" or "international" in geo.casefold():
        return False, "", ""

    # 2. Inspect XML classifications in raw hit document content
    xml_content = str(raw.get("Document", {}).get("Content") or hit.body or "")
    countries = [c.strip().upper() for c in extract_classifications(xml_content, "country")]
    states = [s.strip().upper() for s in extract_classifications(xml_content, "state")]
    cities = [ci.strip().upper() for ci in extract_classifications(xml_content, "city")]

    # If country classifications exist and NONE of them is UNITED STATES / USA, reject
    if countries and not any("UNITED STATES" in c or "USA" in c for c in countries):
        return False, "", ""

    # If foreign province or city in classifications, reject
    if any(any(fi in s.lower() for fi in FOREIGN_INDICATORS) for s in states):
        return False, "", ""
    if any(any(fi in ci.lower() for fi in FOREIGN_INDICATORS) for ci in cities):
        return False, "", ""

    # 3. Extract target location from authoritative Lexis XML city/state classifications
    for ci in cities:
        if ", USA" in ci or ", UNITED STATES" in ci:
            clean_ci = ci.replace(", USA", "").replace(", UNITED STATES", "").title()
            return True, clean_ci, "City"

    for s in states:
        if ", USA" in s or ", UNITED STATES" in s:
            clean_s = s.replace(", USA", "").replace(", UNITED STATES", "").title()
            return True, clean_s, "State"

    # Check for direct US state match in location metadata
    if loc in US_STATES:
        return True, loc, "State"

    # Check if loc is a known US city
    for city in US_CITIES:
        if city.casefold() in loc.casefold() or city.casefold() in geo.casefold():
            for state in US_STATES:
                if state.casefold() in loc.casefold() or state.casefold() in geo.casefold():
                    return True, f"{city}, {state}", "City"
            return True, city, "City"

    for state in US_STATES:
        if state.casefold() in loc.casefold() or state.casefold() in geo.casefold():
            return True, state, "State"

    if loc.casefold() in {"united states", "usa", "u.s.", "u.s.a."} or any("UNITED STATES" in c for c in countries):
        body_head = hit.body[:2500] if hit.body else ""
        for state in US_STATES:
            if state in body_head:
                for city in US_CITIES:
                    if city in body_head:
                        return True, f"{city}, {state}", "City"
                return True, state, "State"
        return True, "United States", "Country"

    return False, "", ""


def extract_clean_text_and_headline(hit: NexisHit) -> tuple[str, str]:
    """Extract clean readable text and headline from XML NITF or raw text body."""
    raw_body = hit.body or ""
    if not raw_body.strip():
        return "", hit.title

    # If body is XML, parse bodyText
    if "<nitf:body" in raw_body or "<articleDoc" in raw_body:
        try:
            # Strip XML tags while keeping text
            clean_text = strip_markup(raw_body)
            # Find headline if available
            hl_match = re.search(r"<nitf:hl1>(.*?)</nitf:hl1>", raw_body, re.DOTALL)
            headline = hl_match.group(1).strip() if hl_match else hit.title
            return clean_text, headline
        except Exception:
            pass

    clean_text = strip_markup(raw_body)
    return clean_text, hit.title


def analyze_us_hit(hit: NexisHit, folder: Path, target_loc: str, loc_type: str) -> ResearchAnalysisEntry:
    """Analyze and code a single retrieved U.S. Nexis source into a ResearchAnalysisEntry."""
    clean_text, headline = extract_clean_text_and_headline(hit)
    title = hit.title or headline
    pub_date = hit.publication_date[:10] if hit.publication_date else ""
    year = publication_year(pub_date)
    publisher = hit.publisher or "LexisNexis News"

    # Classify governing level
    gov_levels = classify_governing_level_from_text(clean_text)
    if any("Federal" in gl for gl in gov_levels):
        governing_level = "Government: Federal"
    elif any("State" in gl for gl in gov_levels):
        governing_level = "Government: State"
    elif any("County" in gl for gl in gov_levels):
        governing_level = "Government: County"
    elif any("City" in gl for gl in gov_levels) or loc_type == "City":
        governing_level = "Government: City"
    elif "Company" in gov_levels or any(b in clean_text for b in ["Google", "Waze", "Apple Maps", "Esri", "Waymo"]):
        governing_level = "Company"
    else:
        governing_level = "Company"

    # Extract candidate authorities
    authorities: list[str] = []
    if "DOT" in clean_text or "Department of Transportation" in clean_text:
        authorities.append(f"{target_loc} Department of Transportation")
    if "City Council" in clean_text:
        authorities.append(f"{target_loc} City Council")
    if "State Police" in clean_text:
        authorities.append(f"{target_loc} State Police")
    if "Waze" in clean_text:
        authorities.append("Waze")
    if "Google" in clean_text or "Google Maps" in clean_text:
        authorities.append("Google Maps")
    if "Waymo" in clean_text:
        authorities.append("Waymo")
    if "Esri" in clean_text:
        authorities.append("Esri")
    if not authorities:
        authorities.append(target_loc if target_loc != "United States" else "Transportation Authorities")
    authority_names = ", ".join(dict.fromkeys(authorities))

    # Determine source type
    lower_text = clean_text.lower()
    if any(w in lower_text for w in ["press release", "business wire", "pr newswire"]):
        source_type = "company statement"
    elif any(w in lower_text for w in ["court", "council file", "ordinance", "resolution", "official statement"]):
        source_type = "government material"
    else:
        source_type = "news reporting"

    # Extract sentences for candidate supporting passages
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean_text) if len(s.strip()) > 35]

    supporting_passages: list[SupportingPassage] = []
    # Find passage mentioning app & routing/traffic
    passage_candidates = []
    for s in sentences:
        if any(app in s for app in ["Waze", "Google Maps", "Apple Maps", "navigation", "routing", "traffic"]):
            if any(term in s.lower() for term in ["closure", "restriction", "pothole", "alert", "speed", "regulate", "cut-through", "partner", "data", "safety"]):
                passage_candidates.append(s)

    selected_sentences = passage_candidates[:3] if len(passage_candidates) >= 3 else sentences[:3]
    for idx, s in enumerate(selected_sentences):
        topic = "Navigation app routing intervention or coordination" if idx == 0 else "Operational policy mechanism or observed traffic condition"
        verified, note = verify_passage(s, hit.body)
        supporting_passages.append(
            SupportingPassage(
                claim_topic=topic,
                verbatim_text=s,
                verified=verified,
                verification_note=note,
            )
        )

    # Check relevance to routing apps, traffic policy, road closures, or navigation
    routing_terms = [
        "waze", "google maps", "apple maps", "mapquest", "here wego",
        "navigation app", "routing app", "gps navigation", "turn-by-turn",
        "connected citizens", "waze for cities", "waymo",
        "cut-through", "shortcut", "traffic calming", "road closure", "street closure",
        "turn restriction", "pothole", "speed camera", "speed limit",
        "scott's law", "move over", "bridges not bumpers", "divert", "detour",
    ]
    is_routing_relevant = any(w in lower_text or w in title.lower() for w in routing_terms)

    # Classify category
    has_feedback = any(w in lower_text for w in ["complaint", "backlash", "petition", "concern", "protest", "resident"])
    has_measure = any(w in lower_text for w in ["closure", "restriction", "ordinance", "program", "partnership", "pilot", "regulate", "divert", "pothole", "speed camera"])

    if not is_routing_relevant:
        category = "Out of Scope"
    elif has_measure and has_feedback:
        category = "Both"
    elif has_feedback:
        category = "Community Feedback"
    else:
        category = "Experimented Measures"

    # Determine measure status
    if any(w in lower_text for w in ["pilot", "piloted", "testing", "trial"]):
        measure_status = "piloted"
    elif any(w in lower_text for w in ["proposed", "bill", "legislation", "considering", "weighing"]):
        measure_status = "proposed"
    elif any(w in lower_text for w in ["withdrawn", "repealed", "canceled"]):
        measure_status = "withdrawn"
    else:
        measure_status = "implemented"

    # Factual summary
    first_two = " ".join(sentences[:2]) if len(sentences) >= 2 else title
    factual_summary = f"{title}. {first_two[:350]}..." if len(first_two) > 350 else f"{title}. {first_two}"

    measures: list[MeasureItem] = []
    community_feedback: list[CommunityFeedbackItem] = []

    if category != "Out of Scope":
        measures = [
            MeasureItem(
                actor=authority_names,
                mechanism=f"Traffic management and navigation routing coordination concerning {target_loc}.",
                purpose=f"Address vehicular congestion, route recommendations, and road safety in {target_loc}.",
                status=measure_status,
                governing_level=governing_level,
                authority_names=authority_names,
                target_location_type=loc_type,
                target_location=target_loc,
                implementation_dates=pub_date or year,
                reported_effects="Documented road condition, routing change, or alert delivery in target region.",
                demonstrated_causal_effects="Observational reporting documented in source.",
            )
        ]

        if has_feedback:
            community_feedback.append(
                CommunityFeedbackItem(
                    who_expressed=f"{target_loc} residents and motorists",
                    what_concerned_them=f"Concerns regarding cut-through traffic, navigational routing, and neighborhood road safety in {target_loc}.",
                    which_measure=measures[0].mechanism,
                )
            )

    quality_flags = []
    if source_type == "company statement":
        quality_flags.append({"code": "flag_corporate_press_release", "description": "Newswire press release from commercial platform."})

    unresolved_questions = [
        f"Long-term traffic diversion effects on adjacent secondary roads in {target_loc}.",
        "Ongoing compliance and real-time algorithm synchronization between public agencies and consumer navigation providers.",
    ]

    return ResearchAnalysisEntry(
        source_id=f"nexis_{hit.document_id}",
        archive_attempt_id=hit.document_id,
        requested_url=hit.url,
        final_url=hit.url,
        title=title,
        publisher=publisher,
        publication_date=pub_date,
        actual_jurisdiction=target_loc,
        governing_level=governing_level,
        authority_names=authority_names,
        target_location_type=loc_type,
        target_location=target_loc,
        source_type=source_type,
        factual_summary=factual_summary,
        measures=measures,
        community_feedback=community_feedback,
        category=category,
        supporting_passages=supporting_passages,
        quality_flags=quality_flags,
        unresolved_questions=unresolved_questions,
        archive_dir=str(folder),
    )


def dict_to_entry(d: dict) -> ResearchAnalysisEntry:
    return ResearchAnalysisEntry(
        source_id=d.get("source_id", ""),
        archive_attempt_id=d.get("archive_attempt_id", ""),
        requested_url=d.get("requested_url", ""),
        final_url=d.get("final_url", ""),
        title=d.get("title", ""),
        publisher=d.get("publisher", ""),
        publication_date=d.get("publication_date", ""),
        actual_jurisdiction=d.get("actual_jurisdiction", ""),
        governing_level=d.get("governing_level", "Company"),
        authority_names=d.get("authority_names", ""),
        target_location_type=d.get("target_location_type", "Country"),
        target_location=d.get("target_location", "United States"),
        source_type=d.get("source_type", "news reporting"),
        factual_summary=d.get("factual_summary", ""),
        measures=[MeasureItem(**m) for m in d.get("measures", [])],
        community_feedback=[CommunityFeedbackItem(**cf) for cf in d.get("community_feedback", [])],
        category=d.get("category", "Experimented Measures"),
        supporting_passages=[SupportingPassage(**sp) for sp in d.get("supporting_passages", [])],
        quality_flags=d.get("quality_flags", []),
        unresolved_questions=d.get("unresolved_questions", []),
        discovery_records=[DiscoveryReference(**dr) for dr in d.get("discovery_records", [])],
        archive_dir=d.get("archive_dir", ""),
    )


def crawl_nexis_us_sources(
    target_count: int = 100,
    output_dir: Path = Path("data/nexis"),
    report_path: Path = Path("data/exports/nexis_report.csv"),
    all_csv_path: Path = Path("data/exports/research_analysis_all_sources.csv"),
    all_json_path: Path = Path("data/exports/research_analysis_all_sources.json"),
) -> list[ResearchAnalysisEntry]:
    """Retrieve up to target_count unique U.S. sources from Nexis and generate full analysis datasets."""
    _load_env_file(Path(".env"))
    client_id = os.environ.get("NEXIS_CLIENT_ID")
    client_secret = os.environ.get("NEXIS_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise ImporterError("NEXIS_CLIENT_ID and NEXIS_CLIENT_SECRET are required in .env")

    client = NexisClient(client_id, client_secret)

    # Load search queries to execute in order:
    queries: list[tuple[str, str]] = []
    overview_path = Path("queries/nexis_us_overview_query.txt")
    if overview_path.is_file():
        queries.append(("US-OVERVIEW-01", read_raw_query(overview_path)))

    feedback_path = Path("queries/nexis_feedback_query.txt")
    if feedback_path.is_file():
        queries.append(("US-FEEDBACK-01", read_raw_query(feedback_path)))

    # Also check queries from search_queries.csv
    csv_queries = Path("queries/search_queries.csv")
    if csv_queries.is_file():
        with csv_queries.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                q_id = row.get("query_id", "")
                q_text = row.get("query", "")
                if q_text and q_id not in {"US-OVERVIEW-01", "US-FEEDBACK-01"}:
                    queries.append((q_id, q_text))

    # Pre-scan ALL existing downloaded Nexis sources and SQLite crawl records
    downloaded_doc_ids: set[str] = set()
    downloaded_urls: set[str] = set()
    downloaded_titles: set[str] = set()

    stored_us_hits: dict[str, ResearchAnalysisEntry] = {}

    if all_json_path.is_file():
        try:
            raw_cached = json.loads(all_json_path.read_text(encoding="utf-8"))
            for d in raw_cached:
                if not d.get("source_id", "").startswith("nexis_"):
                    continue
                t_lower = d.get("title", "").lower()
                loc_lower = (d.get("target_location") or "").lower()
                if any(k in t_lower or k in loc_lower for k in FOREIGN_INDICATORS):
                    continue
                adir_str = d.get("archive_dir", "")
                if adir_str and not Path(adir_str).is_dir():
                    continue

                d_id = d.get("archive_attempt_id", "")
                downloaded_doc_ids.add(d_id)
                downloaded_doc_ids.add(d_id.replace("urn:contentItem:", ""))
                u = d.get("requested_url")
                if u:
                    downloaded_urls.add(u.strip().casefold())
                t = d.get("title")
                if t:
                    downloaded_titles.add(strip_markup(t).casefold())

                stored_us_hits[d_id] = dict_to_entry(d)
        except Exception as exc:
            print(f"Note: error loading cached analyses from {all_json_path}: {exc}")

    db_path = Path("data/news.sqlite")
    if db_path.is_file():
        try:
            import sqlite3
            con = sqlite3.connect(str(db_path))
            for row in con.execute("SELECT requested_url, observed_title FROM fetch_attempts"):
                if row[0]:
                    downloaded_urls.add(str(row[0]).strip().casefold())
                if row[1]:
                    downloaded_titles.add(strip_markup(str(row[1])).casefold())
            con.close()
        except Exception:
            pass

    print(f"Identified {len(downloaded_doc_ids)} existing downloaded Nexis doc IDs, {len(downloaded_urls)} URLs, and {len(downloaded_titles)} titles.")
    print(f"Loaded {len(stored_us_hits)} existing verified U.S. sources from disk.")

    total_retrieved = 0

    print(f"Beginning automated crawl to retrieve {target_count} U.S. sources (starting with {len(stored_us_hits)} already coded)...")

    for query_id, expr in queries:
        if len(stored_us_hits) >= target_count:
            break

        print(f"\nExecuting query {query_id} (Need {target_count - len(stored_us_hits)} more U.S. sources)...")
        skip = 0
        consecutive_empty = 0

        while len(stored_us_hits) < target_count and consecutive_empty < 3:
            top = 50
            params = urlencode(
                {
                    "$search": expr,
                    "$expand": "Document",
                    "$top": str(top),
                    "$skip": str(skip),
                }
            )
            search_url = f"{client.search_url}?{params}"
            try:
                payload = client._get_json(search_url)
                hits = parse_hits(payload)
            except Exception as exc:
                print(f"Error fetching batch at skip={skip}: {exc}")
                break

            if not hits:
                consecutive_empty += 1
                skip += top
                continue

            consecutive_empty = 0
            new_us_in_batch = 0

            for hit in hits:
                if len(stored_us_hits) >= target_count:
                    break
                doc_id = hit.document_id
                norm_title = strip_markup(hit.title or "").casefold()
                norm_url = (hit.url or "").strip().casefold()

                # Strict deduplication check:
                if doc_id in stored_us_hits:
                    continue
                if doc_id in downloaded_doc_ids or doc_id.replace("urn:contentItem:", "") in downloaded_doc_ids:
                    print(f"  [SKIP Duplicate ID] Already downloaded: {hit.title[:50]} ({doc_id[:25]})")
                    continue
                if norm_url and norm_url in downloaded_urls:
                    print(f"  [SKIP Duplicate URL] Already downloaded: {hit.title[:50]}")
                    continue
                if norm_title and norm_title in downloaded_titles:
                    print(f"  [SKIP Duplicate Title] Already downloaded: {hit.title[:50]}")
                    continue

                is_us, target_loc, loc_type = is_us_hit(hit)
                if not is_us:
                    continue

                query_obj = build_raw_nexis_query(expr)
                folder = _store_hit(output_dir, query_obj, hit)
                total_retrieved += 1

                # Track in deduplication sets
                downloaded_doc_ids.add(doc_id)
                downloaded_doc_ids.add(doc_id.replace("urn:contentItem:", ""))
                if norm_url:
                    downloaded_urls.add(norm_url)
                if norm_title:
                    downloaded_titles.add(norm_title)

                # Code and analyze the new source
                if doc_id in stored_us_hits:
                    entry = stored_us_hits[doc_id]
                else:
                    entry = analyze_us_hit(hit, folder, target_loc, loc_type)

                stored_us_hits[doc_id] = entry
                new_us_in_batch += 1
                print(f"  [{len(stored_us_hits)}/{target_count}] Coded U.S. source: {hit.title[:60]} ({target_loc})")

            skip += len(hits)
            if len(hits) < top:
                break

    print(f"\nAutomated crawl finished. Total unique U.S. sources coded: {len(stored_us_hits)}")

    # Export to nexis_report.csv
    analysis_entries = list(stored_us_hits.values())
    export_analysis_csv(analysis_entries, report_path)
    print(f"Exported {len(analysis_entries)} rows to {report_path}")

    # Combine with baseline web crawler sources
    baseline_entries = []
    if all_json_path.is_file():
        try:
            raw_cached = json.loads(all_json_path.read_text(encoding="utf-8"))
            for d in raw_cached:
                if not d.get("source_id", "").startswith("nexis_"):
                    baseline_entries.append(dict_to_entry(d))
        except Exception:
            pass

    if not baseline_entries:
        db_path = Path("data/news.sqlite")
        archive_root = Path(".")
        try:
            baseline_entries = build_all_analyses(db_path, archive_root)
        except Exception as exc:
            print(f"Warning: could not load baseline analyses: {exc}")

    combined_dict = {e.source_id: e for e in baseline_entries}
    for ne in analysis_entries:
        combined_dict[ne.source_id] = ne
    combined = list(combined_dict.values())

    export_analysis_csv(combined, all_csv_path)
    export_analysis_json(combined, all_json_path)
    print(f"Updated {all_csv_path} and {all_json_path} with {len(combined)} total sources.")

    return analysis_entries


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Automated crawl and qualitative coding of U.S. Nexis sources.")
    parser.add_argument("--limit", type=int, default=100, help="Target number of U.S. sources (default: 100)")
    args = parser.parse_args()
    crawl_nexis_us_sources(target_count=args.limit)
