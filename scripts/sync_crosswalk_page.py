"""Synchronize docs/crosswalk.html with docs/data/news_to_law_crosswalk.csv."""

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CW_CSV = ROOT / "docs/data/news_to_law_crosswalk.csv"
CW_HTML = ROOT / "docs/crosswalk.html"


def sync_crosswalk_page():
    if not CW_CSV.exists() or not CW_HTML.exists():
        print(f"Error: {CW_CSV} or {CW_HTML} does not exist.")
        return

    with open(CW_CSV, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    total = len(rows)
    tied = sum(1 for r in rows if r.get("legal_relationship") == "Directly Tied")
    assoc = sum(1 for r in rows if r.get("legal_relationship") == "Potentially Associated")
    gaps = sum(1 for r in rows if r.get("legal_relationship") == "Unaddressed Gap")
    ca = sum(1 for r in rows if r.get("is_california") in ("true", "True", True))
    tier1 = sum(1 for r in rows if "Layer 1" in r.get("governance_layer", ""))

    print(f"Metrics from CSV: Total={total}, Tied={tied}, Assoc={assoc}, Gaps={gaps}, CA={ca}, Tier1={tier1}")

    html = CW_HTML.read_text(encoding="utf-8")

    # 1. Header paragraph
    html = re.sub(
        r'Synthesized crosswalk connecting <strong class="text-white">\d+ verified empirical news incidents</strong> to governing statutory mechanisms and appellate precedents\. Highlights <strong class="text-emerald-400">\d+ Directly Tied</strong> instruments, <strong class="text-blue-400">\d+ Potentially Associated</strong> enabling powers, and <strong class="text-amber-400">\d+ Unaddressed Legal Gaps</strong> across vehicular routing\.',
        f'Synthesized crosswalk connecting <strong class="text-white">{total} verified empirical news incidents</strong> to governing statutory mechanisms and appellate precedents. Highlights <strong class="text-emerald-400">{tied} Directly Tied</strong> instruments, <strong class="text-blue-400">{assoc} Potentially Associated</strong> enabling powers, and <strong class="text-amber-400">{gaps} Unaddressed Legal Gaps</strong> across vehicular routing.',
        html,
    )

    # 2. KPI Cards
    # Total
    html = re.sub(
        r'(<div class="text-\[11px\] text-slate-400 uppercase font-semibold">Total Verified News</div>\s*<div class="text-2xl font-bold text-white mt-1">)\d+(</div>)',
        rf'\g<1>{total}\g<2>',
        html,
    )
    # Directly Tied
    html = re.sub(
        r'(<div class="text-\[11px\] text-emerald-400 uppercase font-semibold">1\. Directly Tied</div>\s*<div class="text-2xl font-bold text-emerald-300 mt-1">)\d+(</div>)',
        rf'\g<1>{tied}\g<2>',
        html,
    )
    # Potentially Associated
    html = re.sub(
        r'(<div class="text-\[11px\] text-blue-400 uppercase font-semibold">2\. Potentially Associated</div>\s*<div class="text-2xl font-bold text-blue-300 mt-1">)\d+(</div>)',
        rf'\g<1>{assoc}\g<2>',
        html,
    )
    # Unaddressed Gaps
    html = re.sub(
        r'(<div class="text-\[11px\] text-amber-400 uppercase font-semibold">3\. Unaddressed Gaps</div>\s*<div class="text-2xl font-bold text-amber-300 mt-1">)\d+(</div>)',
        rf'\g<1>{gaps}\g<2>',
        html,
    )
    # California Focus
    html = re.sub(
        r'(<div class="text-\[11px\] text-cyan-400 uppercase font-semibold">California Focus</div>\s*<div class="text-2xl font-bold text-cyan-300 mt-1">)\d+(</div>)',
        rf'\g<1>{ca}\g<2>',
        html,
    )

    # 3. Gap callout & California callout banners
    html = re.sub(
        r'Synthesis of <strong>\d+ empirical incidents</strong> revealing critical regulatory boundaries',
        f'Synthesis of <strong>{gaps} empirical incidents</strong> revealing critical regulatory boundaries',
        html,
    )
    html = re.sub(
        r'View All \d+ Gap Incidents',
        f'View All {gaps} Gap Incidents',
        html,
    )
    html = re.sub(
        r'Detailed legal synthesis of <strong>\d+ California news records</strong>',
        f'Detailed legal synthesis of <strong>{ca} California news records</strong>',
        html,
    )
    html = re.sub(
        r'View All \d+ California Incidents',
        f'View All {ca} California Incidents',
        html,
    )

    # 4. Tab buttons
    html = re.sub(
        r'All Incidents \(\d+\)',
        f'All Incidents ({total})',
        html,
    )
    html = re.sub(
        r'Directly Tied to Law \(\d+\)',
        f'Directly Tied to Law ({tied})',
        html,
    )
    html = re.sub(
        r'Potentially Associated \(\d+\)',
        f'Potentially Associated ({assoc})',
        html,
    )
    html = re.sub(
        r'Unaddressed by Law / Gaps \(\d+\)',
        f'Unaddressed by Law / Gaps ({gaps})',
        html,
    )
    html = re.sub(
        r'California Focus \(\d+\)',
        f'California Focus ({ca})',
        html,
    )

    # 5. Showing count
    html = re.sub(
        r'<span id="cross-count">Showing \d+ synthesized records</span>',
        f'<span id="cross-count">Showing {total} synthesized records</span>',
        html,
    )

    # 6. Gap theme breakdown
    # Theme 2: 67 (59.3%)
    html = html.replace('67 records (60.9%)</span>', f'67 records (59.3%)</span>')
    html = html.replace('style="width: 60.9%"', 'style="width: 59.3%"')
    # Theme 1: 22 (19.5%)
    html = html.replace('22 records (20.0%)</span>', f'22 records (19.5%)</span>')
    html = html.replace('style="width: 20.0%"', 'style="width: 19.5%"')
    # Theme 5: 12 (10.6%)
    html = html.replace('11 records (10.0%)</span>', f'12 records (10.6%)</span>')
    html = html.replace('style="width: 10.0%"', 'style="width: 10.6%"')
    # Theme 6: 8 (7.1%)
    html = html.replace('8 records (7.3%)</span>', f'8 records (7.1%)</span>')
    html = html.replace('style="width: 7.3%"', 'style="width: 7.1%"')

    # 7. CROSSWALK Javascript Array
    start_tag = 'const CROSSWALK = ['
    start_idx = html.find(start_tag)
    end_tag = 'let activeTab ='
    end_idx = html.find(end_tag, start_idx)

    if start_idx != -1 and end_idx != -1:
        json_str = json.dumps(rows, ensure_ascii=False)
        new_block = f"const CROSSWALK = {json_str};\n    "
        html = html[:start_idx] + new_block + html[end_idx:]
        print("Updated const CROSSWALK array in docs/crosswalk.html")
    else:
        print("Warning: could not locate const CROSSWALK boundaries in docs/crosswalk.html")

    CW_HTML.write_text(html, encoding="utf-8")
    print(f"Successfully synced {CW_HTML} to {total} records.")


if __name__ == "__main__":
    sync_crosswalk_page()
