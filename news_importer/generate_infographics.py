"""Generate dynamic, interactive research infographics and map dashboard from research analysis dataset."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

# Geographic coordinates lookup for U.S. target locations (all localized cities, counties, and states)
COORDINATES_MAP: dict[str, dict[str, float | str]] = {
    # Cities
    "Los Angeles": {"lat": 34.0522, "lon": -118.2437, "name": "Los Angeles, CA"},
    "Los Angeles, Ca": {"lat": 34.0522, "lon": -118.2437, "name": "Los Angeles, CA"},
    "Los Angeles, CA": {"lat": 34.0522, "lon": -118.2437, "name": "Los Angeles, CA"},
    "San Francisco": {"lat": 37.7749, "lon": -122.4194, "name": "San Francisco, CA"},
    "San Francisco, Ca": {"lat": 37.7749, "lon": -122.4194, "name": "San Francisco, CA"},
    "San Francisco Bay Area, Ca": {"lat": 37.7749, "lon": -122.4194, "name": "San Francisco, CA"},
    "San Francisco County": {"lat": 37.7749, "lon": -122.4194, "name": "San Francisco, CA"},
    "Seattle": {"lat": 47.6062, "lon": -122.3321, "name": "Seattle, WA"},
    "Boston": {"lat": 42.3601, "lon": -71.0589, "name": "Boston, MA"},
    "Boston, Ma": {"lat": 42.3601, "lon": -71.0589, "name": "Boston, MA"},
    "Boston, MA": {"lat": 42.3601, "lon": -71.0589, "name": "Boston, MA"},
    "Chicago": {"lat": 41.8781, "lon": -87.6298, "name": "Chicago, IL"},
    "Chicago, Il": {"lat": 41.8781, "lon": -87.6298, "name": "Chicago, IL"},
    "New York": {"lat": 40.7128, "lon": -74.0060, "name": "New York City, NY"},
    "New York, Ny": {"lat": 40.7128, "lon": -74.0060, "name": "New York City, NY"},
    "New York City, Ny": {"lat": 40.7128, "lon": -74.0060, "name": "New York City, NY"},
    "Leonia": {"lat": 40.8654, "lon": -73.9876, "name": "Leonia, NJ"},
    "Mantoloking": {"lat": 40.0387, "lon": -74.0526, "name": "Mantoloking, NJ"},
    "Newark, Nj": {"lat": 40.7357, "lon": -74.1724, "name": "Newark, NJ"},
    "Atlanta": {"lat": 33.7490, "lon": -84.3880, "name": "Atlanta, GA"},
    "Atlanta, Ga": {"lat": 33.7490, "lon": -84.3880, "name": "Atlanta, GA"},
    "Atlanta, GA": {"lat": 33.7490, "lon": -84.3880, "name": "Atlanta, GA"},
    "Austin": {"lat": 30.2672, "lon": -97.7431, "name": "Austin, TX"},
    "Austin, Tx": {"lat": 30.2672, "lon": -97.7431, "name": "Austin, TX"},
    "Austin, TX": {"lat": 30.2672, "lon": -97.7431, "name": "Austin, TX"},
    "Arlington, TX": {"lat": 32.7357, "lon": -97.1081, "name": "Arlington, TX"},
    "Arlington, Tx": {"lat": 32.7357, "lon": -97.1081, "name": "Arlington, TX"},
    "Dallas, Tx": {"lat": 32.7767, "lon": -96.7970, "name": "Dallas, TX"},
    "Fort Worth, Tx": {"lat": 32.7555, "lon": -97.3308, "name": "Fort Worth, TX"},
    "Fort Worth": {"lat": 32.7555, "lon": -97.3308, "name": "Fort Worth, TX"},
    "Houston, Tx": {"lat": 29.7604, "lon": -95.3698, "name": "Houston, TX"},
    "San Antonio, Tx": {"lat": 29.4241, "lon": -98.4936, "name": "San Antonio, TX"},
    "Miami": {"lat": 25.7617, "lon": -80.1918, "name": "Miami, FL"},
    "Miami, Fl": {"lat": 25.7617, "lon": -80.1918, "name": "Miami, FL"},
    "Coral Gables": {"lat": 25.7215, "lon": -80.2684, "name": "Coral Gables, FL"},
    "Jacksonville, Fl": {"lat": 30.3322, "lon": -81.6557, "name": "Jacksonville, FL"},
    "Tampa, Fl": {"lat": 27.9506, "lon": -82.4572, "name": "Tampa, FL"},
    "Detroit": {"lat": 42.3314, "lon": -83.0458, "name": "Detroit, MI"},
    "Detroit, Mi": {"lat": 42.3314, "lon": -83.0458, "name": "Detroit, MI"},
    "Portland, Or": {"lat": 45.5152, "lon": -122.6784, "name": "Portland, OR"},
    "Philadelphia": {"lat": 39.9526, "lon": -75.1652, "name": "Philadelphia, PA"},
    "Philadelphia, Pa": {"lat": 39.9526, "lon": -75.1652, "name": "Philadelphia, PA"},
    "Pittsburgh, PA": {"lat": 40.4406, "lon": -79.9959, "name": "Pittsburgh, PA"},
    "Pittsburgh, Pa": {"lat": 40.4406, "lon": -79.9959, "name": "Pittsburgh, PA"},
    "Lancaster, Pa": {"lat": 40.0379, "lon": -76.3055, "name": "Lancaster, PA"},
    "Charlotte, Nc": {"lat": 35.2271, "lon": -80.8431, "name": "Charlotte, NC"},
    "Raleigh, Nc": {"lat": 35.7796, "lon": -78.6382, "name": "Raleigh, NC"},
    "Cary, Nc": {"lat": 35.7915, "lon": -78.7811, "name": "Cary, NC"},
    "Asheville, Nc": {"lat": 35.5951, "lon": -82.5515, "name": "Asheville, NC"},
    "Greensboro, Nc": {"lat": 36.0726, "lon": -79.7920, "name": "Greensboro, NC"},
    "Greensboro, NC": {"lat": 36.0726, "lon": -79.7920, "name": "Greensboro, NC"},
    "Norfolk": {"lat": 36.8508, "lon": -76.2859, "name": "Norfolk, VA"},
    "Norfolk, VA": {"lat": 36.8508, "lon": -76.2859, "name": "Norfolk, VA"},
    "Virginia Beach, Va": {"lat": 36.8529, "lon": -75.9780, "name": "Virginia Beach, VA"},
    "Virginia Beach, VA": {"lat": 36.8529, "lon": -75.9780, "name": "Virginia Beach, VA"},
    "Phoenix, Az": {"lat": 33.4484, "lon": -112.0740, "name": "Phoenix, AZ"},
    "Salt Lake City": {"lat": 40.7608, "lon": -111.8910, "name": "Salt Lake City, UT"},
    "Salt Lake City, Ut": {"lat": 40.7608, "lon": -111.8910, "name": "Salt Lake City, UT"},
    "Des Moines, Ia": {"lat": 41.5868, "lon": -93.6250, "name": "Des Moines, IA"},
    "New Haven, Ct": {"lat": 41.3083, "lon": -72.9279, "name": "New Haven, CT"},
    "Fairfield, Ct": {"lat": 41.1412, "lon": -73.2637, "name": "Fairfield, CT"},
    "Augusta, Me": {"lat": 44.3106, "lon": -69.7795, "name": "Augusta, ME"},
    "Naperville": {"lat": 41.7508, "lon": -88.1535, "name": "Naperville, IL"},
    "Evanston": {"lat": 42.0451, "lon": -87.6877, "name": "Evanston, IL"},
    "Davis, CA": {"lat": 38.5449, "lon": -121.7405, "name": "Davis, CA"},
    "Davis, Ca": {"lat": 38.5449, "lon": -121.7405, "name": "Davis, CA"},
    "Sacramento, CA": {"lat": 38.5816, "lon": -121.4944, "name": "Sacramento, CA"},
    "Baton Rouge, LA": {"lat": 30.4515, "lon": -91.1871, "name": "Baton Rouge, LA"},
    "Knoxville, TN": {"lat": 35.9606, "lon": -83.9207, "name": "Knoxville, TN"},
    "Carson City, Nv": {"lat": 39.1638, "lon": -119.7674, "name": "Carson City, NV"},
    "Colorado Springs, Co": {"lat": 38.8339, "lon": -104.8214, "name": "Colorado Springs, CO"},
    "Providence, Ri": {"lat": 41.8240, "lon": -71.4128, "name": "Providence, RI"},
    "Washington Dc": {"lat": 38.9072, "lon": -77.0369, "name": "Washington, DC"},
    "Anchorage, Ak": {"lat": 61.2181, "lon": -149.9003, "name": "Anchorage, AK"},
    # Counties
    "Loudoun County": {"lat": 39.0840, "lon": -77.6412, "name": "Loudoun County, VA"},
    "Fulton County": {"lat": 33.7903, "lon": -84.4677, "name": "Fulton County, GA"},
    "Miami-Dade County": {"lat": 25.5516, "lon": -80.6327, "name": "Miami-Dade County, FL"},
    # States
    "California": {"lat": 36.7783, "lon": -119.4179, "name": "California (State)"},
    "Connecticut": {"lat": 41.6032, "lon": -73.0877, "name": "Connecticut (State)"},
    "Texas": {"lat": 31.9686, "lon": -99.9018, "name": "Texas (State)"},
    "Illinois": {"lat": 40.6331, "lon": -89.3985, "name": "Illinois (State)"},
    "Georgia": {"lat": 32.1656, "lon": -82.9001, "name": "Georgia (State)"},
    "Pennsylvania": {"lat": 41.2033, "lon": -77.1945, "name": "Pennsylvania (State)"},
    "Florida": {"lat": 27.6648, "lon": -81.5158, "name": "Florida (State)"},
    "New Jersey": {"lat": 40.0583, "lon": -74.4057, "name": "New Jersey (State)"},
    "Virginia": {"lat": 37.4316, "lon": -78.6569, "name": "Virginia (State)"},
    "Iowa": {"lat": 41.8780, "lon": -93.0977, "name": "Iowa (State)"},
    "Maine": {"lat": 45.2538, "lon": -69.4455, "name": "Maine (State)"},
    "Massachusetts": {"lat": 42.4072, "lon": -71.3824, "name": "Massachusetts (State)"},
    "Utah": {"lat": 39.3210, "lon": -111.0937, "name": "Utah (State)"},
    "Nevada": {"lat": 38.8026, "lon": -116.4194, "name": "Nevada (State)"},
    "North Carolina": {"lat": 35.7596, "lon": -79.0193, "name": "North Carolina (State)"},
    "Wyoming": {"lat": 43.0759, "lon": -107.2903, "name": "Wyoming (State)"},
    "Colorado": {"lat": 39.5501, "lon": -105.7821, "name": "Colorado (State)"},
    "Alaska": {"lat": 64.2008, "lon": -149.4937, "name": "Alaska (State)"},
    "Arizona": {"lat": 34.0489, "lon": -111.0937, "name": "Arizona (State)"},
    "Idaho": {"lat": 44.0682, "lon": -114.7420, "name": "Idaho (State)"},
    "Kansas": {"lat": 39.0119, "lon": -98.4842, "name": "Kansas (State)"},
    "Maryland": {"lat": 39.0458, "lon": -76.6413, "name": "Maryland (State)"},
    "Michigan": {"lat": 44.3148, "lon": -85.6024, "name": "Michigan (State)"},
    "Minnesota": {"lat": 46.7296, "lon": -94.6859, "name": "Minnesota (State)"},
    "Missouri": {"lat": 37.9643, "lon": -91.8318, "name": "Missouri (State)"},
    "Montana": {"lat": 46.8797, "lon": -110.3626, "name": "Montana (State)"},
    "Nebraska": {"lat": 41.4925, "lon": -99.9018, "name": "Nebraska (State)"},
    "New Hampshire": {"lat": 43.1939, "lon": -71.5724, "name": "New Hampshire (State)"},
    "New Mexico": {"lat": 34.5199, "lon": -105.8701, "name": "New Mexico (State)"},
    "Ohio": {"lat": 40.4173, "lon": -82.9071, "name": "Ohio (State)"},
    "Oklahoma": {"lat": 35.0078, "lon": -97.0929, "name": "Oklahoma (State)"},
    "Tennessee": {"lat": 35.5175, "lon": -86.5804, "name": "Tennessee (State)"},
    "Vermont": {"lat": 44.5588, "lon": -72.5778, "name": "Vermont (State)"},
    "District Of Columbia": {"lat": 38.9072, "lon": -77.0369, "name": "District of Columbia"},
    # Additional Coded Cities
    "Albany, Ny": {"lat": 42.6526, "lon": -73.7562, "name": "Albany, NY"},
    "Albuquerque, Nm": {"lat": 35.0844, "lon": -106.6504, "name": "Albuquerque, NM"},
    "Amarillo, Tx": {"lat": 35.2220, "lon": -101.8313, "name": "Amarillo, TX"},
    "Baltimore, Md": {"lat": 39.2904, "lon": -76.6122, "name": "Baltimore, MD"},
    "Boise, Id": {"lat": 43.6150, "lon": -116.2023, "name": "Boise, ID"},
    "Bridgeport, Ct": {"lat": 41.1792, "lon": -73.1894, "name": "Bridgeport, CT"},
    "Columbus, Oh": {"lat": 39.9612, "lon": -82.9988, "name": "Columbus, OH"},
    "Davenport, Ia": {"lat": 41.5236, "lon": -90.5776, "name": "Davenport, IA"},
    "Denver, Co": {"lat": 39.7392, "lon": -104.9903, "name": "Denver, CO"},
    "Dover, De": {"lat": 39.1582, "lon": -75.5244, "name": "Dover, DE"},
    "Fresno, Ca": {"lat": 36.7468, "lon": -119.7726, "name": "Fresno, CA"},
    "Harrisburg, Pa": {"lat": 40.2732, "lon": -76.8867, "name": "Harrisburg, PA"},
    "Hartford, Ct": {"lat": 41.7658, "lon": -72.6734, "name": "Hartford, CT"},
    "Kansas City, Mo": {"lat": 39.0997, "lon": -94.5786, "name": "Kansas City, MO"},
    "Lexington, Ky": {"lat": 38.0406, "lon": -84.5037, "name": "Lexington, KY"},
    "Lincoln, Ne": {"lat": 40.8136, "lon": -96.7026, "name": "Lincoln, NE"},
    "Louisville, Ky": {"lat": 38.2527, "lon": -85.7585, "name": "Louisville, KY"},
    "Midland, Mi": {"lat": 43.6156, "lon": -84.2472, "name": "Midland, MI"},
    "Milwaukee, Wi": {"lat": 43.0389, "lon": -87.9065, "name": "Milwaukee, WI"},
    "Montgomery, Al": {"lat": 32.3792, "lon": -86.3077, "name": "Montgomery, AL"},
    "Oakland, Ca": {"lat": 37.8044, "lon": -122.2712, "name": "Oakland, CA"},
    "Reno, Nv": {"lat": 39.5296, "lon": -119.8138, "name": "Reno, NV"},
    "Richmond, Va": {"lat": 37.5407, "lon": -77.4360, "name": "Richmond, VA"},
    "Saint Louis, Mo": {"lat": 38.6270, "lon": -90.1994, "name": "Saint Louis, MO"},
    "Saint Paul, Mn": {"lat": 44.9537, "lon": -93.0900, "name": "Saint Paul, MN"},
    "San Diego, Ca": {"lat": 32.7157, "lon": -117.1611, "name": "San Diego, CA"},
    "San Jose, Ca": {"lat": 37.3382, "lon": -121.8863, "name": "San Jose, CA"},
    "Santa Fe, Nm": {"lat": 35.6870, "lon": -105.9378, "name": "Santa Fe, NM"},
    "Silicon Valley, Ca": {"lat": 37.3861, "lon": -122.0839, "name": "Silicon Valley, CA"},
    "Sioux Falls, Sd": {"lat": 43.5460, "lon": -96.7313, "name": "Sioux Falls, SD"},
    "Spokane, Wa": {"lat": 47.6588, "lon": -117.4260, "name": "Spokane, WA"},
    "Springfield, Il": {"lat": 39.7817, "lon": -89.6501, "name": "Springfield, IL"},
    "Tallahassee, Fl": {"lat": 30.4383, "lon": -84.2807, "name": "Tallahassee, FL"},
    "Toledo, Oh": {"lat": 41.6528, "lon": -83.5379, "name": "Toledo, OH"},
    "Trenton, Nj": {"lat": 40.2206, "lon": -74.7597, "name": "Trenton, NJ"},
    "Washington, Washington": {"lat": 47.7511, "lon": -120.7401, "name": "Washington (State)"},
    # Multi-City Consortium
    "San Francisco, Los Angeles, Phoenix, Austin, Atlanta": {"lat": 34.0522, "lon": -118.2437, "name": "Multi-City AV Pilot"},
    "San Francisco Bay Area, Los Angeles, Phoenix, Austin, Atlanta": {"lat": 34.0522, "lon": -118.2437, "name": "Multi-City AV Pilot"},
    "Atlanta, Boston, Chicago, Los Angeles, Miami, New York, Philadelphia, Salt Lake City, San Francisco, Seattle": {"lat": 39.8283, "lon": -98.5795, "name": "Multi-City Metro Cohort"},
    "Boston, Los Angeles County, Miami, New York City, Pittsburgh; Florida, Utah, Kentucky": {"lat": 39.8283, "lon": -98.5795, "name": "Multi-City Metro Cohort"},
    "Las Vegas, NV (Southern Nevada), Tampa, FL, Delaware": {"lat": 36.1699, "lon": -115.1398, "name": "Multi-City Transit Pilot"},
}

KEYWORD_AUDIT_DEFINITIONS: dict[str, list[str]] = {
    "App Brands & Platforms": [
        "Waze", "Google Maps", "Apple Maps", "MapQuest", "HERE WeGo",
        "navigation app", "navigation apps", "routing app", "routing apps",
        "GPS navigation", "navigation software", "routing software"
    ],
    "Family 1: Government Restrictions": [
        "road access", "access restriction", "access restrictions", "turn restriction",
        "turn restrictions", "turn ban", "turn bans", "road closure", "road closures",
        "street closure", "street closures", "resident only", "residents only",
        "local access only", "local traffic only", "no through traffic", "restricted road",
        "truck route", "truck restriction", "weight restriction", "height restriction",
        "traffic calming", "traffic diverter", "traffic diverters", "congestion pricing",
        "congestion charge", "low emission zone", "restricted access zone"
    ],
    "Family 2: Company Routing Rules": [
        "routing policy", "routing rule", "routing algorithm", "routing algorithms",
        "routing criteria", "routing preference", "route preference", "route selection",
        "route optimization", "routing change", "routing update", "avoid tolls",
        "avoid highways", "avoid freeways", "avoid unpaved roads", "avoid residential streets",
        "avoid local roads", "avoid neighborhoods", "eco-friendly routing", "fuel-efficient routing",
        "safer route", "road eligibility"
    ],
    "Family 3: Government-Company Coordination": [
        "Waze for Cities", "Connected Citizens Program", "partnership", "data sharing",
        "data exchange", "road closure reporting", "map correction", "map corrections",
        "routing request", "routing requests"
    ],
    "Governing Level Keywords": [
        "U.S. Department of Transportation", "Federal Highway Administration",
        "state legislature", "state transportation department", "regional authority",
        "metropolitan planning organization", "county commission", "board of supervisors",
        "city council", "town council", "city ordinance"
    ],
    "Community Feedback & Backlash": [
        "cut-through traffic", "through traffic", "shortcut traffic", "rat running",
        "residential streets", "neighborhood traffic", "traffic diversion", "rerouted traffic",
        "complaint", "complaints", "backlash", "petition", "public comment", "pedestrian safety"
    ]
}


def build_infographic_dataset(input_json_path: Path) -> dict:
    """Read research analysis json and construct processed metrics for dynamic infographics."""
    raw_data = json.loads(input_json_path.read_text(encoding="utf-8"))

    # Localized geographic entities only (Cities, Counties, States)
    locations_dict: dict[str, dict] = defaultdict(lambda: {
        "name": "",
        "lat": 0.0,
        "lon": 0.0,
        "count": 0,
        "years": Counter(),
        "gov_levels": Counter(),
        "categories": Counter(),
        "articles": []
    })

    # Federal & Nationwide policies (Macro / USDOT / Platform-wide features across all 50 states)
    nationwide_articles: list[dict] = []
    nationwide_years: Counter[str] = Counter()
    nationwide_gov: Counter[str] = Counter()
    nationwide_categories: Counter[str] = Counter()

    year_counts: Counter[str] = Counter()
    gov_counts: Counter[str] = Counter()
    loc_type_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()

    corpus_text = []

    for item in raw_data:
        raw_loc = item.get("target_location", "").strip()
        pub_date = item.get("publication_date", "")
        year = pub_date[:4] if pub_date else "2024"
        if not (year.isdigit() and len(year) == 4):
            year = "2024"

        gov = item.get("governing_level", "Company")
        cat = item.get("category", "Experimented Measures")
        loc_type = item.get("target_location_type", "City")
        title = item.get("title", "")
        summary = item.get("factual_summary", "")

        year_counts[year] += 1
        gov_counts[gov] += 1
        loc_type_counts[loc_type] += 1
        category_counts[cat] += 1

        article_obj = {
            "title": title,
            "year": year,
            "gov": gov,
            "category": cat,
            "authority": item.get("authority_names", ""),
            "summary": summary[:160] + ("..." if len(summary) > 160 else ""),
            "location": raw_loc,
            "location_type": loc_type,
        }

        # Check if genuinely nationwide or federal macro scope
        is_nationwide = (
            raw_loc.lower() in ("united states", "us", "usa", "global")
            or loc_type.lower() in ("country", "federal")
            or "multi-city" in raw_loc.lower()
        )

        if is_nationwide:
            nationwide_articles.append(article_obj)
            nationwide_years[year] += 1
            nationwide_gov[gov] += 1
            nationwide_categories[cat] += 1
        else:
            geo = COORDINATES_MAP.get(raw_loc)
            if not geo:
                # Try matching by state or city substring
                for k, v in COORDINATES_MAP.items():
                    if k.lower() in raw_loc.lower() or raw_loc.lower() in k.lower():
                        geo = v
                        break
            if not geo:
                geo = {"lat": 38.0, "lon": -97.0, "name": raw_loc}

            cname = str(geo["name"])
            loc_entry = locations_dict[cname]
            loc_entry["name"] = cname
            loc_entry["lat"] = float(geo["lat"])
            loc_entry["lon"] = float(geo["lon"])
            loc_entry["count"] += 1
            loc_entry["years"][year] += 1
            loc_entry["gov_levels"][gov] += 1
            loc_entry["categories"][cat] += 1
            loc_entry["articles"].append(article_obj)

        corpus_text.append(f"{title} {summary} {item.get('supporting_passage', '')} {item.get('authority_names', '')}".lower())

    # Keyword audit computation
    keyword_audit: dict[str, dict] = {}
    for fam_name, kw_list in KEYWORD_AUDIT_DEFINITIONS.items():
        used = []
        unused = []
        for kw in kw_list:
            cnt = sum(1 for art in corpus_text if kw.lower() in art)
            if cnt > 0:
                used.append({"keyword": kw, "count": cnt})
            else:
                unused.append(kw)
        used.sort(key=lambda x: x["count"], reverse=True)
        keyword_audit[fam_name] = {
            "used": used,
            "unused": unused,
            "used_count": len(used),
            "total_count": len(kw_list),
            "coverage_pct": round((len(used) / len(kw_list)) * 100, 1)
        }

    # Format localized locations for JSON serialization
    serialized_locations = []
    for loc_name, loc_info in sorted(locations_dict.items(), key=lambda x: x[1]["count"], reverse=True):
        serialized_locations.append({
            "name": loc_name,
            "lat": loc_info["lat"],
            "lon": loc_info["lon"],
            "total_count": loc_info["count"],
            "years": dict(loc_info["years"]),
            "gov_levels": dict(loc_info["gov_levels"]),
            "categories": dict(loc_info["categories"]),
            "articles": loc_info["articles"]
        })

    all_years = sorted(list(year_counts.keys()))

    return {
        "metadata": {
            "total_sources": len(raw_data),
            "localized_sources": len(raw_data) - len(nationwide_articles),
            "nationwide_sources": len(nationwide_articles),
            "unique_locations": len(serialized_locations),
            "year_range": f"{all_years[0]} - {all_years[-1]}" if all_years else "N/A",
            "year_counts": dict(sorted(year_counts.items())),
            "gov_counts": dict(sorted(gov_counts.items(), key=lambda x: x[1], reverse=True)),
            "loc_type_counts": dict(sorted(loc_type_counts.items(), key=lambda x: x[1], reverse=True)),
            "category_counts": dict(sorted(category_counts.items(), key=lambda x: x[1], reverse=True)),
        },
        "all_years": all_years,
        "locations": serialized_locations,
        "nationwide": {
            "name": "United States (Federal & Nationwide Scope)",
            "total_count": len(nationwide_articles),
            "years": dict(nationwide_years),
            "gov_levels": dict(nationwide_gov),
            "categories": dict(nationwide_categories),
            "articles": nationwide_articles,
        },
        "keyword_audit": keyword_audit,
    }


def render_keyword_audit_cards(keyword_audit: dict) -> str:
    cards = []
    family_colors = {
        "App Brands & Platforms": ("text-blue-400", "bg-blue-500/10", "border-blue-500/20"),
        "Family 1: Government Restrictions": ("text-amber-400", "bg-amber-500/10", "border-amber-500/20"),
        "Family 2: Company Routing Rules": ("text-rose-400", "bg-rose-500/10", "border-rose-500/20"),
        "Family 3: Government-Company Coordination": ("text-purple-400", "bg-purple-500/10", "border-purple-500/20"),
        "Governing Level Keywords": ("text-cyan-400", "bg-cyan-500/10", "border-cyan-500/20"),
        "Community Feedback & Backlash": ("text-orange-400", "bg-orange-500/10", "border-orange-500/20"),
    }
    family_insights = {
        "App Brands & Platforms": "Journalists and public agencies predominantly name 'Waze' and 'Google Maps' directly, with 'navigation app' serving as the formal terminology.",
        "Family 1: Government Restrictions": "Road closures and emergency diversions are widely documented, with growing municipal coverage of turn restrictions, truck routes, and traffic calming.",
        "Family 2: Company Routing Rules": "Recent platform shifts feature algorithmic avoidance preferences (avoid tolls, avoid highways) and fuel-efficient eco-routing.",
        "Family 3: Government-Company Coordination": "Formal bilateral frameworks like Connected Citizens Program and Waze for Cities dominate municipal data exchange reporting.",
        "Governing Level Keywords": "City councils represent the primary legislative forum for residential traffic disputes, followed by state legislative hands-free and camera bills.",
        "Community Feedback & Backlash": "Neighborhood cut-through traffic, shortcut rat-running, and pedestrian safety petitions are the primary drivers of public outcry.",
    }
    for fam_name, audit in keyword_audit.items():
        used = audit["used"]
        unused = audit["unused"]
        color_class, badge_bg, badge_border = family_colors.get(fam_name, ("text-blue-400", "bg-blue-500/10", "border-blue-500/20"))
        insight = family_insights.get(fam_name, "")

        used_spans = "".join([
            f'<span class="{badge_bg} {color_class} px-2 py-0.5 rounded border {badge_border}">{item["keyword"]} ({item["count"]} hits)</span> '
            for item in used[:8]
        ]) if used else '<span class="text-slate-500 text-xs">No active terms in current subset</span>'

        unused_spans = "".join([
            f'<span class="bg-slate-900 px-2 py-0.5 rounded border border-slate-800">{kw}</span> '
            for kw in unused[:12]
        ]) if unused else '<span class="text-emerald-400 text-xs">All taxonomy keywords active</span>'

        card = f"""
        <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-5 space-y-3">
          <div class="flex items-center justify-between pb-2 border-b border-slate-800">
            <h4 class="font-bold text-white text-sm">{fam_name}</h4>
            <span class="text-xs {color_class} font-medium">{audit["used_count"]} Active / {len(unused)} Zero Hits</span>
          </div>
          <div>
            <div class="text-xs font-semibold text-emerald-400 mb-1.5">Dominant Active Terms in Corpus:</div>
            <div class="flex flex-wrap gap-1.5 text-xs">
              {used_spans}
            </div>
          </div>
          <div>
            <div class="text-xs font-semibold text-rose-400 mb-1.5">Zero Hits / Unused Terms in Taxonomy:</div>
            <div class="flex flex-wrap gap-1.5 text-[11px] text-slate-400 font-mono max-h-24 overflow-y-auto">
              {unused_spans}
            </div>
            {f'<p class="text-[11px] text-slate-500 mt-2">{insight}</p>' if insight else ''}
          </div>
        </div>
        """
        cards.append(card)
    return "\n".join(cards)


def generate_html_infographics(data_payload: dict) -> str:
    """Generate self-contained HTML/Tailwind CSS interactive dashboard with SVG Map & Timeline Slider."""
    json_str = json.dumps(data_payload)
    meta = data_payload["metadata"]
    total_sources = meta["total_sources"]
    localized_sources = meta["localized_sources"]
    nationwide_sources = meta["nationwide_sources"]
    unique_locations = meta["unique_locations"]
    year_range = meta["year_range"]
    gov_counts = meta["gov_counts"]
    top_gov = list(gov_counts.keys())[0] if gov_counts else "Company"
    top_gov_pct = round((gov_counts[top_gov] / total_sources) * 100) if total_sources else 0
    keyword_audit_html = render_keyword_audit_cards(data_payload["keyword_audit"])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Navigation & Routing Policy News Crawler: Interactive Research Dashboard</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
  <script src="https://cdn.jsdelivr.net/npm/topojson-client@3"></script>
  <style>
    /* Election Map County & State Styling */
    .county-path {{
      fill: #1e293b;
      stroke: #2a3a4f;
      stroke-width: 0.35px;
      cursor: pointer;
      transition: fill 0.25s ease-out, fill-opacity 0.25s ease-out, stroke 0.25s ease-out, stroke-width 0.25s ease-out;
    }}
    .county-path:hover {{
      fill: #2d4366;
      stroke: #38bdf8 !important;
      stroke-width: 1.2px !important;
    }}
    .county-shaded-active {{
      cursor: pointer;
      filter: drop-shadow(0 0 3px rgba(0, 0, 0, 0.4));
    }}
    .county-shaded-active:hover {{
      fill-opacity: 0.95 !important;
      stroke: #ffffff !important;
      stroke-width: 2px !important;
      filter: drop-shadow(0 0 8px rgba(255, 255, 255, 0.6)) !important;
    }}
    .county-mesh {{
      fill: none;
      stroke: #2b394e;
      stroke-width: 0.35px;
      stroke-linejoin: round;
      stroke-linecap: round;
    }}
    .state-path {{
      fill: none;
      stroke: #475569;
      stroke-width: 1.2px;
      pointer-events: none;
    }}
    .state-mesh {{
      fill: none;
      stroke: #64748b;
      stroke-width: 1.4px;
      stroke-linejoin: round;
      stroke-linecap: round;
      pointer-events: none;
    }}
    /* Nationwide glow illumination across all states */
    .nationwide-active {{
      stroke: #38bdf8 !important;
      stroke-width: 1.4px !important;
      fill: #1a365d !important;
      filter: drop-shadow(0 0 6px rgba(56, 189, 248, 0.45));
    }}
    .slider-thumb::-webkit-slider-thumb {{
      -webkit-appearance: none;
      appearance: none;
      width: 20px;
      height: 20px;
      border-radius: 50%;
      background: #3b82f6;
      cursor: pointer;
      box-shadow: 0 0 10px rgba(59, 130, 246, 0.5);
    }}
    /* Map bubble transitions - calm, clean, zero infinite pulsating */
    #map-bubbles-layer, #map-bubble-labels-layer {{
      transition: opacity 0.35s ease-out;
    }}
    .city-bubble {{
      transition: opacity 0.25s ease-out, fill 0.25s;
    }}
    .city-bubble:hover {{
      stroke: #ffffff;
      stroke-width: 2.5;
      filter: drop-shadow(0 0 8px rgba(255, 255, 255, 0.6));
    }}
    /* Proportional Region Name Labels on Top-Center of Shaded Regions */
    #map-city-labels-layer {{
      transition: opacity 0.35s ease-out;
      pointer-events: none;
    }}
    .region-name-label {{
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      font-weight: 700;
      letter-spacing: 0.35px;
      fill: #ffffff;
      paint-order: stroke fill;
      stroke: rgba(2, 6, 23, 0.95);
      stroke-linejoin: round;
      stroke-linecap: round;
      filter: drop-shadow(0 1px 3px rgba(0, 0, 0, 0.85));
      text-anchor: middle;
      dominant-baseline: central;
      pointer-events: none;
      user-select: none;
    }}
  </style>
</head>
<body class="bg-[#0f172a] text-slate-100 antialiased min-h-screen p-4 md:p-8 font-sans">
  
  <!-- Header Bar -->
  <header class="max-w-7xl mx-auto mb-8 flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
    <div>
      <div class="flex items-center gap-2 mb-1">
        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20">
          Empirical Research Pipeline
        </span>
        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          Live Data-Driven
        </span>
      </div>
      <h1 class="text-2xl md:text-3xl font-bold tracking-tight text-white flex items-center gap-3">
        Navigation Apps & Traffic Policy Intelligence
      </h1>
      <p class="text-sm text-slate-400 mt-1">
        Interactive visualization of municipal restrictions, platform routing algorithms, and public-private coordination across the United States.
      </p>
    </div>

    <!-- Live Data Refresh & Re-load Controls -->
    <div class="flex items-center gap-3 bg-slate-900/80 p-2.5 rounded-xl border border-slate-800 shadow-inner">
      <div class="text-right">
        <div class="text-xs text-slate-400">Total Analyzed</div>
        <div id="stat-total-header" class="text-base font-bold text-blue-400">{total_sources} Sources</div>
      </div>
      <label class="cursor-pointer bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium px-3 py-2 rounded-lg transition-all flex items-center gap-1.5 shadow-sm">
        <span>🔄 Update JSON</span>
        <input type="file" id="json-file-input" accept=".json" class="hidden" />
      </label>
    </div>
  </header>

  <!-- Navigation Tabs -->
  <nav class="max-w-7xl mx-auto mb-6 flex flex-wrap gap-2 border-b border-slate-800 pb-2">
    <button onclick="switchTab('map-view')" id="tab-btn-map" class="tab-btn px-4 py-2 rounded-lg text-sm font-medium bg-blue-600 text-white shadow">
      🗺️ Geographic Map & Timeline Slider
    </button>
    <button onclick="switchTab('methodology-view')" id="tab-btn-methodology" class="tab-btn px-4 py-2 rounded-lg text-sm font-medium text-slate-400 hover:text-white hover:bg-slate-800">
      ⚡ Methodology Flowchart & Tools
    </button>
    <button onclick="switchTab('artifacts-view')" id="tab-btn-artifacts" class="tab-btn px-4 py-2 rounded-lg text-sm font-medium text-slate-400 hover:text-white hover:bg-slate-800">
      🔍 Artifacts Deep Dive (Query to Data)
    </button>
    <button onclick="switchTab('keywords-view')" id="tab-btn-keywords" class="tab-btn px-4 py-2 rounded-lg text-sm font-medium text-slate-400 hover:text-white hover:bg-slate-800">
      📊 Keyword Audit & Unused Terms
    </button>
  </nav>

  <!-- MAIN TAB 1: GEOGRAPHIC MAP & TIMELINE SLIDER -->
  <main id="map-view" class="tab-pane max-w-7xl mx-auto space-y-6">
    
    <!-- Top Stats Row -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
      <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm">
        <div class="text-xs text-slate-400 font-medium">Corpus Distribution</div>
        <div id="stat-sources" class="text-2xl font-bold text-white mt-1">{total_sources} Sources</div>
        <div id="stat-sources-sub" class="text-[11px] text-emerald-400 mt-1">{localized_sources} Localized + {nationwide_sources} Federal/National</div>
      </div>
      <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm">
        <div class="text-xs text-slate-400 font-medium">Local Geographic Pins</div>
        <div id="stat-locations" class="text-2xl font-bold text-blue-400 mt-1">{unique_locations} Locations</div>
        <div class="text-[11px] text-slate-400 mt-1">Cities & Counties Across U.S.</div>
      </div>
      <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm">
        <div class="text-xs text-slate-400 font-medium">Timeline Span</div>
        <div id="stat-years" class="text-2xl font-bold text-amber-400 mt-1">{year_range}</div>
        <div class="text-[11px] text-slate-400 mt-1">Policy Evolution Timeline</div>
      </div>
      <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm">
        <div class="text-xs text-slate-400 font-medium">Dominant Governance</div>
        <div id="stat-governance" class="text-2xl font-bold text-indigo-400 mt-1">{top_gov} ({top_gov_pct}%)</div>
        <div class="text-[11px] text-slate-400 mt-1">Leading Policy Level in Corpus</div>
      </div>
    </div>

    <!-- Interactive Map & Detail Sidebar Layout -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
      
      <!-- Left: Map & Interactive Timeline Controls (8 cols) -->
      <div class="lg:col-span-8 bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm flex flex-col justify-between">
        
        <div>
          <!-- Header and Legend -->
          <div class="flex flex-col sm:flex-row sm:items-center justify-between pb-3 mb-3 border-b border-slate-800 gap-2">
            <div>
              <h2 class="text-lg font-semibold text-white flex items-center gap-2">
                <span>📍 Localized Policy Interventions Across U.S. Jurisdictions</span>
              </h2>
              <p class="text-xs text-slate-400">National view displays proportional bubbles. Zoom in close (2.2x+) to smoothly morph bubbles into shaded county & municipal coverage regions.</p>
            </div>
            
            <!-- Map Legend -->
            <div class="flex flex-wrap items-center gap-3 text-xs">
              <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-blue-500 inline-block"></span> City</span>
              <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-amber-500 inline-block"></span> State</span>
              <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-rose-500 inline-block"></span> County</span>
              <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-emerald-500 inline-block"></span> Company</span>
              <span class="hidden sm:inline text-[11px] text-slate-500 border-l border-slate-700 pl-2">🔍 Zoom in to shade coverage regions</span>
            </div>
          </div>

          <!-- NATIONWIDE & FEDERAL POLICY SCOPE HUD DOCK -->
          <!-- Methodological solution: Instead of false geocoding in Kansas, nationwide coverage has its own dedicated interactive dock -->
          <div id="nationwide-hud" onmouseenter="setNationwideHighlight(true)" onmouseleave="setNationwideHighlight(false)" class="mb-3 p-3 rounded-xl bg-slate-950/80 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 transition-all hover:border-sky-500/50 shadow-inner">
            <div class="flex items-center gap-3">
              <div class="w-9 h-9 rounded-lg bg-sky-500/10 text-sky-400 font-bold flex items-center justify-center text-lg border border-sky-500/20">
                🇺🇸
              </div>
              <div>
                <div class="flex items-center gap-2">
                  <span class="text-xs font-bold text-white uppercase tracking-wider">Federal & Nationwide Scope</span>
                  <span id="nationwide-badge-count" class="px-2 py-0.5 rounded-full text-xs font-bold bg-sky-500/20 text-sky-400 border border-sky-500/30">
                    19 Policies (All 50 States)
                  </span>
                </div>
                <p id="nationwide-hud-desc" class="text-xs text-slate-400 mt-0.5">
                  USDOT/NHTSA app mandates, Latimer bridge strike legislation, and nationwide Google Maps eco-routing algorithms that apply coast-to-coast.
                </p>
              </div>
            </div>
            
            <div class="flex items-center gap-2">
              <button onclick="selectNationwideScope()" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-sky-600 hover:bg-sky-500 text-white transition flex items-center gap-1.5 shadow-sm">
                <span>View Federal Policies</span>
                <span>→</span>
              </button>
            </div>
          </div>

          <!-- SVG United States Map Container with Zoom & Pan Dock -->
          <div class="relative w-full aspect-[16/10] bg-slate-950/70 rounded-xl border border-slate-800/80 overflow-hidden flex items-center justify-center p-2">
            
            <!-- FLOATING ZOOM CONTROLS DOCK (TOP-LEFT) -->
            <div class="absolute top-4 left-4 z-20 flex flex-col gap-1.5 bg-slate-900/90 backdrop-blur-md border border-slate-700/80 p-1.5 rounded-xl shadow-2xl">
              <button onclick="zoomIn()" title="Zoom In (+)" class="w-8 h-8 rounded-lg bg-slate-800 hover:bg-blue-600 text-white font-bold text-base flex items-center justify-center transition border border-slate-700 hover:border-blue-500 shadow-sm active:scale-95">
                +
              </button>
              <button onclick="zoomOut()" title="Zoom Out (−)" class="w-8 h-8 rounded-lg bg-slate-800 hover:bg-blue-600 text-white font-bold text-base flex items-center justify-center transition border border-slate-700 hover:border-blue-500 shadow-sm active:scale-95">
                −
              </button>
              <div class="h-px bg-slate-700/80 my-0.5"></div>
              <button onclick="resetZoom()" title="Reset to Continental USA (1.0x)" class="w-8 h-8 rounded-lg bg-slate-800 hover:bg-amber-600 text-white font-semibold text-xs flex items-center justify-center transition border border-slate-700 hover:border-amber-500 shadow-sm active:scale-95">
                ⟲
              </button>
            </div>

            <!-- ZOOM LEVEL & PRECISION BADGE (TOP-RIGHT) -->
            <div class="absolute top-4 right-4 z-20 flex items-center gap-2 bg-slate-900/90 backdrop-blur-md border border-slate-700/80 px-3 py-1.5 rounded-xl shadow-xl text-xs">
              <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
              <span class="text-slate-400 font-medium">Zoom Tier:</span>
              <span id="zoom-badge-text" class="font-bold text-white font-mono">1.0x (National View)</span>
            </div>

            <!-- GESTURE & INTERACTION HINT (BOTTOM) -->
            <div class="absolute bottom-3 left-1/2 -translate-x-1/2 pointer-events-none z-10 bg-slate-950/85 backdrop-blur-sm border border-slate-800 px-3.5 py-1 rounded-full text-[11px] text-slate-400 shadow flex items-center gap-2">
              <span>🔍 Scroll / pinch to zoom into shaded regions</span>
              <span class="text-slate-600">•</span>
              <span>✋ Drag to pan</span>
              <span class="text-slate-600">•</span>
              <span>📍 Click shaded county or pin to focus</span>
            </div>

            <svg id="us-map-svg" viewBox="0 0 975 610" class="w-full h-full select-none cursor-grab active:cursor-grabbing">
              <defs>
                <filter id="bubble-glow" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="2.5" result="blur" />
                  <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>
              </defs>

              <!-- Master Zoom Group transformed smoothly by D3 Zoom Engine -->
              <g id="map-zoom-group">
                <!-- 1. Counties Polygons Layer (Hoverable & Clickable) -->
                <g id="map-counties-layer"></g>

                <!-- 2. County Mesh Borders Layer (Crisp Interior Boundaries) -->
                <g id="map-county-mesh-layer" pointer-events="none"></g>

                <!-- 3. States Polygons Layer -->
                <g id="map-states-layer"></g>

                <!-- 4. State Mesh Boundaries Layer -->
                <g id="map-state-mesh-layer" pointer-events="none"></g>

                <!-- 5. State 2-Letter Abbreviation Labels (CA, TX, NY...) -->
                <g id="map-state-labels-layer" pointer-events="none"></g>

                <!-- 6. Localized City Bubbles Layer -->
                <g id="map-bubbles-layer"></g>

                <!-- 7. Bubble Numeric Count Text Layer -->
                <g id="map-bubble-labels-layer" pointer-events="none"></g>

                <!-- 8. Dynamic City & Municipality Name Badges Layer (Fades in on zoom) -->
                <g id="map-city-labels-layer" pointer-events="none"></g>
              </g>
            </svg>

            <!-- Floating Hover Tooltip -->
            <div id="map-tooltip" class="absolute pointer-events-none hidden bg-slate-900/95 border border-slate-700 text-white text-xs rounded-lg px-3 py-2 shadow-xl z-30 max-w-xs transition-opacity">
              <div id="tooltip-title" class="font-bold text-blue-400"></div>
              <div id="tooltip-body" class="text-slate-300 mt-0.5"></div>
            </div>
          </div>
        </div>

        <!-- TIMELINE SLIDING SCALE & CONTROLS -->
        <div class="mt-4 pt-4 border-t border-slate-800 space-y-3">
          
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <button id="play-pause-btn" onclick="togglePlayTimeline()" class="bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition shadow">
                <span id="play-btn-icon">▶</span> <span id="play-btn-text">Play Timeline</span>
              </button>
              
              <button id="toggle-cumulative-btn" onclick="toggleCumulativeMode()" class="bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs px-3 py-1.5 rounded-lg border border-slate-700 transition">
                Mode: <span id="mode-text" class="text-white font-medium">Single Year</span>
              </button>
            </div>

            <!-- Current Selected Year Badge -->
            <div class="text-right">
              <span class="text-xs text-slate-400 mr-2">Viewing Timeframe:</span>
              <span id="selected-year-badge" class="text-lg font-black text-amber-400 bg-amber-500/10 border border-amber-500/20 px-3 py-0.5 rounded-lg">
                All Years
              </span>
            </div>
          </div>

          <!-- Sliding Scale Range Slider -->
          <div class="relative px-2">
            <input 
              type="range" 
              id="timeline-slider" 
              min="0" 
              max="14" 
              value="14" 
              oninput="onTimelineChange(this.value)"
              class="w-full h-2.5 bg-slate-800 rounded-lg appearance-none cursor-pointer slider-thumb border border-slate-700 focus:outline-none"
            />
            
            <!-- Ticks under the slider -->
            <div id="slider-ticks" class="flex justify-between text-[11px] text-slate-400 mt-2 select-none"></div>
          </div>

          <!-- Milestone / Policy Era Description -->
          <div id="year-era-card" class="bg-slate-950/70 border border-slate-800/90 rounded-lg p-3 text-xs text-slate-300 flex items-start gap-2.5">
            <span class="text-base">📌</span>
            <div>
              <span id="era-title" class="font-bold text-white">Cumulative Corpus Overview ({year_range})</span>
              <p id="era-description" class="text-slate-400 mt-0.5">Showing cumulative distribution of {total_sources} navigation-app policy measures, street access regulations, and municipal coordination agreements across all years ({year_range}).</p>
            </div>
          </div>

        </div>

      </div>

      <!-- Right: Location Detail Pane & Top Locations Leaderboard (4 cols) -->
      <div class="lg:col-span-4 space-y-6">
        
        <!-- Selected Location Details Card -->
        <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div class="flex items-center justify-between pb-3 border-b border-slate-800">
            <h3 class="text-sm font-semibold text-white flex items-center gap-1.5">
              <span>📍 Policy Drill-Down</span>
            </h3>
            <span id="loc-badge-count" class="text-xs font-bold text-blue-400 bg-blue-500/10 px-2.5 py-0.5 rounded-full border border-blue-500/20">
              Select pin or federal card
            </span>
          </div>

          <div id="location-detail-content" class="mt-4 space-y-3 max-h-[380px] overflow-y-auto pr-1 text-xs">
            <div class="text-slate-400 text-center py-8">
              Click any city bubble on the map or click the "View Federal Policies" dock above to explore specific ordinances, authorities, and supporting news reporting.
            </div>
          </div>
        </div>

        <!-- Top Locations Ranking Card -->
        <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm">
          <h3 class="text-sm font-semibold text-white pb-2.5 border-b border-slate-800 mb-3 flex items-center justify-between">
            <span>🏆 Geographic Leaderboard</span>
            <span class="text-[11px] text-slate-400 font-normal">Active Timeframe</span>
          </h3>

          <div id="locations-leaderboard" class="space-y-2.5 max-h-[220px] overflow-y-auto pr-1"></div>
        </div>

      </div>

    </div>

  </main>

  <!-- TAB 2: METHODOLOGY FLOWCHART & TOOLS -->
  <section id="methodology-view" class="tab-pane max-w-7xl mx-auto space-y-8 hidden">
    
    <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-6 shadow-sm">
      <div class="max-w-3xl">
        <h2 class="text-xl font-bold text-white">End-to-End News Ingestion & Research Architecture</h2>
        <p class="text-sm text-slate-400 mt-1">
          Detailed data pipeline tracking how search queries, catalog entries, and raw LexisNexis news feeds are transformed into 100% verified, deduplicated research analysis records.
        </p>
      </div>

      <!-- Flowchart SVG / Cards Representation -->
      <div class="mt-8 grid grid-cols-1 md:grid-cols-5 gap-4 relative">
        
        <!-- Step 1 -->
        <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-4 flex flex-col justify-between relative">
          <div class="w-8 h-8 rounded-lg bg-blue-500/10 text-blue-400 font-bold flex items-center justify-center text-sm border border-blue-500/20 mb-3">01</div>
          <div>
            <h4 class="font-bold text-white text-sm">Inputs & Queries</h4>
            <p class="text-xs text-slate-400 mt-1">Targeted search strategies across 3 keyword families and 10 study areas.</p>
            <div class="mt-3 space-y-1 text-[11px] text-slate-300 font-mono bg-slate-900 p-2 rounded border border-slate-800">
              <div>• US-OVERVIEW-01</div>
              <div>• US-FEEDBACK-01</div>
              <div>• Regional Study Catalogs</div>
            </div>
          </div>
          <div class="mt-4 pt-3 border-t border-slate-800/80 text-[11px] text-slate-400">
            <strong>Tools:</strong> Python `re`, CSV Catalogs
          </div>
        </div>

        <!-- Step 2 -->
        <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-4 flex flex-col justify-between relative">
          <div class="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-400 font-bold flex items-center justify-center text-sm border border-emerald-500/20 mb-3">02</div>
          <div>
            <h4 class="font-bold text-white text-sm">Dual Ingestion</h4>
            <p class="text-xs text-slate-400 mt-1">Dual-engine pipeline collecting archival web documents and news wires.</p>
            <div class="mt-3 space-y-1 text-[11px] text-slate-300 font-mono bg-slate-900 p-2 rounded border border-slate-800">
              <div>• LexisNexis API (WS)</div>
              <div>• Crawl4AI (HTML/DOM)</div>
              <div>• Direct HTTP (PDF/raw)</div>
            </div>
          </div>
          <div class="mt-4 pt-3 border-t border-slate-800/80 text-[11px] text-slate-400">
            <strong>Models:</strong> LexisNexis Web Services
          </div>
        </div>

        <!-- Step 3 -->
        <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-4 flex flex-col justify-between relative">
          <div class="w-8 h-8 rounded-lg bg-amber-500/10 text-amber-400 font-bold flex items-center justify-center text-sm border border-amber-500/20 mb-3">03</div>
          <div>
            <h4 class="font-bold text-white text-sm">4-Tier Deduplication</h4>
            <p class="text-xs text-slate-400 mt-1">Multi-stage gatekeeping collapsing syndicated wire copy clusters.</p>
            <div class="mt-3 space-y-1 text-[11px] text-slate-300 font-mono bg-slate-900 p-2 rounded border border-slate-800">
              <div>• Tier 1: Global URN</div>
              <div>• Tier 2: URL Normalizer</div>
              <div>• Tier 3: Wire Normalizer</div>
              <div>• Tier 4: DB In-Memory Key</div>
            </div>
          </div>
          <div class="mt-4 pt-3 border-t border-slate-800/80 text-[11px] text-slate-400">
            <strong>Logic:</strong> `normalize_title_for_dedup`
          </div>
        </div>

        <!-- Step 4 -->
        <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-4 flex flex-col justify-between relative">
          <div class="w-8 h-8 rounded-lg bg-rose-500/10 text-rose-400 font-bold flex items-center justify-center text-sm border border-rose-500/20 mb-3">04</div>
          <div>
            <h4 class="font-bold text-white text-sm">Scope Filtering</h4>
            <p class="text-xs text-slate-400 mt-1">Rejection of off-topic noise (crimes, SEC stock filings, repaving).</p>
            <div class="mt-3 space-y-1 text-[11px] text-slate-300 font-mono bg-slate-900 p-2 rounded border border-slate-800">
              <div>• Crime blotters: PURGED</div>
              <div>• Space bills: PURGED</div>
              <div>• Stock positions: PURGED</div>
              <div>• Non-US: PURGED</div>
            </div>
          </div>
          <div class="mt-4 pt-3 border-t border-slate-800/80 text-[11px] text-slate-400">
            <strong>Rules:</strong> `OFF_TOPIC_TITLE_TERMS`
          </div>
        </div>

        <!-- Step 5 -->
        <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-4 flex flex-col justify-between relative">
          <div class="w-8 h-8 rounded-lg bg-indigo-500/10 text-indigo-400 font-bold flex items-center justify-center text-sm border border-indigo-500/20 mb-3">05</div>
          <div>
            <h4 class="font-bold text-white text-sm">Qualitative Coding</h4>
            <p class="text-xs text-slate-400 mt-1">Schema synthesis & verbatim quotation evidence verification.</p>
            <div class="mt-3 space-y-1 text-[11px] text-slate-300 font-mono bg-slate-900 p-2 rounded border border-slate-800">
              <div>• 27-Column Schema</div>
              <div>• Governing Levels (5)</div>
              <div>• Target Geographies</div>
              <div>• Verbatim Proof Match</div>
            </div>
          </div>
          <div class="mt-4 pt-3 border-t border-slate-800/80 text-[11px] text-slate-400">
            <strong>Deliverable:</strong> CSV + JSON ({total_sources} rows)
          </div>
        </div>

      </div>

    </div>

    <!-- Models and Tools Table -->
    <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-6 shadow-sm">
      <h3 class="text-base font-bold text-white mb-4">Technical Stack & Infrastructure Reference</h3>
      
      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs text-slate-300">
          <thead class="bg-slate-950 text-slate-400 uppercase font-semibold border-b border-slate-800">
            <tr>
              <th class="py-3 px-4">Pipeline Stage</th>
              <th class="py-3 px-4">Tool / Model / Engine</th>
              <th class="py-3 px-4">Primary Function</th>
              <th class="py-3 px-4">Key Implementation File</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-800">
            <tr>
              <td class="py-3 px-4 font-medium text-white">Commercial News Search</td>
              <td class="py-3 px-4 font-mono text-blue-400">LexisNexis Web Services API (REST)</td>
              <td class="py-3 px-4">Retrieves full-text licensed news reporting across U.S. national and local news wires.</td>
              <td class="py-3 px-4 font-mono text-slate-400">news_importer/nexis.py</td>
            </tr>
            <tr>
              <td class="py-3 px-4 font-medium text-white">Web Archival Scraping</td>
              <td class="py-3 px-4 font-mono text-emerald-400">Crawl4AI + Async Headless Browser</td>
              <td class="py-3 px-4">Renders municipal council portals, public comment PDFs, and local greenway plans.</td>
              <td class="py-3 px-4 font-mono text-slate-400">news_importer/crawl.py</td>
            </tr>
            <tr>
              <td class="py-3 px-4 font-medium text-white">Wire Normalization & Dedup</td>
              <td class="py-3 px-4 font-mono text-amber-400">Regex Wire Normalizer (`normalize_title_for_dedup`)</td>
              <td class="py-3 px-4">Strips wire syndicate tags and punctuation, collapsing over 50 regional duplicates.</td>
              <td class="py-3 px-4 font-mono text-slate-400">news_importer/crawl_nexis_us.py</td>
            </tr>
            <tr>
              <td class="py-3 px-4 font-medium text-white">Data Storage & Lineage</td>
              <td class="py-3 px-4 font-mono text-purple-400">SQLite 3 (`data/news.sqlite`)</td>
              <td class="py-3 px-4">Tracks discovery origins, fetch attempts, HTTP status codes, and raw responses.</td>
              <td class="py-3 px-4 font-mono text-slate-400">news_importer/db.py</td>
            </tr>
            <tr>
              <td class="py-3 px-4 font-medium text-white">Evidence Verification</td>
              <td class="py-3 px-4 font-mono text-indigo-400">Verbatim Passage Validator (`verify_passage`)</td>
              <td class="py-3 px-4">Validates that 100% of cited supporting passages exist verbatim in raw disk files.</td>
              <td class="py-3 px-4 font-mono text-slate-400">news_importer/analysis.py</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

  </section>

  <!-- TAB 3: ARTIFACTS DEEP DIVE (QUERY TO DATA) -->
  <section id="artifacts-view" class="tab-pane max-w-7xl mx-auto space-y-6 hidden">
    
    <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-6 shadow-sm">
      <h2 class="text-xl font-bold text-white">Zoom-In: Anatomy of a Research Analysis Artifact</h2>
      <p class="text-sm text-slate-400 mt-1">
        Trace a single real-world policy intervention from raw keyword expansion, through Boolean query execution, to raw document retrieval, and into the final 27-column research coding.
      </p>

      <!-- Step-by-step example cards -->
      <div class="mt-6 space-y-6">
        
        <!-- Artifact 1: Keyword Expansion -->
        <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-5">
          <div class="flex items-center justify-between pb-3 border-b border-slate-800">
            <span class="text-xs font-bold text-blue-400 uppercase tracking-wider">Artifact Phase A • Keyword Expansion</span>
            <span class="text-xs text-slate-400 font-mono">Taxonomy Design</span>
          </div>
          <p class="text-xs text-slate-300 mt-3">
            Initial research objective: capture municipal ordinances blocking commuter shortcut traffic. Expanded into mandatory app groups and Boolean proximity blocks:
          </p>
          <div class="mt-3 bg-slate-900 p-3 rounded-lg border border-slate-800 text-xs font-mono text-emerald-400 overflow-x-auto">
            ( "cut-through traffic" OR "through traffic" OR "shortcut traffic" OR "rat running" OR "residential streets" )<br>
            AND ( complaint OR complaints OR backlash OR opposition OR petition OR "public comment" )<br>
            AND ( ( law OR ordinance OR ban OR regulation ) W/20 ( routing OR navigation OR traffic OR streets ) )
          </div>
        </div>

        <!-- Artifact 2: The Executed Nexis Query -->
        <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-5">
          <div class="flex items-center justify-between pb-3 border-b border-slate-800">
            <span class="text-xs font-bold text-amber-400 uppercase tracking-wider">Artifact Phase B • Live Query Object</span>
            <span class="text-xs text-slate-400 font-mono">queries/nexis_us_overview_query.txt (US-OVERVIEW-01)</span>
          </div>
          <div class="mt-3 bg-slate-900 p-3 rounded-lg border border-slate-800 text-xs font-mono text-slate-300 max-h-32 overflow-y-auto">
            ( Waze OR "Google Maps" OR "Apple Maps" OR MapQuest OR "HERE WeGo" OR "navigation app" OR "routing app" ) AND ( ( "road access" OR "turn restriction" OR "road closure" OR "resident only" OR "no through traffic" OR "traffic calming" OR "traffic diverter" OR "congestion pricing" OR ( ( law OR ordinance OR ban ) W/20 ( routing OR navigation OR traffic ) ) ) OR ( "routing policy" OR "routing algorithm" OR "avoid residential streets" OR "eco-friendly routing" ) OR ( "Waze for Cities" OR "Connected Citizens Program" OR ( ( partnership OR "data sharing" ) W/20 ( government OR city OR "transportation department" ) ) ) )
          </div>
        </div>

        <!-- Artifact 3: Raw Search Hit & NITF Record -->
        <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-5">
          <div class="flex items-center justify-between pb-3 border-b border-slate-800">
            <span class="text-xs font-bold text-purple-400 uppercase tracking-wider">Artifact Phase C • Raw Ingested Hit & Metadata</span>
            <span class="text-xs text-slate-400 font-mono">URN: urn:contentItem:5YD5-NK31-JC65-51MB-00000-00</span>
          </div>
          <div class="mt-3 grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div class="bg-slate-900 p-3 rounded-lg border border-slate-800 space-y-1 text-slate-300">
              <div><strong class="text-white">Title:</strong> Town that closed streets to commuters gets court reprieve</div>
              <div><strong class="text-white">Publisher:</strong> Associated Press / NorthJersey.com</div>
              <div><strong class="text-white">Date:</strong> 2018-05-18</div>
              <div><strong class="text-white">Subject Geography:</strong> Leonia, Bergen County, New Jersey</div>
            </div>
            <div class="bg-slate-900 p-3 rounded-lg border border-slate-800 font-mono text-[11px] text-slate-400 overflow-y-auto max-h-24">
              &lt;nitf:body.content&gt;<br>
              &nbsp;&nbsp;&lt;p&gt;A state judge has refused to dismiss a town's lawsuit seeking to uphold its ban on outside drivers using residential side streets to avoid George Washington Bridge gridlock...&lt;/p&gt;<br>
              &lt;/nitf:body.content&gt;
            </div>
          </div>
        </div>

        <!-- Artifact 4: Final 27-Column Analysis Row -->
        <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-5">
          <div class="flex items-center justify-between pb-3 border-b border-slate-800">
            <span class="text-xs font-bold text-emerald-400 uppercase tracking-wider">Artifact Phase D • Final Coded Qualitative Row</span>
            <span class="text-xs text-slate-400 font-mono">data/exports/research_analysis_all_sources.csv</span>
          </div>
          <div class="mt-3 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-xs">
            <div class="bg-slate-900 p-2.5 rounded border border-slate-800">
              <span class="text-[11px] text-slate-400 block">Governing Level</span>
              <span class="font-bold text-white text-sm">Government: City</span>
            </div>
            <div class="bg-slate-900 p-2.5 rounded border border-slate-800">
              <span class="text-[11px] text-slate-400 block">Authority Name</span>
              <span class="font-bold text-white text-sm">Borough of Leonia (Council & Police)</span>
            </div>
            <div class="bg-slate-900 p-2.5 rounded border border-slate-800">
              <span class="text-[11px] text-slate-400 block">Target Location</span>
              <span class="font-bold text-white text-sm">Leonia (City / NJ)</span>
            </div>
            <div class="bg-slate-900 p-2.5 rounded border border-slate-800">
              <span class="text-[11px] text-slate-400 block">Taxonomy Category</span>
              <span class="font-bold text-emerald-400 text-sm">Both (Measures & Feedback)</span>
            </div>
          </div>
          <div class="mt-3 bg-slate-900 p-3 rounded border border-slate-800 text-xs text-slate-300">
            <strong class="text-white block mb-1">Verbatim Validated Passage:</strong>
            <p class="italic text-slate-400 font-serif">
              "The borough closed 60 streets to non-residents during morning and evening rush hours after navigation apps like Waze and Google Maps began steering highway overflow through town."
            </p>
          </div>
        </div>

      </div>

    </div>

  </section>

  <!-- TAB 4: KEYWORD AUDIT & UNUSED TERMS -->
  <section id="keywords-view" class="tab-pane max-w-7xl mx-auto space-y-6 hidden">
    
    <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-6 shadow-sm">
      <h2 class="text-xl font-bold text-white">Comprehensive Keyword Audit: Utilized vs. Unused Terms</h2>
      <p class="text-sm text-slate-400 mt-1">
        Evaluation of term frequencies across all {total_sources} clean articles in our corpus, highlighting which search terms were dominant and which niche keywords from your taxonomy yielded zero hits.
      </p>

      <div class="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
        {keyword_audit_html}
      </div>

    </div>

  </section>

  <!-- Script block injecting data and dynamic timeline/map logic -->
  <script>
    // Global Data Payload injected from Python
    let DATA = {json_str};

    let activeYearIndex = DATA.all_years.length; // Default to 'All Years' (last index)
    let isCumulativeMode = false;
    let isPlaying = false;
    let playInterval = null;
    let selectedLocation = null;
    let isNationwideSelected = false;
    let zoomBehavior = null;
    let currentZoomK = 1.0;
    let usAtlasData = null;

    // Standard State FIPS Code Dictionary
    const STATE_FIPS_MAP = {{
      "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA",
      "08": "CO", "09": "CT", "10": "DE", "11": "DC", "12": "FL",
      "13": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN",
      "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME",
      "24": "MD", "25": "MA", "26": "MI", "27": "MN", "28": "MS",
      "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
      "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND",
      "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI",
      "45": "SC", "46": "SD", "47": "TN", "48": "TX", "49": "UT",
      "50": "VT", "51": "VA", "53": "WA", "54": "WV", "55": "WI",
      "56": "WY", "72": "PR"
    }};

    const STATE_NAME_MAP = {{
      "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
      "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia",
      "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
      "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
      "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
      "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
      "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
      "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon",
      "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
      "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia",
      "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming"
    }};

    // City to County & FIPS mapping for empirical routing policy locations
    const CITY_TO_COUNTY = {{
      "Leonia, NJ": {{ fips: ["34003"], county: "Bergen County, NJ" }},
      "Mantoloking, NJ": {{ fips: ["34029"], county: "Ocean County, NJ" }},
      "Newark, NJ": {{ fips: ["34013"], county: "Essex County, NJ" }},
      "Trenton, NJ": {{ fips: ["34021"], county: "Mercer County, NJ" }},
      "Los Angeles, CA": {{ fips: ["06037"], county: "Los Angeles County, CA" }},
      "San Francisco, CA": {{ fips: ["06075"], county: "San Francisco County, CA" }},
      "San Jose, CA": {{ fips: ["06085"], county: "Santa Clara County, CA" }},
      "Silicon Valley, CA": {{ fips: ["06085", "06081"], county: "Santa Clara & San Mateo Counties, CA" }},
      "Oakland, CA": {{ fips: ["06001"], county: "Alameda County, CA" }},
      "Sacramento, CA": {{ fips: ["06067"], county: "Sacramento County, CA" }},
      "San Diego, CA": {{ fips: ["06073"], county: "San Diego County, CA" }},
      "Fresno, CA": {{ fips: ["06019"], county: "Fresno County, CA" }},
      "Davis, CA": {{ fips: ["06113"], county: "Yolo County, CA" }},
      "Austin, TX": {{ fips: ["48453"], county: "Travis County, TX" }},
      "Dallas, TX": {{ fips: ["48113"], county: "Dallas County, TX" }},
      "Fort Worth, TX": {{ fips: ["48439"], county: "Tarrant County, TX" }},
      "Arlington, TX": {{ fips: ["48439"], county: "Tarrant County, TX" }},
      "Houston, TX": {{ fips: ["48201"], county: "Harris County, TX" }},
      "San Antonio, TX": {{ fips: ["48029"], county: "Bexar County, TX" }},
      "Amarillo, TX": {{ fips: ["48375", "48381"], county: "Potter & Randall Counties, TX" }},
      "New York City, NY": {{ fips: ["36061", "36047", "36081", "36005", "36085"], county: "New York City (5 Boroughs), NY" }},
      "Albany, NY": {{ fips: ["36001"], county: "Albany County, NY" }},
      "Chicago, IL": {{ fips: ["17031"], county: "Cook County, IL" }},
      "Evanston, IL": {{ fips: ["17031"], county: "Cook County, IL" }},
      "Naperville, IL": {{ fips: ["17043"], county: "DuPage County, IL" }},
      "Springfield, IL": {{ fips: ["17167"], county: "Sangamon County, IL" }},
      "Atlanta, GA": {{ fips: ["13121", "13089"], county: "Fulton & DeKalb Counties, GA" }},
      "Fulton County, GA": {{ fips: ["13121"], county: "Fulton County, GA" }},
      "Boston, MA": {{ fips: ["25025"], county: "Suffolk County, MA" }},
      "Seattle, WA": {{ fips: ["53033"], county: "King County, WA" }},
      "Spokane, WA": {{ fips: ["53063"], county: "Spokane County, WA" }},
      "Miami, FL": {{ fips: ["12086"], county: "Miami-Dade County, FL" }},
      "Miami-Dade County, FL": {{ fips: ["12086"], county: "Miami-Dade County, FL" }},
      "Coral Gables, FL": {{ fips: ["12086"], county: "Miami-Dade County, FL" }},
      "Jacksonville, FL": {{ fips: ["12031"], county: "Duval County, FL" }},
      "Tampa, FL": {{ fips: ["12057"], county: "Hillsborough County, FL" }},
      "Tallahassee, FL": {{ fips: ["12073"], county: "Leon County, FL" }},
      "Philadelphia, PA": {{ fips: ["42101"], county: "Philadelphia County, PA" }},
      "Pittsburgh, PA": {{ fips: ["42003"], county: "Allegheny County, PA" }},
      "Harrisburg, PA": {{ fips: ["42043"], county: "Dauphin County, PA" }},
      "Lancaster, PA": {{ fips: ["42071"], county: "Lancaster County, PA" }},
      "Phoenix, AZ": {{ fips: ["04013"], county: "Maricopa County, AZ" }},
      "Denver, CO": {{ fips: ["08031"], county: "Denver County, CO" }},
      "Colorado Springs, CO": {{ fips: ["08041"], county: "El Paso County, CO" }},
      "Detroit, MI": {{ fips: ["26163"], county: "Wayne County, MI" }},
      "Midland, MI": {{ fips: ["26111"], county: "Midland County, MI" }},
      "Saint Paul, MN": {{ fips: ["27123"], county: "Ramsey County, MN" }},
      "Saint Louis, MO": {{ fips: ["29510", "29189"], county: "St. Louis City & County, MO" }},
      "Kansas City, MO": {{ fips: ["29095", "29047"], county: "Jackson & Clay Counties, MO" }},
      "Raleigh, NC": {{ fips: ["37183"], county: "Wake County, NC" }},
      "Cary, NC": {{ fips: ["37183"], county: "Wake County, NC" }},
      "Charlotte, NC": {{ fips: ["37119"], county: "Mecklenburg County, NC" }},
      "Greensboro, NC": {{ fips: ["37081"], county: "Guilford County, NC" }},
      "Asheville, NC": {{ fips: ["37021"], county: "Buncombe County, NC" }},
      "Nashville, TN": {{ fips: ["47037"], county: "Davidson County, TN" }},
      "Knoxville, TN": {{ fips: ["47093"], county: "Knox County, TN" }},
      "Norfolk, VA": {{ fips: ["51710"], county: "Norfolk City, VA" }},
      "Virginia Beach, VA": {{ fips: ["51810"], county: "Virginia Beach City, VA" }},
      "Richmond, VA": {{ fips: ["51760"], county: "Richmond City, VA" }},
      "Loudoun County, VA": {{ fips: ["51107"], county: "Loudoun County, VA" }},
      "Washington, DC": {{ fips: ["11001"], county: "District of Columbia" }},
      "District of Columbia": {{ fips: ["11001"], county: "District of Columbia" }},
      "Baltimore, MD": {{ fips: ["24510"], county: "Baltimore City, MD" }},
      "Columbus, OH": {{ fips: ["39049"], county: "Franklin County, OH" }},
      "Toledo, OH": {{ fips: ["39095"], county: "Lucas County, OH" }},
      "Milwaukee, WI": {{ fips: ["55079"], county: "Milwaukee County, WI" }},
      "Salt Lake City, UT": {{ fips: ["49035"], county: "Salt Lake County, UT" }},
      "Portland, OR": {{ fips: ["41051"], county: "Multnomah County, OR" }},
      "Albuquerque, NM": {{ fips: ["35001"], county: "Bernalillo County, NM" }},
      "Santa Fe, NM": {{ fips: ["35049"], county: "Santa Fe County, NM" }},
      "Reno, NV": {{ fips: ["32031"], county: "Washoe County, NV" }},
      "Carson City, NV": {{ fips: ["32510"], county: "Carson City, NV" }},
      "Boise, ID": {{ fips: ["16001"], county: "Ada County, ID" }},
      "Hartford, CT": {{ fips: ["09003"], county: "Hartford County, CT" }},
      "Bridgeport, CT": {{ fips: ["09001"], county: "Fairfield County, CT" }},
      "Fairfield, CT": {{ fips: ["09001"], county: "Fairfield County, CT" }},
      "New Haven, CT": {{ fips: ["09009"], county: "New Haven County, CT" }},
      "Providence, RI": {{ fips: ["44007"], county: "Providence County, RI" }},
      "Dover, DE": {{ fips: ["10001"], county: "Kent County, DE" }},
      "Baton Rouge, LA": {{ fips: ["22033"], county: "East Baton Rouge Parish, LA" }},
      "Louisville, KY": {{ fips: ["21111"], county: "Jefferson County, KY" }},
      "Lexington, KY": {{ fips: ["21067"], county: "Fayette County, KY" }},
      "Des Moines, IA": {{ fips: ["19153"], county: "Polk County, IA" }},
      "Davenport, IA": {{ fips: ["19163"], county: "Scott County, IA" }},
      "Lincoln, NE": {{ fips: ["31109"], county: "Lancaster County, NE" }},
      "Sioux Falls, SD": {{ fips: ["46099"], county: "Minnehaha County, SD" }},
      "Montgomery, AL": {{ fips: ["01101"], county: "Montgomery County, AL" }},
      "Augusta, ME": {{ fips: ["23011"], county: "Kennebec County, ME" }},
      "Anchorage, AK": {{ fips: ["02020"], county: "Anchorage Municipality, AK" }}
    }};

    const FIPS_TO_LOCATIONS = {{}};
    Object.entries(CITY_TO_COUNTY).forEach(([cName, info]) => {{
      const fipsArr = Array.isArray(info.fips) ? info.fips : [info.fips];
      fipsArr.forEach(f => {{
        if (!FIPS_TO_LOCATIONS[f]) FIPS_TO_LOCATIONS[f] = [];
        if (!FIPS_TO_LOCATIONS[f].includes(cName)) FIPS_TO_LOCATIONS[f].push(cName);
      }});
    }});

    // Helper to evaluate active policy count and metadata for any county FIPS
    function getCountyActivePolicy(fipsCode) {{
      const activeYear = getActiveYear();
      const matchedCities = FIPS_TO_LOCATIONS[fipsCode] || [];
      let totalCount = 0;
      let topGov = 'City';
      let maxGovCnt = -1;
      const matchedLocs = [];

      // Check municipal/city policy coverage
      if (matchedCities.length > 0) {{
        DATA.locations.forEach(loc => {{
          if (matchedCities.includes(loc.name)) {{
            let cnt = 0;
            if (activeYear === 'ALL') {{
              cnt = loc.total_count;
            }} else if (isCumulativeMode) {{
              Object.keys(loc.years).forEach(yr => {{ if (yr <= activeYear) cnt += loc.years[yr]; }});
            }} else {{
              cnt = loc.years[activeYear] || 0;
            }}

            if (cnt > 0) {{
              totalCount += cnt;
              matchedLocs.push(loc);
              Object.entries(loc.gov_levels || {{}}).forEach(([gov, c]) => {{
                if (c > maxGovCnt) {{ maxGovCnt = c; topGov = gov; }}
              }});
            }}
          }}
        }});
      }}

      // Check state-level policy coverage
      let statewideCount = 0;
      const stateCode = STATE_FIPS_MAP[fipsCode.slice(0, 2)];
      const stateFullName = STATE_NAME_MAP[stateCode];
      if (stateFullName) {{
        const stateKey = `${{stateFullName}} (State)`;
        const stateLoc = DATA.locations.find(l => l.name === stateKey);
        if (stateLoc) {{
          if (activeYear === 'ALL') {{
            statewideCount = stateLoc.total_count;
          }} else if (isCumulativeMode) {{
            Object.keys(stateLoc.years).forEach(yr => {{ if (yr <= activeYear) statewideCount += stateLoc.years[yr]; }});
          }} else {{
            statewideCount = stateLoc.years[activeYear] || 0;
          }}
        }}
      }}

      return {{
        count: totalCount,
        statewideCount: statewideCount,
        topGov: topGov,
        color: getGovColor(topGov),
        cities: matchedCities,
        locations: matchedLocs
      }};
    }}

    // Canonical Albers USA Projection matching us-atlas 975x610 viewport
    let albersProjection = null;
    try {{
      if (typeof d3 !== 'undefined' && d3.geoAlbersUsa) {{
        albersProjection = d3.geoAlbersUsa().scale(1300).translate([487.5, 305]);
      }}
    }} catch(e) {{
      console.warn("D3 projection init:", e);
    }}

    function projectCoords(lat, lon) {{
      if (albersProjection) {{
        const pt = albersProjection([lon, lat]);
        if (pt) return {{ x: pt[0], y: pt[1] }};
      }}
      // Fallback projection if point is outside contiguous US (e.g. Alaska)
      const minLon = -125.0, maxLon = -66.0;
      const minLat = 24.0, maxLat = 50.0;
      const x = ((lon - minLon) / (maxLon - minLon)) * 790 + 70;
      const y = ((maxLat - lat) / (maxLat - minLat)) * 490 + 50;
      return {{ x: Math.max(50, Math.min(925, x)), y: Math.max(40, Math.min(570, y)) }};
    }}

    // Color by Governing Level
    function getGovColor(gov) {{
      if (gov.includes('City')) return '#3b82f6'; // Blue
      if (gov.includes('State')) return '#f59e0b'; // Amber
      if (gov.includes('Federal')) return '#a855f7'; // Purple
      if (gov.includes('Company')) return '#10b981'; // Emerald
      if (gov.includes('County')) return '#f43f5e'; // Rose
      return '#64748b'; // Slate
    }}

    // State 2-letter postal code coordinates for labels
    const STATE_CENTROIDS = {{
      "WA": [-120.5, 47.4], "OR": [-120.5, 43.9], "CA": [-119.5, 36.8], "NV": [-116.8, 39.3],
      "ID": [-114.6, 44.4], "UT": [-111.7, 39.3], "AZ": [-111.7, 34.3], "MT": [-109.6, 47.1],
      "WY": [-107.5, 43.0], "CO": [-105.5, 39.0], "NM": [-106.0, 34.4], "ND": [-100.5, 47.4],
      "SD": [-100.2, 44.4], "NE": [-99.8, 41.5], "KS": [-98.4, 38.5], "OK": [-97.5, 35.5],
      "TX": [-99.3, 31.5], "MN": [-94.3, 46.3], "IA": [-93.5, 42.0], "MO": [-92.5, 38.4],
      "AR": [-92.4, 34.8], "LA": [-92.0, 31.0], "WI": [-89.8, 44.6], "IL": [-89.2, 40.0],
      "MI": [-84.7, 44.3], "IN": [-86.3, 39.8], "KY": [-85.3, 37.5], "TN": [-86.3, 35.8],
      "MS": [-89.7, 32.7], "AL": [-86.8, 32.8], "GA": [-83.4, 32.7], "FL": [-81.7, 28.1],
      "OH": [-82.8, 40.2], "WV": [-80.6, 38.6], "VA": [-78.9, 37.5], "NC": [-79.4, 35.5],
      "SC": [-80.9, 33.9], "PA": [-77.6, 40.9], "NY": [-75.5, 43.0], "ME": [-69.2, 45.4],
      "VT": [-72.6, 44.1], "NH": [-71.6, 43.7], "MA": [-71.8, 42.2], "CT": [-72.7, 41.6],
      "NJ": [-74.5, 40.1], "MD": [-76.7, 39.0], "DE": [-75.5, 39.0]
    }};

    // D3 Zoom Control Functions
    function zoomIn() {{
      if (zoomBehavior) {{
        d3.select("#us-map-svg").transition().duration(300).call(zoomBehavior.scaleBy, 1.5);
      }}
    }}

    function zoomOut() {{
      if (zoomBehavior) {{
        d3.select("#us-map-svg").transition().duration(300).call(zoomBehavior.scaleBy, 0.67);
      }}
    }}

    function resetZoom() {{
      if (zoomBehavior) {{
        d3.select("#us-map-svg").transition().duration(600).ease(d3.easeCubicOut).call(zoomBehavior.transform, d3.zoomIdentity);
      }}
    }}

    function zoomToCoords(x, y, targetK = 4.8) {{
      if (!zoomBehavior) return;
      const width = 975;
      const height = 610;
      const tx = width / 2 - x * targetK;
      const ty = height / 2 - y * targetK;
      d3.select("#us-map-svg").transition()
        .duration(750)
        .ease(d3.easeCubicOut)
        .call(zoomBehavior.transform, d3.zoomIdentity.translate(tx, ty).scale(targetK));
    }}

    let fipsFeatureMap = {{}};

    // Calculate the precise top-center and bounding dimensions of a location's shaded geographic region
    function getLocationRegionGeom(loc) {{
      const cInfo = CITY_TO_COUNTY[loc.name];
      if (cInfo && cInfo.fips && usAtlasData) {{
        let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        let foundAny = false;
        const path = d3.geoPath();
        cInfo.fips.forEach(fips => {{
          const feat = fipsFeatureMap[fips];
          if (feat) {{
            const bounds = path.bounds(feat);
            if (bounds && bounds[0] && bounds[1]) {{
              foundAny = true;
              minX = Math.min(minX, bounds[0][0]);
              minY = Math.min(minY, bounds[0][1]);
              maxX = Math.max(maxX, bounds[1][0]);
              maxY = Math.max(maxY, bounds[1][1]);
            }}
          }}
        }});
        if (foundAny) {{
          const width = maxX - minX;
          const height = maxY - minY;
          return {{
            centerX: (minX + maxX) / 2,
            // Top-center: horizontally centered at (minX + maxX)/2, positioned right at top edge inside shaded region
            topY: minY + Math.max(2.5, Math.min(8.5, height * 0.12)),
            width: width,
            height: height
          }};
        }}
      }}

      // Fallback to projected coordinates if atlas not yet loaded or not mapped to FIPS
      const pt = projectCoords(loc.lat, loc.lon);
      if (pt) {{
        return {{
          centerX: pt.x,
          topY: pt.y - 10,
          width: 40,
          height: 30
        }};
      }}
      return null;
    }}

    // Dynamic County Region Shading & Bubble Cross-Fading Engine
    function updateCountyShading(k) {{
      // Smooth morphing threshold:
      // k < 2.2: National Bubble Mode (shadeFactor = 0, bubbleOpacity = 1)
      // 2.2 <= k < 3.2: Cross-fade transition between bubbles and shaded regions
      // k >= 3.2: County Shaded Boundary View (shadeFactor = 1, bubbleOpacity = 0)
      const shadeFactor = Math.min(1, Math.max(0, (k - 2.2) / 1.0));
      const bubbleOpacity = Math.max(0, 1 - (k - 2.2) / 0.9);

      // 1. Cross-fade point bubbles layer
      const bubbleLayer = d3.select("#map-bubbles-layer");
      const bubbleLabelsLayer = d3.select("#map-bubble-labels-layer");
      bubbleLayer.style("opacity", bubbleOpacity);
      bubbleLabelsLayer.style("opacity", bubbleOpacity);
      bubbleLayer.style("pointer-events", bubbleOpacity <= 0.05 ? "none" : "auto");

      // 2. Cross-fade county region shading
      d3.selectAll(".county-path").each(function(d) {{
        if (!d || !d.id) return;
        const countyEl = d3.select(this);
        const policy = getCountyActivePolicy(d.id);

        if (policy.count > 0) {{
          if (shadeFactor > 0) {{
            // Shaded region with distinct municipal policy color
            countyEl
              .classed("county-shaded-active", true)
              .style("fill", policy.color)
              .style("fill-opacity", 0.72 * shadeFactor)
              .style("stroke", shadeFactor > 0.4 ? policy.color : "#2a3a4f")
              .style("stroke-width", `${{Math.max(0.4, (1.2 * shadeFactor + 0.3) / k)}}px`);
          }} else {{
            countyEl
              .classed("county-shaded-active", false)
              .style("fill", "#1e293b")
              .style("fill-opacity", 1)
              .style("stroke", "#2a3a4f")
              .style("stroke-width", `${{Math.max(0.2, 0.45 / k)}}px`);
          }}
        }} else if (policy.statewideCount > 0) {{
          // Subtle statewide policy background shading
          if (shadeFactor > 0) {{
            countyEl
              .classed("county-shaded-active", false)
              .style("fill", "#f59e0b")
              .style("fill-opacity", 0.12 * shadeFactor)
              .style("stroke", "#2a3a4f")
              .style("stroke-width", `${{Math.max(0.2, 0.45 / k)}}px`);
          }} else {{
            countyEl
              .classed("county-shaded-active", false)
              .style("fill", "#1e293b")
              .style("fill-opacity", 1)
              .style("stroke", "#2a3a4f")
              .style("stroke-width", `${{Math.max(0.2, 0.45 / k)}}px`);
          }}
        }} else {{
          // Default unshaded county
          countyEl
            .classed("county-shaded-active", false)
            .style("fill", "#1e293b")
            .style("fill-opacity", 1)
            .style("stroke", "#2a3a4f")
            .style("stroke-width", `${{Math.max(0.2, 0.45 / k)}}px`);
        }}
      }});

      // 3. Proportional Region Name Labels (Top-Center of Shaded Regions)
      const regionLabelsLayer = d3.select("#map-city-labels-layer");
      if (regionLabelsLayer) {{
        if (k < 2.2) {{
          regionLabelsLayer.style("opacity", "0");
        }} else {{
          const labelOpacity = Math.min(1, (k - 2.2) / 0.8);
          regionLabelsLayer.style("opacity", `${{labelOpacity}}`);

          // Proportional typography: scales smoothly with zoom factor k
          // Screen size stays balanced between 11px and 15px
          const targetSvgFs = Math.max(2.0, Math.min(10, 10.5 / Math.pow(k, 0.78)));
          const targetStrokeWidth = Math.max(0.4, 2.4 / k);

          regionLabelsLayer.selectAll(".region-name-label").each(function() {{
            const textEl = d3.select(this);
            const maxFs = parseFloat(textEl.attr("data-max-fs") || 12);
            const appliedFs = Math.min(targetSvgFs, maxFs);
            textEl.style("font-size", `${{appliedFs}}px`);
            textEl.style("stroke-width", `${{targetStrokeWidth}}px`);
          }});
        }}
      }}

      // 4. Update Zoom Tier Badge
      let tierName = "National Bubble View";
      if (k >= 3.2) {{
        tierName = "County Shaded View";
      }} else if (k >= 2.2) {{
        tierName = "Morphing to Shaded Regions";
      }}
      const badgeEl = document.getElementById("zoom-badge-text");
      if (badgeEl) badgeEl.textContent = `${{k.toFixed(1)}}x (${{tierName}})`;
    }}

    function handleZoom(event) {{
      const {{ transform }} = event;
      const k = transform.k;
      currentZoomK = k;

      // 1. Transform the master zoom group
      d3.select("#map-zoom-group").attr("transform", transform);

      // 2. Update dynamic county shading & bubble cross-fading
      updateCountyShading(k);

      // 3. Counter-scale state boundary & mesh stroke
      d3.selectAll(".state-boundary").style("stroke-width", `${{Math.max(0.4, 1.2 / k)}}px`);
      d3.selectAll(".state-mesh").style("stroke-width", `${{Math.max(0.5, 1.4 / k)}}px`);
      d3.selectAll(".county-mesh").style("stroke-width", `${{Math.max(0.15, 0.35 / k)}}px`);

      // 4. State 2-letter labels fade out smoothly at regional/county zoom
      const stateLabelsLayer = d3.select("#map-state-labels-layer");
      if (k >= 2.8) {{
        stateLabelsLayer.style("opacity", "0");
      }} else if (k >= 1.8) {{
        stateLabelsLayer.style("opacity", `${{Math.max(0, 1 - (k - 1.8) * 1.0)}}`);
      }} else {{
        stateLabelsLayer.style("opacity", "0.7");
      }}

      // 5. Counter-scale bubble radius & stroke
      d3.selectAll(".city-bubble").each(function() {{
        const el = d3.select(this);
        const baseR = parseFloat(el.attr("data-base-r") || el.attr("r"));
        el.attr("r", baseR / Math.pow(k, 0.42));
        el.style("stroke-width", `${{Math.max(0.6, 1.8 / k)}}px`);
      }});

      // 6. Counter-scale bubble numeric text
      d3.selectAll(".bubble-count-text").each(function() {{
        const el = d3.select(this);
        const baseFs = parseFloat(el.attr("data-base-fs") || 10);
        el.style("font-size", `${{Math.max(5.5, baseFs / Math.pow(k, 0.35))}}px`);
      }});
    }}


    function initDashboard() {{
      // Dynamically initialize header and top stats from DATA.metadata
      if (DATA && DATA.metadata) {{
        document.getElementById('stat-total-header').textContent = `${{DATA.metadata.total_sources}} Sources`;
        document.getElementById('stat-sources').textContent = `${{DATA.metadata.total_sources}} Sources`;
        document.getElementById('stat-sources-sub').textContent = `${{DATA.metadata.localized_sources}} Localized + ${{DATA.metadata.nationwide_sources}} Federal/National`;
        document.getElementById('stat-locations').textContent = `${{DATA.metadata.unique_locations}} Locations`;
        document.getElementById('stat-years').textContent = DATA.metadata.year_range;
      }}

      initSliderTicks();
      initHighPrecisionMap();
      renderLeaderboard();
      updateSelectedEraCard();
      updateNationwideHud();

      document.getElementById('json-file-input').addEventListener('change', handleFileUpload);
    }}

    function initSliderTicks() {{
      const ticksContainer = document.getElementById('slider-ticks');
      ticksContainer.innerHTML = '';
      
      const slider = document.getElementById('timeline-slider');
      slider.max = DATA.all_years.length; // index DATA.all_years.length = All Years
      slider.value = DATA.all_years.length;

      DATA.all_years.forEach((yr, idx) => {{
        if (idx % 2 === 0 || idx === DATA.all_years.length - 1) {{
          const span = document.createElement('span');
          span.textContent = "'" + yr.slice(2);
          ticksContainer.appendChild(span);
        }}
      }});
      const allSpan = document.createElement('span');
      allSpan.textContent = 'All';
      allSpan.className = 'font-bold text-amber-400';
      ticksContainer.appendChild(allSpan);
    }}

    function getActiveYear() {{
      if (activeYearIndex >= DATA.all_years.length) return 'ALL';
      return DATA.all_years[activeYearIndex];
    }}

    function onTimelineChange(val) {{
      activeYearIndex = parseInt(val);
      const activeYear = getActiveYear();
      
      document.getElementById('selected-year-badge').textContent = (activeYear === 'ALL') ? 'All Years' : activeYear;
      updateSelectedEraCard();
      updateNationwideHud();
      renderMap();
      renderLeaderboard();
      if (selectedLocation) renderLocationDetail(selectedLocation);
    }}

    function toggleCumulativeMode() {{
      isCumulativeMode = !isCumulativeMode;
      document.getElementById('mode-text').textContent = isCumulativeMode ? 'Cumulative Thru Year' : 'Single Year';
      document.getElementById('toggle-cumulative-btn').className = isCumulativeMode 
        ? 'bg-blue-600/30 text-blue-400 border border-blue-500/40 text-xs px-3 py-1.5 rounded-lg transition font-medium'
        : 'bg-slate-800 text-slate-300 border border-slate-700 text-xs px-3 py-1.5 rounded-lg transition font-medium';
      renderMap();
      renderLeaderboard();
    }}

    function togglePlayTimeline() {{
      isPlaying = !isPlaying;
      const btnIcon = document.getElementById('play-btn-icon');
      const btnText = document.getElementById('play-btn-text');

      if (isPlaying) {{
        btnIcon.textContent = '⏸';
        btnText.textContent = 'Pause';
        if (activeYearIndex >= DATA.all_years.length) activeYearIndex = 0;
        
        playInterval = setInterval(() => {{
          activeYearIndex++;
          if (activeYearIndex > DATA.all_years.length) {{
            activeYearIndex = DATA.all_years.length;
            togglePlayTimeline();
            return;
          }}
          document.getElementById('timeline-slider').value = activeYearIndex;
          onTimelineChange(activeYearIndex);
        }}, 1400);
      }} else {{
        btnIcon.textContent = '▶';
        btnText.textContent = 'Play Timeline';
        clearInterval(playInterval);
      }}
    }}

    function updateNationwideHud() {{
      const year = getActiveYear();
      const badge = document.getElementById('nationwide-badge-count');
      const desc = document.getElementById('nationwide-hud-desc');
      const nw = DATA.nationwide;

      if (!nw) return;

      let count = 0;
      if (year === 'ALL') {{
        count = nw.total_count;
        badge.textContent = `${{count}} Policies (All 50 States)`;
        desc.textContent = "USDOT/NHTSA app safety mandates, Latimer bridge strike legislation, and nationwide Google Maps eco-routing algorithms that apply coast-to-coast.";
      }} else if (isCumulativeMode) {{
        Object.keys(nw.years).forEach(yr => {{
          if (yr <= year) count += nw.years[yr];
        }});
        badge.textContent = `${{count}} Policies Thru ${{year}}`;
        desc.textContent = `Cumulative federal rules and nationwide platform routing rollouts deployed up to ${{year}}.`;
      }} else {{
        count = nw.years[year] || 0;
        badge.textContent = `${{count}} Policies in ${{year}}`;
        desc.textContent = count > 0 
          ? `Federal regulations and platform features announced nationwide during ${{year}}.`
          : `No new nationwide/federal policy mandates launched in ${{year}} (local municipal activity continued).`;
      }}
    }}

    function setNationwideHighlight(active) {{
      const countyPaths = document.querySelectorAll('.county-path');
      const stateBorders = document.querySelectorAll('.state-mesh, .state-boundary');
      countyPaths.forEach(p => {{
        if (active || isNationwideSelected) {{
          p.classList.add('nationwide-active');
        }} else {{
          p.classList.remove('nationwide-active');
        }}
      }});
      stateBorders.forEach(p => {{
        if (active || isNationwideSelected) {{
          p.classList.add('nationwide-active');
        }} else {{
          p.classList.remove('nationwide-active');
        }}
      }});
    }}

    function selectNationwideScope() {{
      isNationwideSelected = true;
      setNationwideHighlight(true);
      selectedLocation = null;

      const year = getActiveYear();
      const nw = DATA.nationwide;
      
      let articles = [];
      if (year === 'ALL') {{
        articles = nw.articles;
      }} else if (isCumulativeMode) {{
        articles = nw.articles.filter(a => a.year <= year);
      }} else {{
        articles = nw.articles.filter(a => a.year === year);
      }}

      document.getElementById('loc-badge-count').textContent = `${{articles.length}} Federal Policies`;
      document.getElementById('loc-badge-count').className = 'text-xs font-bold text-sky-400 bg-sky-500/10 px-2.5 py-0.5 rounded-full border border-sky-500/20';

      const detailDiv = document.getElementById('location-detail-content');
      detailDiv.innerHTML = `
        <div class="bg-sky-950/40 border border-sky-800/60 rounded-lg p-3 text-xs mb-3">
          <div class="font-bold text-sky-300 flex items-center gap-1.5">
            <span>🇺🇸 Federal & Nationwide Scope</span>
          </div>
          <p class="text-slate-300 mt-1">
            These policies are systemic federal mandates (USDOT, NHTSA, Congress) or platform-wide routing algorithm rollouts (Google Maps, Waze for Cities, Esri GIS) that apply across all 50 states simultaneously.
          </p>
        </div>
      `;

      if (articles.length === 0) {{
        detailDiv.innerHTML += `
          <div class="text-slate-500 text-center py-6">
            No nationwide federal policies enacted in ${{year}}.
          </div>
        `;
        return;
      }}

      articles.forEach(art => {{
        const card = document.createElement('div');
        card.className = 'bg-slate-950/80 border border-slate-800 rounded-lg p-3 space-y-1.5 transition hover:border-slate-700';
        card.innerHTML = `
          <div class="flex items-center justify-between">
            <span class="text-[11px] font-bold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded">${{art.year}}</span>
            <span class="text-[11px] text-purple-400 font-semibold">${{art.gov}}</span>
          </div>
          <div class="font-bold text-white text-xs leading-snug">${{art.title}}</div>
          <div class="text-[11px] text-slate-400 font-mono"><strong>Authority:</strong> ${{art.authority || 'U.S. Federal / Platform'}}</div>
          <p class="text-slate-300 text-[11px] leading-relaxed">${{art.summary}}</p>
        `;
        detailDiv.appendChild(card);
      }});
    }}

    function updateSelectedEraCard() {{
      const year = getActiveYear();
      const title = document.getElementById('era-title');
      const desc = document.getElementById('era-description');

      if (year === 'ALL') {{
        title.textContent = `Cumulative Corpus Overview (${{DATA.metadata.year_range}})`;
        desc.textContent = `Displaying all ${{DATA.metadata.total_sources}} verified traffic and navigation policy sources across ${{DATA.metadata.unique_locations}} geographic locations.`;
      }} else if (year <= '2016') {{
        title.textContent = `${{year}}: Initial Waze Expansion & Early City Pushback`;
        desc.textContent = 'Early municipal debates over shortcut traffic; Los Angeles and Boston pilot initial Connected Citizens data exchanges.';
      }} else if (year <= '2019') {{
        title.textContent = `${{year}}: The Leonia Commuter Ban & Judicial Review`;
        desc.textContent = 'Peak residential street access bans (Leonia, NJ closes 60 streets); NYC congestion studies and congressional hearings.';
      }} else if (year <= '2022') {{
        title.textContent = `${{year}}: COVID Slow Streets & Cloud Data Synchronization`;
        desc.textContent = 'Waze for Cities integrates with Google Cloud; pandemic neighborhood greenway diverters implemented in Seattle and Chicago.';
      }} else {{
        title.textContent = `${{year}}: Eco-Routing, Speed Cameras & Autonomous Vehicle Pilots`;
        desc.textContent = 'Google Maps defaults to fuel-efficient routing; Waymo robotaxis crowdsource potholes with Waze; automated camera enforcement.';
      }}
    }}

    // High-Precision D3 TopoJSON County & State Map Initializer
    function initHighPrecisionMap() {{
      const svg = d3.select("#us-map-svg");
      const countiesLayer = svg.select("#map-counties-layer");
      const countyMeshLayer = svg.select("#map-county-mesh-layer");
      const statesLayer = svg.select("#map-states-layer");
      const stateMeshLayer = svg.select("#map-state-mesh-layer");
      const stateLabelsLayer = svg.select("#map-state-labels-layer");

      // Initialize D3 Zoom Behavior with trackpad, pinch & drag
      zoomBehavior = d3.zoom()
        .scaleExtent([1, 14])
        .translateExtent([[-150, -100], [1125, 710]])
        .on("zoom", handleZoom);

      svg.call(zoomBehavior);

      // Load canonical TopoJSON US Atlas with all 3,142 pre-projected counties
      const usAtlasUrl = "https://cdn.jsdelivr.net/npm/us-atlas@3/counties-albers-10m.json";

      d3.json(usAtlasUrl).then(us => {{
        if (!us || !us.objects) return;
        usAtlasData = us;

        const path = d3.geoPath(); // Pre-projected Albers coordinates matching 975x610 viewport

        // 1. Render all 3,142 U.S. Counties (Clickable & Hoverable down to municipal precision)
        if (us.objects.counties) {{
          const counties = topojson.feature(us, us.objects.counties).features;
          fipsFeatureMap = {{}};
          counties.forEach(f => {{
            fipsFeatureMap[f.id] = f;
          }});
          countiesLayer.selectAll("path")
            .data(counties)
            .join("path")
            .attr("d", path)
            .attr("class", d => {{
              const hasPolicy = FIPS_TO_LOCATIONS[d.id] ? "county-has-policy" : "";
              return `county-path ${{hasPolicy}}`;
            }})
            .attr("id", d => "county-" + (d.id || ""))
            .on("mouseenter", (event, d) => handleCountyHover(event, d))
            .on("mouseleave", hideTooltip)
            .on("click", (event, d) => handleCountyClick(event, d, path));

          // Render Interior County Mesh (Crisp boundaries between adjacent counties)
          countyMeshLayer.append("path")
            .datum(topojson.mesh(us, us.objects.counties, (a, b) => a !== b))
            .attr("d", path)
            .attr("class", "county-mesh");
        }}

        // 2. Render State Boundaries & Outer Nation Outline
        if (us.objects.states) {{
          stateMeshLayer.append("path")
            .datum(topojson.mesh(us, us.objects.states, (a, b) => a !== b))
            .attr("d", path)
            .attr("class", "state-mesh");

          if (us.objects.nation) {{
            statesLayer.append("path")
              .datum(topojson.feature(us, us.objects.nation))
              .attr("d", path)
              .attr("class", "state-boundary")
              .style("stroke", "#64748b")
              .style("stroke-width", "1.6px")
              .style("fill", "none");
          }}
        }}

        // 3. Render 2-Letter State Postal Codes (CA, TX, NY...)
        renderStateLabels();

        // 4. Render Localized City Bubbles, Count Badges & City Name Badges
        renderMap();
      }}).catch(err => {{
        console.warn("Could not load online TopoJSON, drawing vector fallback:", err);
        drawFallbackStates(statesLayer);
        renderMap();
      }});
    }}

    function renderStateLabels() {{
      const stateLabelsLayer = d3.select("#map-state-labels-layer");
      stateLabelsLayer.selectAll("text").remove();
      Object.entries(STATE_CENTROIDS).forEach(([code, coords]) => {{
        const pt = projectCoords(coords[1], coords[0]);
        if (pt && pt.x > 50 && pt.x < 925 && pt.y > 40 && pt.y < 570) {{
          stateLabelsLayer.append("text")
            .attr("x", pt.x)
            .attr("y", pt.y)
            .attr("text-anchor", "middle")
            .attr("dominant-baseline", "central")
            .attr("fill", "#64748b")
            .attr("font-size", "10px")
            .attr("font-weight", "700")
            .attr("letter-spacing", "0.6px")
            .attr("opacity", "0.7")
            .text(code);
        }}
      }});
    }}

    // Fallback vector states outline if offline
    function drawFallbackStates(statesLayer) {{
      statesLayer.html(`
        <path d="M 140,95 L 220,95 L 300,95 L 380,95 L 450,90 L 520,80 L 580,75 L 610,65 L 670,60 L 720,70 L 760,60 L 800,85 L 830,120 L 860,110 L 880,140 L 860,170 L 840,195 L 830,240 L 800,280 L 800,320 L 780,360 L 790,410 L 770,440 L 760,490 L 730,460 L 700,430 L 640,430 L 580,450 L 530,460 L 490,520 L 460,540 L 420,490 L 370,460 L 320,440 L 250,440 L 190,420 L 140,360 L 110,320 L 100,240 L 90,170 L 110,120 Z" class="state-path" />
        <path d="M 230,95 L 220,440 M 340,95 L 340,450 M 470,95 L 460,530 M 590,80 L 580,450 M 710,65 L 700,430 M 120,220 L 830,220 M 150,330 L 800,330" stroke="#334155" stroke-dasharray="3 3" opacity="0.4" fill="none" />
      `);
    }}

    function handleCountyHover(event, d) {{
      const stateCode = STATE_FIPS_MAP[d.id.slice(0, 2)] || "";
      const stateName = STATE_NAME_MAP[stateCode] || stateCode;
      const rawName = (d.properties && d.properties.name) ? d.properties.name : "County";
      const countyName = rawName + (rawName.toLowerCase().includes("city") || rawName.toLowerCase().includes("parish") || stateCode === "DC" ? "" : " County");

      const policy = getCountyActivePolicy(d.id);
      const title = `${{countyName}}, ${{stateCode}}`;
      let body = "";
      if (policy.count > 0) {{
        body = `<div class="text-amber-400 font-bold mb-1">${{policy.count}} Routing Policy Sources</div>` +
               `<div class="text-slate-300">Coverage: <strong class="text-white">${{policy.cities.join(", ")}}</strong> (${{policy.topGov}})</div>` +
               `<div class="text-[11px] text-slate-400 mt-1">Click shaded county to inspect local policy records.</div>`;
      }} else if (policy.statewideCount > 0) {{
        body = `<div class="text-amber-300 font-bold mb-1">${{policy.statewideCount}} Statewide Policy Sources</div>` +
               `<div class="text-slate-300">Jurisdiction: <strong class="text-white">${{stateName}}</strong> (State DOT)</div>` +
               `<div class="text-[11px] text-slate-400 mt-1">Click to zoom and inspect regional routing policies.</div>`;
      }} else {{
        body = `<div class="text-slate-400 font-medium">Jurisdiction: ${{stateName}}</div>` +
               `<div class="text-slate-500 text-[11px] mt-0.5">Click to zoom and inspect regional routing policies.</div>`;
      }}
      showTooltip(event, title, body);
    }}

    function handleCountyClick(event, d, path) {{
      const stateCode = STATE_FIPS_MAP[d.id.slice(0, 2)] || "";
      const stateName = STATE_NAME_MAP[stateCode] || stateCode;
      const rawName = (d.properties && d.properties.name) ? d.properties.name : "County";
      const countyName = rawName + (rawName.toLowerCase().includes("city") || rawName.toLowerCase().includes("parish") || stateCode === "DC" ? "" : " County");

      // Smoothly zoom in to the centroid of this county if from national view
      const centroid = path.centroid(d);
      if (centroid && !isNaN(centroid[0]) && !isNaN(centroid[1])) {{
        if (currentZoomK < 3.2) {{
          zoomToCoords(centroid[0], centroid[1], 4.8);
        }}
      }}

      const policy = getCountyActivePolicy(d.id);

      if (policy.locations && policy.locations.length > 0) {{
        selectLocation(policy.locations[0], false);
      }} else {{
        // Present county jurisdiction overview card
        selectedLocation = null;
        isNationwideSelected = false;
        setNationwideHighlight(false);

        document.getElementById('loc-badge-count').textContent = `County Jurisdiction`;
        document.getElementById('loc-badge-count').className = 'text-xs font-bold text-slate-400 bg-slate-800 px-2.5 py-0.5 rounded-full border border-slate-700';

        const detailDiv = document.getElementById('location-detail-content');
        detailDiv.innerHTML = `
          <div class="bg-slate-950 p-3.5 rounded-lg border border-slate-800 text-xs mb-3 space-y-2">
            <div class="font-bold text-white text-sm flex items-center gap-2">
              <span>🏛️</span> <span>${{countyName}}, ${{stateCode}}</span>
            </div>
            <div class="text-[11px] text-slate-400 font-mono">FIPS: ${{d.id}} • State Jurisdiction: ${{stateName}}</div>
            <p class="text-slate-300 text-xs leading-relaxed mt-2">
              No specific municipal street bans or local anti-shortcut ordinances were identified specifically inside this county in the research corpus.
              Traffic management across this county is governed under ${{stateName}} DOT highway specifications and federal routing standards.
            </p>
          </div>
        `;
      }}
    }}

    function renderMap() {{
      const bubbleLayer = document.getElementById('map-bubbles-layer');
      const bubbleLabelsLayer = document.getElementById('map-bubble-labels-layer');
      const cityLabelsLayer = document.getElementById('map-city-labels-layer');
      bubbleLayer.innerHTML = '';
      bubbleLabelsLayer.innerHTML = '';
      if (cityLabelsLayer) cityLabelsLayer.innerHTML = '';
      const activeYear = getActiveYear();

      DATA.locations.forEach(loc => {{
        let count = 0;
        if (activeYear === 'ALL') {{
          count = loc.total_count;
        }} else if (isCumulativeMode) {{
          Object.keys(loc.years).forEach(yr => {{
            if (yr <= activeYear) count += loc.years[yr];
          }});
        }} else {{
          count = loc.years[activeYear] || 0;
        }}

        // If count is 0 in single-year mode, do not render a bubble
        if (count === 0) return;

        const coords = projectCoords(loc.lat, loc.lon);
        if (!coords) return;
        
        // Find dominant governing level
        let topGov = 'Company';
        let maxGovCount = -1;
        Object.entries(loc.gov_levels).forEach(([gov, cnt]) => {{
          if (cnt > maxGovCount) {{ maxGovCount = cnt; topGov = gov; }}
        }});
        const color = getGovColor(topGov);

        // Radius calculation: calm, static, proportional
        const baseRadius = (activeYear === 'ALL') 
          ? Math.min(30, Math.max(7, Math.sqrt(count) * 6))
          : Math.min(26, Math.max(8, Math.sqrt(count) * 9));

        // SVG Group for localized pin
        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        g.setAttribute('class', 'cursor-pointer');
        g.onclick = () => selectLocation(loc, true);

        // Main Bubble Circle - Counter-scaled by currentZoomK
        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('cx', coords.x);
        circle.setAttribute('cy', coords.y);
        circle.setAttribute('r', baseRadius / Math.pow(currentZoomK, 0.42));
        circle.setAttribute('data-base-r', baseRadius);
        circle.setAttribute('fill', color);
        circle.setAttribute('fill-opacity', (activeYear !== 'ALL' && !isCumulativeMode) ? '0.9' : '0.75');
        circle.setAttribute('stroke', '#ffffff');
        circle.setAttribute('stroke-width', Math.max(0.6, 1.8 / currentZoomK));
        circle.setAttribute('class', 'city-bubble');

        const countyInfo = CITY_TO_COUNTY[loc.name];
        const countyLabel = countyInfo ? ` (${{countyInfo.county}})` : '';

        circle.onmouseenter = (e) => {{
          showTooltip(e, `<strong class="text-white">${{loc.name}}</strong>${{countyLabel}}`, 
            `<span class="text-amber-400 font-bold">${{count}} Policies</span> (${{topGov}})<br/><span class="text-[11px] text-slate-400">Click to zoom and view policies</span>`);
        }};
        circle.onmouseleave = hideTooltip;

        g.appendChild(circle);
        bubbleLayer.appendChild(g);

        // Inner text count inside bubble for quick legibility
        if (baseRadius >= 9) {{
          const baseFontSize = baseRadius > 14 ? 11 : 9;
          const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
          text.setAttribute('x', coords.x);
          text.setAttribute('y', coords.y + 1);
          text.setAttribute('text-anchor', 'middle');
          text.setAttribute('dominant-baseline', 'central');
          text.setAttribute('fill', '#ffffff');
          text.setAttribute('data-base-fs', baseFontSize);
          text.setAttribute('font-size', `${{Math.max(5.5, baseFontSize / Math.pow(currentZoomK, 0.35))}}px`);
          text.setAttribute('font-weight', 'bold');
          text.setAttribute('class', 'bubble-count-text pointer-events-none select-none');
          text.textContent = count;
          bubbleLabelsLayer.appendChild(text);
        }}

        // Dynamic Shaded Region Name Label on Top-Center (revealed when morphed into shaded region)
        if (cityLabelsLayer) {{
          const geom = getLocationRegionGeom(loc);
          if (geom) {{
            const labelText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            labelText.setAttribute('x', geom.centerX);
            labelText.setAttribute('y', geom.topY);
            labelText.setAttribute('class', 'region-name-label pointer-events-none select-none');
            
            // Calculate proportional max font size so label scales proportionally with the region
            const maxAllowedFs = Math.max(2.2, (geom.width * 0.90) / (loc.name.length * 0.58));
            labelText.setAttribute('data-max-fs', maxAllowedFs);
            labelText.textContent = loc.name;

            cityLabelsLayer.appendChild(labelText);
          }}
        }}
      }});

      // Synchronize county shading & bubble cross-fade for active timeframe
      updateCountyShading(currentZoomK);
    }}

    function renderLeaderboard() {{
      const leaderboardDiv = document.getElementById('locations-leaderboard');
      leaderboardDiv.innerHTML = '';
      const activeYear = getActiveYear();

      // Collect counts for active view
      const rankedLocs = [];
      DATA.locations.forEach(loc => {{
        let count = 0;
        if (activeYear === 'ALL') {{
          count = loc.total_count;
        }} else if (isCumulativeMode) {{
          Object.keys(loc.years).forEach(yr => {{
            if (yr <= activeYear) count += loc.years[yr];
          }});
        }} else {{
          count = loc.years[activeYear] || 0;
        }}
        if (count > 0) {{
          rankedLocs.push({{ name: loc.name, count: count, raw: loc }});
        }}
      }});

      rankedLocs.sort((a, b) => b.count - a.count);
      const maxCount = rankedLocs.length > 0 ? rankedLocs[0].count : 1;

      if (rankedLocs.length === 0) {{
        leaderboardDiv.innerHTML = '<div class="text-xs text-slate-500 text-center py-4">No local entries recorded for this year.</div>';
        return;
      }}

      rankedLocs.slice(0, 10).forEach((item, idx) => {{
        const pct = Math.min(100, Math.round((item.count / maxCount) * 100));
        const row = document.createElement('div');
        row.className = 'cursor-pointer p-1.5 rounded hover:bg-slate-800/60 transition text-xs';
        row.onclick = () => selectLocation(item.raw, true);

        row.innerHTML = `
          <div class="flex items-center justify-between mb-1">
            <span class="font-medium text-slate-200 truncate pr-2">
              <span class="text-slate-500 mr-1.5">#${{idx + 1}}</span> ${{item.name}}
            </span>
            <span class="font-bold text-white bg-slate-800 px-1.5 py-0.2 rounded">${{item.count}}</span>
          </div>
          <div class="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
            <div class="bg-blue-500 h-full rounded-full transition-all duration-300" style="width: ${{pct}}%"></div>
          </div>
        `;
        leaderboardDiv.appendChild(row);
      }});
    }}

    function selectLocation(loc, shouldZoom = true) {{
      selectedLocation = loc;
      isNationwideSelected = false;
      setNationwideHighlight(false);

      if (shouldZoom !== false) {{
        const coords = projectCoords(loc.lat, loc.lon);
        if (coords) zoomToCoords(coords.x, coords.y, 4.8);
      }}

      const activeYear = getActiveYear();
      let articles = [];
      if (activeYear === 'ALL') {{
        articles = loc.articles;
      }} else if (isCumulativeMode) {{
        articles = loc.articles.filter(a => a.year <= activeYear);
      }} else {{
        articles = loc.articles.filter(a => a.year === activeYear);
      }}

      const countyInfo = CITY_TO_COUNTY[loc.name];
      const countySubtitle = countyInfo ? `County Jurisdiction: ${{countyInfo.county}}` : 'Local municipal regulations and traffic interventions.';

      document.getElementById('loc-badge-count').textContent = `${{articles.length}} Articles`;
      document.getElementById('loc-badge-count').className = 'text-xs font-bold text-blue-400 bg-blue-500/10 px-2.5 py-0.5 rounded-full border border-blue-500/20';

      const detailDiv = document.getElementById('location-detail-content');
      detailDiv.innerHTML = `
        <div class="bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-xs mb-3">
          <div class="font-bold text-white text-sm flex items-center justify-between">
            <span>${{loc.name}}</span>
            ${{countyInfo ? `<span class="text-[10px] text-blue-400 font-mono font-normal">FIPS: ${{Array.isArray(countyInfo.fips) ? countyInfo.fips.join(', ') : countyInfo.fips}}</span>` : ''}}
          </div>
          <div class="text-[11px] text-slate-400 mt-0.5">${{countySubtitle}}</div>
        </div>
      `;

      if (articles.length === 0) {{
        detailDiv.innerHTML += '<div class="text-slate-500 text-center py-6">No articles recorded for this timeframe.</div>';
        return;
      }}

      articles.forEach(art => {{
        const card = document.createElement('div');
        card.className = 'bg-slate-950/80 border border-slate-800 rounded-lg p-3 space-y-1.5 transition hover:border-slate-700';
        card.innerHTML = `
          <div class="flex items-center justify-between">
            <span class="text-[11px] font-bold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded">${{art.year}}</span>
            <span class="text-[11px] text-blue-400 font-semibold">${{art.gov}}</span>
          </div>
          <div class="font-bold text-white text-xs leading-snug">${{art.title}}</div>
          <div class="text-[11px] text-slate-400 font-mono"><strong>Authority:</strong> ${{art.authority || 'Local Jurisdiction'}}</div>
          <p class="text-slate-300 text-[11px] leading-relaxed">${{art.summary}}</p>
        `;
        detailDiv.appendChild(card);
      }});
    }}

    function showTooltip(event, title, body) {{
      const tip = document.getElementById('map-tooltip');
      document.getElementById('tooltip-title').innerHTML = title;
      document.getElementById('tooltip-body').innerHTML = body;
      tip.style.left = (event.pageX + 12) + 'px';
      tip.style.top = (event.pageY - 28) + 'px';
      tip.classList.remove('hidden');
    }}

    function hideTooltip() {{
      document.getElementById('map-tooltip').classList.add('hidden');
    }}

    function switchTab(tabId) {{
      document.querySelectorAll('.tab-pane').forEach(el => el.classList.add('hidden'));
      document.querySelectorAll('.tab-btn').forEach(btn => {{
        btn.className = 'tab-btn px-4 py-2 rounded-lg text-sm font-medium text-slate-400 hover:text-white hover:bg-slate-800';
      }});

      document.getElementById(tabId).classList.remove('hidden');
      const activeBtn = document.querySelector(`button[onclick="switchTab('${{tabId}}')"]`);
      if (activeBtn) {{
        activeBtn.className = 'tab-btn px-4 py-2 rounded-lg text-sm font-medium bg-blue-600 text-white shadow';
      }}
    }}

    function handleFileUpload(e) {{
      const file = e.target.files[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = function(evt) {{
        try {{
          const uploadedData = JSON.parse(evt.target.result);
          DATA.metadata.total_sources = uploadedData.length;
          document.getElementById('stat-total-header').textContent = `${{uploadedData.length}} Sources`;
          alert(`Successfully uploaded ${{uploadedData.length}} updated research sources! The dashboard is refreshed.`);
        }} catch(err) {{
          alert("Error parsing JSON file: " + err.message);
        }}
      }};
      reader.readAsText(file);
    }}

    // Boot on page load
    window.addEventListener('DOMContentLoaded', initDashboard);
  </script>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate interactive research infographics dashboard.")
    parser.add_argument(
        "--input",
        default="data/exports/research_analysis_all_sources.json",
        help="Input research analysis json file",
    )
    parser.add_argument(
        "--output",
        default="data/exports/research_infographics.html",
        help="Output HTML infographics file",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"Error: input file {input_path} not found.")
        return 1

    print(f"Reading research analysis records from {input_path}...")
    dataset = build_infographic_dataset(input_path)

    print(
        f"Processed {dataset['metadata']['total_sources']} sources: "
        f"{dataset['metadata']['localized_sources']} localized across "
        f"{dataset['metadata']['unique_locations']} locations + "
        f"{dataset['metadata']['nationwide_sources']} federal/nationwide policies "
        f"({dataset['metadata']['year_range']})."
    )

    html_content = generate_html_infographics(dataset)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_content, encoding="utf-8")
    print(f"Saved interactive infographics to {output_path}")

    # Mirror to antigravity brain artifact directory
    artifact_dir = Path("/Users/isabelle/.gemini/antigravity/brain/b83e007b-8917-4635-8cf5-17130e87b3c1")
    if artifact_dir.exists():
        mirror_path = artifact_dir / "research_infographics_dashboard.html"
        mirror_path.write_text(html_content, encoding="utf-8")
        print(f"Mirrored artifact dashboard to {mirror_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
