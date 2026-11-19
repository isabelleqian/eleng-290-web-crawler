"use strict";

const byId = id => document.getElementById(id);
const form = byId("review-filters");

function element(tag, value, className) {
  const node = document.createElement(tag);
  if (value) node.textContent = value;
  if (className) node.className = className;
  return node;
}

function link(label, href, external = false) {
  const node = element("a", label, "text-blue-200 underline");
  node.href = href;
  if (external) {
    node.target = "_blank";
    node.rel = "noreferrer";
  }
  return node;
}

function select(name, title, options) {
  const label = element("label", title, "flex min-w-0 flex-col gap-1 text-sm");
  const control = element("select", "", "w-full rounded-md border border-slate-700 bg-slate-950 px-2 py-2");
  control.name = name;
  control.add(new Option("All", ""));
  for (const [value, text] of options) control.add(new Option(text, value));
  label.append(control);
  byId("review-options").append(label);
  return control;
}

function sourceEvidence(source) {
  const {trial} = source;
  const block = element("section", "", "mt-3 rounded-lg border border-slate-800 bg-slate-950 p-3 text-sm");
  const heading = element("h4", source.title, "font-semibold text-white");
  const recordPage = source.candidate ? "policy_database.html" : "policy_database_archive.html";
  const links = element("p", "", "mt-1 flex flex-wrap gap-x-3 text-xs");
  links.append(link(`Document PC ${source.id}`, `${recordPage}#doc-pc-${source.id}`));
  if (source.pdf) links.append(link("Saved PDF", source.pdf, true));
  if (source.original) links.append(link("Source link", source.original, true));
  block.append(heading, links);
  for (const value of [
    source.publisher,
    trial.description,
    trial.status && "Intervention status: " + trial.status,
    trial.location && "Reported location: " + trial.location,
    "Source candidate codes: " + trial.codes.join(", "),
  ]) {
    if (value) block.append(element("p", value, "mt-2 break-words text-slate-300"));
  }
  for (const evidence of trial.evidence) {
    const pdf = evidence.pdf_page ?? evidence.page ?? "unknown";
    const printed = evidence.printed_page ? ` (printed p. ${evidence.printed_page})` : "";
    const quote = element("blockquote", "", "mt-2 border-l-2 border-slate-600 pl-3 text-slate-200");
    quote.append(element("p", evidence.quote), element("cite", `PDF p. ${pdf}${printed}`, "text-xs not-italic text-slate-400"));
    block.append(quote);
  }
  if (trial.questions.length) {
    block.append(element("h5", "Open questions", "mt-3 font-medium text-amber-200"));
    const list = element("ul", "", "ml-5 list-disc text-slate-300");
    for (const question of trial.questions) list.append(element("li", question));
    block.append(list);
  }
  return block;
}

async function main() {
  let raw;
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
  const {instances, codes, categories} = raw;
  const codebook = new Map(codes.map(code => [code.code, code]));
  const codeCounts = new Map();
  const locations = new Set();
  const statusLabels = {pending: "Pending human review"};
  for (const item of instances) {
    item.places = [...new Set(item.sources.map(source => source.trial.location.split(";")[0].trim()).filter(Boolean))];
    item.places.forEach(place => locations.add(place));
    item.codes.forEach(code => codeCounts.set(code, (codeCounts.get(code) || 0) + 1));
    item.search = [item.id, ...item.codes, ...item.sources.flatMap(source => [
      source.id, source.title, source.trial.description, source.trial.location,
      ...source.trial.evidence.map(evidence => evidence.quote),
    ])].join(" ").toLowerCase();
  }
  const sources = new Set(instances.flatMap(item => item.sources.map(source => source.id)));
  byId("review-summary").textContent = `${instances.length} provisional instances · ${sources.size} source documents · ${codeCounts.size} candidate codes. Evidence and codes are pending human review.`;
  const categoryOf = code => codebook.get(code)?.category;
  const categoriesInUse = new Set([...codeCounts.keys()].map(categoryOf));
  const category = select("category", "Codebook category", categories
    .filter(item => categoriesInUse.has(item.code))
    .map(item => [item.code, `${item.code} · ${item.name}`]));
  const code = select("code", "Candidate code", [...codeCounts.keys()].sort().map(value => [
    value, `${value} · ${codebook.get(value)?.name || value} (${codeCounts.get(value)})`,
  ]));
  select("status", "Review status", [...new Set(instances.map(item => item.reviewStatus))]
    .map(value => [value, statusLabels[value] || value]));
  select("place", "Reported location", [...locations].sort().map(value => [value, value]));

  const params = new URLSearchParams(location.search);
  for (const name of ["q", "category", "code", "status", "place"]) {
    const control = form.elements.namedItem(name);
    const value = params.get(name);
    if (value && (name === "q" || [...control.options].some(option => option.value === value))) {
      control.value = value;
    }
  }

  function render(updateUrl = false) {
    for (const option of code.options) {
      option.hidden = Boolean(option.value && category.value && categoryOf(option.value) !== category.value);
    }
    if (code.selectedOptions[0]?.hidden) code.value = "";
    const state = new URLSearchParams(new FormData(form));
    for (const [key, value] of [...state]) if (!value.trim()) state.delete(key);
    const query = (state.get("q") || "").trim().toLowerCase();
    const matching = instances.filter(item =>
      (!query || item.search.includes(query)) &&
      (!category.value || item.codes.some(value => categoryOf(value) === category.value)) &&
      (!code.value || item.codes.includes(code.value)) &&
      (!state.has("status") || item.reviewStatus === state.get("status")) &&
      (!state.has("place") || item.places.includes(state.get("place")))
    );
    const definition = byId("code-definition");
    const selected = codebook.get(code.value);
    definition.hidden = !selected;
    definition.replaceChildren();
    if (selected) {
      definition.append(element("h2", `${selected.code} · ${selected.name}`, "font-semibold"),
        element("p", selected.definition, "mt-2 text-sm text-slate-300"));
    }
    byId("review-count").textContent = `${matching.length} of ${instances.length} measure instances`;
    const results = byId("review-results");
    results.replaceChildren();
    if (!matching.length) results.append(element("p", "No measures match these filters.", "p-3 text-slate-300"));
    for (const item of matching) {
      const card = element("article", "", "rounded-xl border border-slate-800 bg-slate-900 p-4 target:border-blue-400");
      card.id = item.id;
      card.tabIndex = -1;
      const heading = element("h2", "", "font-semibold text-white");
      heading.append(link(item.id, "#" + item.id));
      card.append(heading);
      const sourceCount = item.sources.length;
      card.append(element("p", `${statusLabels[item.reviewStatus]} · ${sourceCount} ${sourceCount === 1 ? "source" : "sources"}`, "mt-1 text-xs text-amber-200"));
      card.append(element("p", item.sources[0].trial.description, "mt-2 text-sm text-slate-200"));
      const tags = element("div", "", "mt-2 flex flex-wrap gap-2 text-xs");
      for (const value of item.codes) {
        const tag = link(`${value} · ${codebook.get(value)?.name || value}`, `?code=${encodeURIComponent(value)}`);
        tag.className += " rounded border border-slate-700 px-2 py-1";
        tags.append(tag);
      }
      card.append(tags);
      const evidence = element("details", "", "mt-3");
      evidence.append(element("summary", "Review source evidence", "cursor-pointer text-sm text-blue-200"));
      for (const source of item.sources) evidence.append(sourceEvidence(source));
      card.append(evidence);
      results.append(card);
    }
    if (updateUrl) history.replaceState(null, "", location.pathname + (state.size ? "?" + state : ""));
  }

  function revealInstance() {
    const id = location.hash.slice(1);
    if (!instances.some(item => item.id === id)) return;
    if (!byId(id)) {
      form.reset();
      history.replaceState(null, "", location.pathname + location.hash);
      render();
    }
    const card = byId(id);
    card.querySelector("details").open = true;
    card.focus();
  }

  form.addEventListener("input", () => render(true));
  form.addEventListener("submit", event => { event.preventDefault(); render(true); });
  form.querySelector('[type="reset"]').addEventListener("click", event => {
    event.preventDefault();
    form.reset();
    render(true);
  });
  window.addEventListener("hashchange", revealInstance);
  render();
  revealInstance();
}

main().catch(error => {
  byId("review-count").textContent = "Unable to load measures. Reload the page to try again.";
  console.error(error);
});
