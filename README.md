# AI News Scraper: URL importer and archive

This project collects news and regulations about navigation-app traffic, access restrictions, routing-app rules, and community complaints. It has two local stages:

- `import`, `list`, and `export` store URLs you already collected. They do not search the web or download pages.
- `crawl` reads that queue and archives each selected URL. It uses a direct HTTP request for the status, redirects, and original PDF bytes, then uses locally installed Crawl4AI to render HTML.

It does not call a language model, classify topics, or judge credibility.

The sample URLs use `example.com` and are fictional. Do not crawl them as research articles.

## Quick start

Open a terminal in this project folder. Python 3.11 or newer is enough. There is nothing to install.

```bash
python3 -m news_importer import samples/discoveries.csv
python3 -m news_importer list --study-area SF
python3 -m news_importer export --output data/exports/pending.csv
```

The first command creates `data/news.sqlite` and a JSON report under `data/reports/`. For the sample CSV you should see:

```text
accepted: 13
rejected: 0
repeated_urls: 1
warnings: 2
```

`repeated_urls: 1` is the second copy of `https://example.com/seattle/ferry-queue`. Both copies are stored. `warnings: 2` is the Los Angeles row: it is marked `google_first_page` but has no search time and no result rank. It is still imported.

Add `--dry-run` to preview those counts without writing the database or a report.

## CSV contract

The first row is a header. The file must be UTF-8 or UTF-8 with a BOM. Values can be quoted, so a field may contain commas or line breaks. Known column names are matched without regard to case. `URL` and `url` are the same column.

Required column:

| Column | Meaning |
| --- | --- |
| `url` | The URL as collected. This is the only required field. |

Optional columns:

| Column | Meaning |
| --- | --- |
| `title` | Title from the search result or your notes. |
| `query` | The search text that produced the URL. |
| `study_area` | Which research bucket you were searching. See below. |
| `discovery_method` | How you found the URL. See the allowed values. |
| `searched_at` | When the search was run, not when the file was imported. |
| `result_rank` | Position in the result list, starting at 1. |
| `snippet` | The result snippet you saw. |
| `search_language` | Language used for the search, such as `en`. |
| `search_location` | Location setting used for the search, if you recorded one. |
| `notes` | Anything else you want to keep. |

Any other column is kept. It is stored as JSON on the discovery and included again in the crawl-queue export. The sample file uses an extra `collector` column this way.

A blank cell means "not supplied." It stays null. The importer does not guess a title, date, rank, or query. If you pass a command-line default, that default fills blank cells only. A nonblank cell wins, even when the cell is invalid. An invalid cell rejects that row; it does not fall back to the default.

If `discovery_method` is blank and you did not pass `--discovery-method`, it is stored as `unknown`.

Allowed discovery methods:

- `google_first_page`
- `gemini`
- `grok_bot`
- `publisher_search`
- `other`
- `unknown`

Spelling is matched without case sensitivity, so `Gemini` is stored as `gemini`. Any other supplied value is stored as written and flagged for review. Importing a `google_first_page` row does not check that Google actually showed that link.

For `searched_at`, use either:

- a date: `2026-02-11`
- a timestamp with a timezone: `2026-03-01T15:04:00Z` or `2026-03-01T15:04:00-08:00`

A timestamp without a timezone is rejected. The import clock is never copied into `searched_at`.

`result_rank`, when present, must be a positive integer such as `1` or `12`. Zero, decimals, and words are rejected.

Example row, split here only so it is readable:

```csv
url,title,query,study_area,discovery_method,searched_at,result_rank,notes
https://example.com/atlanta/waze-cut-through,"Fictional Atlanta cut-through, banned",Atlanta navigation app traffic,Atlanta,google_first_page,2026-03-01T15:04:00-08:00,1,Hand-collected example.
```

`samples/discoveries.csv` is a full fictional file in this shape.

## Text files

A `.txt` file has one URL per nonblank line. Blank lines are skipped. There are no metadata columns, so use command-line defaults when every line shares the same study area, method, query, or search time.

```bash
python3 -m news_importer import samples/discoveries.txt \
  --study-area SF \
  --discovery-method grok_bot \
  --query "San Francisco routing app restrictions" \
  --searched-at 2026-04-01
```

Record numbers in a text file are line numbers, so the sample's third URL is record 4 because line 3 is blank. In a CSV, record numbers count data rows after the header, starting at 1. Completely blank CSV lines are ignored.

## Study areas

The 12 research buckets live in `news_importer/study_areas.json`. A recognized name or alias is stored as a stable id. The text you typed is kept in `study_area_raw`.

| Stored id | Also accepted |
| --- | --- |
| `atlanta` | Atlanta, ATL |
| `boston` | Boston |
| `chicago` | Chicago |
| `los_angeles` | Los Angeles, LA, L.A. |
| `miami` | Miami |
| `new_york_city` | New York City, NYC, N.Y.C. |
| `philadelphia` | Philadelphia, Philly |
| `salt_lake_city` | Salt Lake City, Salt Lake, SLC |
| `san_francisco` | San Francisco, SF, S.F. |
| `seattle` | Seattle |
| `california` | California, California (state), CA |
| `new_jersey` | New Jersey, New Jersey (state), NJ, N.J. |

`study_area` is the bucket you were searching. It is not a decision about which government the article actually concerns. A missing study area is stored as null and flagged. An unknown value, such as `Paris` or `Los Angeles, CA`, is stored as written and flagged. `New York` alone is not treated as New York City, because that phrase can mean the state, and this project does not include New York State as a bucket.

You can point at another JSON file with `--study-areas`.

## Duplicates and reimports

Every accepted row becomes its own discovery with its own id. Identical rows are kept. The same URL found by two searches is two discoveries.

The importer also builds a normalized URL for comparison:

- surrounding whitespace is removed
- the scheme and hostname are lowercased
- the fragment (`#section`) is removed
- path capitalization, query parameters, their order, and percent-encoding stay as written
- `http` and `https` stay different
- `www` and non-`www` stay different
- tracking parameters are not removed

A repeated URL is an accepted row whose normalized URL already appeared earlier in the same import, or was already stored in the database. The count is how many accepted rows are repeats. The first stored copy is not a repeat. Nothing is deleted or merged.

Running import on a file that was already imported creates a new batch and new discovery rows. The old batch stays. The new rows are reported as repeats. Use the batch id when you want to inspect one import by itself.

Rejected rows are not discoveries. They are listed in the batch's JSON report with the original cells, the record number, and the reason. If some rows in a file are valid and some are not, the valid rows are still imported. A broken CSV file, such as a missing `url` column or an unclosed quote, stops the whole import and does not add a batch.

## What import checks, and what it leaves unverified

Checked before a row is stored:

- the file is readable UTF-8 CSV or text
- `url` is present
- the URL is absolute `http` or `https` and has a hostname
- a port, if written, is an integer from 1 to 65535
- the URL has no unescaped whitespace
- `result_rank`, if written, is a positive integer
- `searched_at`, if written, is a date or a timestamp with a timezone

Flagged on rows that are still stored:

- missing or unrecognized study area
- unrecognized discovery method
- `google_first_page` missing `query`, `searched_at`, or `result_rank`

Not checked:

- the page exists or is reachable
- the page is paywalled
- a PDF opens
- the article is about that study area, or about any particular jurisdiction
- Google showed the link on the first page
- credibility, relevance, novelty, or category

Import does not assign those. A later `crawl` can store an observed title and publication date from the page in the archive. It leaves the imported title and snippet on the discovery row.

## Commands

Run these from the project folder. The default database is `data/news.sqlite`. The default report directory is `data/reports/`.

Import a CSV:

```bash
python3 -m news_importer import samples/discoveries.csv
```

Preview only:

```bash
python3 -m news_importer import samples/discoveries.csv --dry-run
```

Import a text list with defaults for the blank metadata:

```bash
python3 -m news_importer import samples/discoveries.txt \
  --study-area SF \
  --discovery-method grok_bot \
  --query "San Francisco routing app restrictions" \
  --searched-at 2026-04-01
```

Use another database or report folder:

```bash
python3 -m news_importer import samples/discoveries.csv \
  --db data/news.sqlite \
  --report-dir data/reports
```

If the file extension is not `.csv` or `.txt`, add `--format csv` or `--format txt`.

Show recent discoveries:

```bash
python3 -m news_importer list
python3 -m news_importer list --study-area NYC --limit 10
python3 -m news_importer list --batch batch_your_batch_id_here
```

`--study-area` accepts the same aliases as import. `--limit` defaults to 20.

Export the crawl queue:

```bash
python3 -m news_importer export --output data/exports/pending.csv
```

Omit `--output` to write the CSV to the terminal. Export selects rows whose `crawl_status` is `pending`. It does not change that status, so exporting twice returns the same rows until a later stage updates them.

Exit code 0 means the command finished. A finished import can still have rejected rows; read `rejected:` in the summary. Exit code 1 means the file or the database failed and no new batch was written. If the database save succeeds and the report file cannot be written, the command exits with an error that includes the batch id. The discoveries are in SQLite.

Each real import is one database transaction. A database failure rolls the batch back. Earlier batches are left as they were.

## Database and reports

`import_batches` records the file, the command-line defaults, the time of import in UTC, and the counts.

`discoveries` stores, for each accepted row:

- discovery id and batch id
- original URL, normalized URL, and hostname
- the supplied metadata, with extra columns in `extra_metadata_json`
- the original cells in `original_record_json`
- source path and record number
- import time in UTC
- warnings in `warnings_json`
- `crawl_status`, which starts as `pending`
- `is_repeat`, which records whether the normalized URL had already been seen at import time
- `source_id`, `last_outcome`, and `last_attempt_id`, which stay null until a crawl links the row to an archive

An existing database gains those three columns the next time you import or crawl. Discovery ids and the original rows are kept. `sources`, `source_discoveries`, and `fetch_attempts` record the shared archive and each attempt.

The batch report is `data/reports/<batch-id>.json`. It repeats the counts and lists rejected rows, warnings, and repeated normalized URLs. Open that file when you want the machine-readable review list. `python3 -m news_importer list` shows the same warnings in the terminal.

Generated databases, reports, and exports are gitignored. The sample files in `samples/` are part of the project.

`export` still writes the pending queue and does not change `crawl_status`. `crawl` reads the database directly, so you do not need to export before archiving.

## Retrieve and archive

Crawl4AI 0.9.4 and `pypdf` install into the same Python you use for `python3`. One-time setup:

```bash
python3 -m pip install "crawl4ai==0.9.4" pypdf
python3 -m playwright install chromium
crawl4ai-doctor
python3 -c "from crawl4ai.__version__ import __version__; print(__version__)"
```

`crawl4ai-doctor` checks that the browser is ready. PDF text uses `pypdf`, which the install command above includes. If a PDF archive is flagged `pdf_text_unavailable`, install `pypdf` for this same Python and retry.

Import URLs first, then crawl five unique pending URLs:

```bash
python3 -m news_importer import your-urls.csv
python3 -m news_importer crawl --limit 5
```

Preview the queue without fetching or changing the database or archive:

```bash
python3 -m news_importer crawl --limit 5 --dry-run
```

Inspect outcomes:

```bash
python3 -m news_importer list --status fetched
python3 -m news_importer list --status failed
python3 -m news_importer list --status blocked
python3 -m news_importer list --status not_found
```

Each source gets a folder you can browse by study area, site, and page name:

```text
data/archive/<study-area>/<hostname>/<page>--<source-id>/attempt-001/
```

For example, a California bill and a page with no study area land in:

```text
data/archive/california/legiscan.com/ab2015-2025--src_.../attempt-001/
data/archive/unassigned/www.nature.com/s44284-026-00443-x--src_.../attempt-001/
```

`unassigned` means the discovery had no study area. `mixed` means the same URL was linked to more than one study area before its first crawl. The batch id stays on the discovery and records which import the row came from. It is not the folder name. The source id at the end of the folder matches `source_id` in the database. Later discoveries of the same URL stay in that folder. `python3 -m news_importer list` prints the `archive:` path after a crawl.

Open `metadata.json` in the latest attempt folder. `content.md` is the extracted text, `raw.html` is the HTML, and `original.pdf` is present only when the queued URL itself is a PDF. A later crawl moves an older hash-only folder, `data/archive/src_.../`, into this layout and leaves the attempt files inside it.

Every real crawl also refreshes `data/exports/retrievals.csv`. That sheet has one row per discovery and, for the latest attempt, the paths to `raw.html`, `content.md`, `metadata.json`, `original.pdf`, `page.pdf`, and `body.bin` when those files exist. Rebuild it without fetching again:

```bash
python3 -m news_importer export --retrieved --output data/exports/retrievals.csv
```

Retry failed, blocked, and not-found sources without recrawling successes:

```bash
python3 -m news_importer crawl --retry --limit 5
```

Save a webpage PDF snapshot as well as the article text. The snapshot is `page.pdf`. It is not the publisher's original PDF. If the snapshot fails, the HTML and extracted text are still kept.

```bash
python3 -m news_importer crawl --limit 5 --save-page-pdf
```

Other useful selectors:

```bash
python3 -m news_importer crawl --limit 5 --study-area SF
python3 -m news_importer crawl --limit 5 --batch batch_id_here
python3 -m news_importer crawl --limit 5 --timeout 45 --output-dir data/archive
python3 -m news_importer crawl --refresh --limit 5
```

`--refresh` fetches a new attempt for selected pending URLs even when an archive already exists. Older attempt folders are left in place.

`--http-only` skips Crawl4AI and archives the HTTP response text. It cannot make webpage PDF snapshots.

```bash
python3 -m news_importer crawl --limit 5 --http-only
```

### What a crawl does

The crawl selects unique normalized URLs, up to `--limit` (default 5). Every discovery of that URL is linked to one stable source id. A new pending discovery of a URL that already has a saved article reuses that archive unless you pass `--refresh`.

For a URL that needs a fetch, the crawler requests only that URL. It does not follow links or download PDFs linked from the page. Those PDF links are listed in `metadata.json` as `pdf_link_candidates`.

HTML is rendered with Crawl4AI when it is available. The run config turns off deep crawling, stealth, navigator overrides, and overlay removal, and it bypasses Crawl4AI's cache. Original PDFs are detected from the response type and the `%PDF` file header, not only from a `.pdf` suffix. Their bytes are saved as `original.pdf`. Text is extracted with `pypdf` when it is installed. If no text comes out, the original file stays and the attempt is flagged `needs_ocr`. OCR is not implemented yet.

At most two URLs are fetched at once (`--concurrency`, default 2). Requests to the same host wait `--host-delay` seconds (default 1). Timeouts and temporary HTTP failures (429 and 500–504) are retried up to `--retries` extra times (default 2). A `Retry-After` value is honored up to 60 seconds. A longer `Retry-After` is recorded and the crawler stops instead of sending another request. `robots.txt` disallow rules are recorded as `blocked` and are not bypassed. A missing file (HTTP 404) allows the fetch. If `robots.txt` cannot be read — a timeout, a 403, or any status other than 200 or 404 — the URL is recorded as `blocked` and is not requested. Each blocked URL is named in its own robots message.

### Queue status

| Status | Meaning |
| --- | --- |
| `pending` | Imported, or returned here after an interrupted run. Eligible for a normal crawl. |
| `processing` | Claimed by a crawl that has not finished this URL. |
| `fetched` | An attempt was saved. The finer result is `last_outcome`: `retrieved`, `partial`, `paywall`, or `empty`. |
| `blocked` | Robots, HTTP 401/403/429, or an access-barrier page. |
| `not_found` | HTTP 404 or 410. |
| `failed` | Timeout, network error, or HTTP 5xx after the retries. `last_outcome` is `timeout` or `network_error`. |

A real crawl, including one that then selects nothing, first sets leftover `processing` rows back to `pending`. Dry-run does not do that, and it does not fetch. Artifacts are written before the attempt row is marked complete. A crash can leave an attempt folder without a database row; the next attempt uses a new folder and does not overwrite the old one.

HTTP 200, or a successful Crawl4AI result, is not treated as proof of a full article. Short HTML, paywall language, and access-barrier language set `partial`, `paywall`, or `blocked`, and the flags record the signal. Unknown titles and dates stay null. Dates are taken only from ISO-like publication metadata, and conflicting dates stay null.

### Archive metadata

`metadata.json` includes the source id, attempt id, requested URL, final URL, UTC timestamp, HTTP status, content type, observed title, publication date, outcome, quality flags, errors, and artifact paths. Imported titles and snippets are copied under `discovery_records` and are not used as the observed title. The extracted text is the general page text. It is not filtered with research keywords.

## Project layout

```text
news_importer/          import, list, export, and crawl
  study_areas.json      the 12 study areas and aliases
samples/discoveries.csv fictional CSV collected by hand and by research agents
samples/discoveries.txt fictional one-URL-per-line file
tests/test_importer.py  offline importer tests
tests/test_crawl.py     crawl tests against a local HTTP server
```

## Tests

```bash
python3 -m unittest discover -s tests -v
```

Importer tests use temporary databases and do not fetch URLs. Crawl tests use a local HTTP server and fixtures. They do not call live newspaper sites. The Crawl4AI configuration check runs with this same `python3`.

## Limitations

- Import does not search or download pages. Crawl downloads only the queued URL. It does not search, follow links, or download linked PDFs.
- There is no language-model summary, credibility score, topic label, or textbook comparison.
- OCR is not implemented. A PDF with no extractable text is saved and flagged for review.
- Paywall and bot-block flags use the HTTP status, `robots.txt`, and a short list of visible phrases. A Cloudflare script path, or a login line such as "Already a subscriber?", does not by itself mark a captured article blocked or paywalled. A page that says the reader has no permission to access the content is `blocked`. A PDF with no extractable text is `empty` and flagged `needs_ocr`.
- Webpage PDF snapshots require Crawl4AI and `--save-page-pdf`. `--http-only` cannot create them.
- Run one crawl at a time. A second crawl would also reset `processing` rows to `pending`.
- Reimporting a file adds a new batch on purpose. It does not update the old rows.
- Exporting the queue does not mark rows as fetched.
- A study area is a search label, not an inferred jurisdiction.
- `New York` is not an alias for New York City. `Los Angeles, CA` is not an alias for Los Angeles.
- Unbracketed IPv6 addresses are rejected. Use brackets, as in `https://[2001:db8::1]/path`.
- `result_rank` cannot have a leading zero. `searched_at` timestamps need seconds and either `Z` or a numeric offset such as `-08:00`.
- The tool is meant for curated research lists, not a web-scale crawl.
- If the process is killed after the database commit and before the report file is written, the batch is in SQLite and the report is missing. Import again only if you are willing to add another batch; the first batch is already there.
