# AI News Scraper: URL importer

This is the first piece of a research project about navigation-app traffic, access restrictions, routing-app rules, and community complaints. It stores URLs you already collected. It does not search the web, download pages, read PDFs, or call a language model.

Later stages can use Crawl4AI to fetch the articles and PDFs in this queue. This importer does not include Crawl4AI and does not need it installed.

The sample URLs use `example.com` and are fictional.

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
- publication date, credibility, relevance, novelty, or category

Those judgments belong to later stages. This importer does not assign them.

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

The batch report is `data/reports/<batch-id>.json`. It repeats the counts and lists rejected rows, warnings, and repeated normalized URLs. Open that file when you want the machine-readable review list. `python3 -m news_importer list` shows the same warnings in the terminal.

Generated databases, reports, and exports are gitignored. The sample files in `samples/` are part of the project.

## How the export connects to Crawl4AI later

`export` writes a queue, not a new import file. The important columns for the next stage are:

- `discovery_id`, the stable id to write results back to
- `original_url`, the URL that was collected
- `normalized_url`, for comparison only
- `study_area`, `discovery_method`, `query`, `searched_at`, `result_rank`
- `extra_metadata_json`, `warnings_json`, and `original_record_json`

A later script can read that CSV, give Crawl4AI the original URL after trimming surrounding whitespace, save the retrieved HTML or PDF, and then update SQLite:

```sql
UPDATE discoveries
SET crawl_status = 'fetched'
WHERE id = 'disc_...';
```

Fetch the trimmed original URL. The normalized URL is safe for spotting repeats, but it lowercases the host and drops the fragment. PDF links are already eligible for import; this component does not download them. Paywall detection is also left for later.

This repository does not call Crawl4AI. The importer works offline.

## Project layout

```text
news_importer/          command-line importer
  study_areas.json      the 12 study areas and aliases
samples/discoveries.csv fictional CSV collected by hand and by research agents
samples/discoveries.txt fictional one-URL-per-line file
tests/test_importer.py  offline tests
```

## Tests

```bash
python3 -m unittest discover -s tests -v
```

The tests use temporary databases. They do not fetch URLs.

## Limitations

- This component does not search, crawl, parse PDFs, classify articles, or provide a graphical interface.
- Reimporting a file adds a new batch on purpose. It does not update the old rows.
- Exporting the queue does not mark rows as fetched.
- A study area is a search label, not an inferred jurisdiction.
- `New York` is not an alias for New York City. `Los Angeles, CA` is not an alias for Los Angeles.
- Unbracketed IPv6 addresses are rejected. Use brackets, as in `https://[2001:db8::1]/path`.
- `result_rank` cannot have a leading zero. `searched_at` timestamps need seconds and either `Z` or a numeric offset such as `-08:00`.
- The tool is meant for curated research lists, not a web-scale crawl.
- If the process is killed after the database commit and before the report file is written, the batch is in SQLite and the report is missing. Import again only if you are willing to add another batch; the first batch is already there.
