"""Research analysis coding and exports for retrieved LexisNexis sources.

Codes the 8 verified U.S. Nexis sources covering federal regulation, company
data-sharing programs (Waze for Cities, Waymo, Esri, Waycare), and state-level
emergency alert integrations into Google Maps and Waze.
"""

from __future__ import annotations

import json
from pathlib import Path

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
    build_all_analyses,
    export_analysis_csv,
    export_analysis_json,
    publication_year,
    verify_passage,
)


_FOLDER_CACHE: dict[Path, dict[str, Path]] = {}


def _find_nexis_folder(nexis_root: Path, doc_id: str) -> Path | None:
    """Find the stored folder for a specific document ID or slug."""
    if nexis_root not in _FOLDER_CACHE:
        cache: dict[str, Path] = {}
        for p in nexis_root.glob("*/*"):
            if p.is_dir() and (p / "content.txt").is_file():
                cache[p.name] = p
        _FOLDER_CACHE[nexis_root] = cache

    cache = _FOLDER_CACHE[nexis_root]
    suffix = doc_id.replace("urn:contentItem:", "")
    for name, path in cache.items():
        if suffix in name:
            return path

    # Fallback to rglob if nested differently
    for p in nexis_root.rglob(f"*{suffix}*"):
        if p.is_dir() and (p / "content.txt").is_file():
            return p
    return None


def build_nexis_analyses(nexis_root: Path = Path("data/nexis")) -> list[ResearchAnalysisEntry]:
    """Build and validate qualitative research analysis entries for the 8 U.S. Nexis sources."""

    def get_text_and_meta(doc_id: str) -> tuple[str, dict, Path]:
        folder = _find_nexis_folder(nexis_root, doc_id)
        if not folder:
            raise FileNotFoundError(f"Could not find Nexis archive folder for doc_id: {doc_id}")
        content = (folder / "content.txt").read_text(encoding="utf-8")
        meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8")) if (folder / "metadata.json").is_file() else {}
        return content, meta, folder

    entries: list[ResearchAnalysisEntry] = []

    # -------------------------------------------------------------------------
    # 1. Waymo & Waze Pothole Partnership (Benzinga)
    # -------------------------------------------------------------------------
    doc_1 = "urn:contentItem:6J9T-Y0C3-S3T5-M0JH-00000-00"
    text_1, meta_1, folder_1 = get_text_and_meta(doc_1)
    passages_1 = [
        SupportingPassage(
            claim_topic="Waymo sensor pothole detection and municipal data sharing through Waze for Cities",
            verbatim_text='In an official statement, Waymo announced it was partnering with Waze to "provide cities with sharper tools" to deal with potholes on the road. The program would use Waymo\'s "perception and physical feedback" technology to pinpoint pothole locations in the areas that the service operates in.',
        ),
        SupportingPassage(
            claim_topic="Waze for Cities platform integration for municipal Departments of Transportation",
            verbatim_text='Waymo also said that the program would be available to the Department of Transportation (DOT) via the "Waze for Cities" platform.',
        ),
        SupportingPassage(
            claim_topic="Rollout markets and mayoral endorsement of administrative efficiency",
            verbatim_text='The program will initially be launched in the San FranciscoBay Area, Los Angeles, Phoenix, Austin, and Atlanta. Waymo says it has identified over 500 potholes so far in these areas. San Jose Mayor Matt Mahan hailed the program, saying that the technology can help "identify issues like potholes faster" and improve efficiency in the administration\'s responses.',
        ),
    ]
    for p in passages_1:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, text_1)

    entries.append(
        ResearchAnalysisEntry(
            source_id=f"nexis_{doc_1}",
            archive_attempt_id=doc_1,
            requested_url=meta_1.get("url", ""),
            final_url=meta_1.get("url", ""),
            title="Alphabet's Tesla Robotaxi Rival Waymo Announces Partnership With Waze To Help Cities Fix Potholes",
            publisher="Benzinga.com",
            publication_date="2026-04-10",
            actual_jurisdiction="Multi-jurisdiction (San Francisco Bay Area, Los Angeles, Phoenix, Austin, Atlanta)",
            governing_level="Company",
            authority_names="Waymo LLC, Waze (Google / Alphabet), City of San Jose, Municipal Departments of Transportation",
            target_location_type="City",
            target_location="San Francisco Bay Area, Los Angeles, Phoenix, Austin, Atlanta",
            source_type="news reporting",
            factual_summary=(
                "Waymo and Waze launched a collaborative initiative utilizing Waymo autonomous vehicle perception "
                "and vibration/physical feedback sensors to detect road surface potholes during passenger operations. "
                "Road hazard and degradation coordinates are transmitted to municipal transportation departments via "
                "the Waze for Cities data platform, piloting in San Francisco, Los Angeles, Phoenix, Austin, and Atlanta."
            ),
            measures=[
                MeasureItem(
                    actor="Waymo LLC & Waze (Alphabet)",
                    mechanism="Automated road hazard and pothole sensing by robotaxi fleets integrated into Waze for Cities public data exchange platform for municipal road crews.",
                    purpose="Identify pavement degradation and potholes faster, streamline municipal public works repairs, and warn motorists.",
                    status="piloted",
                    governing_level="Company",
                    authority_names="Waymo LLC & Waze (Alphabet)",
                    target_location_type="City",
                    target_location="San Francisco Bay Area, Los Angeles, Phoenix, Austin, Atlanta",
                    implementation_dates="Announced April 2026; initial launch across 5 metropolitan areas.",
                    reported_effects="Over 500 potholes identified during initial rollout; San Jose Mayor Matt Mahan cited faster municipal response times.",
                    demonstrated_causal_effects="Observational identification of 500+ road hazards; causal repair completion rate not evaluated.",
                )
            ],
            community_feedback=[
                CommunityFeedbackItem(
                    who_expressed="San Jose Mayor Matt Mahan",
                    what_concerned_them="Endorsed public-private data collaboration to accelerate pothole detection and improve city public works efficiency.",
                    which_measure="Waymo-Waze pothole reporting partnership via Waze for Cities.",
                )
            ],
            category="Experimented Measures",
            supporting_passages=passages_1,
            quality_flags=[],
            unresolved_questions=[
                "Whether municipal public works departments have formal SLAs to repair potholes reported through Waze for Cities.",
                "Whether detection algorithms trigger route avoidances in Waze navigation before road crews complete repairs.",
            ],
            archive_dir=str(folder_1),
        )
    )

    # -------------------------------------------------------------------------
    # 2. Waymo & Waze Pothole Pilot (Mashable)
    # -------------------------------------------------------------------------
    doc_2 = "urn:contentItem:6KGN-8633-RV2G-70PX-00000-00"
    text_2, meta_2, folder_2 = get_text_and_meta(doc_2)
    passages_2 = [
        SupportingPassage(
            claim_topic="Waymo-Waze pothole patching pilot and municipal road crew data sharing",
            verbatim_text="Transportation companies Waymo and Waze announced a new, pothole-patching pilot today, harnessing their troves of street data to map out areas in need of fixing.",
        ),
        SupportingPassage(
            claim_topic="Sensor detection by autonomous fleet and transmission to state/city DOTs",
            verbatim_text="The program will rely on the perception and physical feedback systems built into Waymo's autonomous fleet vehicles to detect the location and condition of city potholes. That data will then be sent to city and state Departments of Transportation through the free Waze for Cities program",
        ),
        SupportingPassage(
            claim_topic="Crowdsourced verification by Waze app users",
            verbatim_text="Waze users will be able to access and verify the data in the app, starting with riders in Los Angeles, when driving through areas with Waymo fleets.",
        ),
    ]
    for p in passages_2:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, text_2)

    entries.append(
        ResearchAnalysisEntry(
            source_id=f"nexis_{doc_2}",
            archive_attempt_id=doc_2,
            requested_url=meta_2.get("url", ""),
            final_url=meta_2.get("url", ""),
            title="Can Waymo and Waze fix cities' potholes?",
            publisher="Mashable",
            publication_date="2026-04-09",
            actual_jurisdiction="Multi-jurisdiction (San Francisco Bay Area, Los Angeles, Phoenix, Austin, Atlanta)",
            governing_level="Company",
            authority_names="Waymo LLC, Waze (Google), City & State Departments of Transportation",
            target_location_type="City",
            target_location="San Francisco, Los Angeles, Phoenix, Austin, Atlanta",
            source_type="news reporting",
            factual_summary=(
                "Mashable analysis of the Waymo and Waze pothole-patching pilot. Robotaxis automatically detect pavement "
                "flaws and upload them through Waze for Cities to state and local DOTs, while Waze drivers in pilot cities "
                "can view and verify pothole markers in-app. Evaluates municipal capacity bottlenecks to repair identified potholes."
            ),
            measures=[
                MeasureItem(
                    actor="Waymo, Waze, Municipal & State DOTs",
                    mechanism="Autonomous vehicle sensor-based pavement defect detection combined with in-app crowdsourced driver verification and municipal DOT dispatch.",
                    purpose="Fill municipal road inspection reporting gaps, provide real-time hazard warnings to navigation users, and prioritize roadway resurfacing.",
                    status="piloted",
                    governing_level="Company",
                    authority_names="Waymo LLC & Waze",
                    target_location_type="City",
                    target_location="San Francisco, Los Angeles, Phoenix, Austin, Atlanta",
                    implementation_dates="Piloting April 2026 across 5 cities; planned expansion to freeze-thaw climates.",
                    reported_effects="500 potholes mapped across initial test markets.",
                    demonstrated_causal_effects="None established on roadway longevity or municipal budget reallocations.",
                )
            ],
            community_feedback=[
                CommunityFeedbackItem(
                    who_expressed="Urban mobility analysts and local road maintenance stakeholders",
                    what_concerned_them="Concerned that automated pothole discovery without increased municipal infrastructure funding may overwhelm local road crews with unfixable backlogs.",
                    which_measure="Waze for Cities autonomous vehicle pothole data pipeline.",
                )
            ],
            category="Both",
            supporting_passages=passages_2,
            quality_flags=[],
            unresolved_questions=[
                "Whether crowdsourced user verification in Waze filters out false-positive detections from autonomous vehicles.",
                "How long pothole hazard markers persist in Waze routing algorithms after municipal road crews finish repairs.",
            ],
            archive_dir=str(folder_2),
        )
    )

    # -------------------------------------------------------------------------
    # 3. Esri Community Maps Road Closures (Business Wire, 2026)
    # -------------------------------------------------------------------------
    doc_3 = "urn:contentItem:6K23-G0Y3-S99D-X1PV-00000-00"
    text_3, meta_3, folder_3 = get_text_and_meta(doc_3)
    passages_3 = [
        SupportingPassage(
            claim_topic="Esri Community Maps road closure data sharing with Google Maps and Waze",
            verbatim_text="Esri has expanded its Community Maps Program , enabling road closure data to be shared with Google Maps and Waze. The Road Closures solution, in Esri's ArcGIS platform, was introduced last year as a way for users to easily share road closure updates directly with popular consumer mapping providers so they can update their maps with this important information.",
        ),
        SupportingPassage(
            claim_topic="Active municipal participation across 100+ communities nationwide",
            verbatim_text="Over 100 communities around the United States and other countries are actively sharing their road closure information. ArcGIS users can now easily share that same authoritative data with Google Maps and Waze via the Waze for Cities program.",
        ),
        SupportingPassage(
            claim_topic="Public sector demand for Google Maps and Waze integration",
            verbatim_text='"For over a year, we\'ve been working with dozens of our local government users to share their road closure information with our initial consumer mapping partners, Apple Maps and TomTom," said Deane Kensok, chief technology officer for ArcGIS content at Esri.',
        ),
        SupportingPassage(
            claim_topic="Waze product management on seamless integration into consumer apps",
            verbatim_text='"We\'re thrilled to make it easier for drivers to avoid road closures," said Assaf Eisenberg, Waze product manager. "By empowering governments to easily share road closures through the Esri Community Map[s] Program and Waze for Cities, we are seamlessly integrating that information into Waze and Google Maps."',
        ),
    ]
    for p in passages_3:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, text_3)

    entries.append(
        ResearchAnalysisEntry(
            source_id=f"nexis_{doc_3}",
            archive_attempt_id=doc_3,
            requested_url=meta_3.get("url", ""),
            final_url=meta_3.get("url", ""),
            title="Esri Helps Bring Up-to-Date Road Closure Information to Google Maps and Waze",
            publisher="Business Wire",
            publication_date="2026-07-14",
            actual_jurisdiction="United States (Over 100 communities nationwide)",
            governing_level="Company",
            authority_names="Esri, Google Maps, Waze (Google LLC), Local Government Transportation Agencies",
            target_location_type="Country",
            target_location="United States",
            source_type="company statement",
            factual_summary=(
                "Esri expanded its ArcGIS Community Maps Program and Road Closures solution to allow over 100 municipal "
                "and county governments to publish authoritative road closure layers directly to Google Maps and Waze via "
                "Waze for Cities, while ingesting crowdsourced traffic incidents back into public GIS portals."
            ),
            measures=[
                MeasureItem(
                    actor="Esri, Google LLC (Google Maps & Waze), Participating Municipalities",
                    mechanism="ArcGIS Road Closures digital pipeline exporting authoritative municipal street closure records to Google Maps and Waze navigation algorithms via Waze for Cities.",
                    purpose="Prevent navigation apps from directing cut-through or standard traffic onto closed roads, construction zones, or emergency corridors.",
                    status="implemented",
                    governing_level="Company",
                    authority_names="Esri, Google Maps & Waze Product Management",
                    target_location_type="Country",
                    target_location="United States",
                    implementation_dates="Launched initially with Apple Maps and TomTom in 2025; expanded to Google Maps and Waze in July 2026.",
                    reported_effects="Adopted by over 100 local communities; eliminates manual map change requests.",
                    demonstrated_causal_effects="None quantified on network delay; real-time map synchronization confirmed.",
                )
            ],
            community_feedback=[
                CommunityFeedbackItem(
                    who_expressed="Local government GIS and public works contributors",
                    what_concerned_them="Requested direct expansion of the automated closure feed from Apple Maps/TomTom to Google Maps and Waze to cover the majority of consumer drivers.",
                    which_measure="Esri ArcGIS Community Maps Road Closures integration.",
                )
            ],
            category="Experimented Measures",
            supporting_passages=passages_3,
            quality_flags=[
                {"code": "flag_corporate_press_release", "description": "Corporate press release from software vendor Esri announcing commercial integration."}
            ],
            unresolved_questions=[
                "Latency between a municipal GIS road closure entry and its reflection in live consumer routing engines.",
                "Whether municipal road closures intended for cut-through traffic mitigation are accepted by Google Maps on equal footing with emergency/construction closures.",
            ],
            archive_dir=str(folder_3),
        )
    )

    # -------------------------------------------------------------------------
    # 4. Esri & Waze Connected Citizens Program (Business Wire, 2016)
    # -------------------------------------------------------------------------
    doc_4 = "urn:contentItem:5KXP-09P1-DXY3-00J6-00000-00"
    text_4, meta_4, folder_4 = get_text_and_meta(doc_4)
    passages_4 = [
        SupportingPassage(
            claim_topic="Esri and Waze partnership for municipal open data sharing and intelligent transportation",
            verbatim_text="Global smart-mapping leader Esri today announced a new partnership with Waze, the free, crowdsourced traffic and navigation app that makes it easier for governments of every size, anywhere in the world, to begin building intelligent transportation systems in their communities.",
        ),
        SupportingPassage(
            claim_topic="ArcGIS integration with Waze Connected Citizens Program bidirectional feed",
            verbatim_text="Governments already using the Esri ArcGIS platform can quickly and easily exchange data through the Waze Connected Citizens Program, a free, two-way data share of publicly available traffic information.",
        ),
        SupportingPassage(
            claim_topic="Cost avoidance for local governments avoiding physical IoT infrastructure",
            verbatim_text='"Municipalities can now leverage real-time reports without having to invest in sensor networks or an Internet of Things infrastructure," said Andrew Stauffer, manager of civic technology at Esri.',
        ),
    ]
    for p in passages_4:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, text_4)

    entries.append(
        ResearchAnalysisEntry(
            source_id=f"nexis_{doc_4}",
            archive_attempt_id=doc_4,
            requested_url=meta_4.get("url", ""),
            final_url=meta_4.get("url", ""),
            title="Esri Partners with Waze Connected Citizens Program to Deliver Unprecedented Open Data-Sharing Options to Governments Partnership Enables More Municipalities around the World to Share and Analyze Waze Traffic Data",
            publisher="Business Wire",
            publication_date="2016-10-12",
            actual_jurisdiction="United States (National / Municipalities nationwide)",
            governing_level="Company",
            authority_names="Esri, Waze (Google Inc.), Local Government Agencies",
            target_location_type="Country",
            target_location="United States",
            source_type="company statement",
            factual_summary=(
                "Esri formed a foundational partnership with the Waze Connected Citizens Program (CCP) integrating Waze's "
                "crowdsourced traffic data feeds and municipal road closure uploads into the ArcGIS cloud platform, allowing "
                "cities to synchronize navigation maps without investing in dedicated roadside sensor networks."
            ),
            measures=[
                MeasureItem(
                    actor="Esri & Waze (Connected Citizens Program)",
                    mechanism="Cloud-based bidirectional data exchange connector embedding Waze real-time incident reports and municipal road closure geometries into ArcGIS enterprise software.",
                    purpose="Enable municipal governments to monitor live congestion, coordinate emergency responses, and update navigation apps during roadworks.",
                    status="implemented",
                    governing_level="Company",
                    authority_names="Esri & Waze Connected Citizens Program",
                    target_location_type="Country",
                    target_location="United States",
                    implementation_dates="Announced October 12, 2016; deployed globally across ArcGIS municipal subscribers.",
                    reported_effects="Enabled local agencies to access crowdsourced incident data without expensive physical IoT hardware.",
                    demonstrated_causal_effects="None demonstrated.",
                )
            ],
            community_feedback=[
                CommunityFeedbackItem(
                    who_expressed="Andrew Stauffer, Manager of Civic Technology at Esri",
                    what_concerned_them="Emphasized that local governments need cost-effective access to real-time traffic data without expensive physical roadside sensor infrastructure.",
                    which_measure="Waze Connected Citizens Program ArcGIS integration.",
                )
            ],
            category="Experimented Measures",
            supporting_passages=passages_4,
            quality_flags=[
                {"code": "flag_corporate_press_release", "description": "Vendor press release describing commercial cloud connector rollout."}
            ],
            unresolved_questions=[
                "How many U.S. cities actively used the bidirectional feed to upload local traffic calming closures.",
                "Whether municipal traffic engineers found crowdsourced Waze data sufficiently clean for capital planning.",
            ],
            archive_dir=str(folder_4),
        )
    )

    # -------------------------------------------------------------------------
    # 5. Waze & Waycare Traffic Data Pact (VentureBeat, 2018)
    # -------------------------------------------------------------------------
    doc_5 = "urn:contentItem:5S66-H271-F03R-N3F4-00000-00"
    text_5, meta_5, folder_5 = get_text_and_meta(doc_5)
    passages_5 = [
        SupportingPassage(
            claim_topic="Waze and Waycare partnership to share traffic data and relieve congestion",
            verbatim_text="Waze[1] is partnering with traffic-management platform Waycare[2] to share data and improve congested roads.",
        ),
        SupportingPassage(
            claim_topic="Waycare platform orientation toward public transport authorities and first responders",
            verbatim_text="The Waycare platform is geared toward public bodies — such as law enforcement, traffic operations, traffic engineering, emergency services, and the freeway service patrol",
        ),
        SupportingPassage(
            claim_topic="CEO statement on Waze two-way communication partnership",
            verbatim_text="'Waze, from the navigation side, is the most developed, methodical two-way communication partnership we have,'Waycare CEO Noam Maital told VentureBeat.",
        ),
    ]
    for p in passages_5:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, text_5)

    entries.append(
        ResearchAnalysisEntry(
            source_id=f"nexis_{doc_5}",
            archive_attempt_id=doc_5,
            requested_url=meta_5.get("url", ""),
            final_url=meta_5.get("url", ""),
            title="Waze and Waycare strike data-sharing pact to improve city traffic",
            publisher="VentureBeat",
            publication_date="2018-04-26",
            actual_jurisdiction="United States (Southern Nevada / Las Vegas, Tampa, Delaware)",
            governing_level="Company",
            authority_names="Waze (Google LLC), Waycare Technologies, Regional Transportation Commission of Southern Nevada (RTC)",
            target_location_type="City",
            target_location="Las Vegas, NV (Southern Nevada), Tampa, FL, Delaware",
            source_type="news reporting",
            factual_summary=(
                "Waze and traffic intelligence startup Waycare signed a data-sharing agreement to pool crowdsourced Waze "
                "incident data with public agency sensors, cameras, and connected vehicles. The integrated platform was "
                "piloted in Southern Nevada with the Regional Transportation Commission, expanding to Tampa and Delaware "
                "to improve freeway incident response times."
            ),
            measures=[
                MeasureItem(
                    actor="Waze, Waycare Technologies, Regional Transportation Commission of Southern Nevada",
                    mechanism="Aggregating Waze driver reports into Waycare AI traffic management platform alongside municipal telematics, freeway service patrols, and transit feeds.",
                    purpose="Accelerate incident detection, optimize municipal traffic signal timing, and broadcast verified hazard alerts to navigation users.",
                    status="piloted",
                    governing_level="Company",
                    authority_names="Waze, Waycare Technologies, RTC Southern Nevada",
                    target_location_type="City",
                    target_location="Las Vegas, NV (Southern Nevada), Tampa, FL, Delaware",
                    implementation_dates="Inaugural project launched October 2017 in Southern Nevada; data pact formalized April 2018; expanded to FL and DE.",
                    reported_effects="Accelerated incident identification; provided multi-source traffic awareness to public operations centers.",
                    demonstrated_causal_effects="None reported in source.",
                )
            ],
            community_feedback=[
                CommunityFeedbackItem(
                    who_expressed="Noam Maital, CEO of Waycare",
                    what_concerned_them="Praised Waze as the most methodical two-way crowdsourced data partner for municipal traffic operations.",
                    which_measure="Waze Connected Citizens Program and Waycare traffic platform integration.",
                )
            ],
            category="Experimented Measures",
            supporting_passages=passages_5,
            quality_flags=[],
            unresolved_questions=[
                "Degree of reduction in secondary crashes achieved during the Southern Nevada RTC pilot.",
                "Whether bidirectional feeds enabled city traffic management centers to request rerouting around specific bottleneck corridors.",
            ],
            archive_dir=str(folder_5),
        )
    )

    # -------------------------------------------------------------------------
    # 6. USDOT & NHTSA Proposed App Regulation (VentureBeat, 2014)
    # -------------------------------------------------------------------------
    doc_6 = "urn:contentItem:5CFG-S691-F03R-N0CD-00000-00"
    text_6, meta_6, folder_6 = get_text_and_meta(doc_6)
    passages_6 = [
        SupportingPassage(
            claim_topic="Federal transportation bill proposing NHTSA oversight over smartphone navigation apps",
            verbatim_text="If the U.S. government has its way, the Transportation Department will have full oversight over apps like Google Maps, Apple Maps, and Waze. The Obama administration's proposed transportation bill[2] would allow the National Highway Traffic Safety Administration to regulate all types of vehicle navigation aids, including smartphone apps and smart dashboard systems.",
        ),
        SupportingPassage(
            claim_topic="NHTSA authority to impose restrictions and demand modifications for safety",
            verbatim_text="The agency could set restrictions and demand changes if the apps appear to threaten in-car safety, reports the New York Times[3].",
        ),
        SupportingPassage(
            claim_topic="Tech industry opposition and unworkability arguments",
            verbatim_text="Some tech firms have loudly protested the pending legislation. They argue the laws would be impractical to enforce in a rapidly changing market with tens of thousands of navigation apps. 'How can any regulatory authority hope to effectively police such a complex environment?' Timothy McGuckin, CEO of road toll payment startup GeoToll, asked in an op-ed on The Hill[4].",
        ),
    ]
    for p in passages_6:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, text_6)

    entries.append(
        ResearchAnalysisEntry(
            source_id=f"nexis_{doc_6}",
            archive_attempt_id=doc_6,
            requested_url=meta_6.get("url", ""),
            final_url=meta_6.get("url", ""),
            title="The U.S. government wants to regulate Google Maps all other car navigation apps",
            publisher="VentureBeat",
            publication_date="2014-06-16",
            actual_jurisdiction="United States",
            governing_level="Government: Federal",
            authority_names="U.S. Department of Transportation (USDOT), National Highway Traffic Safety Administration (NHTSA), Obama Administration, U.S. Congress",
            target_location_type="Country",
            target_location="United States",
            source_type="news reporting",
            factual_summary=(
                "The Obama administration's proposed federal surface transportation reauthorization bill (GROW AMERICA Act) "
                "included statutory provisions empowering NHTSA to regulate vehicle navigation aids, specifically mobile "
                "smartphone apps like Google Maps, Apple Maps, and Waze, granting authority to mandate design modifications "
                "for distracted driving safety."
            ),
            measures=[
                MeasureItem(
                    actor="U.S. Department of Transportation & NHTSA (Obama Administration)",
                    mechanism="Proposed federal statutory authority under the surface transportation bill granting NHTSA regulatory oversight and recall/modification powers over mobile smartphone navigation apps.",
                    purpose="Mitigate driver distraction by imposing safety restrictions on mobile navigation interfaces.",
                    status="proposed",
                    governing_level="Government: Federal",
                    authority_names="U.S. Department of Transportation (USDOT), NHTSA",
                    target_location_type="Country",
                    target_location="United States",
                    implementation_dates="Proposed in June 2014 transportation bill submitted to Congress.",
                    reported_effects="Intense lobbying and pushback from tech firms and app developers.",
                    demonstrated_causal_effects="Legislation did not enact smartphone pre-market app approval.",
                )
            ],
            community_feedback=[
                CommunityFeedbackItem(
                    who_expressed="Tech industry startups and executives (e.g. Timothy McGuckin, CEO of GeoToll)",
                    what_concerned_them="Protested proposed federal navigation app regulation as unenforceable in a rapidly changing market and a severe threat to mobile tech innovation.",
                    which_measure="Proposed USDOT/NHTSA smartphone navigation app regulatory authority in GROW AMERICA Act.",
                )
            ],
            category="Both",
            supporting_passages=passages_6,
            quality_flags=[],
            unresolved_questions=[
                "Whether Congress ultimately stripped the smartphone navigation app regulatory provision before passing the FAST Act in 2015.",
                "How USDOT distinctively treated built-in dashboard telematics versus standalone mobile operating system apps.",
            ],
            archive_dir=str(folder_6),
        )
    )

    # -------------------------------------------------------------------------
    # 7. Reason Magazine: Federal App Regulation & People v. Spriggs
    # -------------------------------------------------------------------------
    doc_7 = "urn:contentItem:6G76-J083-RVJY-R2R6-00000-00"
    text_7, meta_7, folder_7 = get_text_and_meta(doc_7)
    passages_7 = [
        SupportingPassage(
            claim_topic="Proposed transportation bill giving NHTSA power over Google Maps and Waze",
            verbatim_text="Provisions in the proposed transportation bill—which Congress will look at in the next few months—would give the National Highway Traffic Safety Administration the power to regulate apps like Google Maps and Waze, the crowdsourced traffic reporting tool.",
        ),
        SupportingPassage(
            claim_topic="California distracted driving ticket for map viewing overturned on appeal",
            verbatim_text="In California, Steven R. Spriggs received a $165 ticket two years ago for using his iPhone while driving in stop-and-go traffic near Fresno. A highway patrol motorcycle officer rolled up alongside his car after seeing the glow from the screen on Mr. Spriggs's face.",
        ),
        SupportingPassage(
            claim_topic="National Safety Council demand to regulate nomadic mobile devices",
            verbatim_text='Safety advocates say regulators need to do more. "We absolutely need to be looking at these nomadic devices," said Deborah A. P. Hersman , president of the National Safety Council',
        ),
    ]
    for p in passages_7:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, text_7)

    entries.append(
        ResearchAnalysisEntry(
            source_id=f"nexis_{doc_7}",
            archive_attempt_id=doc_7,
            requested_url=meta_7.get("url", ""),
            final_url=meta_7.get("url", ""),
            title="Stuck in Traffic? Thanks, Obama!: Feds to Regulate Waze, Google Maps, and Other Navigation Apps",
            publisher="Reason Magazine",
            publication_date="2014-06-16",
            actual_jurisdiction="United States (Federal & California state law case study)",
            governing_level="Government: Federal",
            authority_names="U.S. Congress, NHTSA, California Highway Patrol, California Fifth District Court of Appeal",
            target_location_type="Country",
            target_location="United States",
            source_type="news reporting",
            factual_summary=(
                "Reason Magazine analysis of the federal transportation bill proposal to grant NHTSA oversight over "
                "smartphone navigation apps like Waze and Google Maps. Connects federal regulatory ambitions with "
                "state-level distracted driving law enforcement, highlighting the California appellate decision "
                "People v. Spriggs, which overturned a citation given to a driver for looking at a smartphone map in stop-and-go traffic."
            ),
            measures=[
                MeasureItem(
                    actor="U.S. Congress, NHTSA, California State Legislature & Courts",
                    mechanism="Proposed federal statutory oversight by NHTSA over mobile navigation software; state hands-free traffic enforcement (People v. Spriggs appellate ruling legalizing smartphone map consultation while driving).",
                    purpose="Address distracted driving hazards; establish legal boundary between prohibited phone calls/texting and permissible GPS map navigation.",
                    status="proposed",
                    governing_level="Government: Federal",
                    authority_names="NHTSA, California Highway Patrol, California Court of Appeal",
                    target_location_type="Country",
                    target_location="United States",
                    implementation_dates="Federal bill debated 2014; California appellate decision issued 2014.",
                    reported_effects="Judicial reversal of California traffic infraction; national debate over federal regulation of 'nomadic' digital devices.",
                    demonstrated_causal_effects="California appellate ruling established binding state legal precedent permitting viewing mobile GPS maps while driving.",
                )
            ],
            community_feedback=[
                CommunityFeedbackItem(
                    who_expressed="Deborah A. P. Hersman, President of the National Safety Council; motorist Steven R. Spriggs",
                    what_concerned_them="Safety advocates demanded federal regulation of nomadic smartphone devices in moving cars; motorists challenged police enforcement against navigation map usage.",
                    which_measure="NHTSA navigation app regulation and state distracted driving police enforcement.",
                )
            ],
            category="Both",
            supporting_passages=passages_7,
            quality_flags=[],
            unresolved_questions=[
                "Subsequent California legislative amendments to Section 23123.5 regarding hands-free smartphone mounting requirements.",
                "Distinction between state moving violation enforcement and federal safety design standards for navigation apps.",
            ],
            archive_dir=str(folder_7),
        )
    )

    # -------------------------------------------------------------------------
    # 8. Illinois State Police Scott's Law Alerts (Journal-Courier, 2024)
    # -------------------------------------------------------------------------
    doc_8 = "urn:contentItem:6DP3-HNN3-SBYC-S06J-00000-00"
    text_8, meta_8, folder_8 = get_text_and_meta(doc_8)
    passages_8 = [
        SupportingPassage(
            claim_topic="Illinois State Police partnership for GPS traffic safety alerts under Scott's Law",
            verbatim_text="Illinois State Police and the Illinois Department of Innovation and Technology are partnering with a GPS-based traffic information system to provide expanded safety alerts related to Scott’s Law",
        ),
        SupportingPassage(
            claim_topic="Statutory requirement under Scott's Law (The Move Over Law)",
            verbatim_text="Scott’s Law, or The Move Over Law, requires drivers to slow down and change lanes when approaching stationary emergency vehicles",
        ),
        SupportingPassage(
            claim_topic="Google Public Sector and Waze/Google Maps integration",
            verbatim_text="The partnership with HAAS Alert builds on a state police partnership with Google Public Sector and Move Over crash alerts in Waze and Google Maps",
        ),
    ]
    for p in passages_8:
        p.verified, p.verification_note = verify_passage(p.verbatim_text, text_8)

    entries.append(
        ResearchAnalysisEntry(
            source_id=f"nexis_{doc_8}",
            archive_attempt_id=doc_8,
            requested_url=meta_8.get("url", ""),
            final_url=meta_8.get("url", ""),
            title="Alert system to warn Illinois drivers about traffic risks, remind them of Scott's Law",
            publisher="Jacksonville Journal-Courier Online",
            publication_date="2024-12-19",
            actual_jurisdiction="Illinois",
            governing_level="Government: State",
            authority_names="Illinois State Police (ISP), Illinois Department of Innovation and Technology (DoIT), Google Public Sector, HAAS Alert",
            target_location_type="State",
            target_location="Illinois",
            source_type="news reporting",
            factual_summary=(
                "Illinois State Police and the Illinois Department of Innovation and Technology integrated HAAS Alert's "
                "digital alerting service with navigation apps to broadcast real-time warnings to drivers approaching "
                "stationary emergency vehicles on highways under Scott's Law (Move Over Law), expanding on an established "
                "ISP partnership with Google Public Sector for Waze and Google Maps."
            ),
            measures=[
                MeasureItem(
                    actor="Illinois State Police (ISP), Illinois DoIT, Google Public Sector, HAAS Alert",
                    mechanism="Geolocated emergency transponder alerts broadcast into Google Maps, Waze, and in-vehicle navigation systems to notify drivers approaching stationary emergency responders.",
                    purpose="Enforce and promote compliance with Scott's Law (Move Over Law), protect state troopers, and prevent roadside highway crashes.",
                    status="implemented",
                    governing_level="Government: State",
                    authority_names="Illinois State Police (ISP), Illinois Department of Innovation and Technology (DoIT)",
                    target_location_type="State",
                    target_location="Illinois",
                    implementation_dates="Scott's Law alert partnership with Google Public Sector deployed 2024; HAAS Alert integration expanded December 2024.",
                    reported_effects="Real-time in-app collision and Move Over hazard notifications delivered to motorists across Illinois state highway corridors.",
                    demonstrated_causal_effects="None quantified in article on crash rate reductions.",
                )
            ],
            community_feedback=[
                CommunityFeedbackItem(
                    who_expressed="Illinois State Police leadership and roadside safety advocates",
                    what_concerned_them="Advocated proactive in-cab digital alerting through consumer mapping apps as essential to prevent fatal crashes involving stationary patrol cars on highway shoulders.",
                    which_measure="ISP Scott's Law digital alert integration with Waze and Google Maps.",
                )
            ],
            category="Experimented Measures",
            supporting_passages=passages_8,
            quality_flags=[],
            unresolved_questions=[
                "Whether in-app Move Over audio chimes cause driver distraction or prompt abrupt lane changes in heavy traffic.",
                "Percentage of active Illinois drivers utilizing compatible navigation apps during stationary trooper stops.",
            ],
            archive_dir=str(folder_8),
        )
    )

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
        for p in e.supporting_passages:
            if not p.verified:
                raise ValueError(f"Passage '{p.claim_topic}' in {e.source_id} failed verification against source text!")

    return entries


def update_nexis_report(
    nexis_root: Path = Path("data/nexis"),
    report_path: Path = Path("data/exports/nexis_report.csv"),
) -> list[ResearchAnalysisEntry]:
    """Analyze all retrieved U.S. Nexis sources and write fully coded rows to nexis_report.csv."""
    entries = build_nexis_analyses(nexis_root)
    export_analysis_csv(entries, report_path)
    return entries


def update_all_sources_dataset(
    db_path: Path = Path("data/news.sqlite"),
    archive_root: Path = Path("."),
    nexis_root: Path = Path("data/nexis"),
    output_csv: Path = Path("data/exports/research_analysis_all_sources.csv"),
    output_json: Path = Path("data/exports/research_analysis_all_sources.json"),
) -> list[ResearchAnalysisEntry]:
    """Build baseline crawled sources + Nexis sources and export combined datasets."""
    baseline_entries = build_all_analyses(db_path, archive_root)
    nexis_entries = build_nexis_analyses(nexis_root)

    # Avoid duplicate source_ids if run multiple times
    combined_dict: dict[str, ResearchAnalysisEntry] = {e.source_id: e for e in baseline_entries}
    for ne in nexis_entries:
        combined_dict[ne.source_id] = ne

    combined = list(combined_dict.values())
    export_analysis_csv(combined, output_csv)
    export_analysis_json(combined, output_json)
    return combined
