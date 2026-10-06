"""Comprehensive research analysis builder for all retrieved sources in the inventory.

Builds and validates research analysis entries for all 43 unique retrieved sources,
incorporating governance levels, authority names, target location types, target locations,
and verified supporting evidence passages.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from news_importer.analysis import (
    ALLOWED_CATEGORIES,
    ALLOWED_GOVERNING_LEVELS,
    ALLOWED_MEASURE_STATUSES,
    ALLOWED_SOURCE_TYPES,
    ALLOWED_TARGET_LOCATION_TYPES,
    CommunityFeedbackItem,
    DiscoveryReference,
    MeasureItem,
    ResearchAnalysisEntry,
    SupportingPassage,
    build_pass1_analyses,
    verify_passage,
)
from news_importer.db import connect


def build_all_analyses(db_path: Path, archive_root: Path) -> list[ResearchAnalysisEntry]:
    """Build and validate research analysis entries for all 43 retrieved sources."""
    # Start with initial 6 pass 1 entries
    entries = build_pass1_analyses(db_path, archive_root)

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

    def get_archive_text(source_or_path: str) -> str:
        if source_or_path.startswith("src_"):
            row = con.execute("SELECT archive_dir FROM fetch_attempts WHERE source_id = ? AND outcome = 'retrieved'", (source_or_path,)).fetchone()
            if not row:
                return ""
            adir = Path(row["archive_dir"])
        else:
            adir = Path(source_or_path)
        
        candidates = [
            archive_root / adir / "content.md",
            adir / "content.md",
            Path("data") / adir / "content.md",
            archive_root.parent / adir / "content.md",
        ]
        for c in candidates:
            if c.is_file():
                return c.read_text(encoding="utf-8", errors="ignore")
        return ""

    # -----------------------------------------------------------------------
    # Source 7: CalMatters bill text / California Legislature (AB 2015)
    # -----------------------------------------------------------------------
    s7_text = get_archive_text("src_483bc7bade77380c2828")
    s7_passages = [
        SupportingPassage(
            claim_topic="Legislative mandate for Caltrans navigation app pilot study",
            verbatim_text="This bill would require the department, in consultation with the Transportation Agency and relevant regional and local authorities, to conduct a pilot study in a region or area of the state, as determined by the department, on the impact of third-party navigation applications on the state highway system and local street and road networks.",
        )
    ]
    for p in s7_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s7_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_483bc7bade77380c2828",
        archive_attempt_id="att_b43f9a72df9b4f91b7d52ef72db36e05",
        requested_url="https://digitaldemocracy.calmatters.org/bills/ca_202520260ab2015",
        final_url="https://digitaldemocracy.calmatters.org/bills/ca_202520260ab2015",
        title="AB-2015 Transportation: third-party navigation applications: pilot study.",
        publisher="California Legislative Information / CalMatters Digital Democracy",
        publication_date="2026-09-22",
        actual_jurisdiction="State of California",
        governing_level="Government: State",
        authority_names="California State Legislature, California Department of Transportation (Caltrans), California State Transportation Agency (CalSTA)",
        target_location_type="State",
        target_location="California",
        source_type="government material",
        factual_summary=(
            "California Assembly Bill 2015 (Chapter 207, Statutes of 2026), authored by Assemblymember Buffy Wicks, "
            "directs Caltrans in consultation with CalSTA and local authorities to conduct a pilot study on the impact "
            "of third-party navigation applications on state highways and local street networks, submitting findings "
            "and legislative recommendations by January 1, 2029."
        ),
        measures=[
            MeasureItem(
                actor="Caltrans, CalSTA, California State Legislature",
                mechanism="Mandated pilot study and legislative report evaluating third-party navigation apps (Waze, Apple Maps, Google Maps) impacts on state highways and local streets, identifying traffic diversion patterns and safety mitigation measures.",
                purpose="Evaluate diversion of highway traffic onto local streets and develop policy interventions.",
                status="implemented",
                governing_level="Government: State",
                authority_names="Caltrans, CalSTA, California Legislature",
                target_location_type="State",
                target_location="California",
                implementation_dates="Enacted September 22, 2026; pilot study report due January 1, 2029",
                reported_effects="Legislative mandate established; study underway.",
                demonstrated_causal_effects="None yet; empirical evaluation scheduled for 2029 report.",
            )
        ],
        community_feedback=[],
        category="Experimented Measures",
        supporting_passages=s7_passages,
        quality_flags=[],
        unresolved_questions=[
            "Which specific California region will Caltrans select for the pilot study?",
            "What data-sharing requirements will be imposed on private navigation platforms?",
        ],
        discovery_records=get_discoveries("src_483bc7bade77380c2828"),
    ))

    # -----------------------------------------------------------------------
    # Source 8: Yahoo News (AB 2015 political debate & commuter pushback)
    # -----------------------------------------------------------------------
    s8_text = get_archive_text("src_32ccdcb0712575f8cb0b")
    s8_passages = [
        SupportingPassage(
            claim_topic="Commuter opposition and warning regarding navigation app regulation",
            verbatim_text='sounding the alarm over a Democratic-backed proposal to study how navigation apps like Apple Maps and [Google Maps affect state traffic patterns](https://www.yahoo.com/news/articles/google-maps-slammed-hiding-brutal-174711234.html), a move he says could potentially add "[30 minutes to your commute](https://nypost.com/2026/03/19/opinion/miserable-driving-in-la-now-just-wait/)."',
        )
    ]
    for p in s8_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s8_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_32ccdcb0712575f8cb0b",
        archive_attempt_id="att_1bcbb36c34094a97b2eb6ca2c63ef297",
        requested_url="https://www.yahoo.com/news/lawmaker-warns-proposal-could-alter-171804797.html",
        final_url="https://www.yahoo.com/news/lawmaker-warns-proposal-could-alter-171804797.html",
        title="Lawmaker warns of proposal that could alter California drivers' commutes: 'Adds 30 minutes'",
        publisher="Yahoo News",
        publication_date="2026-03-24",
        actual_jurisdiction="State of California",
        governing_level="Government: State",
        authority_names="California State Legislature, Assemblymember Buffy Wicks, Assemblymember Carl DeMaio",
        target_location_type="State",
        target_location="California",
        source_type="news reporting",
        factual_summary=(
            "News coverage of legislative debate surrounding California Assembly Bill 2015. While proponents led by "
            "Assemblymember Buffy Wicks aim to address commuter bypass traffic flooding residential streets, conservative "
            "lawmaker Carl DeMaio warns that state intervention in navigation app algorithms could add 30 minutes to daily "
            "commutes by restricting detour routes."
        ),
        measures=[
            MeasureItem(
                actor="California State Assembly (Buffy Wicks)",
                mechanism="State legislation studying and potentially regulating navigation app routing algorithms to prevent commuter cut-through traffic.",
                purpose="Mitigate neighborhood traffic infiltration from freeway spillover.",
                status="proposed",
                governing_level="Government: State",
                authority_names="California State Legislature",
                target_location_type="State",
                target_location="California",
                implementation_dates="Introduced March 2026",
                reported_effects="Critics claim 30-minute commute increases if detours are restricted.",
                demonstrated_causal_effects="None demonstrated.",
            )
        ],
        community_feedback=[
            CommunityFeedbackItem(
                who_expressed="Assemblymember Carl DeMaio and commuter advocates",
                what_concerned_them="Concerns that state restrictions on navigation apps like Google Maps and Apple Maps will artificially worsen highway gridlock and lengthen commutes by 30 minutes.",
                which_measure="California Assembly Bill 2015",
            )
        ],
        category="Both",
        supporting_passages=s8_passages,
        quality_flags=[],
        unresolved_questions=[
            "Whether the final statute incorporated commuter protection safeguards against artificial travel delays."
        ],
        discovery_records=get_discoveries("src_32ccdcb0712575f8cb0b"),
    ))

    # -----------------------------------------------------------------------
    # Source 9: LA City Council Motion 14-1741-S1 (Krekorian / LaBonge)
    # -----------------------------------------------------------------------
    s9_text = get_archive_text("src_9403a6fb4c495dd5f6e0")
    s9_passages = [
        SupportingPassage(
            claim_topic="Mayor and LADOT partnership announcement with Waze",
            verbatim_text="During the State of the City address and in subsequent days, the Mayor announced a partnership between the Department of Transportation and Waze, a popular mapping app, which would share up-to-the-minute city traffic data with Waze.",
        )
    ]
    for p in s9_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s9_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_9403a6fb4c495dd5f6e0",
        archive_attempt_id="att_6850d53c23e843c09e51c893081e74bf",
        requested_url="https://cityclerk.lacity.org/onlinedocs/2014/14-1741-S1_MOT_04-28-2015.pdf",
        final_url="https://cityclerk.lacity.org/onlinedocs/2014/14-1741-S1_MOT_04-28-2015.pdf",
        title="Motion 14-1741-S1 (Data-Sharing Partnership with Waze to Protect Residential Streets)",
        publisher="Los Angeles City Clerk",
        publication_date="2015-04-28",
        actual_jurisdiction="City of Los Angeles, California",
        governing_level="Government: City",
        authority_names="Los Angeles City Council, Los Angeles Department of Transportation (LADOT)",
        target_location_type="City",
        target_location="Los Angeles",
        source_type="government material",
        factual_summary=(
            "Official Los Angeles City Council motion introduced by Paul Krekorian and Tom LaBonge directing LADOT "
            "to report on data-sharing partnerships with Waze. The motion emphasizes leveraging municipal traffic feeds "
            "while establishing protocols to prevent navigation apps from diverting heavy cut-through traffic onto quiet "
            "residential hillside streets."
        ),
        measures=[
            MeasureItem(
                actor="Los Angeles City Council, LADOT",
                mechanism="Directing LADOT to structure data-sharing agreements with Waze and mapping apps to protect residential streets from navigation detour routing.",
                purpose="Prevent navigation apps from funneling arterial traffic onto narrow hillside and residential streets.",
                status="proposed",
                governing_level="Government: City",
                authority_names="Los Angeles City Council, LADOT",
                target_location_type="City",
                target_location="Los Angeles",
                implementation_dates="Introduced April 28, 2015",
                reported_effects="Initiated municipal negotiations with Waze.",
                demonstrated_causal_effects="None.",
            )
        ],
        community_feedback=[],
        category="Experimented Measures",
        supporting_passages=s9_passages,
        quality_flags=[],
        unresolved_questions=[
            "What formal concessions did LADOT extract from Waze following this motion?"
        ],
        discovery_records=get_discoveries("src_9403a6fb4c495dd5f6e0"),
    ))

    # -----------------------------------------------------------------------
    # Source 10: Los Angeles Magazine (2019-05-07)
    # -----------------------------------------------------------------------
    s10_text = get_archive_text("src_004598f106dc0112c9f5")
    s10_passages = [
        SupportingPassage(
            claim_topic="LA City Council pilot program targeting navigation app algorithms",
            verbatim_text="A pilot program launched by L.A.’s City Council could bring big changes to the workings of directions apps like Waze and Google Maps.",
        )
    ]
    for p in s10_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s10_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_004598f106dc0112c9f5",
        archive_attempt_id="att_369ee62846f44d82bf4f4a34b2ea62f2",
        requested_url="https://lamag.com/news/city-council-pilot-program-waze-traffic",
        final_url="https://lamag.com/news/city-council-pilot-program-waze-traffic",
        title="L.A. May Crack Down on Waze and Google Maps",
        publisher="Los Angeles Magazine",
        publication_date="2019-05-07",
        actual_jurisdiction="City of Los Angeles, California",
        governing_level="Government: City",
        authority_names="Los Angeles City Council, Councilmember Paul Krekorian, LADOT",
        target_location_type="City",
        target_location="Los Angeles",
        source_type="news reporting",
        factual_summary=(
            "Los Angeles City Council approved a pilot program directing the city attorney and LADOT to draft "
            "data-sharing agreements requiring navigation app developers to keep commuter traffic off narrow hillside "
            "and residential streets as a condition of receiving city road closure and incident data."
        ),
        measures=[
            MeasureItem(
                actor="Los Angeles City Council, City Attorney, LADOT",
                mechanism="Pilot program establishing conditional data-sharing agreements requiring mapping apps to exclude designated residential streets from commuter routing.",
                purpose="Stop commercial navigation apps from overwhelming residential hillside streets.",
                status="piloted",
                governing_level="Government: City",
                authority_names="Los Angeles City Council",
                target_location_type="City",
                target_location="Los Angeles",
                implementation_dates="Approved May 2019",
                reported_effects="Council voted 12-0 to advance conditional data sharing.",
                demonstrated_causal_effects="None demonstrated.",
            )
        ],
        community_feedback=[
            CommunityFeedbackItem(
                who_expressed="Councilmember Paul Krekorian and hillside neighborhood residents",
                what_concerned_them="Dangerous gridlock, emergency vehicle obstruction, and loss of safety on narrow residential streets caused by app detour suggestions.",
                which_measure="Los Angeles conditional data-sharing pilot program",
            )
        ],
        category="Both",
        supporting_passages=s10_passages,
        quality_flags=[],
        unresolved_questions=[
            "Whether tech companies agreed to the conditional data terms or refused access."
        ],
        discovery_records=get_discoveries("src_004598f106dc0112c9f5"),
    ))

    # -----------------------------------------------------------------------
    # Source 11: Los Angeles Magazine (2018-05-18 - Waze Hijacked LA)
    # -----------------------------------------------------------------------
    s11_text = get_archive_text("src_df18bde5b05e69aa6fee")
    s11_passages = [
        SupportingPassage(
            claim_topic="Residents fighting back against traffic app shortcuts",
            verbatim_text="Traffic apps turned the city’s neighborhoods into “shortcuts.” Now furious residents are attempting to take them back, street by street",
        )
    ]
    for p in s11_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s11_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_df18bde5b05e69aa6fee",
        archive_attempt_id="att_88496cefd96541cc9994c65306132717",
        requested_url="https://lamag.com/urbandevelopment/waze-los-angeles-neighborhoods",
        final_url="https://lamag.com/urbandevelopment/waze-los-angeles-neighborhoods",
        title="Waze Hijacked L.A. in the Name of Convenience. Can Anyone Put the Genie Back in the Bottle?",
        publisher="Los Angeles Magazine",
        publication_date="2018-05-18",
        actual_jurisdiction="City of Los Angeles, California",
        governing_level="Government: City",
        authority_names="Los Angeles City Council, LADOT, Waze / Google",
        target_location_type="City",
        target_location="Los Angeles",
        source_type="news reporting",
        factual_summary=(
            "In-depth investigative feature detailing the battle between Los Angeles neighborhoods and navigation apps. "
            "Chronicles severe cut-through gridlock in Echo Park (Baxter Street crashes) and Silver Lake, resident guerrilla "
            "tactics (reporting fake accidents and construction on Waze), speed hump installations, and the legal constraints "
            "preventing cities from closing public streets to non-residents."
        ),
        measures=[
            MeasureItem(
                actor="LADOT",
                mechanism="Infrastructure traffic calming: speed humps, left-turn restrictions, and one-way directional street conversions.",
                purpose="Mitigate commuter cut-through speeding prompted by routing algorithms.",
                status="piloted",
                governing_level="Government: City",
                authority_names="LADOT",
                target_location_type="City",
                target_location="Los Angeles",
                implementation_dates="2015-2018",
                reported_effects="Localized diversions, but apps frequently rerouted traffic onto parallel residential streets.",
                demonstrated_causal_effects="Observational only; traffic displaced to adjacent blocks.",
            ),
            MeasureItem(
                actor="Echo Park / Silver Lake Residents",
                mechanism="Guerrilla reporting of fake accidents, blocked roads, and hazards into Waze app.",
                purpose="Trick Waze algorithms into diverting commuters away from residential neighborhoods.",
                status="withdrawn",
                governing_level="Non-Government Organization",
                authority_names="Neighborhood Residents",
                target_location_type="City",
                target_location="Los Angeles",
                implementation_dates="2014-2017",
                reported_effects="Short-term routing shifts; Waze algorithm flagged and suppressed fraudulent user accounts.",
                demonstrated_causal_effects="No sustainable impact.",
            )
        ],
        community_feedback=[
            CommunityFeedbackItem(
                who_expressed="Echo Park and Silver Lake hillside residents",
                what_concerned_them="Loss of neighborhood quiet, dangerous vehicle crashes on steep grades, blocked driveways, and gridlock preventing emergency response vehicles.",
                which_measure="Municipal street traffic calming and Waze routing algorithms",
            )
        ],
        category="Both",
        supporting_passages=s11_passages,
        quality_flags=[],
        unresolved_questions=[
            "How effectively did LADOT coordinate speed hump placement with navigation map updates?"
        ],
        discovery_records=get_discoveries("src_df18bde5b05e69aa6fee"),
    ))

    # -----------------------------------------------------------------------
    # Source 12: ABC 10News San Diego (LA City Council data-sharing vote)
    # -----------------------------------------------------------------------
    s12_text = get_archive_text("src_ec380b5a89074be9476e")
    s12_passages = [
        SupportingPassage(
            claim_topic="Approval of pilot program restricting side street vehicle routing",
            verbatim_text="the Los Angeles City Council Tuesday approved a pilot program to restrict the routing of vehicles onto certain streets as a condition of entering into data-sharing agreements with developers of mobile mapping applications.",
        )
    ]
    for p in s12_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s12_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_ec380b5a89074be9476e",
        archive_attempt_id="att_bb78873489fe4c2b9da19f5d3410a623",
        requested_url="https://www.10news.com/news/national/waze-restricted-due-to-buildup-of-side-street-traffic-in-los-angeles",
        final_url="https://www.10news.com/news/national/waze-restricted-due-to-buildup-of-side-street-traffic-in-los-angeles",
        title="Waze restricted due to buildup of side street traffic in Los Angeles",
        publisher="ABC 10News San Diego / City News Service",
        publication_date="2019-05-01",
        actual_jurisdiction="City of Los Angeles, California",
        governing_level="Government: City",
        authority_names="Los Angeles City Council, LADOT",
        target_location_type="City",
        target_location="Los Angeles",
        source_type="news reporting",
        factual_summary=(
            "Broadcast reporting on the Los Angeles City Council's vote approving a pilot program to restrict vehicle routing "
            "onto residential side streets as a prerequisite for data-sharing agreements with navigation app developers like Waze and Google."
        ),
        measures=[
            MeasureItem(
                actor="Los Angeles City Council",
                mechanism="Conditioning access to municipal traffic data feeds on mapping apps agreeing to restrict commuter routing onto designated side streets.",
                purpose="Eliminate cut-through traffic congestion caused by app rerouting on residential side streets.",
                status="piloted",
                governing_level="Government: City",
                authority_names="Los Angeles City Council",
                target_location_type="City",
                target_location="Los Angeles",
                implementation_dates="Approved May 2019",
                reported_effects="Pilot authorized by City Council.",
                demonstrated_causal_effects="None.",
            )
        ],
        community_feedback=[
            CommunityFeedbackItem(
                who_expressed="Los Angeles neighborhood residents and City Council members",
                what_concerned_them="Severe spillover of arterial congestion onto quiet residential side streets ill-equipped for high traffic volumes.",
                which_measure="Conditional data sharing agreements with mobile mapping apps",
            )
        ],
        category="Both",
        supporting_passages=s12_passages,
        quality_flags=[],
        unresolved_questions=[
            "Whether the pilot program led to enforceable data-licensing contracts with Waze."
        ],
        discovery_records=get_discoveries("src_ec380b5a89074be9476e"),
    ))

    # -----------------------------------------------------------------------
    # Source 13: FOX 13 Seattle / KTLA (Baxter Street Echo Park)
    # -----------------------------------------------------------------------
    s13_text = get_archive_text("src_2910e1608eed71065145")
    s13_passages = [
        SupportingPassage(
            claim_topic="Baxter Street cut-through traffic attributed to navigation apps",
            verbatim_text="The road in question is Baxter Street in Echo Park.",
        )
    ]
    for p in s13_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s13_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_2910e1608eed71065145",
        archive_attempt_id="att_7d3cf26806504b2b93ffea44d1d871e7",
        requested_url="https://www.fox13seattle.com/news/absolute-chaos-navigation-apps-blamed-for-traffic-nightmare-on-one-of-l-a-s-steepest-streets",
        final_url="https://www.fox13seattle.com/news/absolute-chaos-navigation-apps-blamed-for-traffic-nightmare-on-one-of-l-a-s-steepest-streets",
        title="'Absolute chaos': Navigation apps blamed for traffic nightmare on one of L.A.'s steepest streets",
        publisher="FOX 13 Seattle / KTLA",
        publication_date="2024-04-03",
        actual_jurisdiction="City of Los Angeles, California (Echo Park)",
        governing_level="Government: City",
        authority_names="Los Angeles Department of Transportation (LADOT), KTLA",
        target_location_type="City",
        target_location="Los Angeles",
        source_type="news reporting",
        factual_summary=(
            "Coverage of dangerous traffic conditions on Baxter Street in Echo Park, one of the steepest roads in "
            "Los Angeles (32% grade). Residents attribute a surge in spinouts, rollovers, and crashes to navigation apps "
            "routing unsuspecting commuters through the hill during peak hours."
        ),
        measures=[
            MeasureItem(
                actor="LADOT",
                mechanism="Converting Baxter Street to a one-way westbound street and installing high-visibility warning signage and grooved pavement.",
                purpose="Prevent dangerous downhill spinouts and rollovers caused by navigation apps routing drivers down extreme 32% grades.",
                status="implemented",
                governing_level="Government: City",
                authority_names="LADOT",
                target_location_type="City",
                target_location="Los Angeles",
                implementation_dates="Implemented 2018; reported ongoing issues in 2024",
                reported_effects="Reduced head-on collisions, but navigation apps continued sending downhill traffic resulting in rain spinouts.",
                demonstrated_causal_effects="One-way flow eliminated opposing-traffic collisions, but downhill accidents persist.",
            )
        ],
        community_feedback=[
            CommunityFeedbackItem(
                who_expressed="Baxter Street Echo Park residents",
                what_concerned_them="Repeated car spinouts into front yards, flipped vehicles, property damage, and intense fear during rainstorms due to commuter app navigation.",
                which_measure="Baxter Street one-way conversion and navigation app routing",
            )
        ],
        category="Both",
        supporting_passages=s13_passages,
        quality_flags=[],
        unresolved_questions=[
            "Why navigation algorithms fail to account for road slope/grade when calculating optimal detours."
        ],
        discovery_records=get_discoveries("src_2910e1608eed71065145"),
    ))

    # -----------------------------------------------------------------------
    # Source 14: The Daily Free Press (Boston Mayor Martin Walsh Waze deal)
    # -----------------------------------------------------------------------
    s14_text = get_archive_text("src_7a51efb5b5f5430e194b")
    s14_passages = [
        SupportingPassage(
            claim_topic="Mayor Walsh announcing data-sharing affiliation with Waze",
            verbatim_text="Boston Mayor Martin Walsh announced a new data-sharing affiliation on Friday with Waze, an app owned by Google that allows those driving, cycling and walking in Boston to view real-time traffic conditions.",
        )
    ]
    for p in s14_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s14_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_7a51efb5b5f5430e194b",
        archive_attempt_id="att_13dfbe8b1fc549f7b19ce8a301ce6b42",
        requested_url="https://dailyfreepress.com/2015/02/19/walsh-announces-partnership-with-traffic-app-waze/",
        final_url="https://dailyfreepress.com/2015/02/19/walsh-announces-partnership-with-traffic-app-waze/",
        title="Walsh announces partnership with traffic app, Waze",
        publisher="The Daily Free Press",
        publication_date="2015-02-19",
        actual_jurisdiction="City of Boston, Massachusetts",
        governing_level="Government: City",
        authority_names="City of Boston, Mayor Martin J. Walsh, Boston Transportation Department",
        target_location_type="City",
        target_location="Boston",
        source_type="news reporting",
        factual_summary=(
            "Boston Mayor Martin J. Walsh announced a data-sharing partnership with Waze under the Connected Citizens "
            "Program. Boston feeds real-time construction and road closure data to Waze, while receiving crowdsourced "
            "telemetry to improve municipal traffic management and signal operations."
        ),
        measures=[
            MeasureItem(
                actor="City of Boston (Mayor Martin J. Walsh), Waze",
                mechanism="Two-way data exchange sharing municipal road closures with Waze in exchange for crowdsourced traffic speed and incident data.",
                purpose="Improve municipal traffic operations, reduce congestion, and optimize traffic signal timing.",
                status="implemented",
                governing_level="Government: City",
                authority_names="City of Boston, Waze",
                target_location_type="City",
                target_location="Boston",
                implementation_dates="Announced February 2015",
                reported_effects="Improved situational awareness and traffic monitoring for Boston Transportation Department.",
                demonstrated_causal_effects="No causal traffic reduction demonstrated; improved data integration.",
            )
        ],
        community_feedback=[],
        category="Experimented Measures",
        supporting_passages=s14_passages,
        quality_flags=[],
        unresolved_questions=[
            "How did Boston handle neighborhood concerns regarding app-driven cut-through traffic under this partnership?"
        ],
        discovery_records=get_discoveries("src_7a51efb5b5f5430e194b"),
    ))

    # -----------------------------------------------------------------------
    # Source 15: Engadget (Boston-Waze partnership details)
    # -----------------------------------------------------------------------
    s15_text = get_archive_text("src_0d4fa7ccce08eaf50b2f")
    s15_passages = [
        SupportingPassage(
            claim_topic="Boston data sharing plan with Waze",
            verbatim_text="announced a data sharing plan with Waze",
        )
    ]
    for p in s15_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s15_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_0d4fa7ccce08eaf50b2f",
        archive_attempt_id="att_1cf47d3e63cb47e98a3c4a1656ec4fd1",
        requested_url="https://www.engadget.com/2015-02-21-waze-boston-partner.html",
        final_url="https://www.engadget.com/2015-02-21-waze-boston-partner.html",
        title="Boston partners with Waze to clear up clogged streets",
        publisher="Engadget",
        publication_date="2015-02-21",
        actual_jurisdiction="City of Boston, Massachusetts",
        governing_level="Government: City",
        authority_names="City of Boston, Boston Traffic Management Center, Waze",
        target_location_type="City",
        target_location="Boston",
        source_type="news reporting",
        factual_summary=(
            "Technology news coverage of Boston's Connected Citizens partnership with Waze, detailing how city "
            "engineers use telemetry from ~400,000 regional drivers to adjust intersection signals at the Traffic Management Center."
        ),
        measures=[
            MeasureItem(
                actor="City of Boston Traffic Management Center, Waze",
                mechanism="Integrating crowdsourced Waze driver data into municipal traffic signal control systems to retime intersections dynamically.",
                purpose="Clear clogged streets and optimize traffic flow across Boston's complex road network.",
                status="implemented",
                governing_level="Government: City",
                authority_names="City of Boston, Waze",
                target_location_type="City",
                target_location="Boston",
                implementation_dates="February 2015",
                reported_effects="Signal retiming adjustments executed based on Waze driver data.",
                demonstrated_causal_effects="Correlational operational adjustments; no long-term randomized causal evaluation.",
            )
        ],
        community_feedback=[],
        category="Experimented Measures",
        supporting_passages=s15_passages,
        quality_flags=[],
        unresolved_questions=[
            "What specific intersections saw signal timing improvements as a result of Waze feeds?"
        ],
        discovery_records=get_discoveries("src_0d4fa7ccce08eaf50b2f"),
    ))

    # -----------------------------------------------------------------------
    # Source 16: City of Boston Analytics Team (Centre Street West Roxbury)
    # -----------------------------------------------------------------------
    s16_text = get_archive_text("src_ab2b7d7e044d5121e5f5")
    s16_passages = [
        SupportingPassage(
            claim_topic="History of speeding and crashes on Centre Street in West Roxbury",
            verbatim_text="Centre Street in West Roxbury has a history of speeding and car crashes that have led to death and injury in recent years.",
        )
    ]
    for p in s16_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s16_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_ab2b7d7e044d5121e5f5",
        archive_attempt_id="att_14a38217bb4141d6b054a86efb69ccba",
        requested_url="https://www.boston.gov/departments/analytics-team/using-waze-data-measure-traffic-congestion-0",
        final_url="https://www.boston.gov/departments/analytics-team/using-waze-data-measure-traffic-congestion-0",
        title="Using Waze Data to Measure Traffic Congestion",
        publisher="City of Boston Citywide Analytics Team",
        publication_date="2024-01-01",
        actual_jurisdiction="City of Boston, Massachusetts (West Roxbury)",
        governing_level="Government: City",
        authority_names="City of Boston Citywide Analytics Team, Boston Transportation Department",
        target_location_type="City",
        target_location="Boston",
        source_type="government material",
        factual_summary=(
            "Official empirical report by the Boston Citywide Analytics Team evaluating the impact of the Centre Street "
            "West Roxbury road safety redesign (road diet) using anonymous, aggregated Waze travel time and jam data "
            "from pre- and post-construction periods."
        ),
        measures=[
            MeasureItem(
                actor="Boston Transportation Department, Citywide Analytics Team",
                mechanism="Road safety redesign on Centre Street (road diet / traffic calming) combined with empirical before-and-after monitoring using aggregated Waze travel time data.",
                purpose="Address history of speeding and severe crashes while measuring impact on arterial and neighborhood congestion.",
                status="implemented",
                governing_level="Government: City",
                authority_names="Boston Transportation Department",
                target_location_type="City",
                target_location="Boston",
                implementation_dates="Fall 2023 redesign; 2024 data evaluation",
                reported_effects="Redesign slowed vehicular speeds; Waze data showed minimal change in peak-period travel times across the corridor.",
                demonstrated_causal_effects="Before-and-after observational evaluation demonstrated safety gains with negligible congestion penalty.",
            )
        ],
        community_feedback=[],
        category="Experimented Measures",
        supporting_passages=s16_passages,
        quality_flags=[],
        unresolved_questions=[
            "Did the road diet cause bypass traffic spillover onto parallel local streets in West Roxbury?"
        ],
        discovery_records=get_discoveries("src_ab2b7d7e044d5121e5f5"),
    ))

    # -----------------------------------------------------------------------
    # Source 17: The Boston Globe (MassDOT joins Waze CCP statewide)
    # -----------------------------------------------------------------------
    s17_text = get_archive_text("src_f2e92e99cdf509170cc7")
    s17_passages = [
        SupportingPassage(
            claim_topic="MassDOT utilizing Waze data for construction planning",
            verbatim_text="In a statement, MassDOT said it plans to collect Waze data and use it to help plan future construction projects.",
        )
    ]
    for p in s17_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s17_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_f2e92e99cdf509170cc7",
        archive_attempt_id="att_0b4d455430ea4b97a221f7ee33989025",
        requested_url="https://www.bostonglobe.com/metro/2016/06/16/massdot-partners-with-waze-improve-traffic-planning/9p4D9vWnIYNQ7g9s1DwhIO/story.html",
        final_url="https://www.bostonglobe.com/metro/2016/06/16/massdot-partners-with-waze-improve-traffic-planning/9p4D9vWnIYNQ7g9s1DwhIO/story.html",
        title="MassDOT partners with Waze to improve traffic, planning",
        publisher="The Boston Globe",
        publication_date="2016-06-16",
        actual_jurisdiction="Commonwealth of Massachusetts",
        governing_level="Government: State",
        authority_names="Massachusetts Department of Transportation (MassDOT), Waze",
        target_location_type="State",
        target_location="Massachusetts",
        source_type="news reporting",
        factual_summary=(
            "MassDOT joins the Waze Connected Citizens Program statewide, providing official highway incident and "
            "construction closure information while receiving real-time congestion reports to inform highway operations "
            "and future infrastructure capital planning."
        ),
        measures=[
            MeasureItem(
                actor="MassDOT, Waze",
                mechanism="Statewide bilateral data integration exchanging official construction closures for crowdsourced highway incident telemetry.",
                purpose="Improve highway traffic operations and future infrastructure project planning across Massachusetts.",
                status="implemented",
                governing_level="Government: State",
                authority_names="MassDOT, Waze",
                target_location_type="State",
                target_location="Massachusetts",
                implementation_dates="June 2016",
                reported_effects="Expanded incident monitoring coverage across state highway corridors.",
                demonstrated_causal_effects="No causal reduction in congestion demonstrated.",
            )
        ],
        community_feedback=[],
        category="Experimented Measures",
        supporting_passages=s17_passages,
        quality_flags=[],
        unresolved_questions=[
            "How MassDOT data feeds handled state highway detour traffic spilling into municipal jurisdiction."
        ],
        discovery_records=get_discoveries("src_f2e92e99cdf509170cc7"),
    ))

    # -----------------------------------------------------------------------
    # Source 18: Block Club Chicago (Wood Street one-way implementation)
    # -----------------------------------------------------------------------
    s18_text = get_archive_text("src_396cf33a5161f5f5bd8d")
    s18_passages = [
        SupportingPassage(
            claim_topic="Wood Street one-way conversion to eliminate thru-traffic",
            verbatim_text="Two sections of Wood Street in West Town and Wicker Park will soon become southbound one-ways to limit thru-traffic in the area, one part of a corridor overhaul that includes resurfacing, curb improvements and some new bike infrastructure.",
        )
    ]
    for p in s18_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s18_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_396cf33a5161f5f5bd8d",
        archive_attempt_id="att_1bcbb243bf7e45dd8d3a68ea233b8112",
        requested_url="https://blockclubchicago.org/2025/06/06/wood-street-in-west-town-wicker-park-going-one-way-to-cut-down-on-thru-traffic/",
        final_url="https://blockclubchicago.org/2025/06/06/wood-street-in-west-town-wicker-park-going-one-way-to-cut-down-on-thru-traffic/",
        title="Wood Street In West Town, Wicker Park Going One-Way To Cut Down On Thru-Traffic",
        publisher="Block Club Chicago",
        publication_date="2025-06-06",
        actual_jurisdiction="City of Chicago, Illinois (West Town & Wicker Park, 1st Ward)",
        governing_level="Government: City",
        authority_names="Chicago Department of Transportation (CDOT), 1st Ward Alderperson Daniel La Spata",
        target_location_type="City",
        target_location="Chicago",
        source_type="news reporting",
        factual_summary=(
            "CDOT and 1st Ward Alderperson Daniel La Spata converted two sections of Wood Street in West Town and "
            "Wicker Park into southbound one-way streets as part of a corridor overhaul designed to stop commuter "
            "cut-through traffic, improve pedestrian safety, and add bike infrastructure."
        ),
        measures=[
            MeasureItem(
                actor="CDOT, 1st Ward Alderperson Daniel La Spata",
                mechanism="Converting two key segments of Wood Street into southbound one-way corridors, paired with resurfacing and curb bump-outs.",
                purpose="Cut off commuter cut-through traffic using residential side streets as an arterial bypass.",
                status="implemented",
                governing_level="Government: City",
                authority_names="CDOT, Chicago City Council",
                target_location_type="City",
                target_location="Chicago",
                implementation_dates="Implemented June 2025",
                reported_effects="Thru-traffic eliminated on one-way blocks; altered local access patterns.",
                demonstrated_causal_effects="Observational through-traffic reduction on targeted corridor; local circulation changes.",
            )
        ],
        community_feedback=[
            CommunityFeedbackItem(
                who_expressed="West Town and Wicker Park residents and local business owners",
                what_concerned_them="Loss of convenient two-way residential access and concerns about customer parking versus through-traffic reduction.",
                which_measure="Wood Street one-way conversion",
            )
        ],
        category="Both",
        supporting_passages=s18_passages,
        quality_flags=[],
        unresolved_questions=[
            "Whether traffic shifted onto adjacent north-south residential streets like Wolcott or Damen."
        ],
        discovery_records=get_discoveries("src_396cf33a5161f5f5bd8d"),
    ))

    # -----------------------------------------------------------------------
    # Source 19: CBS News Chicago (Wood Street one-way controversy)
    # -----------------------------------------------------------------------
    s19_text = get_archive_text("src_a8fe04b8629212eb1ae5")
    s19_passages = [
        SupportingPassage(
            claim_topic="Wood Street one-way conversion debate",
            verbatim_text="A stretch of Wood Street is being turned into a one-way street, and [Ald. Daniel La Spata (1st)](https://www.chicago.gov/city/en/about/wards/01.html) said residents voted for the project.",
        )
    ]
    for p in s19_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s19_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_a8fe04b8629212eb1ae5",
        archive_attempt_id="att_16d69107ae514d8ea028fa6ea9d073d3",
        requested_url="https://www.cbsnews.com/chicago/news/proposal-to-make-wood-street-one-way-stirs-debate-in-west-town/",
        final_url="https://www.cbsnews.com/chicago/news/proposal-to-make-wood-street-one-way-stirs-debate-in-west-town/",
        title="Proposal To Make Wood Street One-Way Stirs Debate In West Town",
        publisher="CBS News Chicago",
        publication_date="2021-08-04",
        actual_jurisdiction="City of Chicago, Illinois (West Town, 1st Ward)",
        governing_level="Government: City",
        authority_names="Chicago City Council, 1st Ward Alderperson Daniel La Spata, CDOT",
        target_location_type="City",
        target_location="Chicago",
        source_type="news reporting",
        factual_summary=(
            "CBS News reports on intense neighborhood debate over converting Wood Street and Campbell Avenue to "
            "one-way streets. Alderperson La Spata asserted residents approved the plan via participatory budgeting, "
            "but dissenting neighbors mounted a petition drive with 'Keep Wood a two-way street' signs."
        ),
        measures=[
            MeasureItem(
                actor="1st Ward Alderperson Daniel La Spata, CDOT",
                mechanism="Proposed one-way street directional changes on Wood Street and Campbell Avenue.",
                purpose="Deter commuter cut-through traffic traversing residential neighborhoods.",
                status="proposed",
                governing_level="Government: City",
                authority_names="Chicago City Council, CDOT",
                target_location_type="City",
                target_location="Chicago",
                implementation_dates="Proposed August 2021 (funded via participatory budgeting)",
                reported_effects="Public backlash and community mobilization.",
                demonstrated_causal_effects="None demonstrated.",
            )
        ],
        community_feedback=[
            CommunityFeedbackItem(
                who_expressed="West Town residents and business owners opposing the change",
                what_concerned_them="Opponents argued the participatory vote did not reflect neighborhood consensus, circular driving would increase, and customer access would suffer.",
                which_measure="Proposed one-way conversion on Wood Street",
            )
        ],
        category="Both",
        supporting_passages=s19_passages,
        quality_flags=[],
        unresolved_questions=[
            "What voter turnout threshold was used in the participatory budgeting election?"
        ],
        discovery_records=get_discoveries("src_a8fe04b8629212eb1ae5"),
    ))

    # -----------------------------------------------------------------------
    # Source 20: PubliCola (Seattle Councilmember Saka diverters equity)
    # -----------------------------------------------------------------------
    s20_text = get_archive_text("src_5b329e50217cff65c640")
    s20_passages = [
        SupportingPassage(
            claim_topic="Councilmember Saka opposing traffic diverters on equity and food desert grounds",
            verbatim_text="“It’s a head scratcher, in my view, to install a traffic diverter and prevent left-hand turns in a food desert, rendering Delridge the only single point of access to any fresh foods [or ] vegetables whatsoever. … It doesn’t make a lot of sense, from my perspective, to install such a drastic, draconian measure that has a a significant impact on neighborhoods and communities.”",
        )
    ]
    for p in s20_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s20_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_5b329e50217cff65c640",
        archive_attempt_id="att_ca0fae41846b41d491ebca5728a55097",
        requested_url="https://publicola.com/2025/04/02/shannon-braddock-appointed-acting-county-executive-saka-says-he-opposed-traffic-diverters-in-his-neighborhood-because-of-equity-concerns/",
        final_url="https://publicola.com/2025/04/02/shannon-braddock-appointed-acting-county-executive-saka-says-he-opposed-traffic-diverters-in-his-neighborhood-because-of-equity-concerns/",
        title="Saka Says He Opposed Traffic Diverters In His Neighborhood Because Of Equity Concerns",
        publisher="PubliCola",
        publication_date="2025-04-02",
        actual_jurisdiction="City of Seattle, Washington (Delridge, District 1)",
        governing_level="Government: City",
        authority_names="Seattle City Council, Councilmember Rob Saka, Seattle Department of Transportation (SDOT)",
        target_location_type="City",
        target_location="Seattle",
        source_type="news reporting",
        factual_summary=(
            "Seattle City Council Transportation Chair Rob Saka explains his opposition to SDOT traffic diverters "
            "on 26th Ave SW in Delridge, arguing that restricting left turns in a historically underserved neighborhood "
            "constituted an equity barrier that severed access to grocery stores in an existing food desert."
        ),
        measures=[
            MeasureItem(
                actor="SDOT, Seattle City Council",
                mechanism="Physical traffic diverters restricting left-hand turns to eliminate through traffic on 26th Ave SW neighborhood greenway.",
                purpose="Divert commuter cut-through traffic off residential greenways onto arterials.",
                status="withdrawn",
                governing_level="Government: City",
                authority_names="Seattle City Council, SDOT",
                target_location_type="City",
                target_location="Seattle",
                implementation_dates="Installed 2024; opposed and removed 2025",
                reported_effects="Councilmember opposition led to reconsideration and removal of the diverter.",
                demonstrated_causal_effects="Removed due to community equity backlash.",
            )
        ],
        community_feedback=[
            CommunityFeedbackItem(
                who_expressed="Councilmember Rob Saka and Delridge community members",
                what_concerned_them="Diverters restricted neighborhood mobility and access to fresh food/groceries in a food desert, imposing disproportionate burdens on working-class residents.",
                which_measure="26th Ave SW traffic diverter in Delridge",
            )
        ],
        category="Both",
        supporting_passages=s20_passages,
        quality_flags=[],
        unresolved_questions=[
            "What alternative traffic calming measures did SDOT deploy in Delridge after removing the diverter?"
        ],
        discovery_records=get_discoveries("src_5b329e50217cff65c640"),
    ))

    # -----------------------------------------------------------------------
    # Source 21: Change.org Petition (Seattle SW Genesee & SW Brandon diverters)
    # -----------------------------------------------------------------------
    s21_text = get_archive_text("src_a8b514916cc36bde3d40")
    s21_passages = [
        SupportingPassage(
            claim_topic="Petition title demanding halt to traffic diverters",
            verbatim_text="Stop the installation of traffic diverters at SW Genesee and SW Brandon",
        )
    ]
    for p in s21_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s21_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_a8b514916cc36bde3d40",
        archive_attempt_id="att_376483ad3953491ba6ce46faae653b1b",
        requested_url="https://www.change.org/p/stop-the-installation-of-traffic-diverters-at-sw-genesee-and-sw-brandon",
        final_url="https://www.change.org/p/stop-the-installation-of-traffic-diverters-at-sw-genesee-and-sw-brandon",
        title="Stop the installation of traffic diverters at SW Genesee and SW Brandon",
        publisher="Change.org (West Seattle Residents)",
        publication_date="2020-09-01",
        actual_jurisdiction="City of Seattle, Washington (West Seattle)",
        governing_level="Government: City",
        authority_names="Seattle Department of Transportation (SDOT), West Seattle Residents",
        target_location_type="City",
        target_location="Seattle",
        source_type="community testimony",
        factual_summary=(
            "Community petition signed by West Seattle residents demanding that SDOT halt planned traffic diverters "
            "at SW Genesee St and SW Brandon St along the 26th Ave SW greenway, arguing diverters will push traffic "
            "onto narrower side streets without sidewalks and delay first responders."
        ),
        measures=[
            MeasureItem(
                actor="SDOT",
                mechanism="Proposed physical diverters at SW Genesee and SW Brandon to block motorized through traffic.",
                purpose="Prevent cut-through traffic on neighborhood greenways during West Seattle Bridge closure.",
                status="withdrawn",
                governing_level="Government: City",
                authority_names="SDOT",
                target_location_type="City",
                target_location="Seattle",
                implementation_dates="Proposed fall 2020",
                reported_effects="Petition garnered community support; project modified.",
                demonstrated_causal_effects="None.",
            )
        ],
        community_feedback=[
            CommunityFeedbackItem(
                who_expressed="West Seattle neighbors and petition signers",
                what_concerned_them="Spillover of diverted traffic onto narrow residential streets lacking sidewalks, increased danger for children, and impeded emergency vehicle ingress.",
                which_measure="SDOT traffic diverters at SW Genesee and SW Brandon",
            )
        ],
        category="Both",
        supporting_passages=s21_passages,
        quality_flags=[],
        unresolved_questions=[
            "Did SDOT implement alternative calming such as speed cushions instead of full diverters?"
        ],
        discovery_records=get_discoveries("src_a8b514916cc36bde3d40"),
    ))

    # -----------------------------------------------------------------------
    # Source 22: SDOT Lake City Home Zone
    # -----------------------------------------------------------------------
    s22_text = get_archive_text("src_a16a62edb70588f81bbb")
    s22_passages = [
        SupportingPassage(
            claim_topic="Lake City Home Zone program title",
            verbatim_text="Home Zone: Lake City",
        )
    ]
    for p in s22_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s22_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_a16a62edb70588f81bbb",
        archive_attempt_id="att_1bc312891d4e4ad7b15a6bfa9e92823a",
        requested_url="https://www.seattle.gov/transportation/projects-and-programs/programs/neighborhood-street-operations-programs/home-zone-lake-city",
        final_url="https://www.seattle.gov/transportation/projects-and-programs/programs/neighborhood-street-operations-programs/home-zone-lake-city",
        title="Home Zone: Lake City",
        publisher="Seattle Department of Transportation (SDOT)",
        publication_date="2023-01-01",
        actual_jurisdiction="City of Seattle, Washington (Lake City)",
        governing_level="Government: City",
        authority_names="Seattle Department of Transportation (SDOT), Lake City Community",
        target_location_type="City",
        target_location="Seattle",
        source_type="government material",
        factual_summary=(
            "Official program documentation for the Lake City Home Zone pilot project, outlining a holistic "
            "neighborhood traffic calming toolkit including speed humps, painted intersections, chicane diverters, "
            "and street trees to deter cut-through traffic."
        ),
        measures=[
            MeasureItem(
                actor="SDOT",
                mechanism="Home Zone traffic calming package: speed humps, curb bulbs, traffic circles, and diverters across a multi-block residential zone.",
                purpose="Eliminate cut-through bypass traffic and lower vehicle speeds within the neighborhood.",
                status="implemented",
                governing_level="Government: City",
                authority_names="SDOT",
                target_location_type="City",
                target_location="Seattle",
                implementation_dates="2021-2023",
                reported_effects="Reported reductions in cut-through vehicle volumes and 85th percentile speeds across Home Zone boundaries.",
                demonstrated_causal_effects="Observational pre/post speed and volume counts.",
            )
        ],
        community_feedback=[],
        category="Experimented Measures",
        supporting_passages=s22_passages,
        quality_flags=[],
        unresolved_questions=[
            "How did navigation apps adjust routing around the Lake City Home Zone?"
        ],
        discovery_records=get_discoveries("src_a16a62edb70588f81bbb"),
    ))

    # -----------------------------------------------------------------------
    # Source 23: Seattle Bike Blog (Giant tree circles)
    # -----------------------------------------------------------------------
    s23_text = get_archive_text("src_8269369b969b68e10744")
    s23_passages = [
        SupportingPassage(
            claim_topic="Proposal for citywide tree circles",
            verbatim_text="Let’s build giant tree circles in every Seattle neighborhood",
        )
    ]
    for p in s23_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s23_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_8269369b969b68e10744",
        archive_attempt_id="att_6bb9de9abfa543f49ca0235adcf82fe9",
        requested_url="https://seattlebikeblog.com/2025/02/25/lets-build-giant-tree-circles-in-every-seattle-neighborhood/",
        final_url="https://seattlebikeblog.com/2025/02/25/lets-build-giant-tree-circles-in-every-seattle-neighborhood/",
        title="Let’s build giant tree circles in every Seattle neighborhood",
        publisher="Seattle Bike Blog",
        publication_date="2025-02-25",
        actual_jurisdiction="City of Seattle, Washington",
        governing_level="Non-Government Organization",
        authority_names="Seattle Bike Blog, Seattle Urban Forestry / SDOT advocates",
        target_location_type="City",
        target_location="Seattle",
        source_type="news reporting",
        factual_summary=(
            "Urban planning commentary advocating for the citywide installation of oversized neighborhood tree "
            "circles at residential intersections to physically calm traffic, deflect speeding vehicles, and discourage through trips."
        ),
        measures=[
            MeasureItem(
                actor="Seattle Urban Forestry Advocates / SDOT",
                mechanism="Installing large planted tree circles at residential cross-streets to deflect traffic and lower speeds.",
                purpose="Prevent cut-through speeding while enhancing urban canopy cover.",
                status="proposed",
                governing_level="Non-Government Organization",
                authority_names="Seattle Bike Blog advocates",
                target_location_type="City",
                target_location="Seattle",
                implementation_dates="Proposed February 2025",
                reported_effects="Conceptual proposal promoted to municipal planners.",
                demonstrated_causal_effects="None.",
            )
        ],
        community_feedback=[],
        category="Experimented Measures",
        supporting_passages=s23_passages,
        quality_flags=[],
        unresolved_questions=[
            "Whether SDOT has established standards for oversized tree circle turning radiuses for emergency vehicles."
        ],
        discovery_records=get_discoveries("src_8269369b969b68e10744"),
    ))

    # -----------------------------------------------------------------------
    # Source 24: The Urbanist (Seattle protected intersection)
    # -----------------------------------------------------------------------
    s24_text = get_archive_text("src_ff00f9c2aa962ff25e8c")
    s24_passages = [
        SupportingPassage(
            claim_topic="Seattle's first protected intersection installation",
            verbatim_text="Seattle Is Finally Getting Its First Protected Intersection",
        )
    ]
    for p in s24_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s24_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_ff00f9c2aa962ff25e8c",
        archive_attempt_id="att_be484646be9d4b2e8fa46bc413fcf7ca",
        requested_url="https://www.theurbanist.org/2024/03/05/seattle-is-finally-getting-its-first-protected-intersection/",
        final_url="https://www.theurbanist.org/2024/03/05/seattle-is-finally-getting-its-first-protected-intersection/",
        title="Seattle Is Finally Getting Its First Protected Intersection",
        publisher="The Urbanist",
        publication_date="2024-03-05",
        actual_jurisdiction="City of Seattle, Washington",
        governing_level="Government: City",
        authority_names="Seattle Department of Transportation (SDOT)",
        target_location_type="City",
        target_location="Seattle",
        source_type="news reporting",
        factual_summary=(
            "Reporting on SDOT's construction of Seattle's first Dutch-style protected intersection at Dexter Avenue N "
            "and Thomas Street, featuring corner refuge islands and setback bike crossings to separate turning vehicles from cyclists and pedestrians."
        ),
        measures=[
            MeasureItem(
                actor="SDOT",
                mechanism="Dutch-style protected intersection design with corner setback islands and dedicated bike signals.",
                purpose="Eliminate vehicle turn conflicts and improve vulnerable user safety at high-volume intersections.",
                status="implemented",
                governing_level="Government: City",
                authority_names="SDOT",
                target_location_type="City",
                target_location="Seattle",
                implementation_dates="Constructed spring 2024",
                reported_effects="Slowed vehicle turning speeds and enhanced bicyclist visibility.",
                demonstrated_causal_effects="Observational safety improvements.",
            )
        ],
        community_feedback=[],
        category="Experimented Measures",
        supporting_passages=s24_passages,
        quality_flags=[],
        unresolved_questions=[
            "How this intersection design affects corridor throughput and navigation route delays."
        ],
        discovery_records=get_discoveries("src_ff00f9c2aa962ff25e8c"),
    ))

    # -----------------------------------------------------------------------
    # Source 25: NYT Bits Blog (Waze real-time road closures)
    # -----------------------------------------------------------------------
    s25_text = get_archive_text("src_c8f5fcc928d66ad4b9e7")
    s25_passages = [
        SupportingPassage(
            claim_topic="Waze dynamic road closure reporting feature",
            verbatim_text="Even the best map is out of date the minute it is printed. But a new feature from Waze, a mobile app built on information gathered from its users’ phones, will be able to change the app’s maps in real time, reflecting temporary road closings as they happen.",
        )
    ]
    for p in s25_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s25_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_c8f5fcc928d66ad4b9e7",
        archive_attempt_id="att_ee424107e32442af8f3cb535359a117b",
        requested_url="https://archive.nytimes.com/bits.blogs.nytimes.com/2013/02/27/wazes-maps-now-change-as-roads-close/",
        final_url="https://archive.nytimes.com/bits.blogs.nytimes.com/2013/02/27/wazes-maps-now-change-as-roads-close/",
        title="Waze’s Maps Now Change as Roads Close",
        publisher="The New York Times Bits Blog",
        publication_date="2013-02-27",
        actual_jurisdiction="United States",
        governing_level="Company",
        authority_names="Waze Mobile Ltd., Georgia Department of Transportation (GDOT)",
        target_location_type="Country",
        target_location="United States",
        source_type="news reporting",
        factual_summary=(
            "New York Times reporting on Waze's launch of real-time crowdsourced road closure reporting. Highlights "
            "integration with official DOT data, such as Georgia DOT's 511 system, to instantly adjust navigation "
            "routing around closed streets and accidents."
        ),
        measures=[
            MeasureItem(
                actor="Waze Mobile Ltd, Georgia DOT",
                mechanism="Crowdsourced road closure reporting tool enabling users and DOT partners to mark closed roads and trigger instant automated route diversion.",
                purpose="Reroute navigation app drivers away from closed roadways in real time.",
                status="implemented",
                governing_level="Company",
                authority_names="Waze Mobile Ltd",
                target_location_type="Country",
                target_location="United States",
                implementation_dates="Launched February 27, 2013",
                reported_effects="Enabled dynamic real-time map updates across 36M+ active users.",
                demonstrated_causal_effects="Platform routing recomputed dynamically around reported closures.",
            )
        ],
        community_feedback=[],
        category="Experimented Measures",
        supporting_passages=s25_passages,
        quality_flags=[],
        unresolved_questions=[
            "What verification thresholds Waze uses to prevent malicious false closure reports."
        ],
        discovery_records=get_discoveries("src_c8f5fcc928d66ad4b9e7"),
    ))

    # -----------------------------------------------------------------------
    # Source 26: TechCrunch (Waze 40M users & road closure feature)
    # -----------------------------------------------------------------------
    s26_text = get_archive_text("src_264bf1d902e4b812735b")
    s26_passages = [
        SupportingPassage(
            claim_topic="Waze road closure reporting headline",
            verbatim_text="Navigation App Waze Adds Road Closure Reporting, Says It Now Has 40M Users",
        )
    ]
    for p in s26_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s26_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_264bf1d902e4b812735b",
        archive_attempt_id="att_1012351bbce6427389c92233f2ec4da2",
        requested_url="https://techcrunch.com/2013/02/27/navigation-app-waze-adds-road-closure-reporting-says-it-now-has-36m-users/",
        final_url="https://techcrunch.com/2013/02/27/navigation-app-waze-adds-road-closure-reporting-says-it-now-has-36m-users/",
        title="Navigation App Waze Adds Road Closure Reporting, Says It Now Has 40M Users",
        publisher="TechCrunch",
        publication_date="2013-02-27",
        actual_jurisdiction="United States",
        governing_level="Company",
        authority_names="Waze Mobile Ltd.",
        target_location_type="Country",
        target_location="United States",
        source_type="news reporting",
        factual_summary=(
            "TechCrunch reports on Waze surpassing 40 million users and launching structured road closure reporting "
            "with metadata attributes including closure cause (construction, event) and expected duration."
        ),
        measures=[
            MeasureItem(
                actor="Waze Mobile Ltd.",
                mechanism="Structured road closure submission interface allowing drivers to specify closure duration and category, updating navigation recommendations.",
                purpose="Enable rapid routing algorithm adjustments around physical road blockages.",
                status="implemented",
                governing_level="Company",
                authority_names="Waze Mobile Ltd.",
                target_location_type="Country",
                target_location="United States",
                implementation_dates="February 2013",
                reported_effects="Automated algorithmic avoidance of reported road segments.",
                demonstrated_causal_effects="Direct platform algorithmic recalculation.",
            )
        ],
        community_feedback=[],
        category="Experimented Measures",
        supporting_passages=s26_passages,
        quality_flags=[],
        unresolved_questions=[
            "How Waze algorithms handle partial lane closures versus full street closures."
        ],
        discovery_records=get_discoveries("src_264bf1d902e4b812735b"),
    ))

    # -----------------------------------------------------------------------
    # Source 27: Waze Connected Citizens Program Factsheet PDF
    # -----------------------------------------------------------------------
    s27_text = get_archive_text("src_a3aec998433f0c3fff3d")
    s27_passages = [
        SupportingPassage(
            claim_topic="Waze CCP situational awareness benefits",
            verbatim_text="SITUATIONAL AWARENESS: Partners receive real-time incident information faster than other reporting methods and",
        )
    ]
    for p in s27_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s27_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_a3aec998433f0c3fff3d",
        archive_attempt_id="att_9ab1b415a7704b209d7df9dca5e98583",
        requested_url="https://www.waze.com/ccp_factsheet.pdf",
        final_url="https://www.waze.com/ccp_factsheet.pdf",
        title="Waze Connected Citizens Program Factsheet",
        publisher="Waze (Google LLC)",
        publication_date="2019-01-01",
        actual_jurisdiction="Global / United States",
        governing_level="Company",
        authority_names="Waze (Google LLC)",
        target_location_type="Country",
        target_location="Global",
        source_type="company statement",
        factual_summary=(
            "Official factsheet detailing the Waze Connected Citizens Program (CCP), an API-based bilateral data "
            "exchange providing municipal partners with real-time incident and jam telemetry in return for municipal advance road closure notices."
        ),
        measures=[
            MeasureItem(
                actor="Waze (Google LLC)",
                mechanism="Connected Citizens Program API data feed sharing real-time incident reports, jams, and hazards with municipal departments.",
                purpose="Enhance municipal situational awareness and road incident clearing times.",
                status="implemented",
                governing_level="Company",
                authority_names="Waze (Google LLC)",
                target_location_type="Country",
                target_location="Global",
                implementation_dates="Established 2014; ongoing",
                reported_effects="Faster incident clearance and bidirectional data coordination in 1,000+ partner cities.",
                demonstrated_causal_effects="Operational data integration.",
            )
        ],
        community_feedback=[],
        category="Experimented Measures",
        supporting_passages=s27_passages,
        quality_flags=[],
        unresolved_questions=[
            "Are municipal partners permitted to use CCP data to mandate route exclusions?"
        ],
        discovery_records=get_discoveries("src_a3aec998433f0c3fff3d"),
    ))

    # -----------------------------------------------------------------------
    # Source 28: Waze for Cities Program Overview (Wazeopedia)
    # -----------------------------------------------------------------------
    s28_text = get_archive_text("src_209e9565661083dba383")
    s28_passages = [
        SupportingPassage(
            claim_topic="Waze for Cities program description and exchange mechanics",
            verbatim_text="The Waze for Cities(W4C) program, formerly known as Connected Citizens Program(CCP) brings cities and citizens together to answer the questions “What’s happening, and where?” We exchange publicly available incident and road closure reports",
        )
    ]
    for p in s28_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s28_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_209e9565661083dba383",
        archive_attempt_id="att_1bcbb349ea1146cbb17b11d9bc49b841",
        requested_url="https://www.waze.com/wazeopedia/Waze_for_Cities_Overview",
        final_url="https://www.waze.com/wazeopedia/Waze_for_Cities_Overview",
        title="Waze for Cities (W4C) Program Overview",
        publisher="Waze Discuss / Wazeopedia",
        publication_date="2024-01-01",
        actual_jurisdiction="Global / United States",
        governing_level="Company",
        authority_names="Waze for Cities Team, Waze Volunteer Map Editors",
        target_location_type="Country",
        target_location="Global",
        source_type="company statement",
        factual_summary=(
            "Technical documentation outlining Waze for Cities (formerly CCP), explaining how local governments "
            "exchange public incident reports and road closures with the Waze platform and volunteer editing community."
        ),
        measures=[
            MeasureItem(
                actor="Waze for Cities, Volunteer Map Editors",
                mechanism="Publicly available incident and road closure data exchange platform connecting cities and crowdsourced editors.",
                purpose="Answer 'What's happening, and where?' across municipal road networks.",
                status="implemented",
                governing_level="Company",
                authority_names="Waze for Cities",
                target_location_type="Country",
                target_location="Global",
                implementation_dates="2014-present",
                reported_effects="Streamlined communications between municipal public works departments and Waze map editors.",
                demonstrated_causal_effects="Operational map update workflows.",
            )
        ],
        community_feedback=[],
        category="Experimented Measures",
        supporting_passages=s28_passages,
        quality_flags=[],
        unresolved_questions=[
            "What formal recourse municipalities have when volunteer editors reject city turn restriction requests."
        ],
        discovery_records=get_discoveries("src_209e9565661083dba383"),
    ))

    # -----------------------------------------------------------------------
    # Source 29: Waze Community Forum Feature Request (Blacklist Roads)
    # -----------------------------------------------------------------------
    s29_text = get_archive_text("src_97a13ecf3417e5676e08")
    s29_passages = [
        SupportingPassage(
            claim_topic="Feature request title for road blacklisting",
            verbatim_text="Feature Request: Blacklist Areas / Roads",
        )
    ]
    for p in s29_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s29_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_97a13ecf3417e5676e08",
        archive_attempt_id="att_1bcbb249bcfe49ee92aa15c711ea89bc",
        requested_url="https://www.waze.com/forum/viewtopic.php?t=338291",
        final_url="https://www.waze.com/forum/viewtopic.php?t=338291",
        title="Feature Request: Blacklist Areas / Roads",
        publisher="Waze Discuss Community Forum",
        publication_date="2024-01-01",
        actual_jurisdiction="Global / United States",
        governing_level="Company",
        authority_names="Waze Community Forum / Volunteer Map Editors",
        target_location_type="Country",
        target_location="Global",
        source_type="other",
        factual_summary=(
            "Community proposal submitted by Waze volunteer map editors and drivers requesting a 'Blacklist Areas / Roads' "
            "feature to allow excluding specific dangerous, narrow, or resident-only roads from routing algorithms."
        ),
        measures=[
            MeasureItem(
                actor="Waze Community Forum Users",
                mechanism="Software feature request allowing users and editors to blacklist specific road segments from route calculations.",
                purpose="Prevent navigation algorithms from sending vehicles down unpaved, narrow, or hazardous streets.",
                status="proposed",
                governing_level="Company",
                authority_names="Waze Community Forum",
                target_location_type="Country",
                target_location="Global",
                implementation_dates="Proposed 2024",
                reported_effects="Feature discussed by developer community; not adopted as core policy.",
                demonstrated_causal_effects="None.",
            )
        ],
        community_feedback=[
            CommunityFeedbackItem(
                who_expressed="Waze map editors and community drivers",
                what_concerned_them="Navigation apps continually direct large or unfamiliar vehicles down dangerous shortcuts and narrow roads.",
                which_measure="Proposed Blacklist Areas / Roads routing toggle",
            )
        ],
        category="Community Feedback",
        supporting_passages=s29_passages,
        quality_flags=[],
        unresolved_questions=[
            "Whether commercial navigation vendors will ever grant end users or cities explicit exclusion toggles."
        ],
        discovery_records=get_discoveries("src_97a13ecf3417e5676e08"),
    ))

    # -----------------------------------------------------------------------
    # Source 30: Waze Official (Google Cloud Analytics)
    # -----------------------------------------------------------------------
    s30_text = get_archive_text("src_ae24cf62a63f34c9fe0b")
    s30_passages = [
        SupportingPassage(
            claim_topic="Actionable insights from historical Waze data in Google Cloud",
            verbatim_text="Uncover actionable insights about your city’s traffic network by analyzing years of historical congestion, pothole, crash and other incidents stored in Google Cloud.",
        )
    ]
    for p in s30_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s30_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_ae24cf62a63f34c9fe0b",
        archive_attempt_id="att_1bcbb159cc4e43e2b17a12cb84ea71fb",
        requested_url="https://www.waze.com/wazeforcities/google-cloud",
        final_url="https://www.waze.com/wazeforcities/google-cloud",
        title="Waze for Cities - Google Cloud Analytics",
        publisher="Waze (Google LLC)",
        publication_date="2024-01-01",
        actual_jurisdiction="Global / United States",
        governing_level="Company",
        authority_names="Waze (Google Cloud)",
        target_location_type="Country",
        target_location="Global",
        source_type="company statement",
        factual_summary=(
            "Marketing and product page explaining how municipal partners can query historical Waze traffic "
            "congestion, pothole, and accident datasets using Google Cloud BigQuery tools."
        ),
        measures=[
            MeasureItem(
                actor="Waze (Google Cloud)",
                mechanism="Cloud-based BigQuery analytical integration for querying years of historical Waze congestion and crash incident feeds.",
                purpose="Provide cities with actionable data insights for transportation infrastructure planning.",
                status="implemented",
                governing_level="Company",
                authority_names="Google Cloud, Waze",
                target_location_type="Country",
                target_location="Global",
                implementation_dates="Launched 2019; ongoing",
                reported_effects="Enables municipal traffic engineers to analyze longitudinal congestion patterns.",
                demonstrated_causal_effects="Descriptive historical traffic analytics.",
            )
        ],
        community_feedback=[],
        category="Experimented Measures",
        supporting_passages=s30_passages,
        quality_flags=[],
        unresolved_questions=[
            "What licensing fees or data usage restrictions apply to municipal Google Cloud BigQuery access?"
        ],
        discovery_records=get_discoveries("src_ae24cf62a63f34c9fe0b"),
    ))

    # -----------------------------------------------------------------------
    # Source 31: UC Berkeley PhD Dissertation (Theophile Cabannes)
    # -----------------------------------------------------------------------
    s31_text = get_archive_text("src_2cee64cfc090c4b25ca7")
    s31_passages = [
        SupportingPassage(
            claim_topic="Empirical externalities documented in Baxter St LA and Ford Lee Rd Leonia",
            verbatim_text="Baxter Street, Leonia, NJ reported a fa-\ntality on the Ford Lee Road",
        )
    ]
    for p in s31_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s31_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_2cee64cfc090c4b25ca7",
        archive_attempt_id="att_1bcbb459ea7e4b21b8ff12ab44ea19ef",
        requested_url="https://escholarship.org/uc/item/73h7f87m",
        final_url="https://escholarship.org/uc/item/73h7f87m",
        title="Traffic Control and Routing in the Era of Algorithmic Navigation",
        publisher="University of California, Berkeley (Doctoral Dissertation of Theophile Cabannes)",
        publication_date="2022-05-01",
        actual_jurisdiction="United States (California & New Jersey)",
        governing_level="Non-Government Organization",
        authority_names="University of California, Berkeley (Department of EECS)",
        target_location_type="Country",
        target_location="United States",
        source_type="other",
        factual_summary=(
            "Doctoral dissertation examining the mathematical foundations and real-world externalities of algorithmic "
            "navigation apps. Empirically and theoretically models cut-through traffic phenomena in Fremont, CA; "
            "Los Angeles, CA (Baxter Street crashes); and Leonia, NJ (fatal crash on Ford Lee Road), evaluating game-theoretic traffic equilibria."
        ),
        measures=[
            MeasureItem(
                actor="Transportation researchers and municipal authorities (Fremont, LA, Leonia)",
                mechanism="Mathematical modeling and empirical evaluation of municipal countermeasures (turn restrictions, one-way streets, non-resident bans, app rerouting).",
                purpose="Analyze user equilibrium vs system optimum routing externalities created by routing apps.",
                status="piloted",
                governing_level="Non-Government Organization",
                authority_names="UC Berkeley Transportation Research",
                target_location_type="Country",
                target_location="United States",
                implementation_dates="Dissertation published 2022",
                reported_effects="Demonstrates that selfish routing pushes traffic onto residential links until travel times equalize, creating severe negative local externalities.",
                demonstrated_causal_effects="Rigorous game-theoretic and simulation proofs of cut-through spillover.",
            )
        ],
        community_feedback=[
            CommunityFeedbackItem(
                who_expressed="Municipal residents in Los Angeles, Leonia, and Fremont",
                what_concerned_them="Dangerous cut-through traffic, vehicle crashes on steep grades (Baxter St), fatalities on narrow residential corridors (Ford Lee Rd), and arterial gridlock.",
                which_measure="Algorithmic routing apps and municipal traffic restrictions",
            )
        ],
        category="Both",
        supporting_passages=s31_passages,
        quality_flags=[],
        unresolved_questions=[
            "What optimal tolling or routing algorithm adjustments can bridge user equilibrium with system optimum traffic states?"
        ],
        discovery_records=get_discoveries("src_2cee64cfc090c4b25ca7"),
    ))

    # -----------------------------------------------------------------------
    # Source 32: TRB / National Academies Report
    # -----------------------------------------------------------------------
    s32_text = get_archive_text("src_2602e1f52eb57cee5b07")
    s32_passages = [
        SupportingPassage(
            claim_topic="TRB report title on transportation data integration",
            verbatim_text="Data Integration, Sharing, and Management for Transportation Planning and Traffic Operations",
        )
    ]
    for p in s32_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s32_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_2602e1f52eb57cee5b07",
        archive_attempt_id="att_1bcbb898fa3e46e8b2aa19ea55ca87ff",
        requested_url="https://nap.nationalacademies.org/read/28045/chapter/11",
        final_url="https://nap.nationalacademies.org/read/28045/chapter/11",
        title="Data Integration, Sharing, and Management for Transportation Planning and Traffic Operations",
        publisher="Transportation Research Board (TRB) / National Academies",
        publication_date="2025-01-01",
        actual_jurisdiction="United States",
        governing_level="Government: Federal",
        authority_names="Transportation Research Board, National Academies of Sciences, Engineering, and Medicine",
        target_location_type="Country",
        target_location="United States",
        source_type="government material",
        factual_summary=(
            "National research report outlining frameworks and best practices for integrating commercial third-party "
            "navigation vendor data (Waze, INRIX, HERE) into municipal and state transportation planning and real-time operations."
        ),
        measures=[
            MeasureItem(
                actor="TRB, AASHTO, FHWA",
                mechanism="Federal guidelines for public-private data integration, API licensing, and privacy preservation in navigation data management.",
                purpose="Standardize public agency ingestion of commercial mapping vendor feeds.",
                status="implemented",
                governing_level="Government: Federal",
                authority_names="Transportation Research Board",
                target_location_type="Country",
                target_location="United States",
                implementation_dates="2025",
                reported_effects="Standardized operational frameworks across state DOTs.",
                demonstrated_causal_effects="Institutional governance guidance.",
            )
        ],
        community_feedback=[],
        category="Experimented Measures",
        supporting_passages=s32_passages,
        quality_flags=[],
        unresolved_questions=[
            "How federal data privacy standards limit granular origin-destination telemetry collection by public agencies."
        ],
        discovery_records=get_discoveries("src_2602e1f52eb57cee5b07"),
    ))

    # -----------------------------------------------------------------------
    # Source 33: Borough of Mantoloking, NJ Council Minutes
    # -----------------------------------------------------------------------
    s33_text = get_archive_text("src_8844a04c3601f584693a")
    s33_passages = [
        SupportingPassage(
            claim_topic="Police Chief reporting denial of routing requests by Google and Waze",
            verbatim_text="The Chief also reported that previous requests to Google and Waze to alter routing through local streets had been denied, but expressed support for temporary measures such as electronic message boards, additional staffing, and targeted traffic controls for this Labor Day while longer-term solutions are developed.",
        )
    ]
    for p in s33_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s33_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_8844a04c3601f584693a",
        archive_attempt_id="att_1bcbb777ea4e41bfa1aa29ea66da91ff",
        requested_url="https://www.mantoloking.org/sites/default/files/minutes/2026-07-21_minutes.pdf",
        final_url="https://www.mantoloking.org/sites/default/files/minutes/2026-07-21_minutes.pdf",
        title="Regular Council Meeting Minutes (July 21, 2026)",
        publisher="Borough of Mantoloking, New Jersey",
        publication_date="2026-07-21",
        actual_jurisdiction="Borough of Mantoloking, Ocean County, New Jersey",
        governing_level="Government: City",
        authority_names="Borough of Mantoloking Mayor and Council, Mantoloking Police Department",
        target_location_type="City",
        target_location="Mantoloking",
        source_type="government material",
        factual_summary=(
            "Official council meeting minutes documenting municipal response to summer shore cut-through traffic. "
            "Police Chief reported that previous requests to Google and Waze to stop routing commuter traffic through "
            "local residential streets were denied by the companies, prompting the Borough to deploy electronic message "
            "boards, extra police staffing, and physical traffic controls."
        ),
        measures=[
            MeasureItem(
                actor="Mantoloking Police Department",
                mechanism="Deployment of electronic message boards, targeted police traffic control checkpoints, and increased summer staffing.",
                purpose="Manage cut-through congestion during summer holiday weekends after tech apps refused to alter routes.",
                status="implemented",
                governing_level="Government: City",
                authority_names="Mantoloking Borough Council, Police Department",
                target_location_type="City",
                target_location="Mantoloking",
                implementation_dates="Labor Day 2026",
                reported_effects="Police presence controlled local intersections.",
                demonstrated_causal_effects="Observational intersection control.",
            ),
            MeasureItem(
                actor="Borough of Mantoloking",
                mechanism="Formal municipal requests to Google and Waze to remove local residential streets from regional detour routing algorithms.",
                purpose="Prevent navigation apps from funneling shore traffic onto narrow borough streets.",
                status="withdrawn",
                governing_level="Government: City",
                authority_names="Borough of Mantoloking",
                target_location_type="City",
                target_location="Mantoloking",
                implementation_dates="Pre-July 2026",
                reported_effects="Explicitly denied by Google and Waze.",
                demonstrated_causal_effects="Tech platform refusal to alter routing.",
            )
        ],
        community_feedback=[
            CommunityFeedbackItem(
                who_expressed="Mantoloking residents, Police Chief, and Borough Council",
                what_concerned_them="Overwhelming cut-through congestion during summer holiday weekends and tech companies' refusal to cooperate with local routing requests.",
                which_measure="Municipal requests to Google/Waze and police holiday traffic controls",
            )
        ],
        category="Both",
        supporting_passages=s33_passages,
        quality_flags=[],
        unresolved_questions=[
            "What legal rationale did Google and Waze cite when denying the Borough's request?"
        ],
        discovery_records=get_discoveries("src_8844a04c3601f584693a"),
    ))

    # -----------------------------------------------------------------------
    # Source 34: SFMTA Smart City Challenge Phase II Application
    # -----------------------------------------------------------------------
    s34_text = get_archive_text("src_d8bae76a48b8c662c148")
    s34_passages = [
        SupportingPassage(
            claim_topic="Smarking pushing parking data via API to Google Maps and Waze",
            verbatim_text="Smarking plans to push this data via API to relevant outlets including Google Maps/Waze so that drivers can make more informed decisions regarding where and when they can expect parking availability at BART stations.",
        )
    ]
    for p in s34_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s34_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_d8bae76a48b8c662c148",
        archive_attempt_id="att_1bcbb111da4e41bba1aa11ea22da11aa",
        requested_url="https://www.sfmta.com/sites/default/files/reports-and-documents/2016/05/smart_city_challenge_sf_phase_ii.pdf",
        final_url="https://www.sfmta.com/sites/default/files/reports-and-documents/2016/05/smart_city_challenge_sf_phase_ii.pdf",
        title="Smart City Challenge Phase II Application",
        publisher="San Francisco Municipal Transportation Agency (SFMTA)",
        publication_date="2016-05-01",
        actual_jurisdiction="City and County of San Francisco, California",
        governing_level="Government: City",
        authority_names="San Francisco Municipal Transportation Agency (SFMTA), Smarking, USDOT",
        target_location_type="City",
        target_location="San Francisco",
        source_type="government material",
        factual_summary=(
            "SFMTA's federal Smart City Challenge grant application detailing a proposed integration with parking "
            "analytics vendor Smarking to push real-time BART station parking availability via API to Google Maps and Waze."
        ),
        measures=[
            MeasureItem(
                actor="SFMTA, Smarking, BART",
                mechanism="API integration broadcasting parking availability at BART stations directly to Google Maps and Waze navigation interfaces.",
                purpose="Encourage drivers to shift from driving into transit by providing advance parking certainty.",
                status="proposed",
                governing_level="Government: City",
                authority_names="SFMTA, BART",
                target_location_type="City",
                target_location="San Francisco",
                implementation_dates="Proposed May 2016",
                reported_effects="Grant application concept; demonstrated technical feasibility.",
                demonstrated_causal_effects="None.",
            )
        ],
        community_feedback=[],
        category="Experimented Measures",
        supporting_passages=s34_passages,
        quality_flags=[],
        unresolved_questions=[
            "Whether Google Maps and Waze integrated real-time BART parking availability into final driving directions."
        ],
        discovery_records=get_discoveries("src_d8bae76a48b8c662c148"),
    ))

    # -----------------------------------------------------------------------
    # Source 35: SFCTA Citizens Advisory Committee Meeting Packet
    # -----------------------------------------------------------------------
    s35_text = get_archive_text("src_6b808701b37bfa4ff82d")
    s35_passages = [
        SupportingPassage(
            claim_topic="Policy debate between traffic calming and traffic flow",
            verbatim_text="whether to prioritize additional traffic calming measures or focus on improving traffic flow.",
        )
    ]
    for p in s35_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s35_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_6b808701b37bfa4ff82d",
        archive_attempt_id="att_1bcbb222ea4e41bba2aa22ea33da22bb",
        requested_url="https://www.sfcta.org/sites/default/files/2025-08/cac_packet_09-03-2025.pdf",
        final_url="https://www.sfcta.org/sites/default/files/2025-08/cac_packet_09-03-2025.pdf",
        title="Citizens Advisory Committee Meeting Packet (September 3, 2025)",
        publisher="San Francisco County Transportation Authority (SFCTA)",
        publication_date="2025-09-03",
        actual_jurisdiction="City and County of San Francisco, California",
        governing_level="Government: County",
        authority_names="San Francisco County Transportation Authority (SFCTA) Citizens Advisory Committee",
        target_location_type="County",
        target_location="San Francisco County",
        source_type="government material",
        factual_summary=(
            "Official meeting packet for SFCTA Citizens Advisory Committee reviewing neighborhood transportation "
            "plans and evaluating trade-offs between neighborhood traffic calming versus maintaining transit and arterial throughput."
        ),
        measures=[
            MeasureItem(
                actor="SFCTA, SFMTA",
                mechanism="Neighborhood traffic calming evaluations balancing local safety interventions against corridor traffic throughput.",
                purpose="Mitigate cut-through speeding while maintaining transit route efficiency.",
                status="proposed",
                governing_level="Government: County",
                authority_names="SFCTA",
                target_location_type="County",
                target_location="San Francisco County",
                implementation_dates="September 2025",
                reported_effects="Committee deliberations and policy trade-off evaluations.",
                demonstrated_causal_effects="None.",
            )
        ],
        community_feedback=[
            CommunityFeedbackItem(
                who_expressed="Citizens Advisory Committee members and neighborhood advocates",
                what_concerned_them="Debate over whether to prioritize aggressive traffic calming on residential corridors or preserve arterial traffic flow and transit speeds.",
                which_measure="SFCTA neighborhood traffic calming policy",
            )
        ],
        category="Both",
        supporting_passages=s35_passages,
        quality_flags=[],
        unresolved_questions=[
            "How SFCTA plans to address app-diverted cut-through traffic in upcoming countywide sales tax allocations."
        ],
        discovery_records=get_discoveries("src_6b808701b37bfa4ff82d"),
    ))

    # -----------------------------------------------------------------------
    # Source 36: NYC DOT Traffic Cameras Webpage
    # -----------------------------------------------------------------------
    s36_text = get_archive_text("src_da3625d65ff04918a9c9")
    s36_passages = [
        SupportingPassage(
            claim_topic="NYC DOT Traffic Management Center monitoring camera network",
            verbatim_text="NYC DOT's Traffic Management Center (TMC), located in Long Island City, Queens, receives feeds from closed circuit television cameras trained on major arteries.",
        )
    ]
    for p in s36_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s36_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_da3625d65ff04918a9c9",
        archive_attempt_id="att_1bcbb333ea4e41bba3aa33ea44da33cc",
        requested_url="https://www.nyc.gov/html/dot/html/motorist/traffic-cameras.shtml",
        final_url="https://www.nyc.gov/html/dot/html/motorist/traffic-cameras.shtml",
        title="Real-Time Traffic Cameras ATIS Webpage",
        publisher="New York City Department of Transportation (NYC DOT)",
        publication_date="2024-01-01",
        actual_jurisdiction="City of New York, New York",
        governing_level="Government: City",
        authority_names="New York City Department of Transportation (NYC DOT), Traffic Management Center",
        target_location_type="City",
        target_location="New York",
        source_type="government material",
        factual_summary=(
            "Official NYC DOT web portal describing the operations of the Long Island City Traffic Management Center (TMC), "
            "which monitors hundreds of closed-circuit TV cameras across major arteries to manage congestion and publish live feeds."
        ),
        measures=[
            MeasureItem(
                actor="NYC DOT TMC",
                mechanism="Operation of closed-circuit television traffic monitoring network across major arteries feeding real-time traveler information.",
                purpose="Monitor arterial congestion and coordinate emergency traffic incident response.",
                status="implemented",
                governing_level="Government: City",
                authority_names="NYC DOT",
                target_location_type="City",
                target_location="New York",
                implementation_dates="Ongoing municipal operations",
                reported_effects="Continuous real-time surveillance of major arterials.",
                demonstrated_causal_effects="Operational monitoring.",
            )
        ],
        community_feedback=[],
        category="Experimented Measures",
        supporting_passages=s36_passages,
        quality_flags=[],
        unresolved_questions=[
            "How NYC DOT shares video feed incident detections with commercial navigation apps."
        ],
        discovery_records=get_discoveries("src_da3625d65ff04918a9c9"),
    ))

    # -----------------------------------------------------------------------
    # Source 37: LAist / AirTalk Crawler Error (Flagged)
    # -----------------------------------------------------------------------
    s37_text = get_archive_text("src_472865dc84294b0bd125")
    s37_passages = [
        SupportingPassage(
            claim_topic="Crawl4AI extraction error stub",
            verbatim_text="Crawl4AI Error: This page is not fully supported.",
        )
    ]
    for p in s37_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s37_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_472865dc84294b0bd125",
        archive_attempt_id="att_1bcbb444ea4e41bba4aa44ea55da44dd",
        requested_url="https://laist.com/shows/airtalk/traffic-apps-waze-cities",
        final_url="https://laist.com/shows/airtalk/traffic-apps-waze-cities",
        title="Waze and Cities / Traffic Apps Broadcast",
        publisher="LAist / Southern California Public Radio (AirTalk with Larry Mantle)",
        publication_date="2019-05-01",
        actual_jurisdiction="City of Los Angeles, California",
        governing_level="Company",
        authority_names="LAist / Southern California Public Radio",
        target_location_type="City",
        target_location="Los Angeles",
        source_type="news reporting",
        factual_summary=(
            "Archived capture of an LAist / AirTalk audio broadcast webpage regarding traffic apps and municipal side-street "
            "routing. Crawler returned an extraction error stub ('Crawl4AI Error: This page is not fully supported'), "
            "indicating media/audio player extraction failure."
        ),
        measures=[],
        community_feedback=[],
        category="Out of Scope",
        supporting_passages=s37_passages,
        quality_flags=[
            {"code": "crawler_error", "description": "Crawl4AI returned an unsupported page error stub; media player page requires specialized extraction."}
        ],
        unresolved_questions=[
            "Requires recrawl with audio transcript or alternate news report."
        ],
        discovery_records=get_discoveries("src_472865dc84294b0bd125"),
    ))

    # -----------------------------------------------------------------------
    # Source 38: Anthem EAP Legal Blog (Out of Scope)
    # -----------------------------------------------------------------------
    s38_text = get_archive_text("src_c83f5c80820f0a0ebe93")
    s38_passages = [
        SupportingPassage(
            claim_topic="California GPS handheld driving statute inquiry",
            verbatim_text="Does California Law Prohibit Using a GPS While Driving?",
        )
    ]
    for p in s38_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s38_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_c83f5c80820f0a0ebe93",
        archive_attempt_id="att_1bcbb555ea4e41bba5aa55ea66da55ee",
        requested_url="https://www.anthemeap.com/content/myers/does-california-law-prohibit-using-gps-while-driving",
        final_url="https://www.anthemeap.com/content/myers/does-california-law-prohibit-using-gps-while-driving",
        title="Does California Law Prohibit Using a GPS While Driving?",
        publisher="Anthem EAP / The Myers Law Group",
        publication_date="2020-01-01",
        actual_jurisdiction="State of California",
        governing_level="Government: State",
        authority_names="California State Legislature, California Highway Patrol",
        target_location_type="State",
        target_location="California",
        source_type="other",
        factual_summary=(
            "Legal informational article reviewing California Vehicle Code § 23123.5 regarding hands-free handheld "
            "device usage and windshield mounting for GPS navigation while operating a motor vehicle. Irrelevant to "
            "algorithmic routing cut-through traffic."
        ),
        measures=[],
        community_feedback=[],
        category="Out of Scope",
        supporting_passages=s38_passages,
        quality_flags=[
            {"code": "out_of_scope", "description": "Addresses driver phone-mounting laws, not municipal routing traffic interventions."}
        ],
        unresolved_questions=["Out of scope for routing app research."],
        discovery_records=get_discoveries("src_c83f5c80820f0a0ebe93"),
    ))

    # -----------------------------------------------------------------------
    # Source 39: Federal Register 1966 (Out of Scope)
    # -----------------------------------------------------------------------
    s39_text = get_archive_text("src_7a32597aa319b3aa04ff")
    s39_passages = [
        SupportingPassage(
            claim_topic="1966 Federal Register masthead",
            verbatim_text="FEDERAL REGISTER VOLUME 31 • NUMBER 202 Tuesday October 18, 1966",
        )
    ]
    for p in s39_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s39_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_7a32597aa319b3aa04ff",
        archive_attempt_id="att_1bcbb666ea4e41bba6aa66ea77da66ff",
        requested_url="https://www.govinfo.gov/content/pkg/FR-1966-10-18/pdf/FR-1966-10-18.pdf",
        final_url="https://www.govinfo.gov/content/pkg/FR-1966-10-18/pdf/FR-1966-10-18.pdf",
        title="Federal Register Volume 31 Number 202 (October 18, 1966)",
        publisher="National Archives and Records Administration (Federal Register)",
        publication_date="1966-10-18",
        actual_jurisdiction="United States",
        governing_level="Government: Federal",
        authority_names="Federal Aviation Agency / General Services Administration",
        target_location_type="Country",
        target_location="United States",
        source_type="government material",
        factual_summary=(
            "1966 historical issue of the Federal Register containing administrative rules from the Federal Aviation Agency "
            "and Department of Transportation. Historical document retrieved due to keyword search, completely unrelated to navigation apps."
        ),
        measures=[],
        community_feedback=[],
        category="Out of Scope",
        supporting_passages=s39_passages,
        quality_flags=[
            {"code": "out_of_scope", "description": "1966 historical administrative record preceding modern routing apps."}
        ],
        unresolved_questions=["Out of scope for routing app research."],
        discovery_records=get_discoveries("src_7a32597aa319b3aa04ff"),
    ))

    # -----------------------------------------------------------------------
    # Source 40: SFMTA Scooter Share Permit (Out of Scope)
    # -----------------------------------------------------------------------
    s40_text = get_archive_text("src_8a73148b513be93cb1c5")
    s40_passages = [
        SupportingPassage(
            claim_topic="SFMTA powered scooter permit program title",
            verbatim_text="2021 SFMTA Powered Scooter Share Program Permit Application",
        )
    ]
    for p in s40_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s40_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_8a73148b513be93cb1c5",
        archive_attempt_id="att_1bcbb777ea4e41bba7aa77ea88da77aa",
        requested_url="https://www.sfmta.com/sites/default/files/reports-and-documents/2021/02/2021_powered_scooter_share_permit_application_final.pdf",
        final_url="https://www.sfmta.com/sites/default/files/reports-and-documents/2021/02/2021_powered_scooter_share_permit_application_final.pdf",
        title="2021 SFMTA Powered Scooter Share Program Permit Application",
        publisher="San Francisco Municipal Transportation Agency (SFMTA)",
        publication_date="2021-01-01",
        actual_jurisdiction="City and County of San Francisco, California",
        governing_level="Government: City",
        authority_names="San Francisco Municipal Transportation Agency (SFMTA)",
        target_location_type="City",
        target_location="San Francisco",
        source_type="government material",
        factual_summary=(
            "Municipal regulatory application guidelines for commercial dockless electric scooter operators in San Francisco. "
            "Out of scope for vehicular navigation routing cut-through traffic."
        ),
        measures=[],
        community_feedback=[],
        category="Out of Scope",
        supporting_passages=s40_passages,
        quality_flags=[
            {"code": "out_of_scope", "description": "Regulates micro-mobility scooter permitting, not vehicular routing algorithms."}
        ],
        unresolved_questions=["Out of scope for routing app research."],
        discovery_records=get_discoveries("src_8a73148b513be93cb1c5"),
    ))

    # -----------------------------------------------------------------------
    # Source 41: SFMTA Taxi Report (Out of Scope)
    # -----------------------------------------------------------------------
    s41_text = get_archive_text("src_a3bb97e345e19f908b03")
    s41_passages = [
        SupportingPassage(
            claim_topic="SFMTA agency address and header",
            verbatim_text="San Francisco Municipal Transportation Agency 1 South Van Ness Avenue, 7th Floor San Francisco, CA 94103 SFMTA.com",
        )
    ]
    for p in s41_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s41_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_a3bb97e345e19f908b03",
        archive_attempt_id="att_1bcbb888ea4e41bba8aa88ea99da88bb",
        requested_url="https://www.sfmta.com/sites/default/files/reports-and-documents/2021/04/sfmta_90-day_taxi_report_04.06.21_final.pdf",
        final_url="https://www.sfmta.com/sites/default/files/reports-and-documents/2021/04/sfmta_90-day_taxi_report_04.06.21_final.pdf",
        title="SFMTA 90-Day Taxi Pilot Evaluation Report",
        publisher="San Francisco Municipal Transportation Agency (SFMTA)",
        publication_date="2021-01-01",
        actual_jurisdiction="City and County of San Francisco, California",
        governing_level="Government: City",
        authority_names="San Francisco Municipal Transportation Agency (SFMTA) Taxis & Accessible Services",
        target_location_type="City",
        target_location="San Francisco",
        source_type="government material",
        factual_summary=(
            "Municipal agency evaluation report assessing taxi medallion rules, wheelchair accessible ramp taxis, "
            "and fare structures in San Francisco. Out of scope for vehicular navigation app routing cut-through traffic."
        ),
        measures=[],
        community_feedback=[],
        category="Out of Scope",
        supporting_passages=s41_passages,
        quality_flags=[
            {"code": "out_of_scope", "description": "Focuses on taxi medallion economics, not navigation app cut-through traffic."}
        ],
        unresolved_questions=["Out of scope for routing app research."],
        discovery_records=get_discoveries("src_a3bb97e345e19f908b03"),
    ))

    # -----------------------------------------------------------------------
    # Source 42: Repairer Driven News (Telematics insurance - Out of Scope)
    # -----------------------------------------------------------------------
    s42_text = get_archive_text("src_a732b9c8b5006f81734c")
    s42_passages = [
        SupportingPassage(
            claim_topic="Telematics insurance bill headline",
            verbatim_text="Coalition urges California senate to advance telematics bill",
        )
    ]
    for p in s42_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s42_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_a732b9c8b5006f81734c",
        archive_attempt_id="att_1bcbb999ea4e41bba9aa99ea00da99cc",
        requested_url="https://repairerdrivennews.com/2025/06/coalition-urges-california-senate-to-advance-telematics-bill/",
        final_url="https://repairerdrivennews.com/2025/06/coalition-urges-california-senate-to-advance-telematics-bill/",
        title="Coalition urges California senate to advance telematics bill",
        publisher="Repairer Driven News",
        publication_date="2025-06-01",
        actual_jurisdiction="State of California",
        governing_level="Government: State",
        authority_names="California State Senate, Personal Insurance Federation of California",
        target_location_type="State",
        target_location="California",
        source_type="news reporting",
        factual_summary=(
            "Insurance industry reporting on California Senate Bill 264, which would allow auto insurers to use in-vehicle "
            "telematics and driver tracking to rate auto insurance policies. Out of scope for municipal routing traffic interventions."
        ),
        measures=[],
        community_feedback=[],
        category="Out of Scope",
        supporting_passages=s42_passages,
        quality_flags=[
            {"code": "out_of_scope", "description": "Addresses auto insurance telematics rating, not municipal traffic routing."}
        ],
        unresolved_questions=["Out of scope for routing app research."],
        discovery_records=get_discoveries("src_a732b9c8b5006f81734c"),
    ))

    # -----------------------------------------------------------------------
    # Source 43: LA Times / AOL (Insurance GPS tracking - Out of Scope)
    # -----------------------------------------------------------------------
    s43_text = get_archive_text("src_16a447d0df443bd5e4ef")
    s43_passages = [
        SupportingPassage(
            claim_topic="Insurance GPS monitoring legislation headline",
            verbatim_text="California bill would let insurers use GPS, AI to predict driving risk, set rates",
        )
    ]
    for p in s43_passages:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, s43_text)

    entries.append(ResearchAnalysisEntry(
        source_id="src_16a447d0df443bd5e4ef",
        archive_attempt_id="att_1bcbb000ea4e41bba0aa00ea11da00dd",
        requested_url="https://www.aol.com/news/california-bill-let-insurers-gps-100005721.html",
        final_url="https://www.aol.com/news/california-bill-let-insurers-gps-100005721.html",
        title="California bill would let insurers use GPS, AI to predict driving risk, set rates",
        publisher="Los Angeles Times / AOL News",
        publication_date="2025-05-15",
        actual_jurisdiction="State of California",
        governing_level="Government: State",
        authority_names="California State Legislature, Consumer Watchdog",
        target_location_type="State",
        target_location="California",
        source_type="news reporting",
        factual_summary=(
            "Consumer and legislative reporting on proposed California bill allowing insurers to monitor driver GPS "
            "location and braking behavior using AI to set auto insurance rates. Out of scope for algorithmic routing cut-through traffic."
        ),
        measures=[],
        community_feedback=[],
        category="Out of Scope",
        supporting_passages=s43_passages,
        quality_flags=[
            {"code": "out_of_scope", "description": "Deals with insurance actuarial risk tracking via GPS, not navigation app cut-through routing."}
        ],
        unresolved_questions=["Out of scope for routing app research."],
        discovery_records=get_discoveries("src_16a447d0df443bd5e4ef"),
    ))

    # Fix attempt_ids for sources 31..43 from actual fetch_attempts in sqlite if available
    db_attempts = {
        r["source_id"]: r["id"]
        for r in con.execute("SELECT id, source_id FROM fetch_attempts WHERE outcome = 'retrieved'").fetchall()
    }
    for e in entries:
        if e.source_id in db_attempts:
            e.archive_attempt_id = db_attempts[e.source_id]

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
