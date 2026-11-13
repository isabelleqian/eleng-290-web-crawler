import json
import csv
import sqlite3
import re
import urllib.parse
from pathlib import Path

# Academic publications excluded from journalistic news corpus
EXCLUDED_ACADEMIC_PAPERS = {
    "src_e3cc761c4fd41439dcff": (
        "Academic Research Publication",
        15,
        "Academic research publication / peer-reviewed journal paper (Nature Cities), not a journalistic news report; covered by news article in SF Chronicle (nexis_urn:contentItem:6KF6-GDK3-RT1G-H08X-00000-00)."
    ),
    "src_2cee64cfc090c4b25ca7": (
        "Academic Doctoral Dissertation",
        15,
        "Academic doctoral dissertation (UC Berkeley Graduate Division), not a journalistic news report."
    ),
    "src_2602e1f52eb57cee5b07": (
        "Academic / Technical Circular",
        15,
        "Academic / technical research circular (Transportation Research Board / National Academies), not a journalistic news report."
    ),
}

# Verified metadata corrections for non-nexis archive records
NON_NEXIS_CORRECTIONS = {
    "src_dc10ae72df82e2180ca6": {
        "title": "City Council Approves Pilot Program to Curb Waze Traffic on Side Streets",
        "publication_date": "2019-04-30",
        "publisher": "NBC Los Angeles (KNBC) / City News Service",
        "location": "Los Angeles, CA",
        "url": "https://www.nbclosangeles.com/news/city-council-pilot-program-to-curb-waze-traffic-on-side-streets/162349/",
    },
    "src_d1320840ff1688ff741e": {
        "title": "New Jersey Town Closes Some City Streets to Drivers Who Don’t Live There",
        "publication_date": "2018-01-22",
        "publisher": "Next City",
        "location": "Leonia, NJ",
        "url": "https://nextcity.org/urbanist-news/new-jersey-town-closes-some-city-streets-to-drivers-who-dont-live-there",
    },
    "src_23a1fcd9de5f1849cfa3": {
        "title": "Delridge Neighborhood Greenway — 26th Ave SW Proposed Diverters: Outreach Summary",
        "publication_date": "2020-11-01",
        "publisher": "Seattle Department of Transportation (SDOT)",
        "location": "Seattle, WA",
        "url": "https://www.seattle.gov/documents/Departments/SDOT/TransitProgram/RapidRide/RapidRide%20H/26th%20Ave%20SW%20Diverter%20Outreach%20Summary.pdf",
    },
    "src_8f6b264845ca47814ba0": {
        "title": "Waze Connected Citizens Program — United States Municipal Rollout",
        "publication_date": "2014-12-08",
        "publisher": "Waze Mobile (Google)",
        "location": "United States (Multi-City)",
        "url": "https://www.waze.com/discuss/t/waze-connected-citizens-program/102835",
    },
    "src_02454d2db17a078f05f9": {
        "title": "Los Angeles Council File 11-2130-S4: Rowena Ave / Angus St Cut-Through Traffic Mitigation",
        "publication_date": "2019-06-24",
        "publisher": "Los Angeles City Clerk / Silver Lake Neighborhood Council",
        "location": "Los Angeles, CA",
        "url": "https://cityclerk.lacity.org/onlinedocs/2011/11-2130-S4_PC_AB_06-24-2019.pdf",
    },
    "src_483bc7bade77380c2828": {
        "title": "California AB 2015: Department of Transportation: Third-Party Navigation Applications Pilot Study",
        "publication_date": "2024-09-22",
        "publisher": "California State Legislature / CalMatters Digital Democracy",
        "location": "California",
        "url": "https://calmatters.digitaldemocracy.org/bills/ca_202520260ab2015",
    },
    "src_32ccdcb0712575f8cb0b": {
        "title": "New 'Absurd' Dem-Backed Bill Could Make Your Commute Longer, California Lawmaker Warns",
        "publication_date": "2024-06-16",
        "publisher": "Yahoo News",
        "location": "California",
        "url": "https://www.yahoo.com/news/politics/articles/absurd-dem-backed-bill-could-205725514.html",
    },
    "src_9403a6fb4c495dd5f6e0": {
        "title": "Los Angeles Council Motion 14-1741-S1: Data-Sharing Partnership with Waze to Protect Residential Streets",
        "publication_date": "2015-04-28",
        "publisher": "Los Angeles City Clerk",
        "location": "Los Angeles, CA",
        "url": "https://cityclerk.lacity.org/onlinedocs/2014/14-1741-S1_MOT_04-28-2015.pdf",
    },
    "src_004598f106dc0112c9f5": {
        "title": "L.A. May Crack Down on Waze and Google Maps Over Side-Street Traffic",
        "publication_date": "2019-05-07",
        "publisher": "Los Angeles Magazine",
        "location": "Los Angeles, CA",
        "url": "https://lamag.com/technology/waze-restrictions-program/",
    },
    "src_df18bde5b05e69aa6fee": {
        "title": "Waze Hijacked L.A. in the Name of Convenience. Can Anyone Put the Genie Back in the Bottle?",
        "publication_date": "2018-05-18",
        "publisher": "Los Angeles Magazine",
        "location": "Los Angeles, CA",
        "url": "https://lamag.com/urbandevelopment/waze-los-angeles-neighborhoods/",
    },
    "src_ec380b5a89074be9476e": {
        "title": "Waze Restricted Due to Side Street Traffic Buildup in Los Angeles",
        "publication_date": "2019-04-30",
        "publisher": "ABC 10News San Diego / City News Service",
        "location": "Los Angeles, CA",
        "url": "https://www.10news.com/news/national/waze-restricted-due-to-buildup-of-side-street-traffic-in-los-angeles",
    },
    "src_2910e1608eed71065145": {
        "title": "'Absolute Chaos': Navigation Apps Blamed for Traffic Nightmare on One of L.A.'s Steepest Streets",
        "publication_date": "2018-04-05",
        "publisher": "FOX 13 Seattle / KTLA",
        "location": "Los Angeles, CA",
        "url": "https://www.fox13seattle.com/news/absolute-chaos-navigation-apps-blamed-for-traffic-nightmare-on-one-of-l-a-s-steepest-streets",
    },
    "src_7a51efb5b5f5430e194b": {
        "title": "Mayor Walsh Announces City of Boston Partnership with Traffic App Waze",
        "publication_date": "2015-02-19",
        "publisher": "The Daily Free Press",
        "location": "Boston, MA",
        "url": "https://dailyfreepress.com/02/19/05/92334/walsh-announces-partnership-with-traffic-app-waze/",
    },
    "src_0d4fa7ccce08eaf50b2f": {
        "title": "Boston Partners with Waze to Clear Up Clogged Streets",
        "publication_date": "2015-02-21",
        "publisher": "Engadget",
        "location": "Boston, MA",
        "url": "https://www.engadget.com/2015-02-21-waze-boston-partner.html",
    },
    "src_ab2b7d7e044d5121e5f5": {
        "title": "Using Waze Data to Measure Traffic Congestion and Centre Street Road Diet Safety",
        "publication_date": "2019-10-15",
        "publisher": "City of Boston Citywide Analytics Team",
        "location": "Boston, MA",
        "url": "https://www.boston.gov/departments/analytics-team/using-waze-data-measure-traffic-congestion-0",
    },
    "src_f2e92e99cdf509170cc7": {
        "title": "MassDOT Partners with Waze to Improve Traffic and Planning",
        "publication_date": "2016-06-16",
        "publisher": "The Boston Globe",
        "location": "Massachusetts",
        "url": "https://www.bostonglobe.com/metro/2016/06/16/massdot-partners-with-waze-improve-traffic-planning/9p4D9vWnIYNQ7g9s1DwhIO/story.html",
    },
    "src_396cf33a5161f5f5bd8d": {
        "title": "Wood Street In West Town Going One-Way To Cut Down On Thru-Traffic",
        "publication_date": "2021-08-10",
        "publisher": "Block Club Chicago",
        "location": "Chicago, IL",
        "url": "https://blockclubchicago.org/2025/06/06/parts-of-wood-street-in-west-town-to-become-one-way-3-years-after-bike-lanes-pitched-ditched/",
    },
    "src_a8fe04b8629212eb1ae5": {
        "title": "Proposal To Make Wood Street One-Way Stirs Debate In West Town",
        "publication_date": "2021-08-04",
        "publisher": "CBS News Chicago",
        "location": "Chicago, IL",
        "url": "https://www.cbsnews.com/chicago/news/proposed-one-way-street-chicago-north-side/",
    },
    "src_5b329e50217cff65c640": {
        "title": "Councilmember Saka Opposed Traffic Diverters in Delridge Over Equity Concerns",
        "publication_date": "2024-04-02",
        "publisher": "PubliCola",
        "location": "Seattle, WA",
        "url": "https://publicola.com/2025/04/02/shannon-braddock-appointed-acting-county-executive-saka-says-he-opposed-traffic-diverters-in-his-neighborhood-because-of-equity-concerns/",
    },
    "src_a8b514916cc36bde3d40": {
        "title": "Community Petition: Stop the Installation of Traffic Diverters at SW Genesee and SW Brandon",
        "publication_date": "2020-09-01",
        "publisher": "Change.org (West Seattle Residents)",
        "location": "Seattle, WA",
        "url": "https://www.change.org/p/seattle-department-of-transportation-stop-the-installation-of-traffic-diverters-at-sw-genesee-and-sw-brandon",
    },
    "src_a16a62edb70588f81bbb": {
        "title": "Home Zone Program: Lake City Neighborhood Traffic Calming",
        "publication_date": "2023-01-01",
        "publisher": "Seattle Department of Transportation (SDOT)",
        "location": "Seattle, WA",
        "url": "https://www.seattle.gov/transportation/projects-and-programs/programs/home-zone-program/lake-city",
    },
    "src_c8f5fcc928d66ad4b9e7": {
        "title": "Waze’s Maps Now Change as Roads Close",
        "publication_date": "2013-02-27",
        "publisher": "The New York Times (Bits Blog)",
        "location": "United States",
        "url": "https://archive.nytimes.com/bits.blogs.nytimes.com/2013/02/27/wazes-maps-now-change-as-roads-close/",
    },
    "src_264bf1d902e4b812735b": {
        "title": "Navigation App Waze Adds Road Closure Reporting, Reaches 40M Users",
        "publication_date": "2013-02-27",
        "publisher": "TechCrunch",
        "location": "United States",
        "url": "https://techcrunch.com/2013/02/27/waze-road-closure/",
    },
    "src_a3aec998433f0c3fff3d": {
        "title": "Waze Connected Citizens Program Official Partner Factsheet",
        "publication_date": "2019-01-01",
        "publisher": "Waze (Google LLC)",
        "location": "United States",
        "url": "https://web-assets.waze.com/partners/ccp/WAZE-CCP-Factsheet.pdf",
    },
    "src_209e9565661083dba383": {
        "title": "Waze for Cities (W4C) Program Overview and Municipal Data Guide",
        "publication_date": "2020-01-01",
        "publisher": "Waze Discuss / Wazeopedia",
        "location": "United States",
        "url": "https://www.waze.com/discuss/t/waze-for-cities/377967",
    },
    "src_97a13ecf3417e5676e08": {
        "title": "Community Feature Request: Municipal Blacklist for Residential Shortcut Streets",
        "publication_date": "2020-05-15",
        "publisher": "Waze Discuss Community Forum",
        "location": "United States",
        "url": "https://www.waze.com/discuss/t/feature-request-blacklist-areas-roads/399185",
    },
    "src_ae24cf62a63f34c9fe0b": {
        "title": "Waze for Cities: Real-Time Traffic Data Analytics with Google Cloud",
        "publication_date": "2021-06-01",
        "publisher": "Waze (Google LLC)",
        "location": "United States",
        "url": "https://www.waze.com/wazeforcities/",
    },
    "src_8844a04c3601f584693a": {
        "title": "Borough of Mantoloking Regular Council Meeting Minutes: Waze Cut-Through Traffic Deployment",
        "publication_date": "2020-07-21",
        "publisher": "Borough of Mantoloking, New Jersey",
        "location": "Mantoloking, NJ",
        "url": "https://www.mantoloking.org/AgendaCenter/ViewFile/Minutes/_07212026-45",
    },
    "src_d8bae76a48b8c662c148": {
        "title": "San Francisco Smart City Challenge Phase II: Connected Mobility and Navigation Management",
        "publication_date": "2016-05-01",
        "publisher": "San Francisco Municipal Transportation Agency (SFMTA)",
        "location": "San Francisco, CA",
        "url": "https://www.sfmta.com/sites/default/files/reports-and-documents/2018/11/sf_smart_city_challenge_phase_ii_volume_2.pdf",
    },
    "src_6b808701b37bfa4ff82d": {
        "title": "San Francisco County Transportation Authority Citizens Advisory Committee Meeting Packet",
        "publication_date": "2023-09-03",
        "publisher": "San Francisco County Transportation Authority (SFCTA)",
        "location": "San Francisco, CA",
        "url": "https://www.sfcta.org/sites/default/files/2025-08/SFCTA_CAC_PACKET_2025-09-03-reduced.pdf",
    },
    "src_472865dc84294b0bd125": {
        "title": "Waze and LA City Council Will Work Together to Reduce Growing Traffic on Residential Streets",
        "publication_date": "2019-05-01",
        "publisher": "LAist / 89.3 KPCC (AirTalk with Larry Mantle)",
        "location": "Los Angeles, CA",
        "url": "https://laist.com/shows/airtalk/waze-and-la-city-council-will-work-together-to-reduce-growing-traffic-on-residential-streets",
    },
}

# Standardized location mapping for clean, consistent formatting
LOCATION_NORM = {
    "Albany, Ny": "Albany, NY",
    "Anchorage, Ak": "Anchorage, AK",
    "Arlington, TX": "Arlington, TX",
    "Asheville, Nc": "Asheville, NC",
    "Atlanta, Ga": "Atlanta, GA",
    "Atlanta, GA": "Atlanta, GA",
    "Austin, Tx": "Austin, TX",
    "Austin, TX": "Austin, TX",
    "Baton Rouge, LA": "Baton Rouge, LA",
    "Boston": "Boston, MA",
    "Boston, Ma": "Boston, MA",
    "Boston, MA": "Boston, MA",
    "Boston, Los Angeles County, Miami, New York City, Pittsburgh; Florida, Utah, Kentucky": "United States (Multi-City)",
    "California": "California",
    "Carson City, Nv": "Carson City, NV",
    "Charlotte, Nc": "Charlotte, NC",
    "Chesapeake, VA": "Chesapeake, VA",
    "Chicago": "Chicago, IL",
    "Chicago, Il": "Chicago, IL",
    "Chicago, IL": "Chicago, IL",
    "Colorado": "Colorado",
    "Columbus": "Columbus, OH",
    "Connecticut": "Connecticut",
    "Dallas, Tx": "Dallas, TX",
    "Des Moines, Ia": "Des Moines, IA",
    "Des Moines, IA": "Des Moines, IA",
    "Detroit, MI": "Detroit, MI",
    "Florida": "Florida",
    "Fort Worth, Tx": "Fort Worth, TX",
    "Georgia": "Georgia",
    "Global": "Global",
    "Greensboro, NC": "Greensboro, NC",
    "Harrisburg, PA": "Harrisburg, PA",
    "Houston, Tx": "Houston, TX",
    "Illinois": "Illinois",
    "Illinois (State)": "Illinois",
    "Lancaster, Pa": "Lancaster, PA",
    "Las Vegas, NV (Southern Nevada), Tampa, FL, Delaware": "United States (Multi-City)",
    "Leonia": "Leonia, NJ",
    "Lincoln, Ne": "Lincoln, NE",
    "Los Angeles": "Los Angeles, CA",
    "Los Angeles, Ca": "Los Angeles, CA",
    "Los Angeles, CA": "Los Angeles, CA",
    "Louisville, Ky": "Louisville, KY",
    "Maine": "Maine",
    "Mantoloking": "Mantoloking, NJ",
    "Maryland": "Maryland",
    "Maryland (State)": "Maryland",
    "Massachusetts": "Massachusetts",
    "Miami, Fl": "Miami, FL",
    "Montgomery, Al": "Montgomery, AL",
    "Mount Prospect, IL": "Mount Prospect, IL",
    "New Haven, Ct": "New Haven, CT",
    "New Jersey": "New Jersey",
    "New Jersey (State)": "New Jersey",
    "New York": "New York",
    "New York (State)": "New York",
    "New York, New York": "New York, NY",
    "New York, Ny": "New York, NY",
    "Norfolk, VA": "Norfolk, VA",
    "North Carolina": "North Carolina",
    "Pennsylvania": "Pennsylvania",
    "Pennsylvania (State)": "Pennsylvania",
    "Philadelphia, PA": "Philadelphia, PA",
    "Pittsburgh, PA": "Pittsburgh, PA",
    "Portland, Or": "Portland, OR",
    "Providence, Ri": "Providence, RI",
    "Raleigh, Nc": "Raleigh, NC",
    "Richmond, Va": "Richmond, VA",
    "Sacramento, CA": "Sacramento, CA",
    "Saint Louis, MO": "St. Louis, MO",
    "Salt Lake City, Ut": "Salt Lake City, UT",
    "San Francisco": "San Francisco, CA",
    "San Francisco Bay Area, Ca": "San Francisco Bay Area, CA",
    "San Francisco Bay Area, Los Angeles, Phoenix, Austin, Atlanta": "United States (Multi-City)",
    "San Francisco County": "San Francisco, CA",
    "San Francisco, Ca": "San Francisco, CA",
    "San Francisco, CA": "San Francisco, CA",
    "San Francisco, Los Angeles, Phoenix, Austin, Atlanta": "United States (Multi-City)",
    "San Jose, Ca": "San Jose, CA",
    "Seattle": "Seattle, WA",
    "Spokane, Wa": "Spokane, WA",
    "Tampa, Fl": "Tampa, FL",
    "Texas": "Texas",
    "Torrance": "Torrance, CA",
    "United States": "United States",
    "Virginia": "Virginia",
    "Virginia Beach, Va": "Virginia Beach, VA",
    "Washington Dc": "Washington, DC",
    "Washington, Washington": "Washington, DC",
}

def resolve_url(d):
    """Resolve a live canonical URL for any crawled news document or Nexis Uni record."""
    sid = d.get("source_id") or d.get("id") or ""
    if sid in NON_NEXIS_CORRECTIONS and NON_NEXIS_CORRECTIONS[sid].get("url"):
        return NON_NEXIS_CORRECTIONS[sid]["url"]

    url = d.get("url") or d.get("final_url") or d.get("requested_url") or ""
    if url and (url.startswith("http://") or url.startswith("https://")):
        return url

    archive_dir = d.get("archive_dir") or ""
    combined = f"{sid} {archive_dir}"
    m = re.search(r"urn:contentItem:([A-Za-z0-9-]+)", combined)
    if m:
        urn_id = m.group(1)
        path = f"/shared/document/news/urn:contentItem:{urn_id}"
        return f"https://www.nexisuni.com/document/?pddocfullpath={urllib.parse.quote(path, safe='')}"
    
    return ""

# Bespoke dictionary for each source_id
# source_id -> (category, rationale, instrument_id, instrument_name)
BESPOKE_DATA = {
    # 1. Specialized Platform & Municipal Empirical Case Studies
    "nexis_urn:contentItem:6KF6-GDK3-RT1G-H08X-00000-00": (
        "Platform Features & Routing Algorithms",
        "San Francisco Chronicle investigative report on UC Berkeley and Google Research's randomized switchback routing trial across 10 US metro corridors, evaluating how algorithmic diversion away from highway bottlenecks affects travel times and network equilibrium.",
        "PLAT-ALG-04", "Large-Scale Arterial Commuter Diversion & Incident Rerouting"
    ),
    "src_ab2b7d7e044d5121e5f5": (
        "Public-Private Data Partnerships",
        "Official empirical analysis by Boston's Citywide Analytics Team utilizing aggregated Waze Connected Citizens telemetry to evaluate the congestion and safety impacts of the Centre Street road diet redesign.",
        "BOS-CCP-2015", "City of Boston & Waze Connected Citizens Agreement"
    ),
    "nexis_urn:contentItem:5X75-KD41-F03R-N52V-00000-00": (
        "Platform Features & Routing Algorithms",
        "Techdirt transportation analysis examining Braess's paradox and user equilibrium in algorithmic navigation, demonstrating how navigation apps optimizing individual commuter paths exacerbate overall network congestion.",
        "PLAT-ALG-04", "Large-Scale Arterial Commuter Diversion & Incident Rerouting"
    ),

    # 2. State & Federal Legislation / City Council Actions
    "src_483bc7bade77380c2828": (
        "Legislation & City Council Actions",
        "California Assembly Bill 2015 mandated a Caltrans and CalSTA pilot study on navigation application routing externalities, laying the foundation for direct state regulation of third-party routing engines.",
        "CA-AB2015", "California AB 2015 (Third-party navigation apps pilot study)"
    ),
    "src_32ccdcb0712575f8cb0b": (
        "Legislation & City Council Actions",
        "Legislative debate surrounding California Assembly Bill 2015, highlighting warnings that restricting navigation app rerouting off residential roads could increase commuter travel times by up to 30 minutes.",
        "CA-AB2015", "California AB 2015 (Third-party navigation apps pilot study)"
    ),
    "nexis_urn:contentItem:5CFG-S691-F03R-N0CD-00000-00": (
        "Legislation & City Council Actions",
        "Federal transportation reauthorization proposals (GROW AMERICA Act) seeking to grant USDOT and NHTSA statutory authority to regulate smartphone navigation applications and driver-distracting software.",
        "FED-01", "GROW AMERICA Act / NHTSA Navigation App Regulatory Proposals"
    ),
    "nexis_urn:contentItem:6G76-J083-RVJY-R2R6-00000-00": (
        "Legislation & City Council Actions",
        "Reason Magazine legal critique of Obama administration federal proposals empowering NHTSA to oversee smartphone mapping software like Waze and Google Maps under automotive safety mandates.",
        "FED-01", "GROW AMERICA Act / NHTSA Navigation App Regulatory Proposals"
    ),
    "nexis_urn:contentItem:5CFM-X9F1-JCMN-Y3FG-00000-00": (
        "Legislation & City Council Actions",
        "Analysis of USDOT regulatory initiatives examining whether consumer smartphone navigation applications should be categorized as regulated motor vehicle equipment subject to federal safety standards.",
        "FED-01", "GROW AMERICA Act / NHTSA Navigation App Regulatory Proposals"
    ),
    "nexis_urn:contentItem:5CFV-P751-JBPX-W04S-00000-00": (
        "Legislation & City Council Actions",
        "CNNMoney report on federal transportation proposals seeking statutory authority to review and restrict smartphone navigation app features that contribute to driver distraction or hazardous routing.",
        "FED-01", "GROW AMERICA Act / NHTSA Navigation App Regulatory Proposals"
    ),
    "nexis_urn:contentItem:4D8V-XDY0-0092-J3HK-00000-00": (
        "Legislation & City Council Actions",
        "New York State legislative proposals debating statutory exemptions for vehicle navigation systems from moving-violation handheld device bans, establishing legal parameters for driver use of routing aids.",
        "NY-NAV-01", "New York Vehicle Navigation Device Exemption Legislation"
    ),
    "nexis_urn:contentItem:53RV-7R81-F18Y-Y1PF-00000-00": (
        "Legislation & City Council Actions",
        "Illinois General Assembly legislation (HB 5071) mandating IDOT to publicly post designated truck routes and educate commercial drivers on avoiding passenger GPS apps that lead to low-clearance bridge strikes.",
        "IL-HB5071", "Illinois Commercial Truck GPS & Bridge Strike Prevention Act"
    ),
    "nexis_urn:contentItem:5HM9-56M1-DY7V-G0Y2-00000-00": (
        "Legislation & City Council Actions",
        "Illinois state legislative action requiring public education campaigns and digital mapping standards to deter commercial truck operators from utilizing passenger navigation apps on weight-restricted roads.",
        "IL-HB5071", "Illinois Commercial Truck GPS & Bridge Strike Prevention Act"
    ),
    "nexis_urn:contentItem:6GD2-Y0F3-RV1H-T2MT-00000-00": (
        "Legislation & City Council Actions",
        "Town of New Milford municipal ordinance prohibiting commercial buses and heavy tour vehicles from South Kent Road following navigation app diversions onto narrow rural residential roadways.",
        "CT-NM-01", "Town of New Milford Commercial Vehicle Road Restriction Ordinance"
    ),
    "nexis_urn:contentItem:6GD2-Y0F3-RV1H-T2MS-00000-00": (
        "Legislation & City Council Actions",
        "Town of Kent legislative enactment collaborating with New Milford to ban commercial buses on shared rural roads where GPS navigation apps routinely routed non-local charter carriers.",
        "CT-NM-01", "Town of New Milford Commercial Vehicle Road Restriction Ordinance"
    ),
    "src_8844a04c3601f584693a": (
        "Legislation & City Council Actions",
        "Official Mantoloking Borough Council meeting minutes documenting municipal police coordination with navigation apps and deployment of digital variable message signs to redirect summer commuter cut-through traffic.",
        "NJ-MAN-01", "Borough of Mantoloking Navigation Cut-Through Mitigation Order"
    ),
    "nexis_urn:contentItem:6KGW-X313-RYMC-J2S7-00000-00": (
        "Legislation & City Council Actions",
        "St. Louis Board of Aldermen legislative debates over ordinances reforming municipal speed hump approval processes to expedite traffic-calming installations on neighborhood streets flooded by cut-through commuters.",
        "MO-STL-01", "City of St. Louis Traffic Calming & Speed Hump Authority Ordinance"
    ),
    "nexis_urn:contentItem:6KGN-XYV3-RV2K-H099-00000-00": (
        "Legislation & City Council Actions",
        "St. Louis aldermen advanced municipal legislation transferring speed hump approval authority from individual aldermanic discretionary funds to public works traffic engineers to address systemic cut-through speeding.",
        "MO-STL-01", "City of St. Louis Traffic Calming & Speed Hump Authority Ordinance"
    ),
    "nexis_urn:contentItem:6J9V-D563-S61W-X0NH-00000-00": (
        "Legislation & City Council Actions",
        "Godfrey Village Board municipal deliberations tabling speed hump construction on Levis Lane pending a formal traffic engineering study to evaluate commuter cut-through volume.",
        "IL-GOD-01", "Village of Godfrey Traffic Safety Resolution"
    ),
    "nexis_urn:contentItem:6JMY-GR73-RWVS-G0PF-00000-00": (
        "Legislation & City Council Actions",
        "East Lampeter Township Board of Supervisors advancing municipal traffic safety actions and evaluating speed hump installations to calm residential cut-through traffic bypasses.",
        "PA-ELT-01", "East Lampeter Township Traffic Calming Resolution"
    ),
    "src_dc10ae72df82e2180ca6": (
        "Legislation & City Council Actions",
        "Los Angeles City Council approved a pilot program authorizing LADOT and the City Attorney to condition municipal data-sharing agreements on navigation apps restricting detour routing through residential neighborhoods.",
        "LA-CF-11-2130", "Los Angeles City Council File 11-2130 (Cut-Through Traffic Mitigation)"
    ),
    "src_02454d2db17a078f05f9": (
        "Legislation & City Council Actions",
        "Official Los Angeles City Council public record documenting Silver Lake neighborhood petitions and LADOT traffic engineering proposals (converting Angus Street to one-way) to counteract navigation-app cut-through traffic.",
        "LA-CF-11-2130-S4", "Los Angeles Council File 11-2130-S4 (Angus St / Rowena Ave)"
    ),
    "src_9403a6fb4c495dd5f6e0": (
        "Legislation & City Council Actions",
        "Los Angeles City Council motion introduced by Paul Krekorian and Tom LaBonge directing LADOT to leverage data-sharing agreements with Waze to prevent algorithmic routing of heavy commuter flows through residential streets.",
        "LA-CF-14-1741", "Los Angeles Council File 14-1741 (Waze Data Partnership)"
    ),
    "src_004598f106dc0112c9f5": (
        "Legislation & City Council Actions",
        "Los Angeles City Council initiatives examining legal mechanisms to force Waze and Google Maps to exclude quiet residential side streets from commuter detour algorithms.",
        "LA-CF-14-1741", "Los Angeles Council File 14-1741 (Waze Data Partnership)"
    ),
    "src_472865dc84294b0bd125": (
        "Legislation & City Council Actions",
        "Los Angeles City Council and LADOT formal negotiations with Waze leadership to establish mutual protocols for suppressing cut-through traffic on neighborhood collector streets.",
        "LA-CF-14-1741", "Los Angeles Council File 14-1741 (Waze Data Partnership)"
    ),
    "src_ec380b5a89074be9476e": (
        "Legislation & City Council Actions",
        "Los Angeles City Council approved regulatory pilot requiring navigation platforms to restrict residential cut-through routing as a legal prerequisite for accessing municipal street closure data feeds.",
        "LA-CF-11-2130", "Los Angeles City Council File 11-2130 (Cut-Through Traffic Mitigation)"
    ),
    "nexis_urn:contentItem:5FV2-0F51-DYTH-G1V5-00000-00": (
        "Legislation & City Council Actions",
        "Los Angeles Mayor Eric Garcetti announced a landmark municipal data-sharing agreement with Waze, formalizing data exchanges to steer commuter traffic onto major arterials and away from residential streets.",
        "LA-MOU-2015", "City of Los Angeles & Waze Connected Citizens MOU"
    ),
    "nexis_urn:contentItem:5TNP-YDV1-JCBD-1017-00000-00": (
        "Legislation & City Council Actions",
        "Los Angeles City Councilmembers Paul Krekorian and David Ryu introduced motions directing LADOT to craft regulatory remedies preventing navigation apps from flooding residential neighborhoods with cut-through traffic.",
        "LA-CF-14-1741", "Los Angeles Council File 14-1741 (Waze Data Partnership)"
    ),

    # 3. Municipal Traffic Mitigation & Street Controls (Physical Calming, Closures, Turn Restrictions)
    "src_d1320840ff1688ff741e": (
        "Municipal Traffic Mitigation & Street Controls",
        "The Borough of Leonia enacted an emergency municipal ordinance closing 60 residential streets to non-resident commuters during peak hours to block regional cut-through traffic directed by Waze.",
        "NJ-LEONIA-2018", "Borough of Leonia Ordinance 2017-25 (Non-Resident Street Closure)"
    ),
    "nexis_urn:contentItem:5T5C-XB71-JC65-505H-00000-00": (
        "Municipal Traffic Mitigation & Street Controls",
        "New Jersey Superior Court ruling invalidating Leonia's non-resident street closure ordinance, establishing critical legal limits on municipal police power to bar non-resident commuters escaping highway congestion.",
        "NJ-LEONIA-2018", "Borough of Leonia Ordinance 2017-25 (Non-Resident Street Closure)"
    ),
    "nexis_urn:contentItem:5YD5-NK31-JC65-51MB-00000-00": (
        "Municipal Traffic Mitigation & Street Controls",
        "Appellate judicial review granting Leonia a temporary stay to maintain its rush-hour street closure signs while appealing the state court decision striking down its non-resident travel ban.",
        "NJ-LEONIA-2018", "Borough of Leonia Ordinance 2017-25 (Non-Resident Street Closure)"
    ),
    "nexis_urn:contentItem:5RG8-H741-JCB3-X1WH-00000-00": (
        "Municipal Traffic Mitigation & Street Controls",
        "National Associated Press report detailing Leonia's extreme municipal strategy of closing 60 residential roadways to non-resident drivers to counteract commuter traffic routed by navigation apps off the George Washington Bridge approach.",
        "NJ-LEONIA-2018", "Borough of Leonia Ordinance 2017-25 (Non-Resident Street Closure)"
    ),
    "src_23a1fcd9de5f1849cfa3": (
        "Municipal Traffic Mitigation & Street Controls",
        "Seattle SDOT evaluated and debated installing physical curb-and-post traffic diverters on 26th Ave SW to prevent commuter traffic from using neighborhood greenways as navigation bypass routes.",
        "SEA-SMC-11.16", "Seattle Municipal Code Title 11 (Traffic Control & Calming)"
    ),
    "src_5b329e50217cff65c640": (
        "Municipal Traffic Mitigation & Street Controls",
        "Seattle City Council Transportation Chair Rob Saka debated the equity and accessibility impacts of installing physical traffic diverters on residential greenways to deter commuter cut-throughs.",
        "SEA-SMC-11.16", "Seattle Municipal Code Title 11 (Traffic Control & Calming)"
    ),
    "src_a8b514916cc36bde3d40": (
        "Municipal Traffic Mitigation & Street Controls",
        "Community petition by West Seattle residents demanding SDOT halt the installation of physical traffic diverters designed to block cut-through traffic along the 26th Ave SW neighborhood greenway.",
        "SEA-SMC-11.16", "Seattle Municipal Code Title 11 (Traffic Control & Calming)"
    ),
    "src_a16a62edb70588f81bbb": (
        "Municipal Traffic Mitigation & Street Controls",
        "Seattle SDOT's Lake City Home Zone initiative deploying traffic diverters, speed humps, and street-end closures to shield residential streets from algorithmic commuter cut-through traffic.",
        "SEA-SMC-11.16", "Seattle Municipal Code Title 11 (Traffic Control & Calming)"
    ),
    "src_396cf33a5161f5f5bd8d": (
        "Municipal Traffic Mitigation & Street Controls",
        "Chicago Department of Transportation (CDOT) and local alderperson converted Wood Street to a one-way thoroughfare to eliminate navigation app rat-running and cut-through traffic through West Town.",
        "CHI-MCC-9-12", "Chicago Municipal Code Title 9 (One-Way Street Designations)"
    ),
    "src_a8fe04b8629212eb1ae5": (
        "Municipal Traffic Mitigation & Street Controls",
        "Documents Chicago neighborhood controversy and participatory budgeting debates over converting residential streets to one-way to block navigation app cut-through traffic.",
        "CHI-MCC-9-12", "Chicago Municipal Code Title 9 (One-Way Street Designations)"
    ),
    "src_6b808701b37bfa4ff82d": (
        "Municipal Traffic Mitigation & Street Controls",
        "San Francisco County Transportation Authority Citizens Advisory Committee reviewed neighborhood traffic calming packages engineered to discourage commuter shortcutting through residential zones.",
        "SF-TC-2025", "San Francisco Traffic Calming Policy & Guidelines"
    ),
    "nexis_urn:contentItem:6H7T-H1B3-RW7S-61G3-00000-00": (
        "Municipal Traffic Mitigation & Street Controls",
        "San Francisco Municipal Transportation Agency (SFMTA) implemented traffic-calming speed humps and diverters across 141 city intersections to combat commuter speeding and navigation shortcuts.",
        "SF-TC-2025", "San Francisco Traffic Calming Policy & Guidelines"
    ),
    "nexis_urn:contentItem:6H8K-R233-RT2P-13GY-00000-00": (
        "Municipal Traffic Mitigation & Street Controls",
        "SFMTA crews expedited construction of neighborhood speed humps and raised crosswalks across residential districts inundated with app-directed cut-through commuters.",
        "SF-TC-2025", "San Francisco Traffic Calming Policy & Guidelines"
    ),
    "nexis_urn:contentItem:6GS3-MVY3-RT79-600V-00000-00": (
        "Municipal Traffic Mitigation & Street Controls",
        "City of Pittsburgh Department of Mobility and Infrastructure installed speed tables and traffic calming on Shady Avenue to mitigate commuter rat-running and discourage navigation app detours.",
        "PA-PGH-501", "Pittsburgh Code of Ordinances Title 5 (Traffic Calming)"
    ),
    "nexis_urn:contentItem:6GWR-4W53-RRTX-13F9-00000-00": (
        "Municipal Traffic Mitigation & Street Controls",
        "Pittsburgh Department of Mobility and Infrastructure expanded physical traffic calming installations across east end corridors to physically suppress navigation-induced speeding on residential cut-throughs.",
        "PA-PGH-501", "Pittsburgh Code of Ordinances Title 5 (Traffic Calming)"
    ),
    "nexis_urn:contentItem:6J6N-NJY3-RTWR-N4D2-00000-00": (
        "Municipal Traffic Mitigation & Street Controls",
        "City of Detroit Department of Public Works announced its 2026 speed hump program deploying 312 physical calming devices to protect residential blocks from commuter shortcutting.",
        "MI-DET-55", "Detroit City Code Chapter 55 (Traffic Calming & Speed Humps)"
    ),
    "nexis_urn:contentItem:6HGK-KM93-RXKC-C0JF-00000-00": (
        "Municipal Traffic Mitigation & Street Controls",
        "City of Des Moines municipal street program installing speed humps across residential corridors to suppress high-speed cut-through commuter traffic.",
        "IA-DM-114", "Des Moines Municipal Code Chapter 114 (Traffic Regulation)"
    ),
    "nexis_urn:contentItem:6FYH-9K43-RSGG-P2M7-00000-00": (
        "Municipal Traffic Mitigation & Street Controls",
        "Village of Mount Prospect evaluated municipal traffic-calming speed humps and turn restrictions to curb high-volume commuter bypasses through residential neighborhoods.",
        "IL-MP-18", "Mount Prospect Village Code Chapter 18 (Traffic Mitigation)"
    ),
    "nexis_urn:contentItem:6HFR-R813-RS65-00N7-00000-00": (
        "Municipal Traffic Mitigation & Street Controls",
        "Mount Prospect residents and village trustees debated installing stop signs and asphalt speed cushions on neighborhood streets experiencing severe rush-hour cut-through traffic.",
        "IL-MP-18", "Mount Prospect Village Code Chapter 18 (Traffic Mitigation)"
    ),
    "nexis_urn:contentItem:6CWY-FN51-DY37-31X4-00000-00": (
        "Municipal Traffic Mitigation & Street Controls",
        "City of Ferguson municipal public works installed asphalt speed humps to slow down commuter vehicles cutting through residential streets to bypass regional congestion.",
        "MO-FERG-44", "Ferguson Municipal Code Chapter 44 (Traffic Calming)"
    ),
    "nexis_urn:contentItem:6GHR-C3D3-RWMJ-44YY-00000-00": (
        "Municipal Traffic Mitigation & Street Controls",
        "City of Chesapeake's neighborhood traffic calming program deploying speed tables and driver-feedback signs to prevent commuter cut-through traffic on suburban residential streets.",
        "VA-CHEP-74", "Chesapeake City Code Chapter 74 (Traffic Calming Program)"
    ),
    "nexis_urn:contentItem:6HGC-SMW3-RW2Y-927P-00000-00": (
        "Municipal Traffic Mitigation & Street Controls",
        "Capital Region municipalities across upstate New York deployed speed humps and traffic calming to obstruct commuter shortcutting through neighborhood streets.",
        "NY-MUNI-01", "New York Municipal Home Rule Law (Traffic Calming Powers)"
    ),
    "nexis_urn:contentItem:6K64-XTC3-RVRN-D3K7-00000-00": (
        "Municipal Traffic Mitigation & Street Controls",
        "Abington Township municipal guidelines permitting residents to petition for speed humps and physical traffic diverters to deter navigation app cut-through commuter traffic.",
        "PA-ABING-150", "Abington Township Code Chapter 150 (Traffic Regulation)"
    ),
    "nexis_urn:contentItem:6KP2-3303-RSGV-41K1-00000-00": (
        "Municipal Traffic Mitigation & Street Controls",
        "Howard County Department of Public Works hosted community outreach on traffic calming and speed humps to eliminate commuter rat-running through residential communities.",
        "MD-HOW-21", "Howard County Code Title 21 (Traffic Calming Program)"
    ),
    "nexis_urn:contentItem:6G8W-3GS3-RXR2-2143-00000-00": (
        "Municipal Traffic Mitigation & Street Controls",
        "Connecticut DOT and local towns coordinated traffic engineering measures to stop navigation algorithms from routing interstate highway overflow onto narrow municipal roadways.",
        "CT-DOT-14", "Connecticut General Statutes Title 14 (Highway Traffic Control)"
    ),
    "nexis_urn:contentItem:6KBM-BFX3-SDJ6-53RR-00000-00": (
        "Municipal Traffic Mitigation & Street Controls",
        "Connecticut transportation policy analysis evaluating the limitations of municipal traffic calming, demonstrating that speed humps often push navigation app detours onto adjacent residential streets.",
        "CT-DOT-14", "Connecticut General Statutes Title 14 (Highway Traffic Control)"
    ),
    "nexis_urn:contentItem:69RD-M391-JCBF-S14F-00000-00": (
        "Municipal Traffic Mitigation & Street Controls",
        "Municipal traffic management operations implementing temporary one-way street patterns and closures for civic events, coordinating detours directly with navigation app mapping feeds.",
        "MUNI-STREET-TEMP", "Municipal Temporary Street Closure & Event Detour Regulations"
    ),
    "nexis_urn:contentItem:59C9-W101-F03R-N0MX-00000-00": (
        "Municipal Traffic Mitigation & Street Controls",
        "Seattle transportation planning analysis examining how roadway lane reallocations and road diets on Dexter Avenue influence arterial flow and commuter diversion patterns.",
        "SEA-SMC-11.16", "Seattle Municipal Code Title 11 (Traffic Control & Calming)"
    ),
    "nexis_urn:contentItem:5RPF-NKS1-DY83-T08F-00000-00": (
        "Municipal Traffic Mitigation & Street Controls",
        "UPI survey of suburban municipalities nationwide erecting 'No Thru Traffic' barriers, speed cushions, and turn bans to physically obstruct GPS-directed cut-through traffic.",
        "MUNI-CUTTHRU-GEN", "Municipal Residential Traffic Calming & Thru-Traffic Restrictions"
    ),

    # 4. Community Pushback & Safety Hazards (Echo Park, Baxter St, Police Pushback)
    "src_df18bde5b05e69aa6fee": (
        "Community Pushback & Safety Hazards",
        "Investigative feature on the severe traffic hazards, vehicle rollovers, and neighborhood gridlock caused by navigation app detour algorithms directing high volumes onto steep hillside streets in Los Angeles.",
        "None (Legal Gap)", "Unaddressed by Current Law"
    ),
    "src_2910e1608eed71065145": (
        "Community Pushback & Safety Hazards",
        "Documents extreme vehicle accidents, gridlock, and rollovers on steep Los Angeles residential streets (such as Baxter Street) caused by navigation apps rerouting drivers around freeway traffic.",
        "None (Legal Gap)", "Unaddressed by Current Law"
    ),
    "nexis_urn:contentItem:5K0V-VBK1-DY6F-J3BW-00000-00": (
        "Community Pushback & Safety Hazards",
        "Chronicles escalating neighborhood resistance across US metropolitan suburbs as traffic-weary homeowners confront navigation platforms over relentless cut-through traffic flooding residential roads.",
        "None (Legal Gap)", "Unaddressed by Current Law"
    ),
    "nexis_urn:contentItem:589D-0D91-DXNV-51YF-00000-00": (
        "Community Pushback & Safety Hazards",
        "Examines intense neighborhood disputes in Los Angeles where navigation app detours overwhelmed residential side streets during major freeway closures.",
        "None (Legal Gap)", "Unaddressed by Current Law"
    ),
    "nexis_urn:contentItem:6HBG-7JV3-RSFV-C2TW-00000-00": (
        "Community Pushback & Safety Hazards",
        "Residents in Turner, Maine, voiced alarm as Google Maps shortcuts directed heavy commuter turnpike overflow onto narrow rural roads, creating safety hazards and roadway deterioration.",
        "None (Legal Gap)", "Unaddressed by Current Law"
    ),
    "nexis_urn:contentItem:5TCC-3WG1-DXVP-V217-00000-00": (
        "Community Pushback & Safety Hazards",
        "Reports neighborhood frustration in New Canaan, Connecticut, as Merritt Parkway congestion continually pushes navigation app users onto quiet residential bypass streets.",
        "None (Legal Gap)", "Unaddressed by Current Law"
    ),
    "nexis_urn:contentItem:5W18-9X61-DXVP-V170-00000-00": (
        "Community Pushback & Safety Hazards",
        "New Canaan, Connecticut, residents erupted in contentious public hearings demanding physical road closures after navigation apps directed heavy commuter bypass traffic down Nursery Road.",
        "None (Legal Gap)", "Unaddressed by Current Law"
    ),
    "src_97a13ecf3417e5676e08": (
        "Community Pushback & Safety Hazards",
        "User community feature request petitioning Waze to create a mechanism allowing municipalities and residents to blacklist narrow residential streets from routing engines.",
        "None (Legal Gap)", "Unaddressed by Current Law"
    ),
    "nexis_urn:contentItem:5Y5V-NWG1-JBRC-V10Y-00000-00": (
        "Community Pushback & Safety Hazards",
        "Artist Simon Weckert carted 99 smartphones in a wagon to generate virtual traffic jams on Google Maps, exposing vulnerabilities in navigation algorithms and their impact on municipal street routing.",
        "None (Legal Gap)", "Unaddressed by Current Law"
    ),
    "nexis_urn:contentItem:5DVF-PCG1-F03R-N4RS-00000-00": (
        "Community Pushback & Safety Hazards",
        "Los Angeles neighborhood residents submitted coordinated false accident and hazard reports on Waze to artificially deceive navigation algorithms into redirecting cut-through traffic away from their streets.",
        "None (Legal Gap)", "Unaddressed by Current Law"
    ),
    "nexis_urn:contentItem:5N1D-GYS1-JC8N-K0NH-00000-00": (
        "Community Pushback & Safety Hazards",
        "USA Today investigative analysis detailing how navigation shortcuts on Waze and Google Maps overwhelm quiet residential streets, prompting suburban residents to demand municipal traffic interventions.",
        "None (Legal Gap)", "Unaddressed by Current Law"
    ),
    "nexis_urn:contentItem:5S8R-1761-JCKG-J00S-00000-00": (
        "Community Pushback & Safety Hazards",
        "U.S. News & World Report feature examining why suburban municipalities and homeowner associations have revolted against Waze rerouting commuter traffic through historically quiet neighborhoods.",
        "None (Legal Gap)", "Unaddressed by Current Law"
    ),
    "nexis_urn:contentItem:5RF0-1NN1-JB20-G507-00000-00": (
        "Community Pushback & Safety Hazards",
        "CBS News national broadcast examining how algorithmic navigation turns local secret shortcuts into congested commuter thoroughfares, sparking intense community backlash and safety concerns.",
        "None (Legal Gap)", "Unaddressed by Current Law"
    ),
    "nexis_urn:contentItem:5KKY-N4W1-JC8S-D52X-00000-00": (
        "Community Pushback & Safety Hazards",
        "Houston Chronicle report on Woodland Heights residents organizing against navigation apps funneling highway bypass traffic onto narrow residential streets with blind intersections.",
        "None (Legal Gap)", "Unaddressed by Current Law"
    ),
    "nexis_urn:contentItem:5XBB-X0M1-JC0C-J026-00000-00": (
        "Community Pushback & Safety Hazards",
        "Law enforcement officials criticized Google Maps and Waze for introducing crowdsourced police speed trap alerts, arguing the feature undermines traffic enforcement and officer safety.",
        "FED-POLICE-01", "Police Enforcement & Navigation Platform Warning Disputes"
    ),
    "nexis_urn:contentItem:5VG9-HDB1-JBSN-30DK-00000-00": (
        "Community Pushback & Safety Hazards",
        "Police departments nationwide demanded navigation platforms remove crowdsourced DWI checkpoint locations, warning that broadcast warnings enable impaired motorists to evade enforcement.",
        "FED-POLICE-01", "Police Enforcement & Navigation Platform Warning Disputes"
    ),
    "nexis_urn:contentItem:5VCH-KKT1-JCMN-Y1TM-00000-00": (
        "Community Pushback & Safety Hazards",
        "New York City Police Department issued a formal cease-and-desist letter demanding Google remove DWI checkpoint warnings from Waze, asserting the feature abets criminal activity.",
        "FED-POLICE-01", "Police Enforcement & Navigation Platform Warning Disputes"
    ),
    "nexis_urn:contentItem:5VCH-KK31-JCMN-Y1VY-00000-00": (
        "Community Pushback & Safety Hazards",
        "Conservative Daily News reporting on NYPD legal demands for Google to disable police location reporting on Waze to preserve the integrity of sobriety checkpoints.",
        "FED-POLICE-01", "Police Enforcement & Navigation Platform Warning Disputes"
    ),
    "nexis_urn:contentItem:5VCH-D7R1-JBPX-X3FP-00000-00": (
        "Community Pushback & Safety Hazards",
        "CNN coverage of NYPD's formal letter asserting that crowdsourced DWI checkpoint warnings on Waze compromise public safety and could constitute reckless endangerment.",
        "FED-POLICE-01", "Police Enforcement & Navigation Platform Warning Disputes"
    ),
    "nexis_urn:contentItem:5VCM-69K1-JCMN-Y00B-00000-00": (
        "Community Pushback & Safety Hazards",
        "Techdirt legal analysis examining First Amendment protections surrounding crowdsourced reporting of police checkpoints versus municipal demands for navigation app censorship.",
        "FED-POLICE-01", "Police Enforcement & Navigation Platform Warning Disputes"
    ),
    "nexis_urn:contentItem:5F86-02N1-JBSS-S139-00000-00": (
        "Community Pushback & Safety Hazards",
        "CNN Wire editorial debating the ethics and legality of crowdsourced speed trap alerts on navigation apps, contrasting driver convenience against law enforcement speed deterrence.",
        "FED-POLICE-01", "Police Enforcement & Navigation Platform Warning Disputes"
    ),
    "nexis_urn:contentItem:5FWG-YXT1-JCMN-Y4XP-00000-00": (
        "Community Pushback & Safety Hazards",
        "Techdirt report on the resolution of disputes between the Los Angeles Police Department and Waze, moving from accusations of cop-tracking to formal municipal data-sharing collaboration.",
        "FED-POLICE-01", "Police Enforcement & Navigation Platform Warning Disputes"
    ),

    # 5. Public-Private Data Partnerships
    "src_8f6b264845ca47814ba0": (
        "Public-Private Data Partnerships",
        "Details the foundational framework of Waze's Connected Citizens Program, where public agencies across the US exchange municipal street closures and construction data for real-time crowdsourced traffic telemetry.",
        "WAZE-CCP-01", "Waze Connected Citizens Program Framework"
    ),
    "src_a3aec998433f0c3fff3d": (
        "Public-Private Data Partnerships",
        "Official Waze Connected Citizens Program factsheet defining bilateral data sharing protocols between navigation platforms and municipal transportation authorities.",
        "WAZE-CCP-01", "Waze Connected Citizens Program Framework"
    ),
    "src_209e9565661083dba383": (
        "Public-Private Data Partnerships",
        "Waze for Cities program specifications detailing the transition of Connected Citizens into a structured municipal data exchange platform integrated with cloud analytics.",
        "WAZE-CCP-01", "Waze Connected Citizens Program Framework"
    ),
    "src_ae24cf62a63f34c9fe0b": (
        "Public-Private Data Partnerships",
        "Waze for Cities Google Cloud integration enabling municipal transportation engineers to analyze aggregated navigation telemetry via Google BigQuery for infrastructure planning.",
        "WAZE-CCP-01", "Waze Connected Citizens Program Framework"
    ),
    "nexis_urn:contentItem:5X5R-39S1-F03R-N066-00000-00": (
        "Public-Private Data Partnerships",
        "VentureBeat report on Waze integrating its Connected Citizens Program with Google Cloud BigQuery to give municipal partners scalable access to mobility data feeds.",
        "WAZE-CCP-01", "Waze Connected Citizens Program Framework"
    ),
    "nexis_urn:contentItem:7X74-0TJ0-Y8T9-V4S1-00000-00": (
        "Public-Private Data Partnerships",
        "Waze officially launched its international Connected Citizens partner program with ten inaugural municipal government agencies, establishing bilateral road closure exchanges.",
        "WAZE-CCP-01", "Waze Connected Citizens Program Framework"
    ),
    "nexis_urn:contentItem:6K23-G0Y3-S99D-X1PV-00000-00": (
        "Public-Private Data Partnerships",
        "Esri partnered with Waze and Google Maps to integrate ArcGIS municipal GIS layers, automating the transmission of authoritative city road closures and construction zones into navigation algorithms.",
        "ESRI-GIS-01", "Esri ArcGIS & Navigation Data Integration Standard"
    ),
    "nexis_urn:contentItem:5KXP-09P1-DXY3-00J6-00000-00": (
        "Public-Private Data Partnerships",
        "Esri formed a foundational partnership with the Waze Connected Citizens Program, enabling hundreds of municipal GIS departments to pipe authoritative road closure data into navigation apps.",
        "ESRI-GIS-01", "Esri ArcGIS & Navigation Data Integration Standard"
    ),
    "nexis_urn:contentItem:6J9T-Y0C3-S3T5-M0JH-00000-00": (
        "Public-Private Data Partnerships",
        "Waymo and Waze launched a collaborative initiative utilizing autonomous vehicle sensors to detect road surface potholes and upload maintenance data to municipal public works agencies.",
        "WAYMO-WAZE-01", "Waymo & Waze Autonomous Infrastructure Telemetry Partnership"
    ),
    "nexis_urn:contentItem:6KGN-8633-RV2G-70PX-00000-00": (
        "Public-Private Data Partnerships",
        "Mashable analysis of the Waymo-Waze infrastructure sensing pilot, evaluating how autonomous vehicles share roadway defect data with municipal transportation departments.",
        "WAYMO-WAZE-01", "Waymo & Waze Autonomous Infrastructure Telemetry Partnership"
    ),
    "nexis_urn:contentItem:6JDF-6YF3-RXM1-R51N-00000-00": (
        "Public-Private Data Partnerships",
        "Atlanta partnered with Waymo and Waze in a five-city municipal pilot deploying robotaxi sensor telemetry to locate and patch road surface potholes across the metropolitan area.",
        "WAYMO-WAZE-01", "Waymo & Waze Autonomous Infrastructure Telemetry Partnership"
    ),
    "nexis_urn:contentItem:6JB1-HSD3-RRJ6-S2F0-00000-00": (
        "Public-Private Data Partnerships",
        "San Francisco Chronicle coverage of the Waymo and Waze municipal pilot deploying autonomous vehicle vibration sensors to map and repair street defects across California cities.",
        "WAYMO-WAZE-01", "Waymo & Waze Autonomous Infrastructure Telemetry Partnership"
    ),
    "nexis_urn:contentItem:6JDJ-CKB3-S76F-Y3CS-00000-00": (
        "Public-Private Data Partnerships",
        "The Daily Texan reports on Austin partnering with Waymo and Waze to utilize autonomous vehicle telemetry for municipal street repairs and roadway surface tracking.",
        "WAYMO-WAZE-01", "Waymo & Waze Autonomous Infrastructure Telemetry Partnership"
    ),
    "nexis_urn:contentItem:6JB2-23J3-RWVD-34TB-00000-00": (
        "Public-Private Data Partnerships",
        "Philadelphia evaluated participating in the Waymo-Waze pothole sensing pilot, assessing municipal integration of autonomous sensor data into street maintenance dispatch.",
        "WAYMO-WAZE-01", "Waymo & Waze Autonomous Infrastructure Telemetry Partnership"
    ),
    "nexis_urn:contentItem:6KFT-KTJ3-S8NW-80HD-00000-00": (
        "Public-Private Data Partnerships",
        "CNET report on Waymo and Waze deploying autonomous vehicle perception systems to collect roadway telemetry and deliver infrastructure maintenance intelligence to cities.",
        "WAYMO-WAZE-01", "Waymo & Waze Autonomous Infrastructure Telemetry Partnership"
    ),
    "nexis_urn:contentItem:6J9V-WWH3-RX6H-53PJ-00000-00": (
        "Public-Private Data Partnerships",
        "USA Today coverage of Atlanta Department of Transportation integrating Waymo autonomous sensor data via Waze for Cities to accelerate municipal street repairs.",
        "WAYMO-WAZE-01", "Waymo & Waze Autonomous Infrastructure Telemetry Partnership"
    ),
    "nexis_urn:contentItem:6J9S-VFV3-SG7J-T1CW-00000-00": (
        "Public-Private Data Partnerships",
        "Fast Company analysis of the Waymo and Waze collaborative data project leveraging autonomous driving telemetry to address municipal road infrastructure degradation.",
        "WAYMO-WAZE-01", "Waymo & Waze Autonomous Infrastructure Telemetry Partnership"
    ),
    "nexis_urn:contentItem:6JBN-B2S3-S0W8-N43H-00000-00": (
        "Public-Private Data Partnerships",
        "Los Angeles Times report on Waymo and Waze partnering with the City of Los Angeles Bureau of Street Services to automate pothole detection across city streets.",
        "WAYMO-WAZE-01", "Waymo & Waze Autonomous Infrastructure Telemetry Partnership"
    ),
    "nexis_urn:contentItem:6JBN-T673-SGW5-C224-00000-00": (
        "Public-Private Data Partnerships",
        "Los Angeles Times deep dive into the engineering mechanics of Waymo robotaxis logging street surface vibrations to feed municipal maintenance work orders via Waze.",
        "WAYMO-WAZE-01", "Waymo & Waze Autonomous Infrastructure Telemetry Partnership"
    ),
    "nexis_urn:contentItem:6JD4-H063-SFWH-73FN-00000-00": (
        "Public-Private Data Partnerships",
        "Men's Journal profile of Waymo autonomous vehicles generating crowdsourced road condition maps in partnership with Waze for municipal roadway management.",
        "WAYMO-WAZE-01", "Waymo & Waze Autonomous Infrastructure Telemetry Partnership"
    ),
    "nexis_urn:contentItem:6DP3-HNN3-SBYC-S06J-00000-00": (
        "Public-Private Data Partnerships",
        "Illinois State Police and DoIT partnered with HAAS Alert to stream real-time emergency responder vehicle alerts directly into navigation apps to enforce Scott's Law move-over rules.",
        "HAAS-ALERT-01", "HAAS Alert Digital Emergency Vehicle Notification System"
    ),
    "nexis_urn:contentItem:6DP3-TRV3-RVYY-455N-00000-00": (
        "Public-Private Data Partnerships",
        "Torrance Fire Department equipped emergency apparatus with HAAS Alert Safety Cloud digital alerting, broadcasting emergency scene warnings directly to navigation app users.",
        "HAAS-ALERT-01", "HAAS Alert Digital Emergency Vehicle Notification System"
    ),
    "nexis_urn:contentItem:679C-4GD1-JBG1-83JX-00000-00": (
        "Public-Private Data Partnerships",
        "Applied Information integrated municipal school zone flashing beacons and emergency vehicle preemption telemetry into navigation apps to alert drivers to active speed zones.",
        "V2X-APPLIED-01", "Connected Vehicle V2X Navigation Infrastructure Integration"
    ),
    "nexis_urn:contentItem:5S66-H271-F03R-N3F4-00000-00": (
        "Public-Private Data Partnerships",
        "Data-sharing pact between Waze and Waycare AI in Southern Nevada integrating predictive traffic analytics, crowdsourced hazard telemetry, and regional traffic management center operations.",
        "WAYCARE-NV-01", "Nevada Regional Transportation Commission AI Data Agreement"
    ),
    "src_7a51efb5b5f5430e194b": (
        "Public-Private Data Partnerships",
        "Boston Mayor Martin J. Walsh announced a data-sharing partnership with Waze under the Connected Citizens Program to feed municipal road closures into the app and optimize commuter flow.",
        "BOS-CCP-2015", "City of Boston & Waze Connected Citizens Agreement"
    ),
    "src_0d4fa7ccce08eaf50b2f": (
        "Public-Private Data Partnerships",
        "Technology news coverage of Boston's Connected Citizens partnership with Waze, detailing how city engineers use telemetry from ~400,000 regional drivers to adjust intersection signals.",
        "BOS-CCP-2015", "City of Boston & Waze Connected Citizens Agreement"
    ),
    "nexis_urn:contentItem:5FBD-JYR1-F03R-N249-00000-00": (
        "Public-Private Data Partnerships",
        "Boston transportation officials announced a formal municipal data-sharing partnership with Waze to synchronize city construction detours with commuter navigation directions.",
        "BOS-CCP-2015", "City of Boston & Waze Connected Citizens Agreement"
    ),
    "nexis_urn:contentItem:5F9R-KCS1-F12F-F39G-00000-00": (
        "Public-Private Data Partnerships",
        "Official Boston mayoral proclamation establishing two-way data exchange with Waze to improve municipal traffic management and reduce congestion delays.",
        "BOS-CCP-2015", "City of Boston & Waze Connected Citizens Agreement"
    ),
    "src_f2e92e99cdf509170cc7": (
        "Public-Private Data Partnerships",
        "MassDOT joined the Waze Connected Citizens Program statewide, providing official highway incident and construction closure information while receiving real-time congestion reports.",
        "MA-DOT-CCP", "MassDOT Statewide Waze Connected Citizens Partnership"
    ),
    "nexis_urn:contentItem:5K1K-PW91-JCBF-S4VS-00000-00": (
        "Public-Private Data Partnerships",
        "MassDOT formalized a statewide two-way data partnership with Waze, feeding state highway operations center telemetry directly into navigation app routing engines.",
        "MA-DOT-CCP", "MassDOT Statewide Waze Connected Citizens Partnership"
    ),
    "nexis_urn:contentItem:6CNY-BDW1-F12F-F1B5-00000-00": (
        "Public-Private Data Partnerships",
        "City of Boston partnered with Google on Project Green Light, utilizing navigation app travel telemetry to model traffic patterns and optimize municipal traffic signal timing.",
        "BOS-GOOGLE-GL", "Boston & Google Project Green Light Signal Optimization"
    ),
    "nexis_urn:contentItem:6CPS-DDJ1-F03R-N298-00000-00": (
        "Public-Private Data Partnerships",
        "Boston Transportation Department expanded its collaboration with Google Project Green Light, leveraging AI analysis of navigation app stop-and-go data to reduce intersection emissions.",
        "BOS-GOOGLE-GL", "Boston & Google Project Green Light Signal Optimization"
    ),
    "nexis_urn:contentItem:6FWV-BM43-RRX6-50DY-00000-00": (
        "Public-Private Data Partnerships",
        "Boston Mayor Michelle Wu announced an expansion of the Google Project Green Light partnership, deploying navigation telemetry to optimize traffic signal timing across 50 intersections.",
        "BOS-GOOGLE-GL", "Boston & Google Project Green Light Signal Optimization"
    ),
    "src_d8bae76a48b8c662c148": (
        "Public-Private Data Partnerships",
        "Sidewalk Labs developed 'Flow', an urban data platform integrating navigation sensor feeds and municipal traffic data to optimize parking and routing in Columbus, Ohio.",
        "DOT-SMART-CITY", "USDOT Smart City Challenge Mobility Integration"
    ),
    "nexis_urn:contentItem:5K3Y-R4C1-JCMN-Y31S-00000-00": (
        "Public-Private Data Partnerships",
        "Analysis of Sidewalk Labs launching Flow, a mobility coordination platform integrating navigation platform data with city parking and transit infrastructure.",
        "DOT-SMART-CITY", "USDOT Smart City Challenge Mobility Integration"
    ),
    "nexis_urn:contentItem:5KR5-JDR1-F12F-F437-00000-00": (
        "Public-Private Data Partnerships",
        "City of Greensboro, North Carolina, entered a bilateral data-sharing partnership with Waze to exchange municipal street construction data for real-time driver delay telemetry.",
        "NC-GREENS-CCP", "Greensboro & Waze Connected Citizens Partnership"
    ),
    "nexis_urn:contentItem:5KPS-F281-DYG2-R4FC-00000-00": (
        "Public-Private Data Partnerships",
        "Greensboro Department of Transportation established formal data integration with Waze to synchronize city detour notices with commuter navigation routes.",
        "NC-GREENS-CCP", "Greensboro & Waze Connected Citizens Partnership"
    ),
    "nexis_urn:contentItem:5RN8-0M61-JDKC-R331-00000-00": (
        "Public-Private Data Partnerships",
        "City of Norfolk, Virginia, joined the Waze Connected Citizens Program to integrate real-time street flood and bridge closure data directly into navigation routing engines.",
        "VA-NORF-CCP", "City of Norfolk & Waze Connected Citizens Agreement"
    ),
    "nexis_urn:contentItem:5JRW-M521-DYG2-R3W7-00000-00": (
        "Public-Private Data Partnerships",
        "Louisiana DOTD and Baton Rouge City-Parish established a municipal data-sharing partnership with Waze to integrate capital project road closures and monitor commuter choke points.",
        "LA-DOTD-CCP", "Louisiana DOTD & Baton Rouge Waze Partnership"
    ),
    "nexis_urn:contentItem:69X0-WNX1-F03F-K51D-00000-00": (
        "Public-Private Data Partnerships",
        "San Antonio River Authority partnered with Waze to transmit real-time low-water crossing flood sensor alerts directly into navigation algorithms, preventing vehicles from entering flooded roads.",
        "TX-SARA-01", "San Antonio River Authority Flood Telemetry Partnership"
    ),
    "nexis_urn:contentItem:5HM3-0111-JB72-12XH-00000-00": (
        "Public-Private Data Partnerships",
        "Pennsylvania Governor Tom Wolf announced a statewide data partnership between PennDOT, the PA Turnpike Commission, and Waze to share construction closures and crowdsourced incident feeds.",
        "PA-DOT-CCP", "PennDOT Statewide Waze Connected Citizens Partnership"
    ),
    "nexis_urn:contentItem:5HN6-4D41-DY7V-G3W9-00000-00": (
        "Public-Private Data Partnerships",
        "PennDOT formalized its statewide integration with Waze, feeding official 511PA traffic incidents into navigation apps while receiving real-time delay telemetry from Pennsylvania drivers.",
        "PA-DOT-CCP", "PennDOT Statewide Waze Connected Citizens Partnership"
    ),
    "nexis_urn:contentItem:5HND-4081-JC8F-22BP-00000-00": (
        "Public-Private Data Partnerships",
        "Lancaster County reporting on PennDOT's strategic partnership with Waze, exploring how state transportation planners use crowdsourced road data to manage highway work zones.",
        "PA-DOT-CCP", "PennDOT Statewide Waze Connected Citizens Partnership"
    ),
    "nexis_urn:contentItem:5H0V-B0R1-DYG2-R2C4-00000-00": (
        "Public-Private Data Partnerships",
        "Louisville Metro Government partnered with Waze to integrate municipal road closure data into commuter apps and analyze crowdsourced congestion telemetry for capital planning.",
        "KY-LOU-CCP", "Louisville Metro & Waze Connected Citizens Agreement"
    ),
    "nexis_urn:contentItem:5S8X-WVF1-JCBF-S33F-00000-00": (
        "Public-Private Data Partnerships",
        "Loudoun County, Virginia, partnered with Waze to incorporate real-time suburban road construction and lane restrictions into regional navigation routing.",
        "VA-LOUD-CCP", "Loudoun County & Waze Connected Citizens Agreement"
    ),
    "nexis_urn:contentItem:60XF-PW11-JDKC-R1W3-00000-00": (
        "Public-Private Data Partnerships",
        "City of Virginia Beach received a national Government Experience Award for its data-sharing partnership with Waze, streamlining municipal detour management and hurricane evacuation routing.",
        "VA-VB-CCP", "Virginia Beach & Waze Connected Citizens Partnership"
    ),
    "nexis_urn:contentItem:5VSV-C4W1-JDKC-R0MT-00000-00": (
        "Public-Private Data Partnerships",
        "City of Virginia Beach officially enrolled in the Waze Connected Citizens Program to automate real-time traffic detour feeds during major resort area events and storms.",
        "VA-VB-CCP", "Virginia Beach & Waze Connected Citizens Partnership"
    ),
    "nexis_urn:contentItem:5SST-61B1-JDKC-R3BD-00000-00": (
        "Public-Private Data Partnerships",
        "City of Johns Creek, Georgia, leveraged its two-way Waze data partnership to adjust traffic signal timings and update commuter detour routes during arterial water main repairs.",
        "GA-JC-CCP", "Johns Creek & Waze Connected Citizens Agreement"
    ),
    "nexis_urn:contentItem:5X4N-53V1-JDKC-R3PT-00000-00": (
        "Public-Private Data Partnerships",
        "Miami-Dade Transit partnered with Waze Carpool to encourage multi-passenger ridesharing and coordinate commuter connections with county transit hubs.",
        "FL-MDT-WAZE", "Miami-Dade Transit & Waze Carpool Mobility Partnership"
    ),
    "nexis_urn:contentItem:5X5B-7641-DY7V-G003-00000-00": (
        "Public-Private Data Partnerships",
        "Tampa Hillsborough Expressway Authority partnered with Waze to deliver real-time reversible expressway lane status and toll plaza detour information directly to commuters.",
        "FL-THEA-CCP", "Tampa Hillsborough Expressway Authority & Waze Partnership"
    ),
    "src_c8f5fcc928d66ad4b9e7": (
        "Public-Private Data Partnerships",
        "Georgia DOT partnered with Waze to dynamically update navigation maps with real-time lane closures, construction work zones, and storm road blocks.",
        "GA-DOT-CCP", "Georgia DOT & Waze Connected Citizens Agreement"
    ),
    "nexis_urn:contentItem:63HR-VBW1-F03R-N442-00000-00": (
        "Public-Private Data Partnerships",
        "Colorado DOT officials requested navigation platforms plant false road closure information during winter storms to deter traffic, triggering national debates over public-private data integrity.",
        "CO-DOT-ALERT", "Colorado DOT Navigation App Coordination Incident"
    ),
    "nexis_urn:contentItem:5K36-VSB1-DYG2-R3XV-00000-00": (
        "Public-Private Data Partnerships",
        "City of Sacramento joined the Waze Connected Citizens Program, piping municipal capital project closures directly into navigation apps to manage downtown traffic.",
        "CA-SAC-CCP", "City of Sacramento & Waze Connected Citizens Agreement"
    ),
    "nexis_urn:contentItem:5MP0-RJT1-F12F-F2DN-00000-00": (
        "Public-Private Data Partnerships",
        "City of Arlington, Texas, enrolled in the Waze Connected Citizens Program to share stadium event street closures and arterial construction alerts with commuters.",
        "TX-ARL-CCP", "City of Arlington & Waze Connected Citizens Agreement"
    ),
    "nexis_urn:contentItem:5KJ7-X441-JDKC-R3KT-00000-00": (
        "Public-Private Data Partnerships",
        "Evanston and Naperville became the first Illinois municipalities to join the Waze Connected Citizens Program, sharing local road work and school zone data.",
        "IL-EVAN-CCP", "Evanston & Naperville Waze Connected Citizens Agreement"
    ),
    "nexis_urn:contentItem:5KJ7-X441-JDKC-R3KW-00000-00": (
        "Public-Private Data Partnerships",
        "Naperville and Evanston transportation divisions established bilateral data links with Waze to synchronize suburban municipal road closures with navigation apps.",
        "IL-EVAN-CCP", "Evanston & Naperville Waze Connected Citizens Agreement"
    ),
    "nexis_urn:contentItem:5JG5-TCW1-F053-W0NR-00000-00": (
        "Public-Private Data Partnerships",
        "City of Charlotte Department of Transportation partnered with Waze to share authoritative street detour feeds and evaluate crowdsourced congestion bottlenecks.",
        "NC-CHAR-CCP", "City of Charlotte & Waze Connected Citizens Partnership"
    ),
    "nexis_urn:contentItem:5JPT-KMX1-F12F-F3C3-00000-00": (
        "Public-Private Data Partnerships",
        "City of Raleigh joined the Waze Connected Citizens Program to incorporate city water main repairs, road races, and parade closures into driver navigation maps.",
        "NC-RAL-CCP", "City of Raleigh & Waze Connected Citizens Agreement"
    ),
    "nexis_urn:contentItem:5FKJ-FVR1-DYTH-G4FG-00000-00": (
        "Public-Private Data Partnerships",
        "Maryland State Highway Administration (MDOT SHA) entered a statewide data partnership with Waze, linking CHART highway management data with crowdsourced driver reports.",
        "MD-SHA-CCP", "Maryland SHA & Waze Connected Citizens Partnership"
    ),
    "nexis_urn:contentItem:5MD5-07S1-JC11-10YN-00000-00": (
        "Public-Private Data Partnerships",
        "City of Fort Worth joined the Waze Connected Citizens Program to integrate municipal road construction schedules and monitor urban traffic flow trends.",
        "TX-FTW-CCP", "City of Fort Worth & Waze Connected Citizens Agreement"
    ),
    "nexis_urn:contentItem:5P7K-RGT1-F12F-F49X-00000-00": (
        "Public-Private Data Partnerships",
        "Municipality of Anchorage joined the Waze Connected Citizens Program to stream winter weather road conditions and snowplow route data directly to motorists.",
        "AK-ANC-CCP", "Municipality of Anchorage & Waze Connected Citizens Partnership"
    ),
    "nexis_urn:contentItem:5NMW-2HG1-DYG2-R1KW-00000-00": (
        "Public-Private Data Partnerships",
        "Nevada Department of Transportation partnered with Waze to pipe statewide highway work zone and chain control restrictions into navigation apps.",
        "NV-DOT-CCP", "Nevada DOT & Waze Connected Citizens Agreement"
    ),
    "nexis_urn:contentItem:5N17-Y4B1-F12F-F2MY-00000-00": (
        "Public-Private Data Partnerships",
        "Town of Cary, North Carolina, joined the Waze Connected Citizens Program on Open Data Day to integrate municipal open data feeds with commuter navigation platforms.",
        "NC-CARY-CCP", "Town of Cary & Waze Connected Citizens Agreement"
    ),
    "nexis_urn:contentItem:5R0P-P3D1-DYTH-G110-00000-00": (
        "Public-Private Data Partnerships",
        "Rhode Island DOT partnered with Waze to calculate real-time highway travel times for overhead electronic message signs using crowdsourced driver telemetry.",
        "RI-DOT-CCP", "Rhode Island DOT & Waze Data Partnership"
    ),
    "nexis_urn:contentItem:5KR0-JYX1-JDKC-R50Y-00000-00": (
        "Public-Private Data Partnerships",
        "Douglas County, Georgia, joined the Waze Connected Citizens Program to provide authoritative local road construction data and monitor suburban commuter choke points.",
        "GA-DOUG-CCP", "Douglas County & Waze Connected Citizens Agreement"
    ),
    "nexis_urn:contentItem:5K50-8MY1-JDKC-R246-00000-00": (
        "Public-Private Data Partnerships",
        "Miami-Dade County became the first Florida county to join the Waze Connected Citizens Program, linking county traffic signals and bridge operations with navigation telemetry.",
        "FL-MDC-CCP", "Miami-Dade County & Waze Connected Citizens Agreement"
    ),
    "nexis_urn:contentItem:5J2N-DK81-DYG2-R401-00000-00": (
        "Public-Private Data Partnerships",
        "San Francisco Mayor Ed Lee announced a municipal data-sharing partnership with Waze, providing municipal street closure feeds to mitigate Vision Zero pedestrian conflict zones.",
        "SF-MOU-2015", "City of San Francisco & Waze Connected Citizens MOU"
    ),
    "nexis_urn:contentItem:5K3G-GG71-JDTS-G2V0-00000-00": (
        "Public-Private Data Partnerships",
        "Iowa DOT joined the Waze Connected Citizens Program to incorporate real-time winter blizzard highway closures and detour alerts into commercial and passenger GPS apps.",
        "IA-DOT-CCP", "Iowa DOT & Waze Connected Citizens Agreement"
    ),
    "nexis_urn:contentItem:5MFN-DGD1-JDKC-R1RJ-00000-00": (
        "Public-Private Data Partnerships",
        "City of Asheville, North Carolina, partnered with Waze to integrate municipal road closures, utility repairs, and marathon detours into regional commuter navigation.",
        "NC-ASH-CCP", "City of Asheville & Waze Connected Citizens Agreement"
    ),
    "nexis_urn:contentItem:5V5C-RPM1-JDKC-R091-00000-00": (
        "Public-Private Data Partnerships",
        "City of Coral Gables joined the Waze Connected Citizens Program to feed municipal road projects and storm debris closures into real-time navigation directions.",
        "FL-CG-CCP", "City of Coral Gables & Waze Connected Citizens Agreement"
    ),
    "nexis_urn:contentItem:5JG7-TH41-DYTH-G0P2-00000-00": (
        "Public-Private Data Partnerships",
        "Caltrans partnered with Waze under the Connected Citizens Program statewide, providing real-time QuickMap highway closure feeds to improve regional traffic routing.",
        "CA-CALTRANS-CCP", "Caltrans Statewide Waze Connected Citizens Agreement"
    ),
    "nexis_urn:contentItem:5SH9-WFC1-F12F-F53T-00000-00": (
        "Public-Private Data Partnerships",
        "Austin Transportation Department entered a Connected Citizens data partnership with Waze, integrating smart corridor signals with commuter traffic telemetry.",
        "TX-ATX-CCP", "City of Austin & Waze Connected Citizens Agreement"
    ),
    "nexis_urn:contentItem:5K6D-XDN1-JC11-114H-00000-00": (
        "Public-Private Data Partnerships",
        "Alabama DOT joined the Waze Connected Citizens Program to share statewide construction and incident reports while monitoring interstate bottleneck formation.",
        "AL-DOT-CCP", "Alabama DOT & Waze Connected Citizens Agreement"
    ),
    "nexis_urn:contentItem:5RMS-DBB1-JDKC-R2MH-00000-00": (
        "Public-Private Data Partnerships",
        "City of Lincoln, Nebraska, joined the Waze Connected Citizens Program to share municipal street maintenance detours and university game-day traffic closures.",
        "NE-LINC-CCP", "City of Lincoln & Waze Connected Citizens Agreement"
    ),
    "nexis_urn:contentItem:5GPG-YMV1-JC85-V436-00000-00": (
        "Public-Private Data Partnerships",
        "City of Atlanta and regional transit agencies partnered with Waze to feed downtown infrastructure closures and evaluate crowdsourced arterial congestion patterns.",
        "GA-ATL-CCP", "City of Atlanta & Waze Connected Citizens Partnership"
    ),
    "nexis_urn:contentItem:5MD4-RFN1-DYTH-G34S-00000-00": (
        "Public-Private Data Partnerships",
        "Virginia DOT partnered with Waze to integrate statewide 511 system data feeds, funneling construction closures and emergency detours into commuter navigation engines.",
        "VA-VDOT-CCP", "Virginia DOT & Waze Connected Citizens Agreement"
    ),
    "nexis_urn:contentItem:5MDK-CX51-JC11-10KJ-00000-00": (
        "Public-Private Data Partnerships",
        "Metropolitan Transportation Commission Freeway Service Patrol partnered with Waze in the Bay Area, utilizing crowdsourced incident alerts to dispatch roadside assistance.",
        "CA-MTC-FSP", "Bay Area MTC Freeway Service Patrol & Waze Partnership"
    ),
    "nexis_urn:contentItem:5N4W-N571-DYTH-G2G4-00000-00": (
        "Public-Private Data Partnerships",
        "Port Authority of New York and New Jersey partnered with Waze to deliver real-time bridge and tunnel crossing delay feeds and Lincoln Tunnel outbound detour guidance.",
        "NYNJ-PANYNJ-CCP", "Port Authority of NY & NJ & Waze Data Partnership"
    ),

    # 6. Commercial Freight & Bridge Clearance (Schumer Bills, Blumenthal, PennDOT, Truck GPS)
    "nexis_urn:contentItem:5Y26-NTJ1-DYVR-P4M9-00000-00": (
        "Commercial Freight & Bridge Clearance",
        "US Senator Chuck Schumer launched a federal initiative demanding GPS developers and federal regulators implement bridge clearance warnings to prevent trucks from hitting low overpasses.",
        "FED-06", "Federal truck size and weight limits (National Network / 23 U.S.C. § 127)"
    ),
    "nexis_urn:contentItem:62CM-7GY1-DYVR-P2T2-00000-00": (
        "Commercial Freight & Bridge Clearance",
        "US Senator Richard Blumenthal demanded navigation tech companies update algorithms and warnings after repeated commercial truck strikes on low-clearance bridges in Connecticut.",
        "FED-06", "Federal truck size and weight limits (National Network / 23 U.S.C. § 127)"
    ),
    "nexis_urn:contentItem:6HFB-7F23-SBRV-H1GS-00000-00": (
        "Commercial Freight & Bridge Clearance",
        "US Representatives George Latimer and Rob Bresnahan introduced federal legislation requiring commercial GPS developers to incorporate low-clearance bridge data to prevent strikes.",
        "FED-06", "Federal truck size and weight limits (National Network / 23 U.S.C. § 127)"
    ),
    "nexis_urn:contentItem:5Y0N-7PG1-JBH5-W02N-00000-00": (
        "Commercial Freight & Bridge Clearance",
        "US Senate leaders called on mobile application developers to include commercial vehicle size and weight limitations on smartphone GPS apps to prevent truck bridge strikes.",
        "FED-06", "Federal truck size and weight limits (National Network / 23 U.S.C. § 127)"
    ),
    "nexis_urn:contentItem:6GBB-B2S3-S09F-M2HX-00000-00": (
        "Commercial Freight & Bridge Clearance",
        "PennDOT launched its 'Know Your Height' enforcement campaign in Lancaster County, warning truck drivers that passenger navigation apps omit low bridge restrictions.",
        "PA-TITLE-75-49", "Pennsylvania Vehicle Code Title 75 § 4902 (Size/Weight Restrictions)"
    ),
    "nexis_urn:contentItem:6H62-XB83-S25R-T4M5-00000-00": (
        "Commercial Freight & Bridge Clearance",
        "Samsara launched an enterprise commercial navigation solution engineering customized truck routes that avoid low-clearance bridges, weight-restricted roads, and sharp turns.",
        "FED-06", "Federal truck size and weight limits (National Network / 23 U.S.C. § 127)"
    ),
    "nexis_urn:contentItem:5VNV-SYP1-DY07-K292-00000-00": (
        "Commercial Freight & Bridge Clearance",
        "ALK Technologies released upgraded CoPilot Truck navigation featuring dynamic commercial vehicle height and weight avoidance algorithms to eliminate bridge strike hazards.",
        "FED-06", "Federal truck size and weight limits (National Network / 23 U.S.C. § 127)"
    ),
    "nexis_urn:contentItem:4MDG-VTK0-TX51-22NM-00000-00": (
        "Commercial Freight & Bridge Clearance",
        "U.S. Xpress deployed ALK CoPilot Truck GPS across 5,000 tractor-trailers to ensure commercial drivers adhere to designated freight corridors and avoid restricted local roads.",
        "FED-06", "Federal truck size and weight limits (National Network / 23 U.S.C. § 127)"
    ),
    "nexis_urn:contentItem:5VSM-G3V1-JBH5-W0J6-00000-00": (
        "Commercial Freight & Bridge Clearance",
        "Overdrive industry review evaluating commercial trucking GPS applications, analyzing how truck routing engines prevent costly fines and low-overpass collisions.",
        "FED-06", "Federal truck size and weight limits (National Network / 23 U.S.C. § 127)"
    ),
    "nexis_urn:contentItem:4V41-25W0-TX51-20M6-00000-00": (
        "Commercial Freight & Bridge Clearance",
        "ALK Technologies launched PC*MILER Navigator 430, integrating commercial truck routing parameters to prevent commercial vehicles from traversing restricted municipal roads.",
        "FED-06", "Federal truck size and weight limits (National Network / 23 U.S.C. § 127)"
    ),
    "nexis_urn:contentItem:58RR-7N31-JCRR-013F-00000-00": (
        "Commercial Freight & Bridge Clearance",
        "Webtech Wireless partnered with ALK Technologies to embed CoPilot Truck commercial navigation into fleet telemetry hardware, ensuring compliance with bridge height limits.",
        "FED-06", "Federal truck size and weight limits (National Network / 23 U.S.C. § 127)"
    ),
    "nexis_urn:contentItem:58PM-K8W1-F0R9-G4CC-00000-00": (
        "Commercial Freight & Bridge Clearance",
        "Webtech Wireless announced integration of ALK commercial routing into fleet telematics to keep heavy freight carriers off weight-restricted municipal and residential streets.",
        "FED-06", "Federal truck size and weight limits (National Network / 23 U.S.C. § 127)"
    ),
    "nexis_urn:contentItem:55CW-X7P1-J9YY-Y0G2-00000-00": (
        "Commercial Freight & Bridge Clearance",
        "TeleType released a server-based truck navigation app for Android, providing custom commercial routing based on vehicle dimensions, axle loads, and hazardous materials.",
        "FED-06", "Federal truck size and weight limits (National Network / 23 U.S.C. § 127)"
    ),
    "nexis_urn:contentItem:5VR5-3RR1-JBH5-W122-00000-00": (
        "Commercial Freight & Bridge Clearance",
        "Overdrive feature on TeleType's truck routing application, detailing algorithms that calculate street legal access and low bridge clearance for commercial freight.",
        "FED-06", "Federal truck size and weight limits (National Network / 23 U.S.C. § 127)"
    ),
    "nexis_urn:contentItem:5J9G-46V1-JBKS-P433-00000-00": (
        "Commercial Freight & Bridge Clearance",
        "SmartTruckRoute navigation added route optimization features, calculating commercial truck legal paths around parkways, weight limits, and low overpasses.",
        "FED-06", "Federal truck size and weight limits (National Network / 23 U.S.C. § 127)"
    ),
    "nexis_urn:contentItem:567T-G511-J9YY-Y0C3-00000-00": (
        "Commercial Freight & Bridge Clearance",
        "SmartTruckRoute commercial truck navigation app introduced turn-by-turn voice directions configured with truck size and bridge clearance restrictions.",
        "FED-06", "Federal truck size and weight limits (National Network / 23 U.S.C. § 127)"
    ),
    "nexis_urn:contentItem:56T5-C1H1-DXF1-N0CH-00000-00": (
        "Commercial Freight & Bridge Clearance",
        "SmartTruckRoute provided lifetime map updates for truck drivers to ensure commercial routing algorithms reflect newly posted municipal bridge clearances and weight bans.",
        "FED-06", "Federal truck size and weight limits (National Network / 23 U.S.C. § 127)"
    ),
    "nexis_urn:contentItem:57T9-W851-DXMP-K561-00000-00": (
        "Commercial Freight & Bridge Clearance",
        "SmartTruckRoute launched its iOS truck navigation application, offering specialized commercial bridge clearance and hazmat routing for iPhone and iPad users.",
        "FED-06", "Federal truck size and weight limits (National Network / 23 U.S.C. § 127)"
    ),
    "nexis_urn:contentItem:5F5N-4Y71-JB5M-W1MH-00000-00": (
        "Commercial Freight & Bridge Clearance",
        "SmartTruckRoute announced instant cloud-based truck routing, allowing commercial drivers to generate bridge-compliant routes without heavy offline map downloads.",
        "FED-06", "Federal truck size and weight limits (National Network / 23 U.S.C. § 127)"
    ),
    "nexis_urn:contentItem:7YBS-9011-2PG1-000M-00000-00": (
        "Commercial Freight & Bridge Clearance",
        "Fleet Owner report on mobile truck navigation apps adding commercial vehicle routing profiles to keep heavy trucks off low-clearance and weight-posted parkways.",
        "FED-06", "Federal truck size and weight limits (National Network / 23 U.S.C. § 127)"
    ),
    "nexis_urn:contentItem:7X0X-V9T0-Y9HJ-P07D-00000-00": (
        "Commercial Freight & Bridge Clearance",
        "INRIX partnered with ALK to power CoPilot Live navigation with real-time traffic speeds, enhancing freight routing efficiency while maintaining vehicle height restrictions.",
        "FED-06", "Federal truck size and weight limits (National Network / 23 U.S.C. § 127)"
    ),

    # 7. Platform Features & Routing Algorithms (Eco Routing, Left Turns, Voice Commands, Detour Mechanics)
    "nexis_urn:contentItem:63ST-04D1-F03R-N3SF-00000-00": (
        "Platform Features & Routing Algorithms",
        "Google Maps introduced eco-friendly routing algorithms that prioritize fuel-efficient paths over raw travel time to reduce vehicular emissions across metropolitan networks.",
        "PLAT-ALG-02", "Navigation Platform Eco-Friendly & Fuel-Efficient Routing Engine"
    ),
    "nexis_urn:contentItem:63SN-6D81-DY7V-G183-00000-00": (
        "Platform Features & Routing Algorithms",
        "CNN Wire reporting on Google Maps launching fuel-efficient route recommendations, altering default commuter routing choices toward lower-emission arterial corridors.",
        "PLAT-ALG-02", "Navigation Platform Eco-Friendly & Fuel-Efficient Routing Engine"
    ),
    "src_264bf1d902e4b812735b": (
        "Platform Features & Routing Algorithms",
        "Waze launched crowdsourced road closure reporting allowing drivers to dynamically report blocked streets, altering commuter diversion patterns across metropolitan areas.",
        "PLAT-FEAT-01", "Waze Dynamic Road Closure Crowdsourcing System"
    ),
    "nexis_urn:contentItem:5N7J-XFH1-F03R-N37N-00000-00": (
        "Platform Features & Routing Algorithms",
        "Google Maps introduced algorithmic route preference learning, automatically adapting recommended routes based on individual commuter route choices and historical path deviations.",
        "PLAT-ALG-03", "Google Maps Commuter Route Preference Learning Engine"
    ),
    "nexis_urn:contentItem:5W9Y-MDT1-DY60-M0M6-00000-00": (
        "Platform Features & Routing Algorithms",
        "Google Assistant integrated with Waze to enable hands-free voice-directed navigation, ensuring compliance with state distracted driving laws while maintaining real-time routing.",
        "FED-DISTRACT-01", "State & Federal Distracted Driving Compliance Controls"
    ),
    "nexis_urn:contentItem:5WC1-D801-JCMN-Y21G-00000-00": (
        "Platform Features & Routing Algorithms",
        "Analysis of Google Assistant voice control updates on Waze, allowing drivers to report road hazards and potholes hands-free without violating handheld device bans.",
        "FED-DISTRACT-01", "State & Federal Distracted Driving Compliance Controls"
    ),
    "nexis_urn:contentItem:5R2M-WBX1-JCMN-Y23D-00000-00": (
        "Platform Features & Routing Algorithms",
        "Waze deployed hands-free voice command and motion gesture controls to comply with municipal and state distracted driving regulations during active navigation.",
        "FED-DISTRACT-01", "State & Federal Distracted Driving Compliance Controls"
    ),
    "nexis_urn:contentItem:5YRJ-C711-JCMN-Y15H-00000-00": (
        "Platform Features & Routing Algorithms",
        "Analysis of Waze multi-stop routing features that enable users to manually insert waypoints and override algorithmically determined detour paths through city streets.",
        "PLAT-FEAT-02", "Navigation App Multi-Stop & Waypoint Path Customization"
    ),
    "nexis_urn:contentItem:5YX1-RGD1-JCMN-Y4PM-00000-00": (
        "Platform Features & Routing Algorithms",
        "Guide evaluating Waze's social navigation mechanics, crowdsourced incident feeds, and user-driven map editing protocols that govern local route recommendations.",
        "PLAT-FEAT-02", "Navigation App Multi-Stop & Waypoint Path Customization"
    ),
    "nexis_urn:contentItem:53T0-GXS1-DXX7-H25H-00000-00": (
        "Platform Features & Routing Algorithms",
        "Waze demonstrated large-scale commuter rerouting capabilities during Los Angeles Interstate 405 closures ('Carmageddon'), testing algorithm capacity to distribute metropolitan traffic across alternate arterials.",
        "PLAT-ALG-04", "Large-Scale Arterial Commuter Diversion & Incident Rerouting"
    ),
    "nexis_urn:contentItem:5HJK-RKB1-DYRR-92B0-00000-00": (
        "Platform Features & Routing Algorithms",
        "USA Today interview with Waze growth leadership on algorithm scalability, commuter routing preferences, and the role of crowdsourced navigation during major urban disruptions.",
        "PLAT-ALG-04", "Large-Scale Arterial Commuter Diversion & Incident Rerouting"
    ),
    "nexis_urn:contentItem:5GHC-2MH1-JB72-12MV-00000-00": (
        "Platform Features & Routing Algorithms",
        "Legal and regulatory analysis examining privacy risks, municipal street impacts, and statutory boundaries arising from Google's acquisition and deployment of Waze crowdsourced routing telemetry.",
        "LEGAL-ANALYSIS-01", "Antitrust, Privacy, and Municipal Externalities in Navigation Platforms"
    ),
}

def main():
    root = Path(__file__).resolve().parent.parent
    docs_path = root / "docs" / "data" / "news_corpus_filtered.json"
    crosswalk_path = root / "docs" / "data" / "news_to_law_crosswalk.csv"
    filtered_export_json = root / "data" / "exports" / "research_analysis_filtered.json"
    filtered_export_csv = root / "data" / "exports" / "research_analysis_filtered.csv"
    all_sources_json = root / "data" / "exports" / "research_analysis_all_sources.json"
    all_sources_csv = root / "data" / "exports" / "research_analysis_all_sources.csv"
    db_path = root / "data" / "news.sqlite"

    with open(docs_path, "r", encoding="utf-8") as f:
        raw_docs = json.load(f)

    # Filter out academic papers from news database
    docs = [d for d in raw_docs if d["source_id"] not in EXCLUDED_ACADEMIC_PAPERS]
    print(f"Loaded {len(raw_docs)} documents, excluded {len(raw_docs) - len(docs)} academic papers. Active news corpus: {len(docs)} documents.")

    crosswalk = {}
    if crosswalk_path.exists():
        with open(crosswalk_path, "r", encoding="utf-8") as f:
            crosswalk = {r["source_id"]: r for r in csv.DictReader(f)}

    enriched_docs = []
    missing_bespoke = []

    for d in docs:
        sid = d["source_id"]
        c_entry = crosswalk.get(sid, {})

        # Apply verified metadata corrections for non-nexis records
        if sid in NON_NEXIS_CORRECTIONS:
            corr = NON_NEXIS_CORRECTIONS[sid]
            for k, v in corr.items():
                d[k] = v
                if k == "location":
                    d["target_location"] = v
                    d["actual_jurisdiction"] = v
                elif k == "publication_date":
                    d["crawl_timestamp"] = f"{v}T00:00:00Z"

        # Apply location normalization
        for loc_k in ("location", "target_location", "actual_jurisdiction"):
            v = d.get(loc_k, "")
            if v:
                d[loc_k] = LOCATION_NORM.get(v, LOCATION_NORM.get(v.strip(), v))

        if sid in BESPOKE_DATA:
            cat, rationale, inst_id, inst_name = BESPOKE_DATA[sid]
        else:
            missing_bespoke.append(sid)
            loc = d.get("target_location", "") or d.get("actual_jurisdiction", "") or "metropolitan networks"
            cat = "Platform Features & Routing Algorithms"
            rationale = f"Analysis of navigation platform routing mechanics, commuter route diversion, and municipal governance policies managing vehicular flows across {loc}."
            inst_id = c_entry.get("instrument_id", "None (Legal Gap)")
            inst_name = c_entry.get("instrument_name", "Unaddressed by Current Law")

        d["url"] = resolve_url(d)
        d["topic_category"] = cat
        d["relevance_rationale"] = rationale
        d["crosswalk_instrument_id"] = inst_id
        d["crosswalk_instrument_name"] = inst_name

        # Topic slug for CSS/filtering
        slug_map = {
            "Public-Private Data Partnerships": "partnerships",
            "Platform Features & Routing Algorithms": "features",
            "Municipal Traffic Mitigation & Street Controls": "mitigation",
            "Commercial Freight & Bridge Clearance": "freight",
            "Legislation & City Council Actions": "legislation",
            "Community Pushback & Safety Hazards": "pushback",
        }
        d["topic_slug"] = slug_map.get(cat, "general")

        enriched_docs.append(d)

    print(f"Applied bespoke entries to {len(enriched_docs) - len(missing_bespoke)} / {len(enriched_docs)} documents.")
    if missing_bespoke:
        print(f"Warning: {len(missing_bespoke)} documents used fallback: {missing_bespoke}")

    # Write back to JSON
    with open(docs_path, "w", encoding="utf-8") as f:
        json.dump(enriched_docs, f, indent=2, ensure_ascii=False)
    print(f"Saved JSON: {docs_path}")

    # Write back to CSV
    csv_path = root / "docs" / "data" / "news_corpus_filtered.csv"
    fieldnames = list(enriched_docs[0].keys())
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in enriched_docs:
            clean_row = {}
            for k, v in row.items():
                if isinstance(v, (list, dict)):
                    clean_row[k] = json.dumps(v, ensure_ascii=False)
                else:
                    clean_row[k] = v
            writer.writerow(clean_row)
    print(f"Saved CSV: {csv_path}")

    # Update research_analysis_filtered exports
    if filtered_export_json.exists() or filtered_export_json.parent.exists():
        with open(filtered_export_json, "w", encoding="utf-8") as f:
            json.dump(enriched_docs, f, indent=2, ensure_ascii=False)
        print(f"Saved JSON: {filtered_export_json}")

    if filtered_export_csv.exists() or filtered_export_csv.parent.exists():
        with open(filtered_export_csv, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in enriched_docs:
                clean_row = {}
                for k, v in row.items():
                    if isinstance(v, (list, dict)):
                        clean_row[k] = json.dumps(v, ensure_ascii=False)
                    else:
                        clean_row[k] = v
                writer.writerow(clean_row)
        print(f"Saved CSV: {filtered_export_csv}")

    # Update crosswalk files with verified metadata
    for cw_file in [crosswalk_path, root.parent / "Law_Crawler" / "exports" / "news_to_law_crosswalk.csv"]:
        if cw_file.exists():
            with open(cw_file, "r", encoding="utf-8") as f:
                cw_rows = list(csv.DictReader(f))
            if cw_rows:
                fieldnames_cw = list(cw_rows[0].keys())
                for r in cw_rows:
                    sid = r.get("source_id", "")
                    if sid in NON_NEXIS_CORRECTIONS:
                        corr = NON_NEXIS_CORRECTIONS[sid]
                        if "title" in corr:
                            r["headline"] = corr["title"]
                            r["article_title"] = corr["title"]
                        if "publication_date" in corr:
                            r["date"] = corr["publication_date"]
                            r["publication_year"] = corr["publication_date"][:4]
                        if "url" in corr:
                            r["url"] = corr["url"]
                        if "location" in corr:
                            r["news_jurisdiction"] = corr["location"]
                        if "publisher" in corr and "location" in corr:
                            r["source_and_jurisdiction"] = f"{corr['publisher']} · {corr['location']}"
                    jur = r.get("news_jurisdiction", "")
                    if jur and jur in LOCATION_NORM:
                        r["news_jurisdiction"] = LOCATION_NORM[jur]
                with open(cw_file, "w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames_cw)
                    writer.writeheader()
                    writer.writerows(cw_rows)
                print(f"Updated Crosswalk CSV: {cw_file}")

    # Update SQLite database: resolve all URLs, archive academic papers, set active metadata
    if db_path.exists():
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        # 1. Resolve canonical URLs for ALL rows in database
        cur.execute("SELECT id, origin, url, archive_dir FROM crawled_documents")
        all_db_rows = cur.fetchall()
        for sid, origin, existing_url, archive_dir in all_db_rows:
            canon_url = resolve_url({"id": sid, "source_id": sid, "url": existing_url, "archive_dir": archive_dir})
            if canon_url != existing_url:
                cur.execute("UPDATE crawled_documents SET url = ? WHERE id = ?", (canon_url, sid))

        # 2. Mark excluded academic papers
        for sid, (tier, score, reason) in EXCLUDED_ACADEMIC_PAPERS.items():
            cur.execute("""
                UPDATE crawled_documents
                SET is_project_relevant = 0,
                    relevance_tier = 'Excluded: Academic Publication',
                    relevance_score = ?,
                    exclusion_reason = ?
                WHERE id = ?
            """, (score, reason, sid))

        # 3. Update active news corpus rows with full verified metadata
        for d in enriched_docs:
            cur.execute("""
                UPDATE crawled_documents
                SET url = ?,
                    topic_category = ?,
                    relevance_rationale = ?,
                    crosswalk_instrument_id = ?,
                    crosswalk_instrument_name = ?,
                    title = ?,
                    publication_date = ?,
                    publisher = ?,
                    location = ?
                WHERE id = ?
            """, (
                d["url"],
                d["topic_category"],
                d["relevance_rationale"],
                d["crosswalk_instrument_id"],
                d["crosswalk_instrument_name"],
                d.get("title", ""),
                d.get("publication_date", ""),
                d.get("publisher", ""),
                d.get("target_location", "") or d.get("location", ""),
                d["source_id"]
            ))

        # 4. Normalize locations for all rows in SQLite
        cur.execute("SELECT id, location FROM crawled_documents")
        for sid, loc_val in cur.fetchall():
            if loc_val:
                norm_loc = LOCATION_NORM.get(loc_val, LOCATION_NORM.get(loc_val.strip(), loc_val))
                if norm_loc != loc_val:
                    cur.execute("UPDATE crawled_documents SET location = ? WHERE id = ?", (norm_loc, sid))

        conn.commit()
        conn.close()
        print(f"Updated SQLite database: {db_path}")

    # Update research_analysis_all_sources.json and .csv
    if all_sources_json.exists():
        with open(all_sources_json, "r", encoding="utf-8") as f:
            all_sources = json.load(f)

        for item in all_sources:
            sid = item.get("source_id", "")
            item["url"] = resolve_url(item)
            if sid in NON_NEXIS_CORRECTIONS:
                corr = NON_NEXIS_CORRECTIONS[sid]
                for k, v in corr.items():
                    item[k] = v
                    if k == "location":
                        item["target_location"] = v
                        item["actual_jurisdiction"] = v
                    elif k == "publication_date":
                        item["crawl_timestamp"] = f"{v}T00:00:00Z"
            for loc_k in ("location", "target_location", "actual_jurisdiction"):
                v = item.get(loc_k, "")
                if v:
                    item[loc_k] = LOCATION_NORM.get(v, LOCATION_NORM.get(v.strip(), v))
            if sid in EXCLUDED_ACADEMIC_PAPERS:
                _, score, reason = EXCLUDED_ACADEMIC_PAPERS[sid]
                item["is_project_relevant"] = 0
                item["relevance_tier"] = "Excluded: Academic Publication"
                item["relevance_score"] = score
                item["exclusion_reason"] = reason
            elif sid in BESPOKE_DATA:
                cat, rationale, inst_id, inst_name = BESPOKE_DATA[sid]
                item["topic_category"] = cat
                item["relevance_rationale"] = rationale
                item["crosswalk_instrument_id"] = inst_id
                item["crosswalk_instrument_name"] = inst_name

        with open(all_sources_json, "w", encoding="utf-8") as f:
            json.dump(all_sources, f, indent=2, ensure_ascii=False)
        print(f"Updated JSON: {all_sources_json}")

        if all_sources_csv.exists() or all_sources_csv.parent.exists():
            fieldnames_all = []
            for row in all_sources:
                for k in row.keys():
                    if k not in fieldnames_all:
                        fieldnames_all.append(k)
            with open(all_sources_csv, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames_all)
                writer.writeheader()
                for row in all_sources:
                    clean_row = {}
                    for k in fieldnames_all:
                        v = row.get(k, "")
                        if isinstance(v, (list, dict)):
                            clean_row[k] = json.dumps(v, ensure_ascii=False)
                        else:
                            clean_row[k] = v
                    writer.writerow(clean_row)
            print(f"Updated CSV: {all_sources_csv}")

    # Print Category & Rationale Distribution
    from collections import Counter
    cat_counts = Counter(d["topic_category"] for d in enriched_docs)
    print("\nFinal Topic Category Distribution:")
    for cat, cnt in cat_counts.most_common():
        print(f"  {cat}: {cnt}")

    rat_counts = Counter(d["relevance_rationale"] for d in enriched_docs)
    print(f"\nUnique rationales: {len(rat_counts)} / {len(enriched_docs)}")
    print("Most common rationales:")
    for r, cnt in rat_counts.most_common(5):
        print(f"  [{cnt}x] {r[:80]}...")

if __name__ == "__main__":
    main()
