"""Embed JSON data into policy and law HTML pages for seamless local (file://) and online viewing."""

import json
from pathlib import Path

DOCS = Path(__file__).resolve().parents[1] / "docs"

def embed_policy_database():
    ps_file = DOCS / "data" / "policy_screening.json"
    if not ps_file.exists():
        print(f"Error: {ps_file} not found")
        return
    ps_data = json.loads(ps_file.read_text(encoding="utf-8"))
    min_ps = json.dumps(ps_data, separators=(",", ":"), ensure_ascii=False).replace("<", "\\u003c")
    data_tag = f'<script type="application/json" id="policy-screening-data">{min_ps}</script>\n</body>'

    # Update policy_database.html and policy_database_archive.html
    for fname in ["policy_database.html", "policy_database_archive.html"]:
        p = DOCS / fname
        if not p.exists():
            continue
        html = p.read_text(encoding="utf-8")
        if 'id="policy-screening-data"' in html:
            # Replace existing tag
            start = html.index('<script type="application/json" id="policy-screening-data">')
            end = html.index("</script>", start) + len("</script>")
            html = html[:start] + f'<script type="application/json" id="policy-screening-data">{min_ps}</script>' + html[end:]
        else:
            html = html.replace("</body>", data_tag, 1)
        p.write_text(html, encoding="utf-8")
        print(f"Embedded policy screening data into {p.name}")

    # Update policy_database.js to read from embedded tag if available
    js_p = DOCS / "policy_database.js"
    if js_p.exists():
        js_code = js_p.read_text(encoding="utf-8")
        target = '  const response = await fetch("data/policy_screening.json");\n  if (!response.ok) throw new Error("Policy dataset could not be loaded");\n  const all = await response.json();'
        replacement = """  let all;
  const embedded = byId("policy-screening-data");
  if (embedded && embedded.textContent.trim()) {
    try {
      all = JSON.parse(embedded.textContent);
    } catch (e) {
      console.warn("Failed to parse embedded policy data, falling back to fetch", e);
    }
  }
  if (!all) {
    const response = await fetch("data/policy_screening.json");
    if (!response.ok) throw new Error("Policy dataset could not be loaded");
    all = await response.json();
  }"""
        if target in js_code:
            js_code = js_code.replace(target, replacement, 1)
            js_p.write_text(js_code, encoding="utf-8")
            print("Updated policy_database.js with embedded data fallback.")


def embed_policy_measure_review():
    pm_file = DOCS / "data" / "policy_measure_review.json"
    if not pm_file.exists():
        return
    pm_data = json.loads(pm_file.read_text(encoding="utf-8"))
    min_pm = json.dumps(pm_data, separators=(",", ":"), ensure_ascii=False).replace("<", "\\u003c")
    data_tag = f'<script type="application/json" id="policy-measure-data">{min_pm}</script>\n</body>'

    p = DOCS / "policy_measure_review.html"
    if p.exists():
        html = p.read_text(encoding="utf-8")
        if 'id="policy-measure-data"' in html:
            start = html.index('<script type="application/json" id="policy-measure-data">')
            end = html.index("</script>", start) + len("</script>")
            html = html[:start] + f'<script type="application/json" id="policy-measure-data">{min_pm}</script>' + html[end:]
        else:
            html = html.replace("</body>", data_tag, 1)
        p.write_text(html, encoding="utf-8")
        print(f"Embedded policy measure review data into {p.name}")

    js_p = DOCS / "measure_review.js"
    if js_p.exists():
        js_code = js_p.read_text(encoding="utf-8")
        target = '  const response = await fetch("data/policy_measure_review.json");\n  if (!response.ok) throw new Error("Policy measure data could not be loaded");\n  const {instances, codes, categories} = await response.json();'
        replacement = """  let raw;
  const embedded = document.getElementById("policy-measure-data");
  if (embedded && embedded.textContent.trim()) {
    try {
      raw = JSON.parse(embedded.textContent);
    } catch (e) {
      console.warn("Failed to parse embedded measure review data, falling back to fetch", e);
    }
  }
  if (!raw) {
    const response = await fetch("data/policy_measure_review.json");
    if (!response.ok) throw new Error("Policy measure data could not be loaded");
    raw = await response.json();
  }
  const {instances, codes, categories} = raw;"""
        if target in js_code:
            js_code = js_code.replace(target, replacement, 1)
            js_p.write_text(js_code, encoding="utf-8")
            print("Updated measure_review.js with embedded data fallback.")


def embed_law_database():
    law_file = DOCS / "data" / "current_law_database.json"
    if not law_file.exists():
        return
    law_data = json.loads(law_file.read_text(encoding="utf-8"))
    min_law = json.dumps(law_data, separators=(",", ":"), ensure_ascii=False).replace("<", "\\u003c")
    data_tag = f'<script type="application/json" id="current-law-data">{min_law}</script>\n</body>'

    p = DOCS / "law_database.html"
    if p.exists():
        html = p.read_text(encoding="utf-8")
        if 'id="current-law-data"' in html:
            start = html.index('<script type="application/json" id="current-law-data">')
            end = html.index("</script>", start) + len("</script>")
            html = html[:start] + f'<script type="application/json" id="current-law-data">{min_law}</script>' + html[end:]
        else:
            html = html.replace("</body>", data_tag, 1)
        p.write_text(html, encoding="utf-8")
        print(f"Embedded law data into {p.name}")

    # Update current_law.js to support embedded fallback
    js_p = DOCS / "current_law.js"
    if js_p.exists():
        js_code = js_p.read_text(encoding="utf-8")
        target = "  async function load(path) {\n    const response = await fetch(path + '?v=current-law-20261118-1');\n    if (!response.ok) throw new Error('The checked collection could not be loaded.');\n    return response.json();\n  }"
        replacement = """  async function load(path) {
    if (path.includes('current_law_database.json')) {
      const emb = document.getElementById('current-law-data');
      if (emb && emb.textContent.trim()) {
        try { return JSON.parse(emb.textContent); } catch (e) {}
      }
    }
    if (path.includes('current_news_law_crosswalk.json')) {
      const emb = document.getElementById('current-crosswalk-data');
      if (emb && emb.textContent.trim()) {
        try { return JSON.parse(emb.textContent); } catch (e) {}
      }
    }
    const response = await fetch(path + '?v=current-law-20261118-1');
    if (!response.ok) throw new Error('The checked collection could not be loaded.');
    return response.json();
  }"""
        if target in js_code:
            js_code = js_code.replace(target, replacement, 1)
            js_p.write_text(js_code, encoding="utf-8")
            print("Updated current_law.js with embedded data fallback.")


if __name__ == "__main__":
    embed_policy_database()
    embed_policy_measure_review()
    embed_law_database()
    print("All offline database fallbacks embedded successfully.")
