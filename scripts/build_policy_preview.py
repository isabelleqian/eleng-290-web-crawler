"""Build the local Policy Database preview from the course's Policy Commons exports."""

import argparse
import csv
import json
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import quote, urlsplit

from news_importer.site_navigation import render_site_navigation


REPO = Path(__file__).resolve().parents[1]
SNAPSHOT = "2026-11-17"
SITE_FILES = (
    "index.html", "policy_database.html", "policy_database_archive.html",
    "policy_measure_review.html", "policy_database.js", "measure_review.js",
    "policy_overview.js", "data/policy_screening.json", "data/policy_measure_review.json",
)


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def index(rows, field):
    records = {str(row[field]): row for row in rows}
    if len(records) != len(rows):
        raise ValueError(f"Duplicate {field} in input")
    return records


def safe_url(value):
    if value and urlsplit(value).scheme in {"https", "http"}:
        return value
    return ""


def read_trials(data):
    documents = {
        row["document_id"]: row["source_record_id"]
        for filename in ("exploratory_measure_extraction.json", "additional_document_trials.json")
        for row in read_json(data / filename)
    }
    trials = defaultdict(dict)
    with (data / f"five_document_measure_trials_revision_{SNAPSHOT}.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        for row in csv.DictReader(stream):
            artifact_id = documents[row["document_id"]]
            instance_id = row["measure_instance_id"]
            trial = trials[artifact_id].setdefault(instance_id, {
                "id": instance_id,
                "description": row["description"],
                "status": row["status"],
                "location": row["location"],
                "codes": json.loads(row["codes"]),
                "questions": json.loads(row["missing_information"]),
                "evidence": [],
            })
            for evidence in json.loads(row["evidence"]):
                excerpt = {key: evidence[key] for key in ("pdf_page", "page", "printed_page", "quote")
                           if key in evidence}
                if excerpt not in trial["evidence"]:
                    trial["evidence"].append(excerpt)
    return trials


def build_measure_review(rows):
    # Use the same code names, categories, and definitions as the Overview's Measures panel.
    overview = (REPO / "docs/index.html").read_text(encoding="utf-8")
    payload, _ = json.JSONDecoder().raw_decode(overview.split("let DATA = ", 1)[1])
    panel = payload["measures"]
    instances = {}
    for row in rows:
        for trial in row["trials"]:
            instance = instances.setdefault(trial["id"], {
                "id": trial["id"], "reviewStatus": "pending", "sources": [],
            })
            instance["sources"].append({
                "id": row["id"], "title": row["title"], "publisher": row["publisher"],
                "candidate": row["candidate"], "pdf": row["pdf"],
                "original": row["original"] or row["url"], "trial": trial,
            })
    for instance in instances.values():
        instance["codes"] = sorted({code for source in instance["sources"] for code in source["trial"]["codes"]})
    return {
        "categories": panel["categories"],
        "codes": [{key: item[key] for key in ("code", "name", "category", "definition")}
                  for item in panel["measures"]],
        "instances": sorted(instances.values(), key=lambda item: item["id"]),
    }


def integrate_overview(output, review):
    instances = {item["id"]: item for item in review["instances"]}
    places = []
    if "PILOT_MI_002" in instances:
        # Bellevue confirms both intersections. The national map marker represents
        # the neighborhood, using the earlier preview's approximate coordinates.
        places.append({
            "id": "PILOT_MI_002", "name": "Woodridge, Bellevue, Washington",
            "lat": 47.59, "lon": -122.17, "scope": "Neighborhood marker (approximate)",
            "site": "128th Ave SE at SE 30th St and SE 32nd St",
            "source": "https://bellevuewa.gov/city-government/departments/transportation/projects/neighborhood-projects/woodridge-traffic",
        })
    data = {
        "counts": Counter(code for item in instances.values() for code in item["codes"]),
        "total": len(instances), "places": places,
    }
    payload = json.dumps(data).replace("<", "\\u003c")
    path = output / "index.html"
    html = path.read_text(encoding="utf-8")
    data_tag = '<script type="application/json" id="policy-overview-data">'
    if data_tag in html:
        start = html.index(data_tag) + len(data_tag)
        end = html.index("</script>", start)
        path.write_text(html[:start] + payload + html[end:], encoding="utf-8")
        return
    replacements = (
        ("</head>", '<script defer src="policy_overview.js"></script>\n</head>'),
        ('<g id="map-city-labels-layer" pointer-events="none"></g>',
         '<g id="map-city-labels-layer" pointer-events="none"></g>\n                <g id="policy-measure-map-layer"></g>'),
        ('<h3 class="text-sm font-semibold text-white">Articles</h3>',
         '<h3 class="text-sm font-semibold text-white">Location details</h3>'),
        ("Click any city bubble on the map or open the United States dock to read the articles filed there.",
         'Select a News bubble, the United States dock, or an orange Policy marker. '
         '<a class="text-blue-200 underline" href="policy_measure_review.html">Review Policy measures</a>'),
        ("      if (selectedLocation) renderLocationDetail(selectedLocation);",
         "      if (selectedLocation) selectLocation(selectedLocation, false);"),
        ("      const countyInfo = CITY_TO_COUNTY[loc.name];\n      const countySubtitle",
         "      if (loc.policyMeasure) {\n        policyOverview.renderLocation(loc.policyMeasure);\n"
         "        return;\n      }\n\n      const countyInfo = CITY_TO_COUNTY[loc.name];\n      const countySubtitle"),
        ("      initMeasures();", "      initMeasures();\n      policyOverview.mountMap(projectCoords, selectLocation);\n"
         "      if (location.hash === '#measures-view') switchTab('measures-view');"),
        ('      let category = \'all\';\n      let selected = panel.measures',
         "      policyOverview.describeMeasures(summary);\n      let category = 'all';\n      let selected = panel.measures"),
        ("          row.querySelector('b').textContent = String(item.count || 0);",
         "          policyOverview.measureCounts(row.querySelector('b'), item);"),
        ("        detail.appendChild(definition);\n        const found = (panel.articles",
         "        detail.appendChild(definition);\n        policyOverview.measureDetails(detail, measure);\n"
         "        const found = (panel.articles"),
        ("No saved article matched this measure.", "No saved News article matched this measure."),
    )
    for before, after in replacements:
        if html.count(before) != 1:
            raise ValueError(f"Expected one Overview integration point: {before}")
        html = html.replace(before, after, 1)
    html = html.replace("</body>", f"{data_tag}{payload}</script>\n</body>", 1)
    path.write_text(html, encoding="utf-8")


def build_preview(source, output, *, public=False):
    data = source / "data"
    archive = index(read_json(data / "source_verification_round3.json"), "artifact_id")
    candidates = index(read_json(data / f"policy_candidate_evidence_index_{SNAPSHOT}.json"), "artifact_id")
    decisions = index(read_json(data / f"human_document_decisions_overlay_{SNAPSHOT}.json"), "artifact_id")
    pilot = index(read_json(REPO / "docs/data/policycommons_pilot.json"), "pc_record_id")
    trials = read_trials(data)
    if not pilot.keys() <= candidates.keys() <= archive.keys():
        raise ValueError("Expected the published pilot and audit candidates to be nested in Round 3")
    shutil.copytree(REPO / "docs", output, dirs_exist_ok=True, ignore=shutil.ignore_patterns("superpowers"))
    rows = []
    review = []
    for artifact_id, raw in archive.items():
        candidate = candidates.get(artifact_id, {})
        prior = pilot.get(artifact_id, {})
        original_review = candidate.get("original_review") or {}
        # The dated decision overlay is authoritative where it supplies a record.
        decision = decisions.get(artifact_id, raw)
        before = (raw.get("human_validated"), raw.get("human_decision"))
        after = (decision.get("human_validated"), decision.get("human_decision"))
        if before != after:
            review.append({"id": artifact_id, "round3": before, "overlay": after})
        evidence = raw.get("evidence", "")
        publisher_match = re.search(r'link "([^"\n]+)"[^\n]*\n\s+- /url: /orgs/', evidence)
        date_match = re.search(r"· ([^·\n]+) ·", evidence)
        publisher = prior.get("publisher") or (publisher_match[1] if publisher_match else "")
        dates = candidate.get("platform_date_mentions") or []
        platform_date = prior.get("platform_display_date") or (dates[0] if dates else "")
        platform_date = platform_date or (date_match[1].strip() if date_match else "")
        original_date = candidate.get("publication_date_verified") or ""
        if prior.get("publication_date") != prior.get("platform_display_date"):
            original_date = original_date or prior.get("publication_date") or ""
        date = original_date or platform_date
        year = re.search(r"\b(?:19|20)\d{2}\b", date)
        pdf = ""
        originals = [item["path"] for item in candidate.get("local_originals", [])]
        if prior.get("local_pdf"):
            originals.append(prior["local_pdf"])
        if public and prior.get("local_pdf"):
            name = Path(prior["local_pdf"]).name
            if (REPO / "docs/policy-originals" / name).is_file():
                pdf = "policy-originals/" + quote(name)
        for value in originals if not public else ():
            original = (source / value).resolve()
            if original.is_relative_to(source.resolve()) and original.suffix.lower() == ".pdf" and original.is_file():
                target = output / "policy-originals" / f"pc-{artifact_id}-{original.name}"
                shutil.copy2(original, target)
                pdf = "policy-originals/" + quote(target.name)
                break
        rows.append({
            "id": artifact_id,
            "candidate": artifact_id in candidates,
            "group": candidate.get("document_group_id", ""),
            "document": prior.get("document_id") or (f"PC_DOC_{candidate['document_group_id']}" if candidate else ""),
            "title": candidate.get("title") or raw["platform_title"],
            "publisher": publisher,
            "date": date,
            "year": year[0] if year else "",
            "dateBasis": "Original document" if original_date else "Platform metadata" if date else "",
            "model": raw["current_model_proposal"],
            "human": (decision.get("human_decision") or "") if decision.get("human_validated") is True else "",
            "decisionSource": "2026-11-17 decision overlay" if artifact_id in decisions else "Round 3",
            "scope": ((decision.get("decision_scope") if not public else "") or prior.get("human_decision_scope", ""))
                     if decision.get("human_validated") is True else "",
            "reason": prior.get("screening_reason", "") if public else raw["current_reason"],
            "auditReason": "" if public else original_review.get("reason") or "",
            "auditEvidence": "" if public else original_review.get("evidence") or "",
            "evidencePages": candidate.get("evidence_pages") or [],
            "evidenceLevel": raw.get("current_evidence_level") or raw.get("evidence_level", ""),
            "queries": candidate.get("query_ids") or raw["all_query_ids"],
            "collection": raw["collection"],
            "url": safe_url(candidate.get("pc_url") or raw["url"]),
            "original": safe_url(candidate.get("original_url") or prior.get("original_url")),
            "pdf": pdf,
            "trials": list(trials.get(artifact_id, {}).values()),
        })
    (output / "data/policy_screening.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if not public:
        (output / "data/policy_decision_reconciliation.json").write_text(
            json.dumps(review, indent=2) + "\n", encoding="utf-8"
        )
    template_dir = Path(__file__).with_name("policy_preview")
    template = (template_dir / "page.html").read_text(encoding="utf-8")
    for page, mode, title, source_template in (
        ("policy_database.html", "candidate", "Policy Database", template),
        ("policy_database_archive.html", "archive", "Policy Screening Archive", template),
        ("policy_measure_review.html", "", "Policy Measure Review",
         (template_dir / "measure_review.html").read_text(encoding="utf-8")),
    ):
        html = (source_template.replace("__MODE__", mode).replace("__TITLE__", title)
                .replace("__NAV__", render_site_navigation(page, "      ")))
        (output / page).write_text(html, encoding="utf-8")
    for script in ("policy_database.js", "measure_review.js", "policy_overview.js"):
        shutil.copy2(template_dir / script, output / script)
    review = build_measure_review(rows)
    (output / "data/policy_measure_review.json").write_text(
        json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    integrate_overview(output, review)

    # Embed offline JSON fallbacks so local file:// browsing does not fail due to CORS
    min_ps = json.dumps(rows, separators=(",", ":"), ensure_ascii=False).replace("<", "\\u003c")
    data_tag_ps = f'<script type="application/json" id="policy-screening-data">{min_ps}</script>\n</body>'
    for page in ("policy_database.html", "policy_database_archive.html"):
        p = output / page
        p.write_text(p.read_text(encoding="utf-8").replace("</body>", data_tag_ps, 1), encoding="utf-8")
    min_pm = json.dumps(review, separators=(",", ":"), ensure_ascii=False).replace("<", "\\u003c")
    data_tag_pm = f'<script type="application/json" id="policy-measure-data">{min_pm}</script>\n</body>'
    pm_page = output / "policy_measure_review.html"
    pm_page.write_text(pm_page.read_text(encoding="utf-8").replace("</body>", data_tag_pm, 1), encoding="utf-8")


def build_public_site(source):
    with TemporaryDirectory() as directory:
        output = Path(directory)
        build_preview(source, output, public=True)
        for filename in SITE_FILES:
            shutil.copyfile(output / filename, REPO / "docs" / filename)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=REPO.parent / "policy-search")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--publish", action="store_true", help="write the public export into docs/")
    args = parser.parse_args()
    if args.publish:
        if args.output:
            parser.error("--publish cannot be combined with --output")
        build_public_site(args.source.resolve())
        raise SystemExit(0)
    output = (args.output or args.source / "outputs/policy-interaction-preview").resolve()
    if output.is_relative_to(REPO) or REPO.is_relative_to(output):
        parser.error("Preview output must be outside the website repository")
    build_preview(args.source.resolve(), output)
    print(output)
