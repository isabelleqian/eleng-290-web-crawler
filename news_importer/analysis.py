"""Research analysis module for the news-crawler project.

Performs qualitative and quantitative research-analysis passes over archived sources,
validating exact supporting evidence passages, managing duplicate discovery records,
and exporting structured analysis datasets to JSON and CSV.
"""

from __future__ import annotations

import csv
import json
import re
import sqlite3
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from news_importer.db import connect


# ---------------------------------------------------------------------------
# Codebook Enums and Allowed Values
# ---------------------------------------------------------------------------

ALLOWED_SOURCE_TYPES = {
    "news reporting",
    "government material",
    "company statement",
    "community testimony",
    "other",
}

ALLOWED_MEASURE_STATUSES = {
    "proposed",
    "piloted",
    "implemented",
    "withdrawn",
    "unclear",
}

ALLOWED_CATEGORIES = {
    "Experimented Measures",
    "Community Feedback",
    "Both",
    "Out of Scope",
}

ALLOWED_GOVERNING_LEVELS = {
    "Government: Federal",
    "Government: State",
    "Government: County",
    "Government: City",
    "Company",
    "Non-Government Organization",
}

ALLOWED_TARGET_LOCATION_TYPES = {
    "City",
    "County",
    "State",
    "Country",
}


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class DiscoveryReference:
    """A discovery record linked to a source."""
    discovery_id: str
    batch_id: str
    study_area: str | None
    discovery_method: str
    original_url: str


@dataclass
class MeasureItem:
    """An operational, legal, or infrastructural measure identified in the source."""
    actor: str
    mechanism: str
    purpose: str
    status: str  # proposed, piloted, implemented, withdrawn, unclear
    governing_level: str | None = None  # Government: Federal / State / County / City / Company / Non-Government Organization
    authority_names: str | None = None
    target_location_type: str | None = None  # City / County / State / Country
    target_location: str | None = None
    implementation_dates: str | None = None
    reported_effects: str | None = None
    demonstrated_causal_effects: str | None = None


@dataclass
class CommunityFeedbackItem:
    """Documented community, resident, or stakeholder feedback."""
    who_expressed: str
    what_concerned_them: str
    which_measure: str


@dataclass
class SupportingPassage:
    """Verbatim text snippet verified against the archived content on disk."""
    claim_topic: str
    verbatim_text: str
    verified: bool = False
    verification_note: str = ""


@dataclass
class ResearchAnalysisEntry:
    """Comprehensive research analysis for one unique archived source."""
    source_id: str
    archive_attempt_id: str
    requested_url: str
    final_url: str
    title: str
    publisher: str
    publication_date: str | None
    actual_jurisdiction: str
    governing_level: str  # Government: Federal / State / County / City / Company / Non-Government Organization
    authority_names: str
    target_location_type: str  # City / County / State / Country
    target_location: str
    source_type: str  # news reporting, government material, company statement, community testimony, other
    factual_summary: str
    measures: list[MeasureItem]
    community_feedback: list[CommunityFeedbackItem]
    category: str  # Experimented Measures, Community Feedback, Both, Out of Scope
    supporting_passages: list[SupportingPassage]
    quality_flags: list[dict[str, str]]
    unresolved_questions: list[str]
    discovery_records: list[DiscoveryReference] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Evidence Passage Verification
# ---------------------------------------------------------------------------

def normalize_whitespace(text: str) -> str:
    """Collapse consecutive whitespace and newlines for robust text comparison."""
    return re.sub(r"\s+", " ", text).strip()


def strip_markdown(text: str) -> str:
    """Strip markdown links, images, and formatting to obtain plain text."""
    # Strip images first so ! is not left behind
    t = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"", text)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    return t


def verify_passage(verbatim_passage: str, archive_markdown: str) -> tuple[bool, str]:
    """Verify that a passage exists in the archive markdown, checking exact and normalized forms."""
    if verbatim_passage in archive_markdown:
        return True, "Exact verbatim match"
    
    norm_passage = normalize_whitespace(verbatim_passage)
    norm_content = normalize_whitespace(archive_markdown)
    if norm_passage in norm_content:
        return True, "Normalized whitespace match"
    
    stripped_passage = normalize_whitespace(strip_markdown(verbatim_passage))
    stripped_content = normalize_whitespace(strip_markdown(archive_markdown))
    if stripped_passage in stripped_content:
        return True, "Plaintext normalized match"

    if norm_passage.lower() in norm_content.lower() or stripped_passage.lower() in stripped_content.lower():
        return True, "Case-insensitive normalized match"
        
    return False, "Passage not found in archive content"


# ---------------------------------------------------------------------------
# Inventory Functions
# ---------------------------------------------------------------------------

def inventory_archived_sources(db_path: Path, archive_base: Path) -> list[dict[str, Any]]:
    """Scan SQLite and archive folders to generate an inventory of all captured sources."""
    con = connect(db_path)
    con.row_factory = sqlite3.Row
    
    rows = con.execute("""
        SELECT fa.id AS attempt_id, fa.source_id, fa.attempt_number, fa.requested_url, 
               fa.final_url, fa.retrieved_at, fa.http_status, fa.content_type, 
               fa.observed_title, fa.publication_date, fa.outcome, fa.quality_flags_json, 
               fa.error, fa.archive_dir, fa.source_kind,
               s.normalized_url, s.hostname
        FROM fetch_attempts fa
        JOIN sources s ON fa.source_id = s.id
        ORDER BY fa.source_id, fa.attempt_number
    """).fetchall()
    
    # Also fetch all discoveries mapped to source
    disc_rows = con.execute("""
        SELECT sd.source_id, d.id AS discovery_id, d.batch_id, d.study_area, 
               d.discovery_method, d.original_url
        FROM source_discoveries sd
        JOIN discoveries d ON sd.discovery_id = d.id
    """).fetchall()
    
    disc_by_source: dict[str, list[dict[str, Any]]] = {}
    for d in disc_rows:
        disc_by_source.setdefault(d["source_id"], []).append(dict(d))
        
    inventory = []
    for r in rows:
        flags = json.loads(r["quality_flags_json"])
        attempt_dir = archive_base / r["archive_dir"] if not str(r["archive_dir"]).startswith(str(archive_base)) else Path(r["archive_dir"])
        has_md = (attempt_dir / "content.md").is_file() and (attempt_dir / "content.md").stat().st_size > 0
        has_html = (attempt_dir / "raw.html").is_file() and (attempt_dir / "raw.html").stat().st_size > 0
        has_pdf = (attempt_dir / "original.pdf").is_file() or (attempt_dir / "page.pdf").is_file()
        
        linked_discs = disc_by_source.get(r["source_id"], [])
        
        inventory.append({
            "source_id": r["source_id"],
            "attempt_id": r["attempt_id"],
            "attempt_number": r["attempt_number"],
            "hostname": r["hostname"],
            "requested_url": r["requested_url"],
            "observed_title": r["observed_title"],
            "publication_date": r["publication_date"],
            "outcome": r["outcome"],
            "quality_flag_codes": [f["code"] for f in flags],
            "quality_flags": flags,
            "has_markdown": has_md,
            "has_html": has_html,
            "has_pdf": has_pdf,
            "archive_dir": str(r["archive_dir"]),
            "discovery_count": len(linked_discs),
            "discovery_ids": [d["discovery_id"] for d in linked_discs],
            "study_areas": list({d["study_area"] for d in linked_discs if d["study_area"]}),
        })
    con.close()
    return inventory


def export_inventory_csv(inventory: list[dict[str, Any]], output_path: Path) -> None:
    """Write inventory summary to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "source_id", "attempt_id", "attempt_number", "hostname", "requested_url",
            "observed_title", "publication_date", "outcome", "quality_flag_codes",
            "has_markdown", "has_html", "has_pdf", "discovery_count", "study_areas", "archive_dir"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for item in inventory:
            row = dict(item)
            row["quality_flag_codes"] = "; ".join(item["quality_flag_codes"])
            row["study_areas"] = "; ".join(item["study_areas"])
            row.pop("quality_flags", None)
            row.pop("discovery_ids", None)
            writer.writerow(row)


# ---------------------------------------------------------------------------
# Initial Research Pass 1 Definition
# ---------------------------------------------------------------------------

def build_pass1_analyses(db_path: Path, archive_root: Path) -> list[ResearchAnalysisEntry]:
    """Build and validate research analysis entries for the initial five unique sources."""
    con = connect(db_path)
    con.row_factory = sqlite3.Row
    
    def get_discoveries(source_id: str) -> list[DiscoveryReference]:
        rows = con.execute("""
            SELECT d.id, d.batch_id, d.study_area, d.discovery_method, d.original_url
            FROM discoveries d
            JOIN source_discoveries sd ON d.id = sd.discovery_id
            WHERE sd.source_id = ?
        """, (source_id,)).fetchall()
        return [
            DiscoveryReference(
                discovery_id=r["id"],
                batch_id=r["batch_id"],
                study_area=r["study_area"],
                discovery_method=r["discovery_method"],
                original_url=r["original_url"],
            ) for r in rows
        ]

    def get_archive_text(archive_rel_path: str) -> str:
        # Determine full path
        p = archive_root / archive_rel_path / "content.md"
        if not p.is_file():
            # try stripping data/
            p = archive_root.parent / archive_rel_path / "content.md"
        if p.is_file():
            return p.read_text(encoding="utf-8")
        return ""

    entries: list[ResearchAnalysisEntry] = []

    # -----------------------------------------------------------------------
    # Source 1: Nature Cities (Academic empirical randomized experiment)
    # -----------------------------------------------------------------------
    s1_text = get_archive_text("data/archive/unassigned/www.nature.com/s44284-026-00443-x--src_e3cc761c4fd41439dcff/attempt-002")
    s1_passages = [
        SupportingPassage(
            claim_topic="Intervention mechanism and observed aggregate efficiency effects",
            verbatim_text=(
                "Here we report large-scale empirical experiments evaluating routing-based traffic interventions "
                "on ~100 highly congested road segments across 10 major US cities. By rerouting a small share of "
                "Google Maps trips from targeted congested highway and arterial segments to less congested alternatives "
                "of equivalent road-classes with comparable travel times, we observe a city-average 2% increase in vehicle "
                "speeds on the intervened segments, along with improved travel times 0.7% and potential annual reductions "
                "exceeding 1,000 tons of CO2-equivalent emissions per city in the majority of studied locations."
            ),
        ),
        SupportingPassage(
            claim_topic="Causal identification via randomized switchback crossover design",
            verbatim_text=(
                "Second, we used a switchback (also known as crossover) experimental design that alternated the "
                "treatment status of all users in a given geography over time. Switchback designs are commonly "
                "used in medical studies and have recently been adopted by ride-hailing platforms such as Uber and Lyft"
            ),
        ),
        SupportingPassage(
            claim_topic="Demonstrated causal speed increases in specific metro areas",
            verbatim_text=(
                "The impact of the intervention was particularly pronounced in cities where freeway segments were "
                "targeted. This is the case in Atlanta and Los Angeles, for instance, for which the median speed "
                "effect was 3.30% and 4.56%, respectively."
            ),
        ),
        SupportingPassage(
            claim_topic="Data retention limitation and duration of experimental window",
            verbatim_text=(
                "Our initial analysis focused only on segment-level outcomes and used a full 6 months of data. "
                "We added a trip-level analysis to ascertain our results on network effects after the initial analysis "
                "was done. Due to data retention limitations, we were only able to use the final 2 months of data for this second analysis."
            ),
        ),
    ]
    for p in s1_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s1_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_e3cc761c4fd41439dcff",
        archive_attempt_id="att_891dd9e8e77b46e6a9d4a1796bb7d165",
        requested_url="https://www.nature.com/articles/s44284-026-00443-x",
        final_url="https://www.nature.com/articles/s44284-026-00443-x",
        title="Urban congestion relief experiments through routing-app interventions",
        publisher="Nature Cities (Springer Nature / Google Research)",
        publication_date="2026-06-16",
        actual_jurisdiction="Multi-jurisdiction (10 US Metros: Atlanta, Boston, Chicago, Los Angeles, Miami, New York, Philadelphia, Salt Lake City, San Francisco, Seattle)",
        governing_level="Company",
        authority_names="Google Research & Google Maps Navigation Team",
        target_location_type="City",
        target_location="Atlanta, Boston, Chicago, Los Angeles, Miami, New York, Philadelphia, Salt Lake City, San Francisco, Seattle",
        source_type="other",
        factual_summary=(
            "Google Research and academic co-authors conducted randomized switchback routing experiments "
            "across approximately 100 congested arterial and highway segments in 10 major US metropolitan areas. "
            "By rerouting a small share of Google Maps navigation requests to alternative routes of equivalent road "
            "classification and comparable travel times, the intervention achieved a city-average 2% increase in vehicle "
            "speeds on intervened segments, a 0.7% improvement in city-average travel times, and projected annual CO2-equivalent "
            "emissions savings exceeding 1,000 tons per city."
        ),
        measures=[
            MeasureItem(
                actor="Google Research & Google Maps Navigation Engine",
                mechanism="Algorithmic marginal rerouting of a minor fraction of drivers from congested highway and arterial bottlenecks onto comparable equivalent-class alternative corridors.",
                purpose="Relieve bottleneck congestion, improve urban corridor speeds, shorten aggregate travel times, and decrease vehicle CO2 emissions.",
                status="piloted",
                governing_level="Company",
                authority_names="Google Research & Google Maps Navigation Team",
                target_location_type="City",
                target_location="Atlanta, Boston, Chicago, Los Angeles, Miami, New York, Philadelphia, Salt Lake City, San Francisco, Seattle",
                implementation_dates="6-month experimental period (with 2-month window for retained trip-level data)",
                reported_effects="Projected annual reductions exceeding 1,000 tons of CO2-equivalent emissions per city.",
                demonstrated_causal_effects=(
                    "Causally identified via randomized crossover/switchback design: 2% city-average increase in "
                    "vehicle speed on intervened segments; 0.7% improvement in city travel times; median speed effect "
                    "of 3.30% in Atlanta and 4.56% in Los Angeles on targeted freeway corridors."
                ),
            )
        ],
        community_feedback=[],
        category="Experimented Measures",
        supporting_passages=s1_passages,
        quality_flags=[],
        unresolved_questions=[
            "Extent of spillover effects on unmonitored local streets adjacent to alternative corridors.",
            "Long-term equilibrium behavior if uncoordinated third-party navigation apps (e.g. Apple Maps, Waze) counter-route traffic.",
            "Driver compliance retention if alternate routes involve minor individual travel time penalties."
        ],
        discovery_records=get_discoveries("src_e3cc761c4fd41439dcff"),
    ))

    # -----------------------------------------------------------------------
    # Source 2: NBC Los Angeles (Municipal council pilot to curb app traffic)
    # -----------------------------------------------------------------------
    s2_text = get_archive_text("data/archive/los_angeles/www.nbclosangeles.com/city-council-pilot-program-to-curb-waze-traffic-on-side-streets-162349--src_dc10ae72df82e2180ca6/attempt-001")
    s2_passages = [
        SupportingPassage(
            claim_topic="Council vote approving pilot program conditioning data-sharing agreements",
            verbatim_text=(
                "With mobile traffic applications such as Waze causing a flood of traffic on tiny side streets, "
                "the City Council Tuesday approved a pilot program to restrict the routing of vehicles onto certain "
                "streets as a condition of entering into data-sharing agreements with developers of mobile mapping applications."
            ),
        ),
        SupportingPassage(
            claim_topic="Councilman Krekorian rationale and unanimous 12-0 vote",
            verbatim_text=(
                '"There are tremendous advantages to apps like Waze," Councilman Paul Krekorian said last year '
                "when discussing his motion that led to Tuesday's 12-0 vote to create the pilot. \"They can make driving "
                "more efficient, but with every technological advance, any consequences that arise must be taken into account.\""
            ),
        ),
        SupportingPassage(
            claim_topic="Aiming for municipal-tech dialogue to increase neighborhood safety",
            verbatim_text=(
                'He added that the city "will have the go-ahead to start a dialogue with these tech companies '
                "to see if they will work more closely with us to reduce the impact their apps are having on small "
                'residential streets and increase the level of traffic safety in our neighborhoods."'
            ),
        ),
        SupportingPassage(
            claim_topic="Prior data agreement history and Waze corporate response",
            verbatim_text=(
                "Los Angeles had a data-sharing agreement with Waze from 2015 through 2017. "
                '"We comply with local laws and regulations where applicable and are always happy to have a dialogue '
                'with cities," a Waze spokesperson told NBC4 in a statement.'
            ),
        ),
    ]
    for p in s2_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s2_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_dc10ae72df82e2180ca6",
        archive_attempt_id="att_41933d3af29d415685ec2b065022fdd0",
        requested_url="https://www.nbclosangeles.com/news/city-council-pilot-program-to-curb-waze-traffic-on-side-streets/162349/",
        final_url="https://www.nbclosangeles.com/news/city-council-pilot-program-to-curb-waze-traffic-on-side-streets/162349/",
        title="City Council Approves Pilot Program to Curb Waze Traffic on Side Streets",
        publisher="NBC Los Angeles (KNBC) / City News Service",
        publication_date="2019-04-30",
        actual_jurisdiction="City of Los Angeles, California",
        governing_level="Government: City",
        authority_names="Los Angeles City Council, Los Angeles Department of Transportation (LADOT)",
        target_location_type="City",
        target_location="Los Angeles",
        source_type="news reporting",
        factual_summary=(
            "On April 30, 2019, the Los Angeles City Council unanimously voted (12-0) to approve a pilot program "
            "authorizing city officials to condition future municipal data-sharing agreements with navigation application "
            "developers (such as Waze) on commitments to restrict algorithmic routing of vehicles onto small residential side streets."
        ),
        measures=[
            MeasureItem(
                actor="Los Angeles City Council (Councilmember Paul Krekorian) & Mapping Application Developers",
                mechanism="Contractual conditioning of municipal traffic data-sharing agreements on app developers restricting vehicle routing onto specified residential side streets.",
                purpose="Curtail side-street traffic flooding and protect residential neighborhood traffic safety.",
                status="piloted",
                governing_level="Government: City",
                authority_names="Los Angeles City Council, Los Angeles Department of Transportation (LADOT)",
                target_location_type="City",
                target_location="Los Angeles",
                implementation_dates="Approved by City Council on April 30, 2019 (referencing 2015-2017 earlier data agreement)",
                reported_effects="Anticipated reduction in app-directed cut-through traffic through city-tech dialogue.",
                demonstrated_causal_effects="None demonstrated; no empirical traffic counts or algorithm-compliance audits reported.",
            )
        ],
        community_feedback=[
            CommunityFeedbackItem(
                who_expressed="Los Angeles neighborhood residents across residential districts",
                what_concerned_them="Navigation applications such as Waze causing severe traffic headaches and a flood of cut-through vehicles on tiny side streets not designed for heavy traffic.",
                which_measure="App-directed cut-through routing and municipal negotiations over data-sharing restrictions.",
            )
        ],
        category="Both",
        supporting_passages=s2_passages,
        quality_flags=[],
        unresolved_questions=[
            "Whether mapping platforms formally signed data-sharing agreements containing restrictive routing clauses.",
            "Legal viability of conditioning public data feeds on proprietary algorithmic routing behavior."
        ],
        discovery_records=get_discoveries("src_dc10ae72df82e2180ca6"),
    ))

    # -----------------------------------------------------------------------
    # Source 3: Next City (Leonia, NJ Rush-Hour Street Closures)
    # -----------------------------------------------------------------------
    s3_text = get_archive_text("data/archive/new_jersey/nextcity.org/new-jersey-town-closes-some-city-streets-to-drivers-who-dont-live-there--src_d1320840ff1688ff741e/attempt-001")
    s3_passages = [
        SupportingPassage(
            claim_topic="60-street rush-hour ban on non-resident drivers with $200 fine",
            verbatim_text=(
                "Residents of Leonia, New Jersey, are fed up with traffic apps that treat their small borough as a shortcut "
                "to the nearby George Washington Bridge. Starting Monday, officials began banning out-of-town drivers "
                "from using 60 streets during morning and evening rush hours, and threatened violators with a $200 fine."
            ),
        ),
        SupportingPassage(
            claim_topic="App-driven traffic volume and severe resident impact quoted by Police Chief Rowe",
            verbatim_text=(
                '“Without question, the game changer has been the navigation apps,” Tom Rowe, Leonia’s police chief, '
                'told the Times. “In the morning, if I sign onto my Waze account, I find there are 250,000 ‘Wazers’ '
                "in the area. When the primary roads become congested, it directs vehicles into Leonia and pushes them "
                "onto secondary and tertiary roads. We have had days when people can’t get out of their driveways.”"
            ),
        ),
        SupportingPassage(
            claim_topic="Vehicle tag mechanism and Waze restricted-access display",
            verbatim_text=(
                "This week, Leonia residents will begin displaying yellow tags on their cars, signaling to police "
                "that they belong on the “shut-down” streets. The road closures will show up on the Waze app as restricted "
                "access streets, according to a Waze spokesperson."
            ),
        ),
        SupportingPassage(
            claim_topic="Legal pushback and potential court challenges to street closure",
            verbatim_text=(
                "Borough officials claim the new measure is legal, but it could be tested in court — especially if it "
                "sets a precedent for other traffic-app weary towns across the country."
            ),
        ),
    ]
    for p in s3_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s3_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_d1320840ff1688ff741e",
        archive_attempt_id="att_925f41780bb1430ca5d5735cf2a95969",
        requested_url="https://nextcity.org/urbanist-news/new-jersey-town-closes-some-city-streets-to-drivers-who-dont-live-there",
        final_url="https://nextcity.org/urbanist-news/new-jersey-town-closes-some-city-streets-to-drivers-who-dont-live-there",
        title="New Jersey Town Closes Some City Streets to Drivers Who Don’t Live There",
        publisher="Next City (Author: Rachel Dovey)",
        publication_date="2018-01-22",
        actual_jurisdiction="Borough of Leonia, Bergen County, New Jersey",
        governing_level="Government: City",
        authority_names="Borough of Leonia (Borough Council & Leonia Police Department)",
        target_location_type="City",
        target_location="Leonia",
        source_type="news reporting",
        factual_summary=(
            "On January 22, 2018, the Borough of Leonia, New Jersey, closed 60 municipal streets to non-resident drivers "
            "during peak morning (6-10 AM) and evening (4-9 PM) rush hours, backed by yellow resident car tags and a $200 fine. "
            "The measure aimed to halt massive navigation-app traffic diversion heading to the George Washington Bridge. "
            "While Waze agreed to display the closures as restricted access, legal authorities and critics challenged the "
            "legality of privatizing public streets."
        ),
        measures=[
            MeasureItem(
                actor="Borough of Leonia Municipal Officials and Leonia Police Department",
                mechanism="Physical/regulatory closure of 60 streets to out-of-town drivers during morning/evening commute hours, enforced via yellow resident vehicle tags and $200 fines, reflected in Waze as restricted access.",
                purpose="Prevent hundreds of thousands of navigation-app drivers bypassing I-95/GWB congestion from overwhelming residential streets and blocking emergency responders.",
                status="implemented",
                governing_level="Government: City",
                authority_names="Borough of Leonia (Borough Council & Leonia Police Department)",
                target_location_type="City",
                target_location="Leonia",
                implementation_dates="Effective Monday, January 22, 2018 (rush hours: 6-10 AM and 4-9 PM)",
                reported_effects="Waze updated maps to reflect 60 streets as restricted access; residents reported relief from gridlock.",
                demonstrated_causal_effects="None demonstrated; no independent causal before-after traffic counts or regional spillover studies included.",
            )
        ],
        community_feedback=[
            CommunityFeedbackItem(
                who_expressed="Leonia residents",
                what_concerned_them="Trapped in driveways due to bumper-to-bumper cut-through traffic, with emergency medical and fire vehicles unable to access residential streets.",
                which_measure="Navigation app shortcuts through borough streets.",
            ),
            CommunityFeedbackItem(
                who_expressed="Regional commuters and legal critics",
                what_concerned_them="Illegality and inequity of closing publicly funded streets to non-residents, raising fundamental questions about public right-of-way ownership.",
                which_measure="Leonia's 60-street resident-only rush hour ban.",
            ),
            CommunityFeedbackItem(
                who_expressed="Municipal peers (e.g. Takoma Park, MD Public Works)",
                what_concerned_them="Enforceability dilemmas of 'No through traffic' rules, which require stopping every vehicle unlike simple turn restrictions.",
                which_measure="Municipal street access restrictions targeting through-traffic.",
            ),
        ],
        category="Both",
        supporting_passages=s3_passages,
        quality_flags=[],
        unresolved_questions=[
            "Whether the ordinance survived subsequent legal challenge by the New Jersey Attorney General or state courts.",
            "Net diversion volume forced onto neighboring corridors (e.g. Fort Lee, Englewood, I-95 mainlines)."
        ],
        discovery_records=get_discoveries("src_d1320840ff1688ff741e"),
    ))

    # -----------------------------------------------------------------------
    # Source 4: Seattle DOT (Delridge 26th Ave SW Diverter Outreach Summary)
    # -----------------------------------------------------------------------
    s4_text = get_archive_text("data/archive/seattle/www.seattle.gov/26th-20ave-20sw-20diverter-20outreach-20summary.pdf--src_23a1fcd9de5f1849cfa3/attempt-001")
    s4_passages = [
        SupportingPassage(
            claim_topic="Origin and goal of 26th Ave SW traffic diverters",
            verbatim_text=(
                "Ultimately, SDOT decided to use diverters at SW Brandon St and SW Genesee St on 26th Ave SW as a way "
                "to improve safety. A traffic diverter is made up of a curb and post that is designed to separate vehicle "
                "and bicycle traffic. The goal of the diverters along 26th Ave SW was to decrease cut-through traffic along "
                "the street and keep people walking, biking, and rolling safely."
            ),
        ),
        SupportingPassage(
            claim_topic="Community pushback and decision to pause/halt installation",
            verbatim_text=(
                "As we started public notification for installation on the diverters, we heard from many community "
                "members that they wanted to keep the current access they had at these two intersections, while the "
                "diverters restricted some turning movements. In response, we paused installation of the diverters to "
                "continue the conversation about how we can work together to make 26th Ave SW safer for people walking and biking."
            ),
        ),
        SupportingPassage(
            claim_topic="Outreach timeline and halting notification date",
            verbatim_text="7.28.20 Email Notified neighbors that SDOT would be halting construction of diverters.",
        ),
        SupportingPassage(
            claim_topic="Survey results: Resident dissatisfaction and concern about diversion to 25th Ave SW",
            verbatim_text=(
                "The biggest reasons against options one and two (diverters and modified diverters) was inconvenience "
                "to the people that lived there and over 10 people mentioned that reducing traffic on 26th Ave SW will "
                "just divert traffic to 25th Ave SW, a narrower street, and not actually fix the traffic problem in the area."
            ),
        ),
    ]
    for p in s4_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s4_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_23a1fcd9de5f1849cfa3",
        archive_attempt_id="att_6fe894d90ee14900983c15793abe70e9",
        requested_url="https://www.seattle.gov/documents/Departments/SDOT/TransitProgram/RapidRide/RapidRide%20H/26th%20Ave%20SW%20Diverter%20Outreach%20Summary.pdf",
        final_url="https://www.seattle.gov/documents/Departments/SDOT/TransitProgram/RapidRide/RapidRide%20H/26th%20Ave%20SW%20Diverter%20Outreach%20Summary.pdf",
        title="Delridge Neighborhood Greenway | 26th Ave SW Proposed Diverters: Outreach Summary",
        publisher="Seattle Department of Transportation (SDOT)",
        publication_date="2020-11-01",
        actual_jurisdiction="City of Seattle, Washington (Delridge Neighborhood)",
        governing_level="Government: City",
        authority_names="Seattle Department of Transportation (SDOT), Seattle City Council",
        target_location_type="City",
        target_location="Seattle",
        source_type="government material",
        factual_summary=(
            "Following the removal of bike lanes on Delridge Way SW for the RapidRide H Line transit project, "
            "SDOT proposed installing curb-and-post traffic diverters at SW Brandon St and SW Genesee St along 26th Ave SW "
            "to prevent vehicle cut-through traffic on the neighborhood greenway. After initial notification in July 2020, "
            "intense neighborhood backlash prompted SDOT to halt construction on July 28, 2020 and conduct a public outreach "
            "process (293 survey responses, 32 meeting participants). The community overwhelmingly rejected the diverter options, "
            "citing loss of neighborhood access and fears that traffic would merely divert to 25th Ave SW."
        ),
        measures=[
            MeasureItem(
                actor="Seattle Department of Transportation (SDOT) & Seattle City Council",
                mechanism="Physical traffic diverters (curb and post barriers restricting vehicle turns to right-in/right-out) to separate bike/pedestrian movements and block through-traffic.",
                purpose="Decrease cut-through traffic along the 26th Ave SW neighborhood greenway and improve bicycle/pedestrian safety.",
                status="withdrawn",
                governing_level="Government: City",
                authority_names="Seattle Department of Transportation (SDOT), Seattle City Council",
                target_location_type="City",
                target_location="Seattle",
                implementation_dates="City Council proviso February 21, 2020; flyering July 23, 2020; construction halted July 28, 2020; outreach survey Sept 25 - Oct 15, 2020.",
                reported_effects="Anticipated reduction in cut-through traffic and safer pedestrian/cyclist conditions.",
                demonstrated_causal_effects="None demonstrated; project halted prior to construction due to community opposition.",
            )
        ],
        community_feedback=[
            CommunityFeedbackItem(
                who_expressed="Delridge neighborhood residents (87.37% living near route; 293 survey respondents, 32 meeting participants)",
                what_concerned_them=(
                    "Inconvenience from lost turn access; loss of Delridge playfield parking; and concern that "
                    "restricting 26th Ave SW would simply push cut-through traffic onto 25th Ave SW, a much narrower residential street."
                ),
                which_measure="Proposed traffic diverters at SW Brandon St and SW Genesee St on 26th Ave SW.",
            ),
            CommunityFeedbackItem(
                who_expressed="Survey respondents suggesting alternatives",
                what_concerned_them="Questioned necessity of physical barriers; suggested retiming the traffic light at Brandon/Delridge to reduce cut-through incentive or installing a traffic circle/4-way stop.",
                which_measure="SDOT traffic diverter designs.",
            ),
        ],
        category="Both",
        supporting_passages=s4_passages,
        quality_flags=[],
        unresolved_questions=[
            "Whether SDOT ultimately replaced the diverters with a Stay Healthy Street or traffic circle.",
            "Whether Delridge Way signal retiming was evaluated as an alternative mitigation."
        ],
        discovery_records=get_discoveries("src_23a1fcd9de5f1849cfa3"),
    ))

    # -----------------------------------------------------------------------
    # Source 5: Waze Discuss (Connected Citizens Program Launch & Outreach)
    # *Note: Represents a unique source with preserved duplicate discovery records*
    # -----------------------------------------------------------------------
    s5_text = get_archive_text("data/archive/mixed/www.waze.com/waze-connected-citizens-program-102835--src_8f6b264845ca47814ba0/attempt-001")
    s5_passages = [
        SupportingPassage(
            claim_topic="Waze Connected Citizens bilateral data exchange program launch",
            verbatim_text=(
                "The Waze Connected Citizens program brings cities and citizens together to answer the questions "
                "“What’s happening, and where?” We exchange publicly available incident and road closure reports, "
                "enabling our government partners to respond more immediately to accidents and congestion on their roads. "
                "In turn, we aggregate our partners’ data on the Waze platform, resulting in one of the most succinct, "
                "thorough overviews of current road conditions today."
            ),
        ),
        SupportingPassage(
            claim_topic="Claimed benefits for drivers and municipal traffic planning",
            verbatim_text=(
                "With the addition of city data, Wazers will be even safer on the roads and more knowledgeable about "
                "construction, marathons, floods or anything else that can cause delays. And for our government partners, "
                "publicly-available Waze data is a powerful tool to build more efficient cities."
            ),
        ),
        SupportingPassage(
            claim_topic="Inaugural government and municipal partners across the US",
            verbatim_text=(
                "Several major cities & government agencies have already began partnering with Waze including Boston, "
                "Miami, Los Angeles, Pittsburgh, New York City & the NYPD. Additionally, the Kentucky Transportation Cabinet "
                "along with the Florida Department of Transportation have partnered with Waze as well with no costs to the taxpayers."
            ),
        ),
        SupportingPassage(
            claim_topic="Community template for volunteer outreach to local DOTs",
            verbatim_text=(
                "I’d like to share a generalized template I created for those who wish to reach out to their local Government "
                "Agencies & Cities or Department of Transportation. > Dear Mayor / Government Agency Name, > I am reaching out "
                "to you to see if [Agency Name] would be interested in considering a partnership with Waze."
            ),
        ),
    ]
    for p in s5_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s5_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_8f6b264845ca47814ba0",
        archive_attempt_id="att_5db8f86052ce4fabb59446ee1eeb1197",
        requested_url="https://www.waze.com/discuss/t/waze-connected-citizens-program/102835",
        final_url="https://www.waze.com/discuss/t/waze-connected-citizens-program/102835",
        title="Waze Connected Citizens Program - United States - Waze Discuss",
        publisher="Waze Discuss / Waze Mobile Ltd (Google)",
        publication_date="2014-12-08",
        actual_jurisdiction="Multi-jurisdiction / United States (Inaugural partners: Boston, Los Angeles County, NYPD, Florida DOT, Utah, Kentucky)",
        governing_level="Company",
        authority_names="Waze Mobile Ltd (Google), Boston, Los Angeles County, Miami, New York City / NYPD, Pittsburgh, Florida DOT, Utah DOT, Kentucky Transportation Cabinet",
        target_location_type="City",
        target_location="Boston, Los Angeles County, Miami, New York City, Pittsburgh; Florida, Utah, Kentucky",
        source_type="company statement",
        factual_summary=(
            "On the Waze Discuss map editor community forum, community leadership and Waze coordinators presented "
            "the Waze Connected Citizens Program (CCP), a free two-way data-sharing partnership between Waze and municipal/state "
            "transportation agencies. Municipalities supply authoritative road closure, construction, and incident feeds, while "
            "Waze provides real-time driver incident and congestion telemetry. Volunteer map editors coordinated outreach templates "
            "to onboard departments of transportation across the United States."
        ),
        measures=[
            MeasureItem(
                actor="Waze / Google and Municipal & State Transportation Agencies",
                mechanism="Bilateral real-time data-sharing agreement: public agencies exchange closure and construction data in return for real-time crowdsourced traffic telemetry at no taxpayer cost.",
                purpose="Optimize urban traffic flow, speed emergency response to incidents, and route navigation-app users around construction and bottlenecks.",
                status="implemented",
                governing_level="Company",
                authority_names="Waze Mobile Ltd (Google), Boston, Los Angeles County, Miami, New York City / NYPD, Pittsburgh, Florida DOT, Utah DOT, Kentucky Transportation Cabinet",
                target_location_type="City",
                target_location="Boston, Los Angeles County, Miami, New York City, Pittsburgh; Florida, Utah, Kentucky",
                implementation_dates="Officially launched October 1, 2014 ('W10' cohort); ongoing municipal onboarding 2014-2015+",
                reported_effects="Asserted to 'save everyone time and gas money on their daily commute' and build 'more efficient cities'.",
                demonstrated_causal_effects="None demonstrated; no empirical traffic impact studies or system-level delay evaluations reported.",
            )
        ],
        community_feedback=[
            CommunityFeedbackItem(
                who_expressed="Volunteer Waze map editors (Champs and State Managers like MGODLEW, dmcrandall, AlanOfTheBerg)",
                what_concerned_them=(
                    "How to recruit hesitant municipal DOTs; standardizing partnership outreach templates; "
                    "coordinating official wiki documentation; ensuring accurate map representation of local road networks."
                ),
                which_measure="Waze Connected Citizens Program government data partnerships.",
            )
        ],
        category="Experimented Measures",
        supporting_passages=s5_passages,
        quality_flags=[
            {
                "code": "ambiguous_publication_date",
                "signal": "Page metadata contained more than one publication date: 2014-12-08, 2015-02-22, 2015-02-23, 2015-03-16, 2015-03-17, 2015-03-24"
            }
        ],
        unresolved_questions=[
            "Whether data sharing provided cities any contractual leverage to limit routing through quiet residential neighborhoods.",
            "Whether municipal road closure data accelerated cut-through diversion onto parallel local streets."
        ],
        discovery_records=get_discoveries("src_8f6b264845ca47814ba0"),
    ))

    # -----------------------------------------------------------------------
    # Companion Source: LA City Clerk / SLNC (Community Testimony)
    # *Direct primary testimony submitted to Council File 11-2130-S4*
    # -----------------------------------------------------------------------
    s6_text = get_archive_text("data/archive/los_angeles/cityclerk.lacity.org/11-2130-s4_pc_ab_06-24-2019.pdf--src_02454d2db17a078f05f9/attempt-001")
    s6_passages = [
        SupportingPassage(
            claim_topic="SLNC Community Impact Statement documenting bypass traffic on Angus Street",
            verbatim_text=(
                "Importantly, and separate from the road diet, an increase in bypass traffic on the adjacent local "
                "streets was also noted by LADOT. On June 13, 2019, stakeholders in attendance (more than 20) at the "
                "Committee meeting described the treacherous conditions on Angus Street, community members expressed "
                "their fear and specifically that they constantly fear for their own and their children’s lives due to "
                "the bypass traffic that speeds on Angus Street."
            ),
        ),
        SupportingPassage(
            claim_topic="Direct resident testimony from Angus Street on ignored stop signs and hostility",
            verbatim_text=(
                "Our home is at the stop sign at the intersection of Angus and Kenilworth that is often ignored. "
                "I cannot tell you how many times I've been yelled at, honked at, and called various names, while "
                "simply trying to back out of my garage or walk across the street to my house. We've been here since 2013 "
                "and while it wasn't great when we moved it, its horrible now. I have two small children, one of whom walks "
                "to school in the neighborhood. He has learned to put up his hand to ask cars to stop so he can cross the "
                "street (at a stop sign!!) to go home. It's amazing how many cars ignore him. Please help us make our street safe again!"
            ),
        ),
    ]
    for p in s6_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s6_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_02454d2db17a078f05f9",
        archive_attempt_id="att_fe674e659af44b6cad1efedf5ad0a9e9",
        requested_url="https://cityclerk.lacity.org/onlinedocs/2011/11-2130-S4_PC_AB_06-24-2019.pdf",
        final_url="https://cityclerk.lacity.org/onlinedocs/2011/11-2130-S4_PC_AB_06-24-2019.pdf",
        title="Communication from Public: Council File #11-2130-S4 (Rowena Ave / Angus St Cut-Through Mitigation)",
        publisher="Los Angeles City Clerk / Silver Lake Neighborhood Council",
        publication_date="2019-06-24",
        actual_jurisdiction="City of Los Angeles, California (Silver Lake, Council District 4)",
        governing_level="Government: City",
        authority_names="Silver Lake Neighborhood Council, Los Angeles City Council, Los Angeles Department of Transportation (LADOT)",
        target_location_type="City",
        target_location="Los Angeles",
        source_type="community testimony",
        factual_summary=(
            "Official Community Impact Statement and public comment letters submitted to the Los Angeles City Council "
            "regarding Council File 11-2130-S4. Silver Lake stakeholders and the neighborhood council testified that while "
            "the Rowena Avenue road diet improved arterial safety, cut-through traffic spilled over onto adjacent residential streets, "
            "producing treacherous speeding conditions on Angus Street and Waverly Drive. The neighborhood council unanimously (18-0) "
            "demanded that LADOT convert Angus Street to a one-way westbound corridor."
        ),
        measures=[
            MeasureItem(
                actor="Silver Lake Neighborhood Council, Los Angeles City Council (CD4), LADOT",
                mechanism="Converting Angus Street between Moreno Dr and Kenilworth Ave to a one-way westbound street; installing pedestrian-scale lighting and crosswalks; studying traffic calming at Waverly Dr and Glendale Blvd.",
                purpose="Mitigate dangerous speeding cut-through bypass traffic displaced from Rowena Avenue onto local residential streets.",
                status="proposed",
                governing_level="Government: City",
                authority_names="Silver Lake Neighborhood Council, Los Angeles City Council, Los Angeles Department of Transportation (LADOT)",
                target_location_type="City",
                target_location="Los Angeles",
                implementation_dates="Approved 18-0 by SLNC Governing Board on June 18, 2019; submitted to City Clerk on June 24, 2019.",
                reported_effects="LADOT confirmed reduction in collision frequency on Rowena Avenue, but noted concurrent increase in bypass traffic on local streets.",
                demonstrated_causal_effects="None demonstrated for proposed one-way conversion; observational collision reduction documented on re-engineered arterial.",
            )
        ],
        community_feedback=[
            CommunityFeedbackItem(
                who_expressed="Silver Lake Neighborhood Council and Angus Street residents (Katie Singh, Annie Field)",
                what_concerned_them=(
                    "Constant fear for children's lives due to speeding bypass cut-through traffic, ignored stop signs, "
                    "and driver hostility (honking and yelling) toward residents backing out of garages."
                ),
                which_measure="Council File 11-2130-S4 / Cut-through traffic mitigation on Angus Street.",
            )
        ],
        category="Both",
        supporting_passages=s6_passages,
        quality_flags=[],
        unresolved_questions=[
            "Whether LA City Council approved funding for the Angus Street one-way conversion.",
            "Whether navigation apps adjusted routes following the proposed one-way conversion."
        ],
        discovery_records=get_discoveries("src_02454d2db17a078f05f9"),
    ))

    # Validate all entries against the taxonomy codebook
    for e in entries:
        if e.governing_level not in ALLOWED_GOVERNING_LEVELS:
            raise ValueError(f"Invalid governing_level '{e.governing_level}' in source {e.source_id}")
        if e.target_location_type not in ALLOWED_TARGET_LOCATION_TYPES:
            raise ValueError(f"Invalid target_location_type '{e.target_location_type}' in source {e.source_id}")
        if e.category not in ALLOWED_CATEGORIES:
            raise ValueError(f"Invalid category '{e.category}' in source {e.source_id}")
        if e.source_type not in ALLOWED_SOURCE_TYPES:
            raise ValueError(f"Invalid source_type '{e.source_type}' in source {e.source_id}")
        for m in e.measures:
            if m.status not in ALLOWED_MEASURE_STATUSES:
                raise ValueError(f"Invalid measure status '{m.status}' in source {e.source_id}")
            if m.governing_level and m.governing_level not in ALLOWED_GOVERNING_LEVELS:
                raise ValueError(f"Invalid measure governing_level '{m.governing_level}' in source {e.source_id}")
            if m.target_location_type and m.target_location_type not in ALLOWED_TARGET_LOCATION_TYPES:
                raise ValueError(f"Invalid measure target_location_type '{m.target_location_type}' in source {e.source_id}")

    con.close()
    return entries


def build_all_analyses(db_path: Path, archive_root: Path) -> list[ResearchAnalysisEntry]:
    """Build and validate research analysis entries for all archived sources in the inventory."""
    from news_importer.all_analyses import build_all_analyses as _build_all
    return _build_all(db_path, archive_root)


# ---------------------------------------------------------------------------
# Exporting Analysis Datasets
# ---------------------------------------------------------------------------

def export_analysis_json(entries: list[ResearchAnalysisEntry], output_path: Path) -> None:
    """Export the validated analysis dataset to formatted JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [asdict(e) for e in entries]
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def export_analysis_csv(entries: list[ResearchAnalysisEntry], output_path: Path) -> None:
    """Export a flattened tabular summary of analysis findings to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "source_id",
        "archive_attempt_id",
        "title",
        "publisher",
        "publication_date",
        "actual_jurisdiction",
        "governing_level",
        "authority_names",
        "target_location_type",
        "target_location",
        "source_type",
        "category",
        "measure_actors",
        "measure_mechanisms",
        "measure_statuses",
        "measure_implementation_dates",
        "reported_effects",
        "demonstrated_causal_effects",
        "feedback_stakeholders",
        "feedback_concerns",
        "quality_flag_codes",
        "unresolved_questions",
        "discovery_ids",
        "requested_url",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for e in entries:
            writer.writerow({
                "source_id": e.source_id,
                "archive_attempt_id": e.archive_attempt_id,
                "title": e.title,
                "publisher": e.publisher,
                "publication_date": e.publication_date or "",
                "actual_jurisdiction": e.actual_jurisdiction,
                "governing_level": e.governing_level,
                "authority_names": e.authority_names,
                "target_location_type": e.target_location_type,
                "target_location": e.target_location,
                "source_type": e.source_type,
                "category": e.category,
                "measure_actors": "; ".join(m.actor for m in e.measures),
                "measure_mechanisms": "; ".join(m.mechanism for m in e.measures),
                "measure_statuses": "; ".join(m.status for m in e.measures),
                "measure_implementation_dates": "; ".join(m.implementation_dates or "" for m in e.measures),
                "reported_effects": "; ".join(m.reported_effects or "" for m in e.measures),
                "demonstrated_causal_effects": "; ".join(m.demonstrated_causal_effects or "" for m in e.measures),
                "feedback_stakeholders": "; ".join(cf.who_expressed for cf in e.community_feedback),
                "feedback_concerns": "; ".join(cf.what_concerned_them for cf in e.community_feedback),
                "quality_flag_codes": "; ".join(q["code"] for q in e.quality_flags),
                "unresolved_questions": "; ".join(e.unresolved_questions),
                "discovery_ids": "; ".join(d.discovery_id for d in e.discovery_records),
                "requested_url": e.requested_url,
            })
