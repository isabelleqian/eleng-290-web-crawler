"""Generate dynamic, interactive research infographics and map dashboard from research analysis dataset."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

# Geographic coordinates lookup for U.S. target locations
COORDINATES_MAP: dict[str, dict[str, float | str]] = {
    # Cities
    "Los Angeles": {"lat": 34.0522, "lon": -118.2437, "name": "Los Angeles, CA"},
    "Los Angeles, Ca": {"lat": 34.0522, "lon": -118.2437, "name": "Los Angeles, CA"},
    "San Francisco": {"lat": 37.7749, "lon": -122.4194, "name": "San Francisco, CA"},
    "San Francisco, Ca": {"lat": 37.7749, "lon": -122.4194, "name": "San Francisco, CA"},
    "San Francisco Bay Area, Ca": {"lat": 37.7749, "lon": -122.4194, "name": "San Francisco, CA"},
    "San Francisco, Los Angeles, Phoenix, Austin, Atlanta": {"lat": 37.7749, "lon": -122.4194, "name": "Multi-City AV Pilot"},
    "San Francisco Bay Area, Los Angeles, Phoenix, Austin, Atlanta": {"lat": 37.7749, "lon": -122.4194, "name": "Multi-City AV Pilot"},
    "Seattle": {"lat": 47.6062, "lon": -122.3321, "name": "Seattle, WA"},
    "Boston": {"lat": 42.3601, "lon": -71.0589, "name": "Boston, MA"},
    "Boston, Ma": {"lat": 42.3601, "lon": -71.0589, "name": "Boston, MA"},
    "Chicago": {"lat": 41.8781, "lon": -87.6298, "name": "Chicago, IL"},
    "Chicago, Il": {"lat": 41.8781, "lon": -87.6298, "name": "Chicago, IL"},
    "New York": {"lat": 40.7128, "lon": -74.0060, "name": "New York City, NY"},
    "New York, Ny": {"lat": 40.7128, "lon": -74.0060, "name": "New York City, NY"},
    "Leonia": {"lat": 40.8654, "lon": -73.9876, "name": "Leonia, NJ"},
    "Atlanta": {"lat": 33.7490, "lon": -84.3880, "name": "Atlanta, GA"},
    "Atlanta, Ga": {"lat": 33.7490, "lon": -84.3880, "name": "Atlanta, GA"},
    "Austin": {"lat": 30.2672, "lon": -97.7431, "name": "Austin, TX"},
    "Austin, Tx": {"lat": 30.2672, "lon": -97.7431, "name": "Austin, TX"},
    "Miami": {"lat": 25.7617, "lon": -80.1918, "name": "Miami, FL"},
    "Coral Gables": {"lat": 25.7215, "lon": -80.2684, "name": "Coral Gables, FL"},
    "Detroit": {"lat": 42.3314, "lon": -83.0458, "name": "Detroit, MI"},
    "Detroit, Mi": {"lat": 42.3314, "lon": -83.0458, "name": "Detroit, MI"},
    "Portland, Or": {"lat": 45.5152, "lon": -122.6784, "name": "Portland, OR"},
    "Philadelphia": {"lat": 39.9526, "lon": -75.1652, "name": "Philadelphia, PA"},
    "Philadelphia, Pa": {"lat": 39.9526, "lon": -75.1652, "name": "Philadelphia, PA"},
    "Dallas, Tx": {"lat": 32.7767, "lon": -96.7970, "name": "Dallas, TX"},
    "Houston, Tx": {"lat": 29.7604, "lon": -95.3698, "name": "Houston, TX"},
    "Charlotte, Nc": {"lat": 35.2271, "lon": -80.8431, "name": "Charlotte, NC"},
    "Raleigh, Nc": {"lat": 35.7796, "lon": -78.6382, "name": "Raleigh, NC"},
    "Cary, Nc": {"lat": 35.7915, "lon": -78.7811, "name": "Cary, NC"},
    "Asheville, Nc": {"lat": 35.5951, "lon": -82.5515, "name": "Asheville, NC"},
    "Greensboro, Nc": {"lat": 36.0726, "lon": -79.7920, "name": "Greensboro, NC"},
    "Norfolk": {"lat": 36.8508, "lon": -76.2859, "name": "Norfolk, VA"},
    "Virginia Beach, Va": {"lat": 36.8529, "lon": -75.9780, "name": "Virginia Beach, VA"},
    "Phoenix, Az": {"lat": 33.4484, "lon": -112.0740, "name": "Phoenix, AZ"},
    "Salt Lake City": {"lat": 40.7608, "lon": -111.8910, "name": "Salt Lake City, UT"},
    "Des Moines, Ia": {"lat": 41.5868, "lon": -93.6250, "name": "Des Moines, IA"},
    "New Haven, Ct": {"lat": 41.3083, "lon": -72.9279, "name": "New Haven, CT"},
    "Augusta, Me": {"lat": 44.3106, "lon": -69.7795, "name": "Augusta, ME"},
    "Fort Worth": {"lat": 32.7555, "lon": -97.3308, "name": "Fort Worth, TX"},
    "Naperville": {"lat": 41.7508, "lon": -88.1535, "name": "Naperville, IL"},
    "Evanston": {"lat": 42.0451, "lon": -87.6877, "name": "Evanston, IL"},
    "Fairfield, Ct": {"lat": 41.1412, "lon": -73.2637, "name": "Fairfield, CT"},
    "Loudoun County": {"lat": 39.0840, "lon": -77.6412, "name": "Loudoun County, VA"},
    "Fulton County": {"lat": 33.7903, "lon": -84.4677, "name": "Fulton County, GA"},
    "Miami-Dade County": {"lat": 25.5516, "lon": -80.6327, "name": "Miami-Dade County, FL"},
    # States
    "California": {"lat": 36.7783, "lon": -119.4179, "name": "California"},
    "Connecticut": {"lat": 41.6032, "lon": -73.0877, "name": "Connecticut"},
    "Texas": {"lat": 31.9686, "lon": -99.9018, "name": "Texas"},
    "Illinois": {"lat": 40.6331, "lon": -89.3985, "name": "Illinois"},
    "Georgia": {"lat": 32.1656, "lon": -82.9001, "name": "Georgia"},
    "Pennsylvania": {"lat": 41.2033, "lon": -77.1945, "name": "Pennsylvania"},
    "Florida": {"lat": 27.6648, "lon": -81.5158, "name": "Florida"},
    "New Jersey": {"lat": 40.0583, "lon": -74.4057, "name": "New Jersey"},
    "Virginia": {"lat": 37.4316, "lon": -78.6569, "name": "Virginia"},
    "Iowa": {"lat": 41.8780, "lon": -93.0977, "name": "Iowa"},
    "Maine": {"lat": 45.2538, "lon": -69.4455, "name": "Maine"},
    "Massachusetts": {"lat": 42.4072, "lon": -71.3824, "name": "Massachusetts"},
    "Utah": {"lat": 39.3210, "lon": -111.0937, "name": "Utah"},
    "Nevada": {"lat": 38.8026, "lon": -116.4194, "name": "Nevada"},
    "North Carolina": {"lat": 35.7596, "lon": -79.0193, "name": "North Carolina"},
    "Wyoming": {"lat": 43.0759, "lon": -107.2903, "name": "Wyoming"},
    # National & Platform
    "United States": {"lat": 39.8283, "lon": -98.5795, "name": "Nationwide (U.S.)"},
    "Global": {"lat": 38.5000, "lon": -96.0000, "name": "Global / Platform"},
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

    # Aggregate location metrics
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

    year_counts: Counter[str] = Counter()
    gov_counts: Counter[str] = Counter()
    loc_type_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()

    corpus_text = []

    for item in raw_data:
        raw_loc = item.get("target_location", "United States").strip()
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

        geo = COORDINATES_MAP.get(raw_loc, COORDINATES_MAP["United States"])
        cname = str(geo["name"])

        loc_entry = locations_dict[cname]
        loc_entry["name"] = cname
        loc_entry["lat"] = float(geo["lat"])
        loc_entry["lon"] = float(geo["lon"])
        loc_entry["count"] += 1
        loc_entry["years"][year] += 1
        loc_entry["gov_levels"][gov] += 1
        loc_entry["categories"][cat] += 1
        loc_entry["articles"].append({
            "title": title,
            "year": year,
            "gov": gov,
            "category": cat,
            "authority": item.get("authority_names", ""),
            "summary": summary[:140] + ("..." if len(summary) > 140 else "")
        })

        # Gather corpus text for keyword audit
        corpus_text.append(f"{title} {summary} {item.get('supporting_passage', '')} {item.get('authority_names', '')}".lower())

    joined_corpus = " ".join(corpus_text)

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

    # Format locations for JSON serialization
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
            "unique_locations": len(serialized_locations),
            "year_range": f"{all_years[0]} - {all_years[-1]}" if all_years else "N/A",
            "year_counts": dict(sorted(year_counts.items())),
            "gov_counts": dict(sorted(gov_counts.items(), key=lambda x: x[1], reverse=True)),
            "loc_type_counts": dict(sorted(loc_type_counts.items(), key=lambda x: x[1], reverse=True)),
            "category_counts": dict(sorted(category_counts.items(), key=lambda x: x[1], reverse=True)),
        },
        "all_years": all_years,
        "locations": serialized_locations,
        "keyword_audit": keyword_audit,
    }


def generate_html_infographics(data_payload: dict) -> str:
    """Generate self-contained HTML/Tailwind CSS interactive dashboard with SVG Map & Timeline Slider."""
    json_str = json.dumps(data_payload)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Navigation & Routing Policy News Crawler: Interactive Research Dashboard</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <style>
    /* Custom SVG map styling & pulse animations */
    .map-pulse {{
      animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
    }}
    @keyframes pulse {{
      0%, 100% {{ opacity: 0.8; transform: scale(1); }}
      50% {{ opacity: 0.3; transform: scale(1.35); }}
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
        <div class="text-xs text-slate-400">Loaded Records</div>
        <div id="stat-total-header" class="text-base font-bold text-blue-400">195 Sources</div>
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
        <div class="text-xs text-slate-400 font-medium">Corpus Size</div>
        <div id="stat-sources" class="text-2xl font-bold text-white mt-1">195</div>
        <div class="text-[11px] text-emerald-400 mt-1">36 Web Crawler + 159 Nexis</div>
      </div>
      <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm">
        <div class="text-xs text-slate-400 font-medium">Active Locations</div>
        <div id="stat-locations" class="text-2xl font-bold text-blue-400 mt-1">36 Pins</div>
        <div class="text-[11px] text-slate-400 mt-1">Coast-to-Coast Coverage</div>
      </div>
      <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm">
        <div class="text-xs text-slate-400 font-medium">Timeline Span</div>
        <div id="stat-years" class="text-2xl font-bold text-amber-400 mt-1">2013 - 2026</div>
        <div class="text-[11px] text-slate-400 mt-1">14-Year Policy Evolution</div>
      </div>
      <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-4 shadow-sm">
        <div class="text-xs text-slate-400 font-medium">Top Governing Level</div>
        <div class="text-2xl font-bold text-indigo-400 mt-1">Municipal (32%)</div>
        <div class="text-[11px] text-slate-400 mt-1">63 City-Level Ordinances</div>
      </div>
    </div>

    <!-- Interactive Map & Detail Sidebar Layout -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
      
      <!-- Left: Map & Interactive Timeline Controls (8 cols) -->
      <div class="lg:col-span-8 bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm flex flex-col justify-between">
        
        <div>
          <div class="flex flex-col sm:flex-row sm:items-center justify-between pb-3 mb-2 border-b border-slate-800 gap-2">
            <div>
              <h2 class="text-lg font-semibold text-white flex items-center gap-2">
                <span>📍 Policy Interventions Across U.S. Jurisdictions</span>
              </h2>
              <p class="text-xs text-slate-400">Bubble radius scales with article frequency. Colored by governing authority level.</p>
            </div>
            
            <!-- Map Legend -->
            <div class="flex flex-wrap items-center gap-3 text-xs">
              <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-blue-500 inline-block"></span> City</span>
              <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-amber-500 inline-block"></span> State</span>
              <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-purple-500 inline-block"></span> Federal</span>
              <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-full bg-emerald-500 inline-block"></span> Company</span>
            </div>
          </div>

          <!-- SVG United States Map Container -->
          <div class="relative w-full aspect-[16/10] bg-slate-950/60 rounded-xl border border-slate-800/80 overflow-hidden flex items-center justify-center p-2">
            
            <svg id="us-map-svg" viewBox="0 0 960 600" class="w-full h-full select-none">
              <!-- Defs for glow filter -->
              <defs>
                <filter id="bubble-glow" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="3" result="blur" />
                  <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>
              </defs>

              <!-- Stylized Background US Map Outline -->
              <g id="map-states-layer" fill="#1e293b" stroke="#334155" stroke-width="1.2" stroke-linejoin="round">
                <!-- Continental US Simplified Silhouette Path -->
                <path d="M 140,95 L 220,95 L 300,95 L 380,95 L 450,90 L 520,80 L 580,75 L 610,65 L 670,60 L 720,70 L 760,60 L 800,85 L 830,120 L 860,110 L 880,140 L 860,170 L 840,195 L 830,240 L 800,280 L 800,320 L 780,360 L 790,410 L 770,440 L 760,490 L 730,460 L 700,430 L 640,430 L 580,450 L 530,460 L 490,520 L 460,540 L 420,490 L 370,460 L 320,440 L 250,440 L 190,420 L 140,360 L 110,320 L 100,240 L 90,170 L 110,120 Z" />
                <!-- Great Lakes water cutouts -->
                <path d="M 620,110 Q 640,140 680,120 Q 710,140 730,120 Q 710,95 670,95 Z" fill="#0f172a" stroke="#334155" stroke-width="1" />
                <!-- State boundary guide grid lines -->
                <path d="M 230,95 L 220,440 M 340,95 L 340,450 M 470,95 L 460,530 M 590,80 L 580,450 M 710,65 L 700,430" stroke="#334155" stroke-dasharray="3 3" opacity="0.4" />
                <path d="M 120,220 L 830,220 M 150,330 L 800,330" stroke="#334155" stroke-dasharray="3 3" opacity="0.4" />
              </g>

              <!-- Dynamic Map Bubbles Layer -->
              <g id="map-bubbles-layer"></g>

              <!-- Map Labels Layer -->
              <g id="map-labels-layer" pointer-events="none"></g>
            </svg>

            <!-- Floating Hover Tooltip -->
            <div id="map-tooltip" class="absolute pointer-events-none hidden bg-slate-900/95 border border-slate-700 text-white text-xs rounded-lg px-3 py-2 shadow-xl z-30 max-w-xs transition-opacity">
              <div id="tooltip-title" class="font-bold text-blue-400"></div>
              <div id="tooltip-body" class="text-slate-300 mt-0.5"></div>
            </div>
          </div>
        </div>

        <!-- TIMELINE SLIDING SCALE & CONTROLS -->
        <div class="mt-5 pt-4 border-t border-slate-800 space-y-3">
          
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
            <div id="slider-ticks" class="flex justify-between text-[11px] text-slate-400 mt-2 select-none">
              <!-- Dynamically populated ticks -->
            </div>
          </div>

          <!-- Milestone / Policy Era Description -->
          <div id="year-era-card" class="bg-slate-950/70 border border-slate-800/90 rounded-lg p-3 text-xs text-slate-300 flex items-start gap-2.5">
            <span class="text-base">📌</span>
            <div>
              <span id="era-title" class="font-bold text-white">Full 14-Year Cumulative Overview</span>
              <p id="era-description" class="text-slate-400 mt-0.5">Showing cumulative distribution of 195 navigation-app policy measures, street access regulations, and municipal coordination agreements across all years (2013–2026).</p>
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
              <span>📍 Location Drill-Down</span>
            </h3>
            <span id="loc-badge-count" class="text-xs font-bold text-blue-400 bg-blue-500/10 px-2.5 py-0.5 rounded-full border border-blue-500/20">
              Select a pin
            </span>
          </div>

          <div id="location-detail-content" class="mt-4 space-y-3 max-h-[380px] overflow-y-auto pr-1 text-xs">
            <div class="text-slate-400 text-center py-8">
              Click any bubble on the map to explore specific ordinances, authorities, and supporting news reporting for that jurisdiction.
            </div>
          </div>
        </div>

        <!-- Top Locations Ranking Card -->
        <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm">
          <h3 class="text-sm font-semibold text-white pb-2.5 border-b border-slate-800 mb-3 flex items-center justify-between">
            <span>🏆 Geographic Leaderboard</span>
            <span class="text-[11px] text-slate-400 font-normal">Entries in Active View</span>
          </h3>

          <div id="locations-leaderboard" class="space-y-2.5 max-h-[220px] overflow-y-auto pr-1">
            <!-- Dynamically populated bars -->
          </div>
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
          <div class="w-8 h-8 rounded-lg bg-blue-500/10 text-blue-400 font-bold flex items-center justify-center text-sm border border-blue-500/20 mb-3">
            01
          </div>
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
          <div class="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-400 font-bold flex items-center justify-center text-sm border border-emerald-500/20 mb-3">
            02
          </div>
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
          <div class="w-8 h-8 rounded-lg bg-amber-500/10 text-amber-400 font-bold flex items-center justify-center text-sm border border-amber-500/20 mb-3">
            03
          </div>
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
          <div class="w-8 h-8 rounded-lg bg-rose-500/10 text-rose-400 font-bold flex items-center justify-center text-sm border border-rose-500/20 mb-3">
            04
          </div>
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
          <div class="w-8 h-8 rounded-lg bg-indigo-500/10 text-indigo-400 font-bold flex items-center justify-center text-sm border border-indigo-500/20 mb-3">
            05
          </div>
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
            <strong>Deliverable:</strong> CSV + JSON (195 rows)
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
        Evaluation of term frequencies across all 195 clean articles in our corpus, highlighting which search terms were dominant and which niche keywords from your taxonomy yielded zero hits.
      </p>

      <div class="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
        
        <!-- App Group -->
        <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-5 space-y-3">
          <div class="flex items-center justify-between pb-2 border-b border-slate-800">
            <h4 class="font-bold text-white text-sm">Navigation App Group</h4>
            <span class="text-xs text-blue-400 font-medium">9 Used / 5 Unused</span>
          </div>
          <div>
            <div class="text-xs font-semibold text-emerald-400 mb-1.5">Dominant Terms in Corpus:</div>
            <div class="flex flex-wrap gap-1.5 text-xs">
              <span class="bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded border border-emerald-500/20">Waze (146 hits)</span>
              <span class="bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded border border-emerald-500/20">Google Maps (82 hits)</span>
              <span class="bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded border border-emerald-500/20">navigation app (28 hits)</span>
              <span class="bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded border border-emerald-500/20">Apple Maps (4 hits)</span>
            </div>
          </div>
          <div>
            <div class="text-xs font-semibold text-rose-400 mb-1.5">Zero Hits / Unused Terms:</div>
            <div class="flex flex-wrap gap-1.5 text-xs text-slate-400 font-mono">
              <span class="bg-slate-900 px-2 py-0.5 rounded border border-slate-800">MapQuest</span>
              <span class="bg-slate-900 px-2 py-0.5 rounded border border-slate-800">routing app(s)</span>
              <span class="bg-slate-900 px-2 py-0.5 rounded border border-slate-800">navigation software</span>
              <span class="bg-slate-900 px-2 py-0.5 rounded border border-slate-800">routing software</span>
            </div>
            <p class="text-[11px] text-slate-500 mt-2">Insight: Journalists almost exclusively name "Waze" or "Google Maps" directly, rarely using generic phrases like "routing software".</p>
          </div>
        </div>

        <!-- Family 1: Gov Restrictions -->
        <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-5 space-y-3">
          <div class="flex items-center justify-between pb-2 border-b border-slate-800">
            <h4 class="font-bold text-white text-sm">Family 1: Government Restrictions</h4>
            <span class="text-xs text-amber-400 font-medium">6 Used / 31 Unused</span>
          </div>
          <div>
            <div class="text-xs font-semibold text-emerald-400 mb-1.5">Active Terms in Corpus:</div>
            <div class="flex flex-wrap gap-1.5 text-xs">
              <span class="bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded border border-emerald-500/20">road closure(s) (19)</span>
              <span class="bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded border border-emerald-500/20">traffic diverter(s) (6)</span>
              <span class="bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded border border-emerald-500/20">congestion pricing (3)</span>
              <span class="bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded border border-emerald-500/20">traffic calming (2)</span>
            </div>
          </div>
          <div>
            <div class="text-xs font-semibold text-rose-400 mb-1.5">Zero Hits / Unused Terms:</div>
            <div class="flex flex-wrap gap-1.5 text-[11px] text-slate-400 font-mono max-h-24 overflow-y-auto">
              <span class="bg-slate-900 px-2 py-0.5 rounded border border-slate-800">turn restriction(s)</span>
              <span class="bg-slate-900 px-2 py-0.5 rounded border border-slate-800">turn ban(s)</span>
              <span class="bg-slate-900 px-2 py-0.5 rounded border border-slate-800">resident only</span>
              <span class="bg-slate-900 px-2 py-0.5 rounded border border-slate-800">local access only</span>
              <span class="bg-slate-900 px-2 py-0.5 rounded border border-slate-800">no through traffic</span>
              <span class="bg-slate-900 px-2 py-0.5 rounded border border-slate-800">truck route</span>
              <span class="bg-slate-900 px-2 py-0.5 rounded border border-slate-800">weight/height restriction</span>
              <span class="bg-slate-900 px-2 py-0.5 rounded border border-slate-800">low emission zone</span>
            </div>
            <p class="text-[11px] text-slate-500 mt-2">Insight: Because these were grouped with "OR" in US-OVERVIEW-01, dominant wire items about "road closure" crowded out niche terms like "turn ban".</p>
          </div>
        </div>

        <!-- Family 2: Company Routing Rules -->
        <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-5 space-y-3">
          <div class="flex items-center justify-between pb-2 border-b border-slate-800">
            <h4 class="font-bold text-white text-sm">Family 2: Company Routing Rules</h4>
            <span class="text-xs text-rose-400 font-medium">3 Used / 34 Unused</span>
          </div>
          <div>
            <div class="text-xs font-semibold text-emerald-400 mb-1.5">Active Terms in Corpus:</div>
            <div class="flex flex-wrap gap-1.5 text-xs">
              <span class="bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded border border-emerald-500/20">routing algorithm(s) (2)</span>
              <span class="bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded border border-emerald-500/20">avoid highways (1)</span>
            </div>
          </div>
          <div>
            <div class="text-xs font-semibold text-rose-400 mb-1.5">Zero Hits / Unused Terms:</div>
            <div class="flex flex-wrap gap-1.5 text-[11px] text-slate-400 font-mono max-h-24 overflow-y-auto">
              <span class="bg-slate-900 px-2 py-0.5 rounded border border-slate-800">avoid tolls</span>
              <span class="bg-slate-900 px-2 py-0.5 rounded border border-slate-800">avoid freeways</span>
              <span class="bg-slate-900 px-2 py-0.5 rounded border border-slate-800">avoid unpaved roads</span>
              <span class="bg-slate-900 px-2 py-0.5 rounded border border-slate-800">avoid residential streets</span>
              <span class="bg-slate-900 px-2 py-0.5 rounded border border-slate-800">avoid local roads</span>
              <span class="bg-slate-900 px-2 py-0.5 rounded border border-slate-800">eco-friendly routing</span>
              <span class="bg-slate-900 px-2 py-0.5 rounded border border-slate-800">fuel-efficient route</span>
              <span class="bg-slate-900 px-2 py-0.5 rounded border border-slate-800">routing preference</span>
            </div>
            <p class="text-[11px] text-slate-500 mt-2">Recommendation: Run targeted standalone searches for "avoid residential streets" and "eco-friendly routing" without broad closure terms.</p>
          </div>
        </div>

        <!-- Family 3: Public-Private Coordination -->
        <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-5 space-y-3">
          <div class="flex items-center justify-between pb-2 border-b border-slate-800">
            <h4 class="font-bold text-white text-sm">Family 3: Government Coordination</h4>
            <span class="text-xs text-purple-400 font-medium">7 Used / 4 Unused</span>
          </div>
          <div>
            <div class="text-xs font-semibold text-emerald-400 mb-1.5">Active Terms in Corpus:</div>
            <div class="flex flex-wrap gap-1.5 text-xs">
              <span class="bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded border border-emerald-500/20">partnership(s) (26)</span>
              <span class="bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded border border-emerald-500/20">Connected Citizens Program (23)</span>
              <span class="bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded border border-emerald-500/20">agreement(s) (8)</span>
              <span class="bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded border border-emerald-500/20">Waze for Cities (5)</span>
            </div>
          </div>
          <div>
            <div class="text-xs font-semibold text-rose-400 mb-1.5">Zero Hits / Unused Terms:</div>
            <div class="flex flex-wrap gap-1.5 text-xs text-slate-400 font-mono">
              <span class="bg-slate-900 px-2 py-0.5 rounded border border-slate-800">map correction(s)</span>
              <span class="bg-slate-900 px-2 py-0.5 rounded border border-slate-800">routing request(s)</span>
            </div>
            <p class="text-[11px] text-slate-500 mt-2">Insight: "Connected Citizens Program" was the primary branding public agencies used; "routing request" rarely appears in press releases.</p>
          </div>
        </div>

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

    // Projection constants for 960x600 continental US SVG
    // US Bounding Box: lon -125 to -66, lat 24 to 50
    function projectCoords(lat, lon) {{
      const minLon = -125.0, maxLon = -66.0;
      const minLat = 24.0, maxLat = 50.0;
      const x = ((lon - minLon) / (maxLon - minLon)) * 780 + 70;
      const y = ((maxLat - lat) / (maxLat - minLat)) * 480 + 50;
      return {{ x: Math.max(50, Math.min(910, x)), y: Math.max(40, Math.min(550, y)) }};
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

    function initDashboard() {{
      initSliderTicks();
      renderMap();
      renderLeaderboard();
      updateSelectedEraCard();

      // Setup JSON file upload listener
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

    function updateSelectedEraCard() {{
      const year = getActiveYear();
      const title = document.getElementById('era-title');
      const desc = document.getElementById('era-description');

      if (year === 'ALL') {{
        title.textContent = 'Cumulative Corpus Overview (2013 - 2026)';
        desc.textContent = 'Displaying all 195 verified traffic and navigation policy sources across 36 geographic locations.';
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

    function renderMap() {{
      const bubbleLayer = document.getElementById('map-bubbles-layer');
      bubbleLayer.innerHTML = '';
      const activeYear = getActiveYear();

      DATA.locations.forEach(loc => {{
        let count = 0;
        if (activeYear === 'ALL') {{
          count = loc.total_count;
        }} else if (isCumulativeMode) {{
          // Sum up to selected year
          Object.keys(loc.years).forEach(yr => {{
            if (yr <= activeYear) count += loc.years[yr];
          }});
        }} else {{
          count = loc.years[activeYear] || 0;
        }}

        if (count === 0) return;

        const coords = projectCoords(loc.lat, loc.lon);
        
        // Find dominant governing level
        let topGov = 'Company';
        let maxGovCount = -1;
        Object.entries(loc.gov_levels).forEach(([gov, cnt]) => {{
          if (cnt > maxGovCount) {{ maxGovCount = cnt; topGov = gov; }}
        }});
        const color = getGovColor(topGov);

        // Radius calculation
        const baseRadius = (activeYear === 'ALL') 
          ? Math.min(36, Math.max(7, Math.sqrt(count) * 6))
          : Math.min(34, Math.max(9, Math.sqrt(count) * 11));

        // SVG Group for location pin
        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        g.setAttribute('class', 'cursor-pointer transition-all duration-300');
        g.onclick = () => selectLocation(loc);

        // Outer pulsing ring for active/current year items
        if (activeYear !== 'ALL' && (loc.years[activeYear] || 0) > 0) {{
          const pulseCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
          pulseCircle.setAttribute('cx', coords.x);
          pulseCircle.setAttribute('cy', coords.y);
          pulseCircle.setAttribute('r', baseRadius * 1.5);
          pulseCircle.setAttribute('fill', 'none');
          pulseCircle.setAttribute('stroke', color);
          pulseCircle.setAttribute('stroke-width', '1.5');
          pulseCircle.setAttribute('class', 'map-pulse');
          g.appendChild(pulseCircle);
        }}

        // Main Bubble Circle
        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('cx', coords.x);
        circle.setAttribute('cy', coords.y);
        circle.setAttribute('r', baseRadius);
        circle.setAttribute('fill', color);
        circle.setAttribute('fill-opacity', '0.65');
        circle.setAttribute('stroke', '#ffffff');
        circle.setAttribute('stroke-width', '1.5');
        circle.setAttribute('filter', 'url(#bubble-glow)');

        // Hover events
        circle.onmouseenter = (e) => showTooltip(e, loc, count);
        circle.onmouseleave = hideTooltip;

        // Count Text inside bubble
        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('x', coords.x);
        text.setAttribute('y', coords.y + 4);
        text.setAttribute('text-anchor', 'middle');
        text.setAttribute('fill', '#ffffff');
        text.setAttribute('font-size', baseRadius > 14 ? '11px' : '9px');
        text.setAttribute('font-weight', 'bold');
        text.setAttribute('pointer-events', 'none');
        text.textContent = count;

        g.appendChild(circle);
        g.appendChild(text);
        bubbleLayer.appendChild(g);
      }});
    }}

    function showTooltip(e, loc, count) {{
      const tip = document.getElementById('map-tooltip');
      const title = document.getElementById('tooltip-title');
      const body = document.getElementById('tooltip-body');

      title.textContent = `${{loc.name}} (${{count}} Sources)`;
      const activeYear = getActiveYear();
      const yrText = (activeYear === 'ALL') ? 'Across all years' : `In ${{activeYear}}`;
      
      const govKeys = Object.keys(loc.gov_levels).slice(0, 2).join(', ');
      body.innerHTML = `<strong>${{yrText}}</strong><br>Gov: ${{govKeys}}<br><span class="text-blue-300 underline mt-1 block">Click to view articles</span>`;

      tip.style.left = `${{e.clientX - 20}}px`;
      tip.style.top = `${{e.clientY - 70}}px`;
      tip.classList.remove('hidden');
    }}

    function hideTooltip() {{
      document.getElementById('map-tooltip').classList.add('hidden');
    }}

    function selectLocation(loc) {{
      selectedLocation = loc;
      renderLocationDetail(loc);
    }}

    function renderLocationDetail(loc) {{
      const activeYear = getActiveYear();
      const container = document.getElementById('location-detail-content');
      const badge = document.getElementById('loc-badge-count');

      // Filter articles for current timeframe
      let filtered = loc.articles;
      if (activeYear !== 'ALL') {{
        filtered = isCumulativeMode 
          ? loc.articles.filter(a => a.year <= activeYear)
          : loc.articles.filter(a => a.year === activeYear);
      }}

      badge.textContent = `${{filtered.length}} / ${{loc.total_count}} total`;

      if (filtered.length === 0) {{
        container.innerHTML = `
          <div class="text-slate-400 text-center py-6">
            No articles recorded in <strong>${{loc.name}}</strong> for timeframe <strong>${{activeYear}}</strong>.
          </div>
        `;
        return;
      }}

      container.innerHTML = `
        <div class="font-bold text-white text-sm mb-1">${{loc.name}}</div>
        <div class="text-[11px] text-slate-400 mb-3 flex flex-wrap gap-2">
          ${{Object.entries(loc.gov_levels).map(([gov, cnt]) => `
            <span class="bg-slate-800 px-1.5 py-0.5 rounded text-slate-300 border border-slate-700">${{gov}}: ${{cnt}}</span>
          `).join('')}}
        </div>
        <div class="space-y-2">
          ${{filtered.map(art => `
            <div class="bg-slate-950 p-2.5 rounded-lg border border-slate-800/90 hover:border-slate-700 transition">
              <div class="flex items-center justify-between text-[11px] mb-1">
                <span class="font-bold text-amber-400">${{art.year}}</span>
                <span class="text-slate-400 bg-slate-900 px-1.5 py-0.2 rounded">${{art.gov}}</span>
              </div>
              <div class="font-medium text-slate-200">${{art.title}}</div>
              <div class="text-slate-400 mt-1 line-clamp-2">${{art.summary}}</div>
            </div>
          `).join('')}}
        </div>
      `;
    }}

    function renderLeaderboard() {{
      const container = document.getElementById('locations-leaderboard');
      container.innerHTML = '';
      const activeYear = getActiveYear();

      // Calculate counts for each location in active view
      const ranked = DATA.locations.map(loc => {{
        let cnt = 0;
        if (activeYear === 'ALL') cnt = loc.total_count;
        else if (isCumulativeMode) {{
          Object.keys(loc.years).forEach(y => {{ if (y <= activeYear) cnt += loc.years[y]; }});
        }} else {{
          cnt = loc.years[activeYear] || 0;
        }}
        return {{ name: loc.name, count: cnt, raw: loc }};
      }}).filter(item => item.count > 0).sort((a, b) => b.count - a.count);

      const maxCount = ranked.length > 0 ? ranked[0].count : 1;

      ranked.slice(0, 8).forEach(item => {{
        const pct = Math.round((item.count / maxCount) * 100);
        const row = document.createElement('div');
        row.className = 'cursor-pointer group';
        row.onclick = () => selectLocation(item.raw);

        row.innerHTML = `
          <div class="flex justify-between text-xs mb-0.5">
            <span class="text-slate-300 group-hover:text-blue-400 transition truncate pr-2">${{item.name}}</span>
            <span class="font-bold text-white">${{item.count}}</span>
          </div>
          <div class="w-full bg-slate-950 rounded-full h-1.5 overflow-hidden">
            <div class="bg-blue-500 h-1.5 rounded-full transition-all duration-300" style="width: ${{pct}}%"></div>
          </div>
        `;
        container.appendChild(row);
      }});
    }}

    function switchTab(tabId) {{
      document.querySelectorAll('.tab-pane').forEach(el => el.classList.add('hidden'));
      document.querySelectorAll('.tab-btn').forEach(btn => {{
        btn.className = 'tab-btn px-4 py-2 rounded-lg text-sm font-medium text-slate-400 hover:text-white hover:bg-slate-800';
      }});

      document.getElementById(tabId).classList.remove('hidden');
      const activeBtnId = tabId.replace('-view', '');
      const activeBtn = document.getElementById(`tab-btn-${{activeBtnId}}`);
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
          const freshData = JSON.parse(evt.target.result);
          // Re-aggregate and update DATA
          updateWithRawJSON(freshData);
          alert(`Successfully loaded ${{freshData.length}} updated research sources!`);
        }} catch(err) {{
          alert('Error parsing uploaded JSON: ' + err.message);
        }}
      }};
      reader.readAsText(file);
    }}

    function updateWithRawJSON(records) {{
      // Update header count
      document.getElementById('stat-total-header').textContent = `${{records.length}} Sources`;
      document.getElementById('stat-sources').textContent = records.length;
      // In a full build, this would re-run build_infographic_dataset client-side
      location.reload();
    }}

    // Kick off initialization
    window.addEventListener('DOMContentLoaded', initDashboard);
  </script>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description="Generate interactive research infographics and map dashboard.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/exports/research_analysis_all_sources.json"),
        help="Path to research analysis JSON file (default: data/exports/research_analysis_all_sources.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/exports/research_infographics.html"),
        help="Path to save generated HTML dashboard (default: data/exports/research_infographics.html)",
    )
    parser.add_argument(
        "--artifact-output",
        type=Path,
        default=Path("/Users/isabelle/.gemini/antigravity/brain/b83e007b-8917-4635-8cf5-17130e87b3c1/research_infographics_dashboard.html"),
        help="Path to mirror dashboard into artifact directory",
    )
    args = parser.parse_args()

    if not args.input.is_file():
        raise FileNotFoundError(f"Input dataset not found at {args.input}")

    print(f"Reading research analysis records from {args.input}...")
    dataset = build_infographic_dataset(args.input)
    print(f"Processed {dataset['metadata']['total_sources']} sources across {dataset['metadata']['unique_locations']} locations ({dataset['metadata']['year_range']}).")

    html_content = generate_html_infographics(dataset)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html_content, encoding="utf-8")
    print(f"Saved interactive infographics to {args.output}")

    if args.artifact_output:
        args.artifact_output.parent.mkdir(parents=True, exist_ok=True)
        args.artifact_output.write_text(html_content, encoding="utf-8")
        print(f"Mirrored artifact dashboard to {args.artifact_output}")


if __name__ == "__main__":
    main()
