"use strict";

const policyOverview = (() => {
  const data = JSON.parse(document.getElementById("policy-overview-data").textContent);
  const reviewPage = "policy_measure_review.html";

  function link(text, href) {
    const node = document.createElement("a");
    node.textContent = text;
    node.href = href;
    node.className = "text-blue-200 underline underline-offset-2";
    return node;
  }

  function paragraph(text) {
    const node = document.createElement("p");
    node.textContent = text;
    return node;
  }

  function forCode(code) {
    return reviewPage + "?code=" + encodeURIComponent(code);
  }

  function describeMeasures(summary) {
    const note = paragraph(`Policy Commons adds ${data.total} provisional instances pending human review. News bars count matching articles.`);
    note.className = "mt-2 text-sm text-slate-300";
    summary.after(note);
  }

  function measureCounts(container, measure) {
    const count = data.counts[measure.code] || 0;
    container.className = "shrink-0 text-right text-xs text-blue-300";
    const policy = count ? link(`Policy ${count}`, forCode(measure.code)) : document.createElement("span");
    if (!count) policy.textContent = "Policy 0";
    policy.classList.add("block", "mt-1");
    policy.title = `${count} provisional Policy instances`;
    policy.addEventListener("click", event => event.stopPropagation());
    const news = document.createElement("span");
    news.textContent = `News ${measure.count || 0}`;
    container.append(news, policy);
  }

  function measureDetails(container, measure) {
    const news = measure.count || 0;
    const count = data.counts[measure.code] || 0;
    const note = paragraph(`${news} matching News ${news === 1 ? "article" : "articles"} · `);
    const label = `${count} provisional Policy ${count === 1 ? "instance" : "instances"}`;
    note.append(count ? link(label, forCode(measure.code)) : label);
    note.className = "mb-3 text-sm text-slate-300";
    container.append(note);
  }

  function renderLocation(place) {
    document.getElementById("loc-badge-count").textContent = "1 provisional Policy instance";
    const detail = document.getElementById("location-detail-content");
    const heading = document.createElement("h4");
    heading.className = "text-sm font-semibold text-white";
    heading.textContent = place.name;
    const source = link("City of Bellevue project source", place.source);
    source.classList.add("block");
    detail.replaceChildren(
      heading,
      paragraph(place.scope),
      paragraph(place.site),
      link(`Review ${place.id}`, reviewPage + "#" + place.id),
      source,
    );
  }

  function mountMap(project, selectLocation) {
    const layer = document.getElementById("policy-measure-map-layer");
    for (const place of data.places) {
      const showPlace = () => selectLocation({...place, articles: [], policyMeasure: place}, false);
      const {x, y} = project(place.lat, place.lon);
      const pin = document.createElementNS("http://www.w3.org/2000/svg", "path");
      pin.setAttribute("d", `M ${x} ${y - 9} l 9 9 -9 9 -9 -9 z`);
      pin.setAttribute("fill", "#fb923c");
      pin.setAttribute("stroke", "#171a1b");
      pin.setAttribute("stroke-width", "2");
      pin.setAttribute("vector-effect", "non-scaling-stroke");
      pin.setAttribute("role", "button");
      pin.setAttribute("tabindex", "0");
      pin.setAttribute("aria-label", `Show Policy measure for ${place.name}`);
      pin.style.cursor = "pointer";
      pin.addEventListener("click", showPlace);
      pin.addEventListener("keydown", event => {
        if (event.key !== "Enter" && event.key !== " ") return;
        event.preventDefault();
        showPlace();
      });
      layer.append(pin);
    }
  }

  return {describeMeasures, measureCounts, measureDetails, mountMap, renderLocation};
})();
