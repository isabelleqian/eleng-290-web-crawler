"use strict";

const byId = id => document.getElementById(id);
const archiveMode = document.body.dataset.mode === "archive";
const form = byId("filters");
const labels = {
  INCLUDE: "Include",
  EXCLUDE: "Exclude",
  UNCERTAIN: "Uncertain",
  pending: "Pending human decision",
  trial: "Exploratory coding",
  unextracted: "Not extracted",
  unknown: "Unknown",
  candidate: "Audit candidate",
  other: "Other screening record",
  advanced_only: "Advanced only",
  phrase_incremental: "Phrase incremental",
  shared: "Shared",
};
const human = row => row.human || "pending";
const extraction = row => row.trials.length ? "trial" : "unextracted";
const year = row => row.year || "unknown";
const facets = [
  ["human", "Human decision", row => [human(row)], true],
  ...(archiveMode ? [
    ["model", "Round 3 model proposal", row => [row.model], false],
    ["membership", "Candidate membership", row => [row.candidate ? "candidate" : "other"], false],
  ] : [
    ["extraction", "Measure extraction", row => [extraction(row)], true],
    ["year", "Publication year", row => [year(row)], false],
    ["publisher", "Publisher", row => [row.publisher || "unknown"], false],
  ]),
  ["query", "Query ID", row => row.queries, false],
  ...(archiveMode ? [["collection", "Collection", row => [row.collection], false]] : []),
];

function element(tag, value, className) {
  const node = document.createElement(tag);
  if (value) node.textContent = value;
  if (className) node.className = className;
  return node;
}

function countValues(rows, getValues) {
  const counts = new Map();
  for (const row of rows) {
    for (const value of new Set(getValues(row))) counts.set(value, (counts.get(value) || 0) + 1);
  }
  return counts;
}

function populateFilters(rows) {
  for (const [key, title, getValues, buttons] of facets) {
    const counts = countValues(rows, getValues);
    const entries = [...counts.keys()].sort((a, b) => (labels[a] || a).localeCompare(labels[b] || b));
    const area = byId(["query", "collection"].includes(key) ? "extra-filters" : "main-filters");
    if (buttons) {
      const group = element("fieldset", "", "min-w-0");
      group.append(element("legend", title, "mb-1 text-xs"));
      for (const value of ["", ...entries]) {
        const label = element("label", "", "mr-2 inline-flex cursor-pointer items-center gap-1 rounded-md border border-slate-700 px-2 py-2 text-xs has-[:checked]:border-blue-400 has-[:checked]:bg-blue-950");
        const radio = element("input");
        radio.type = "radio";
        radio.name = key;
        radio.value = value;
        radio.defaultChecked = !value;
        label.append(radio, value ? `${labels[value] || value} (${counts.get(value)})` : `All (${rows.length})`);
        group.append(label);
      }
      area.append(group);
    } else {
      const label = element("label", title, "flex flex-col gap-1 text-xs");
      const select = element("select", "", "max-w-64 rounded-lg border border-slate-700 bg-slate-950 px-2 py-2");
      select.name = key;
      select.add(new Option(`All (${rows.length})`, ""));
      for (const value of entries) select.add(new Option(`${labels[value] || value} (${counts.get(value)})`, value));
      label.append(select);
      area.append(label);
    }
  }
  if (archiveMode) byId("availability").hidden = true;
}

function appendLink(parent, label, url, external = false) {
  if (!url) return;
  const link = element("a", label, "mr-3 inline-block text-blue-200 underline");
  link.href = url;
  if (external) {
    link.target = "_blank";
    link.rel = "noreferrer";
  }
  parent.append(link);
}

function details(title) {
  const block = element("details", "", "mt-2");
  block.append(element("summary", title, "cursor-pointer text-blue-200"));
  return block;
}

function renderRows(matches, groups) {
  const result = document.createDocumentFragment();
  for (const row of matches) {
    const tr = element("tr", "", "align-top target:bg-blue-950");
    tr.id = "doc-pc-" + row.id;
    tr.tabIndex = -1;
    const documentCell = element("td", "", "w-1/2 p-3");
    const permalink = element("a", row.title, "font-semibold text-white hover:underline");
    permalink.href = "#" + tr.id;
    documentCell.append(permalink);
    const meta = [row.publisher, row.date && `${row.date} (${row.dateBasis})`, row.document].filter(Boolean);
    documentCell.append(element("p", [...meta, "PC " + row.id].join(" · "), "mt-1 text-xs text-slate-400"));
    const sources = element("div", "", "mt-2 text-xs");
    appendLink(sources, "Policy Commons", row.url, true);
    appendLink(sources, "Publisher original", row.original, true);
    appendLink(sources, "Saved PDF", row.pdf, true);
    documentCell.append(sources);
    const peers = (groups.get(row.group) || []).filter(peer => peer.id !== row.id);
    if (peers.length) {
      const versions = details(`Tentative document group (${peers.length + 1} records)`);
      for (const peer of peers) appendLink(versions, "PC " + peer.id, "#doc-pc-" + peer.id);
      documentCell.append(versions);
    }
    const decision = element("td", labels[human(row)], "p-3");
    if (archiveMode) {
      decision.append(element("p", `Round 3 model: ${labels[row.model]} · ${labels[row.candidate ? "candidate" : "other"]}`, "mt-1 text-xs text-slate-400"));
    }
    const screening = details("Screening details");
    if (row.human) screening.append(element("p", `Human decision source: ${row.decisionSource}`, "mt-1 text-xs"));
    for (const value of [row.scope, row.reason, row.evidenceLevel.replaceAll("_", " "),
      row.auditReason && "Candidate audit: " + row.auditReason,
      row.auditEvidence,
      row.evidencePages.length ? "Source evidence pages: " + row.evidencePages.join(", ") : "",
      row.queries.length ? "Query IDs: " + row.queries.join(", ") : ""]) {
      if (value) screening.append(element("p", value, "mt-1 text-xs text-slate-300"));
    }
    decision.append(screening);
    const measure = element("td", labels[extraction(row)], "p-3");
    if (row.trials.length) {
      const codes = element("div", "", "mt-2 flex flex-wrap gap-2 text-xs");
      for (const code of [...new Set(row.trials.flatMap(trial => trial.codes))].sort()) {
        appendLink(codes, code, "policy_measure_review.html?code=" + encodeURIComponent(code));
      }
      measure.append(codes);
      const evidence = details(`Measure evidence (${row.trials.length})`);
      for (const trial of row.trials) {
        const block = element("div", "", "mt-3 border-l border-amber-600 pl-2 text-xs");
        appendLink(block, trial.id, "policy_measure_review.html#" + encodeURIComponent(trial.id));
        block.append(element("p", `Candidate codes: ${trial.codes.join(", ")}`, "font-semibold"));
        for (const value of [trial.description, trial.status, trial.location,
          ...trial.evidence.map(item => `PDF p. ${item.pdf_page ?? item.page ?? "unknown"}${item.printed_page ? ` (printed p. ${item.printed_page})` : ""} · ${item.quote}`),
          ...trial.questions]) {
          if (value) block.append(element("p", value, "mt-1"));
        }
        evidence.append(block);
      }
      measure.append(evidence);
    }
    tr.append(documentCell, decision, measure);
    result.append(tr);
  }
  if (!matches.length) {
    const tr = element("tr");
    const cell = element("td", "No documents match these filters.", "p-6 text-slate-300");
    cell.colSpan = 3;
    tr.append(cell);
    result.append(tr);
  }
  byId("rows").replaceChildren(result);
}

async function main() {
  let all;
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
  }
  const candidates = all.filter(row => row.candidate);
  const records = archiveMode ? all : candidates;
  const groups = new Map();
  for (const row of candidates) {
    if (!groups.has(row.group)) groups.set(row.group, []);
    groups.get(row.group).push(row);
  }
  const format = count => count.toLocaleString("en-US");
  const modelCounts = countValues(all, row => [row.model]);
  byId("scope-summary").textContent = archiveMode
    ? `Round 3 screening snapshot · ${format(all.length)} records · Model proposals: ${modelCounts.get("INCLUDE")} include, ${modelCounts.get("UNCERTAIN")} uncertain, ${modelCounts.get("EXCLUDE")} exclude.`
    : `${candidates.length} source records · ${groups.size} tentative document groups · ${candidates.filter(row => row.trials.length).length} documents with exploratory coding.`;
  const switchView = byId("switch-view");
  switchView.href = archiveMode ? "policy_database.html" : "policy_database_archive.html";
  switchView.textContent = archiveMode
    ? `← Policy Database (${candidates.length} candidates)`
    : `View Screening Archive (${format(all.length)} records) →`;
  populateFilters(records);
  byId("year-chart").hidden = archiveMode;
  const years = [...countValues(records, row => [year(row)]).keys()].sort();
  const searchText = new Map(records.map(row => [row.id, [
    row.title, row.publisher, row.id, "pc_" + row.id, row.document, row.reason, row.auditReason,
    ...row.trials.map(trial => trial.id),
  ].join(" ").toLowerCase()]));

  function restoreParams() {
    form.reset();
    for (const [key, value] of new URLSearchParams(location.search)) {
      const input = form.elements.namedItem(key);
      if (!input) continue;
      if (input.type === "checkbox") input.checked = value === "on";
      else if (input instanceof HTMLSelectElement && !Array.from(input.options).some(option => option.value === value)) continue;
      else input.value = value;
      if (key === "query" || key === "collection") byId("more-filters").open = true;
    }
  }

  function render(updateUrl = true) {
    const active = new URLSearchParams(new FormData(form));
    for (const [key, value] of [...active]) if (!value.trim()) active.delete(key);
    const needle = (active.get("q") || "").trim().toLowerCase();
    const base = records.filter(row =>
      (!needle || searchText.get(row.id).includes(needle)) &&
      (!active.has("pdf") || archiveMode || row.pdf) &&
      (!active.has("original") || archiveMode || row.original) &&
      facets.every(([key, , getter]) => key === "year" || !active.has(key) || getter(row).includes(active.get(key)))
    );
    const matches = base.filter(row => !active.has("year") || year(row) === active.get("year"));
    byId("results-count").textContent = `${format(matches.length)} of ${format(records.length)} records`;
    renderRows(matches, groups);
    if (!archiveMode) {
      const bars = byId("year-bars");
      const counts = countValues(base, row => [year(row)]);
      const maximum = Math.max(1, ...counts.values());
      const focusYear = document.activeElement?.dataset.year;
      bars.replaceChildren();
      for (const value of years) {
        const count = counts.get(value) || 0;
        const button = element("button", "", "flex w-14 flex-col items-center justify-end rounded-md border border-slate-700 p-1 text-xs hover:bg-slate-800 aria-pressed:border-blue-400");
        button.type = "button";
        button.dataset.year = value;
        button.setAttribute("aria-pressed", String(active.get("year") === value));
        const bar = element("span", "", "w-5 rounded-t bg-blue-500");
        bar.style.height = `${Math.round(56 * count / maximum)}px`;
        bar.setAttribute("aria-hidden", "true");
        button.append(count, bar, labels[value] || value);
        button.addEventListener("click", () => {
          form.elements.year.value = form.elements.year.value === value ? "" : value;
          update();
        });
        bars.append(button);
        if (focusYear === value) button.focus();
      }
    }
    if (updateUrl) {
      const query = active.toString();
      history.replaceState(null, "", location.pathname + (query ? "?" + query : ""));
    }
  }

  function update() {
    byId("notice").textContent = "";
    render();
  }

  function revealHash() {
    const anchor = location.hash.slice(1);
    if (!/^doc-pc-\d+$/.test(anchor)) return;
    let row = byId(anchor);
    if (!row && records.some(record => "doc-pc-" + record.id === anchor)) {
      form.reset();
      history.replaceState(null, "", location.pathname + location.hash);
      render(false);
      byId("notice").textContent = "Filters cleared to show the linked record.";
      row = byId(anchor);
    }
    if (row) {
      row.focus({preventScroll: true});
      row.scrollIntoView({block: "center"});
    }
  }

  restoreParams();
  render(false);
  revealHash();
  form.addEventListener("input", update);
  form.addEventListener("submit", event => { event.preventDefault(); update(); });
  form.querySelector('[type="reset"]').addEventListener("click", event => {
    event.preventDefault();
    form.reset();
    update();
  });
  window.addEventListener("hashchange", revealHash);
}

main().catch(error => {
  byId("results-count").textContent = "Unable to load the Policy Database. Reload the page to try again.";
  console.error(error);
});
