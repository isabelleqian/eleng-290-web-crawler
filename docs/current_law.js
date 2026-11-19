/* Current-law publication views share one explicit, fail-closed collection. */
(() => {
  'use strict';
  const pageSize = 12;
  const el = id => document.getElementById(id);
  const node = (tag, text = '', className = '') => {
    const n = document.createElement(tag);
    if (text !== null) n.textContent = text;
    if (className) n.className = className;
    return n;
  };
  const number = n => n.toLocaleString('en-US');
  const link = (text, href) => {
    const n = node('a', text); n.href = href;
    if (/^https?:/.test(href)) { n.target = '_blank'; n.rel = 'noopener noreferrer'; }
    return n;
  };
  async function load(path) {
    const response = await fetch(path + '?v=current-law-20261118-1');
    if (!response.ok) throw new Error('The checked collection could not be loaded.');
    return response.json();
  }
  function checkCollection(data) {
    if (!Array.isArray(data.records) || data.records.length !== data.counts.total) throw new Error('Collection count mismatch.');
    const ids = new Set();
    for (const r of data.records) {
      if (ids.has(r.id) || ![1, 2, 3].includes(r.tier) || !data.codebook[r.category_code] || r.current_status !== 'In force in the official current text reviewed') throw new Error('An unapproved or inconsistent legal entry was rejected.');
      ids.add(r.id);
    }
    for (const tier of [1, 2, 3]) if (data.records.filter(r => r.tier === tier).length !== data.counts.by_tier[tier]) throw new Error('Tier count mismatch.');
  }
  function silentReset(form) { form.dataset.silentReset = '1'; form.reset(); delete form.dataset.silentReset; }
  function detail(dl, label, text) {
    const group = node('div'); group.append(node('dt', label), node('dd', text)); dl.append(group);
  }
  function record(r) {
    const item = node('details', null, `law-record tier-${r.tier}`); item.id = 'law-' + r.id;
    const summary = node('summary');
    summary.append(node('span', `Tier ${r.tier} · ${r.jurisdiction} · ${r.category_code}`, 'record-meta'), node('strong', r.title), node('span', r.citation, 'record-citation'));
    item.append(summary, node('p', r.summary));
    const dl = node('dl', null, 'record-details');
    detail(dl, 'Legal instrument', `${r.instrument_type} · ${r.id}`);
    detail(dl, 'Primary codebook subclass', `${r.category_code} · ${r.category_name}`);
    detail(dl, 'Scope of application', r.scope);
    detail(dl, 'Tier rationale', r.classification_rationale);
    detail(dl, 'Operative supporting passage', r.operative_evidence);
    detail(dl, 'Current status', `${r.current_status}. Checked ${r.status_checked_on}.`);
    detail(dl, 'Source currency', r.source_currency);
    detail(dl, 'Commencement', r.effective_date);
    detail(dl, 'Amendment/version information', r.latest_amendment);
    detail(dl, 'Liability and penalties', r.penalties_and_liability);
    detail(dl, 'Exceptions and qualifications', r.exceptions);
    if (r.notes) detail(dl, 'Notes', r.notes);
    item.append(dl, link('Read the official operative source ↗', r.official_url));
    return item;
  }
  function countTable(body, groups, records, describe) {
    body.replaceChildren();
    for (const group of groups) {
      const subset = records.filter(r => describe.key(r) === group);
      const row = node('tr'); row.append(node('td', describe.label(group)));
      for (const tier of [1, 2, 3]) row.append(node('td', number(subset.filter(r => r.tier === tier).length)));
      row.append(node('td', number(subset.length))); body.append(row);
    }
    const total = node('tr'); total.append(node('th', 'Total'));
    for (const tier of [1, 2, 3]) total.append(node('td', number(records.filter(r => r.tier === tier).length)));
    total.append(node('td', number(records.length))); body.append(total);
  }
  function lawPage(data) {
    const records = data.records; let currentPage = 0;
    el('law-total').textContent = number(records.length);
    el('law-jurisdictions').textContent = number(Object.keys(data.counts.by_jurisdiction).length);
    el('law-categories').textContent = '6';
    const families = {A:'Access and movement restrictions', B:'Physical traffic calming and street design', C:'Traffic control and operations', D:'Pricing and charges', E:'Routing and navigation', F:'Planning, data, and demand management'};
    for (const [family, name] of Object.entries(families)) {
      const section = node('section', null, 'codebook-family');
      section.append(node('h3', `${family}. ${name}`));
      const list = node('dl', null, 'codebook-definitions');
      for (const [code, label] of Object.entries(data.codebook).filter(([code]) => code.startsWith(family))) {
        const row = node('div'); row.append(node('dt', code), node('dd', label)); list.append(row);
      }
      section.append(list); el('full-codebook').append(section);
    }
    el('collection-description').textContent = `${number(records.length)} checked, nonoverlapping legal entries appear in the public collection. Pending proposals, future-effective instruments, non-specific placeholders and sources awaiting individual legal verification are outside this collection.`;
    el('screening-summary').textContent = `This verified subset covers the federal level and ${Object.keys(data.counts.by_jurisdiction).length - 1} states. Each retained entry was checked against official operative text; nationwide, DC and California local coverage remain incomplete. Source currency is stated per record.`;
    for (const tier of [1, 2, 3]) el('tier-count-' + tier).textContent = number(data.counts.by_tier[tier]);
    const jurisdictions = Object.keys(data.counts.by_jurisdiction).sort();
    for (const value of jurisdictions) { const o = node('option', value); o.value = value; el('current-law-jurisdiction').append(o); }
    for (const code of Object.keys(data.codebook).sort()) { const o = node('option', `${code} · ${data.codebook[code]}`); o.value = code; el('current-law-category').append(o); }
    for (const type of Object.keys(data.counts.by_instrument_type).sort()) { const o = node('option', type); o.value = type; el('current-law-type').append(o); }
    countTable(el('jurisdiction-counts'), jurisdictions, records, {key: r => r.jurisdiction, label: g => g});
    countTable(el('category-counts'), Object.keys(data.codebook).sort(), records, {key: r => r.category_code, label: g => `${g} · ${data.codebook[g]}`});
    for (const [type, count] of Object.entries(data.counts.by_instrument_type)) el('instrument-counts').append(node('p', `${type}: ${number(count)}`));
    function filtered() {
      const query = el('current-law-search').value.trim().toLowerCase();
      return records.filter(r => (!el('current-law-tier').value || r.tier === Number(el('current-law-tier').value)) && (!el('current-law-jurisdiction').value || r.jurisdiction === el('current-law-jurisdiction').value) && (!el('current-law-category').value || r.category_code === el('current-law-category').value) && (!el('current-law-type').value || r.instrument_type === el('current-law-type').value) && (!query || [r.id, r.title, r.citation, r.summary, r.scope, r.classification_rationale, r.category_name].join(' ').toLowerCase().includes(query)));
    }
    function render() {
      const rows = filtered(); const pages = Math.max(1, Math.ceil(rows.length / pageSize)); currentPage = Math.min(currentPage, pages - 1);
      el('current-law-results-count').textContent = `${number(rows.length)} of ${number(records.length)} current legal entries`;
      el('current-law-records').replaceChildren(...rows.slice(currentPage * pageSize, (currentPage + 1) * pageSize).map(record));
      if (!rows.length) el('current-law-records').append(node('p', 'No checked instruments match these filters.'));
      el('law-page').textContent = `Page ${currentPage + 1} of ${pages}`;
      el('law-previous').disabled = currentPage === 0; el('law-next').disabled = currentPage + 1 >= pages;
    }
    function activate(id) {
      for (const section of document.querySelectorAll('.research-pane')) section.hidden = section.id !== id;
      for (const a of document.querySelectorAll('[data-section]')) { if (a.dataset.section === id) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); }
    }
    function hash() {
      const value = decodeURIComponent(location.hash.slice(1)) || 'summary';
      if (value.startsWith('law-')) {
        const r = records.find(r => 'law-' + r.id === value);
        if (r) { silentReset(el('current-law-filters')); el('current-law-search').value = r.id; currentPage = 0; render(); activate('database'); const item = el(value); item.open = true; item.scrollIntoView({block: 'start'}); return; }
      }
      activate(['summary', 'empirical', 'database'].includes(value) ? value : 'summary');
    }
    el('current-law-filters').addEventListener('input', () => { currentPage = 0; render(); });
    el('current-law-filters').addEventListener('change', () => { currentPage = 0; render(); });
    el('current-law-filters').addEventListener('submit', e => e.preventDefault());
    el('current-law-filters').addEventListener('reset', () => { if (el('current-law-filters').dataset.silentReset) return; queueMicrotask(() => { currentPage = 0; render(); }); });
    el('law-previous').onclick = () => { currentPage--; render(); };
    el('law-next').onclick = () => { currentPage++; render(); };
    for (const a of document.querySelectorAll('[data-tier-link]')) a.addEventListener('click', () => { silentReset(el('current-law-filters')); el('current-law-tier').value = a.dataset.tierLink; currentPage = 0; render(); activate('database'); });
    window.addEventListener('hashchange', hash); render(); hash();
    el('law-load-status').textContent = `Current collection loaded · ${number(records.length)} entries · reviewed ${data.as_of}`;
  }
  function crosswalkPage(laws, data) {
    const eligible = new Set(laws.records.map(r => r.id));
    const links = data.verified_links.filter(r => eligible.has(r.instrument_id) && r.verification_status === 'Verified article-to-current-provision relationship');
    if (links.length !== data.verified_links.length) throw new Error('An unapproved crosswalk relationship was rejected.');
    el('crosswalk-law-total').textContent = number(laws.records.length);
    el('crosswalk-link-total').textContent = number(links.length);
    el('crosswalk-news-total').textContent = number(data.news.length);
    el('crosswalk-status').textContent = data.status;
    el('crosswalk-load-status').textContent = 'Current-law references reconciled with the checked collection.';
    for (const r of links) el('verified-crosswalk-links').append(link(r.instrument_id, 'law_database.html#law-' + encodeURIComponent(r.instrument_id)));
    let currentPage = 0;
    function newsRecord(r) {
      const d = node('details', null, 'news-reference'); d.id = 'doc-' + r.source_id;
      const s = node('summary'); s.append(node('span', `${r.date || 'Date not established'} · ${r.jurisdiction}`, 'record-meta'), node('strong', r.headline));
      d.append(s, node('p', r.factual_summary || 'No archived factual summary is available.'), node('p', 'Current-law relationship: not independently established in this review.', 'method-note'), link('Open the news source ↗', r.url)); return d;
    }
    function filtered() {
      const query = el('crosswalk-search').value.trim().toLowerCase();
      return data.news.filter(r => !query || [r.news_id, r.source_id, r.headline, r.jurisdiction, r.factual_summary].join(' ').toLowerCase().includes(query));
    }
    function render() {
      const rows = filtered(); const pages = Math.max(1, Math.ceil(rows.length / pageSize)); currentPage = Math.min(currentPage, pages - 1);
      el('crosswalk-results-count').textContent = `${number(rows.length)} of ${number(data.news.length)} reference news records`;
      el('crosswalk-news-records').replaceChildren(...rows.slice(currentPage * pageSize, (currentPage + 1) * pageSize).map(newsRecord));
      el('crosswalk-page').textContent = `Page ${currentPage + 1} of ${pages}`; el('crosswalk-previous').disabled = currentPage === 0; el('crosswalk-next').disabled = currentPage + 1 >= pages;
    }
    function hash() {
      const id = decodeURIComponent(location.hash.slice(1)); if (!id.startsWith('doc-')) return;
      const index = data.news.findIndex(r => 'doc-' + r.source_id === id); if (index < 0) return;
      silentReset(el('crosswalk-filters')); currentPage = Math.floor(index / pageSize); render(); const item = el(id); if (item) { item.open = true; item.scrollIntoView({block: 'start'}); }
    }
    el('crosswalk-filters').addEventListener('input', () => { currentPage = 0; render(); });
    el('crosswalk-filters').addEventListener('reset', () => { if (el('crosswalk-filters').dataset.silentReset) return; queueMicrotask(() => { currentPage = 0; render(); }); });
    el('crosswalk-filters').addEventListener('submit', e => e.preventDefault());
    el('crosswalk-previous').onclick = () => { currentPage--; render(); }; el('crosswalk-next').onclick = () => { currentPage++; render(); };
    window.addEventListener('hashchange', hash); render(); hash();
  }
  async function init() {
    const page = document.body.dataset.researchPage;
    const status = el(page === 'law' ? 'law-load-status' : 'crosswalk-load-status');
    try {
      const data = await load('data/current_law_database.json'); checkCollection(data);
      if (page === 'law') lawPage(data);
      else crosswalkPage(data, await load('data/current_news_law_crosswalk.json'));
    } catch (error) {
      status.textContent = 'The verified collection is unavailable or inconsistent. No historical candidate data has been substituted. Please reload or consult the research audit.';
      status.setAttribute('role', 'alert'); console.error(error);
    }
  }
  init();
})();
