"""Offline tests for the local URL importer."""

from __future__ import annotations

import csv
import io
import json
import sqlite3
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from news_importer.db import EXPORT_COLUMNS, connect, ensure_schema  # noqa: E402
from news_importer.errors import ImporterError  # noqa: E402
from news_importer.importer import import_path  # noqa: E402
from news_importer.models import ImportDefaults  # noqa: E402
from news_importer.study_areas import load_catalog  # noqa: E402
from news_importer.urls import check_url  # noqa: E402

SAMPLE_CSV = ROOT / "samples" / "discoveries.csv"
SAMPLE_TXT = ROOT / "samples" / "discoveries.txt"


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str] | None = None) -> None:
    if fieldnames is None:
        names: list[str] = []
        seen: set[str] = set()
        for row in rows:
            for key in row:
                if key not in seen:
                    names.append(key)
                    seen.add(key)
    else:
        names = fieldnames
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=names, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


class TestUrls(unittest.TestCase):
    def test_normalization_keeps_path_query_and_encoding(self) -> None:
        original = "HTTPS://News.Example.COM/Traffic/Report?b=2&a=1%2F2&utm_source=test#top"
        checked = check_url(original)
        self.assertTrue(checked.ok)
        self.assertEqual(
            checked.normalized,
            "https://news.example.com/Traffic/Report?b=2&a=1%2F2&utm_source=test",
        )
        self.assertEqual(checked.hostname, "news.example.com")

    def test_http_https_www_and_path_case_stay_distinct(self) -> None:
        forms = [
            check_url("https://www.example.com/a"),
            check_url("https://example.com/a"),
            check_url("http://example.com/a"),
            check_url("https://example.com/A"),
            check_url("https://example.com/a?b=1&a=2"),
            check_url("https://example.com/a?a=2&b=1"),
            check_url("https://example.com"),
            check_url("https://example.com/"),
        ]
        normalized = [item.normalized for item in forms]
        self.assertEqual(len(normalized), len(set(normalized)))

    def test_surrounding_whitespace_is_trimmed_only_for_comparison(self) -> None:
        checked = check_url("  HTTPS://Example.COM/a  ")
        self.assertTrue(checked.ok)
        self.assertEqual(checked.normalized, "https://example.com/a")

    def test_userinfo_port_and_ipv6_are_preserved(self) -> None:
        user = check_url("https://User:P%61ss@Example.COM/A")
        self.assertEqual(user.normalized, "https://User:P%61ss@example.com/A")
        port = check_url("https://example.com:443/Foo")
        self.assertEqual(port.normalized, "https://example.com:443/Foo")
        ipv6 = check_url("https://[2001:DB8::1]:8443/Path")
        self.assertEqual(ipv6.normalized, "https://[2001:db8::1]:8443/Path")
        self.assertEqual(ipv6.hostname, "2001:db8::1")

    def test_rejections(self) -> None:
        cases = {
            None: "missing_url",
            "   ": "missing_url",
            "https://example.com/a b": "unescaped_whitespace",
            "ftp://example.com/a": "unsupported_scheme",
            "example.com/a": "unsupported_scheme",
            "https://": "missing_hostname",
            "https://example.com:abc/a": "malformed_port",
            "https://example.com:/a": "malformed_port",
            "https://example.com:99999/a": "malformed_port",
            "https://example.com:0/a": "malformed_port",
            "http://::1/": "malformed_url",
        }
        for original, code in cases.items():
            with self.subTest(original=original):
                checked = check_url(original)
                self.assertFalse(checked.ok)
                self.assertEqual(checked.code, code)


class TestStudyAreas(unittest.TestCase):
    def test_builtin_catalog_covers_the_twelve_areas(self) -> None:
        catalog = load_catalog()
        self.assertEqual(
            [area.id for area in catalog.areas],
            [
                "atlanta",
                "boston",
                "chicago",
                "los_angeles",
                "miami",
                "new_york_city",
                "philadelphia",
                "salt_lake_city",
                "san_francisco",
                "seattle",
                "california",
                "new_jersey",
            ],
        )
        aliases = {
            "NYC": "new_york_city",
            "N.Y.C.": "new_york_city",
            "SF": "san_francisco",
            "S.F.": "san_francisco",
            "LA": "los_angeles",
            "L.A.": "los_angeles",
            "Philly": "philadelphia",
            "SLC": "salt_lake_city",
            "ATL": "atlanta",
            "CA": "california",
            "California (state)": "california",
            "NJ": "new_jersey",
            "N.J.": "new_jersey",
        }
        for label, area_id in aliases.items():
            match = catalog.resolve(label)
            self.assertIsNotNone(match)
            assert match is not None
            self.assertEqual(match.id, area_id)
        self.assertIsNone(catalog.resolve("New York"))
        self.assertIsNone(catalog.resolve("Los Angeles, CA"))
        self.assertEqual(catalog.resolve("California").display_name, "California (state)")

    def test_alias_collision_is_rejected(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "areas.json"
            path.write_text(
                json.dumps(
                    {
                        "study_areas": [
                            {"id": "a", "name": "A", "kind": "city", "aliases": ["shared"]},
                            {"id": "b", "name": "B", "kind": "city", "aliases": ["shared"]},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ImporterError) as raised:
                load_catalog(path)
            self.assertIn("matches both", str(raised.exception))


class TestImport(unittest.TestCase):
    def test_mixed_file_imports_valid_rows_and_reports_the_rest(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "mixed.csv"
            database = root / "news.sqlite"
            reports = root / "reports"
            write_csv(
                source,
                [
                    {
                        "url": "  https://example.com/ok  ",
                        "title": "Kept",
                        "result_rank": "2",
                        "study_area": "Boston",
                    },
                    {"url": "", "title": "Missing"},
                    {"url": "ftp://example.com/nope", "title": "Scheme"},
                    {"url": "https://example.com/a b", "title": "Space"},
                    {"url": "https://example.com:99999/x", "title": "Port"},
                    {"url": "https://example.com/ok", "title": "Second copy", "result_rank": "0"},
                    {"url": "example.com/path", "title": "Relative", "result_rank": "1"},
                    {
                        "url": "https://example.com/ranked",
                        "title": "Bad rank",
                        "result_rank": "first",
                        "searched_at": "March 1",
                    },
                ],
            )
            summary = import_path(source, db_path=database, report_dir=reports)
            self.assertEqual(summary.accepted, 1)
            self.assertEqual(summary.rejected, 7)
            self.assertEqual(summary.repeated_urls, 0)
            report = json.loads(Path(summary.report_path or "").read_text(encoding="utf-8"))
            self.assertEqual(report["summary"]["accepted"], 1)
            reasons = {
                item["record_number"]: [reason["code"] for reason in item["reasons"]]
                for item in report["rejected"]
            }
            self.assertEqual(reasons[2], ["missing_url"])
            self.assertEqual(reasons[3], ["unsupported_scheme"])
            self.assertEqual(reasons[4], ["unescaped_whitespace"])
            self.assertEqual(reasons[5], ["malformed_port"])
            self.assertEqual(reasons[6], ["invalid_result_rank"])
            self.assertEqual(reasons[7], ["unsupported_scheme"])
            self.assertCountEqual(
                reasons[8],
                ["invalid_result_rank", "invalid_searched_at"],
            )
            self.assertEqual(report["rejected"][1]["original_record"]["url"], "ftp://example.com/nope")
            row = self._rows(database)[0]
            self.assertEqual(row["original_url"], "  https://example.com/ok  ")
            self.assertEqual(row["normalized_url"], "https://example.com/ok")
            self.assertEqual(row["crawl_status"], "pending")
            self.assertEqual(self._count(database, "discoveries"), 1)

    def test_duplicates_are_kept_and_reimport_creates_a_new_batch(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "dupes.csv"
            database = root / "news.sqlite"
            reports = root / "reports"
            write_csv(
                source,
                [
                    {"url": "https://example.com/same#one", "study_area": "Miami"},
                    {"url": "https://example.com/same#two", "study_area": "Miami"},
                    {"url": "https://example.com/same#two", "study_area": "Miami"},
                ],
            )
            first = import_path(source, db_path=database, report_dir=reports)
            second = import_path(source, db_path=database, report_dir=reports)
            self.assertEqual(first.accepted, 3)
            self.assertEqual(first.repeated_urls, 2)
            self.assertEqual(first.repeated_normalized_urls, ["https://example.com/same"])
            self.assertEqual(second.accepted, 3)
            self.assertEqual(second.repeated_urls, 3)
            self.assertNotEqual(first.batch_id, second.batch_id)
            rows = self._rows(database)
            self.assertEqual(len(rows), 6)
            self.assertEqual(len({row["id"] for row in rows}), 6)
            self.assertEqual(self._count(database, "import_batches"), 2)
            self.assertEqual(len(list(reports.glob("*.json"))), 2)
            flags = [row["is_repeat"] for row in rows if row["batch_id"] == first.batch_id]
            self.assertEqual(flags, [0, 1, 1])

    def test_quoting_bom_metadata_and_query_strings(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "quoted.csv"
            database = root / "space dir" / "news.sqlite"
            with source.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.writer(handle, lineterminator="\n")
                writer.writerow(
                    [
                        "URL",
                        "title",
                        "notes",
                        "collector",
                        "query",
                        "study_area",
                        "discovery_method",
                        "searched_at",
                        "result_rank",
                        "snippet",
                    ]
                )
                writer.writerow(
                    [
                        "HTTPS://News.Example.COM/Traffic/Report?b=2&a=1%2F2&utm_source=test#top",
                        "Traffic, routing",
                        "line1\nline2",
                        "grok session",
                        "routing apps",
                        "NYC",
                        "Gemini",
                        "2026-03-01T15:04:00Z",
                        "4",
                        "café snippet",
                    ]
                )
                writer.writerow(
                    [
                        "https://example.com/plain",
                        "Plain",
                        "",
                        "",
                        "",
                        "Paris",
                        "Grok Bot",
                        "",
                        "",
                        "",
                    ]
                )
            summary = import_path(source, db_path=database, report_dir=root / "reports")
            self.assertEqual(summary.accepted, 2)
            self.assertEqual(summary.rejected, 0)
            rows = {row["input_record_number"]: row for row in self._rows(database)}
            first = rows[1]
            self.assertEqual(
                first["original_url"],
                "HTTPS://News.Example.COM/Traffic/Report?b=2&a=1%2F2&utm_source=test#top",
            )
            self.assertEqual(
                first["normalized_url"],
                "https://news.example.com/Traffic/Report?b=2&a=1%2F2&utm_source=test",
            )
            self.assertEqual(first["title"], "Traffic, routing")
            self.assertEqual(first["notes"], "line1\nline2")
            self.assertEqual(first["snippet"], "café snippet")
            self.assertEqual(json.loads(first["extra_metadata_json"]), {"collector": "grok session"})
            original = json.loads(first["original_record_json"])
            self.assertEqual(original["URL"], first["original_url"])
            self.assertIn("\n", original["notes"])
            self.assertEqual(first["study_area"], "new_york_city")
            self.assertEqual(first["study_area_raw"], "NYC")
            self.assertEqual(first["discovery_method"], "gemini")
            self.assertEqual(first["discovery_method_raw"], "Gemini")
            self.assertIsNone(first["warnings_json"] and json.loads(first["warnings_json"]) or None)
            second = rows[2]
            self.assertEqual(second["study_area"], "Paris")
            self.assertEqual(second["discovery_method"], "Grok Bot")
            warning_codes = {item["code"] for item in json.loads(second["warnings_json"])}
            self.assertEqual(
                warning_codes,
                {"unrecognized_study_area", "unrecognized_discovery_method"},
            )

    def test_google_provenance_warnings_do_not_drop_the_row(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "google.csv"
            database = root / "news.sqlite"
            write_csv(
                source,
                [
                    {
                        "url": "https://example.com/google",
                        "study_area": "Seattle",
                        "discovery_method": "google_first_page",
                        "query": "",
                        "searched_at": "",
                        "result_rank": "",
                    },
                    {
                        "url": "https://example.com/complete",
                        "study_area": "Seattle",
                        "discovery_method": "google_first_page",
                        "query": "seattle routing",
                        "searched_at": "2026-04-01",
                        "result_rank": "1",
                    },
                ],
            )
            summary = import_path(source, db_path=database, report_dir=root / "reports")
            self.assertEqual(summary.accepted, 2)
            self.assertEqual(summary.warnings, 3)
            self.assertEqual(summary.records_with_warnings, 1)
            warned = self._rows(database)[0]
            fields = [item["field"] for item in json.loads(warned["warnings_json"])]
            self.assertEqual(fields, ["query", "searched_at", "result_rank"])
            self.assertIsNone(warned["query"])
            self.assertIsNone(warned["searched_at"])
            self.assertIsNone(warned["result_rank"])
            self.assertNotEqual(warned["imported_at"], warned["searched_at"])
            self.assertRegex(warned["imported_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_row_values_win_and_invalid_row_values_do_not_use_defaults(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "defaults.csv"
            database = root / "news.sqlite"
            write_csv(
                source,
                [
                    {
                        "url": "https://example.com/row",
                        "study_area": "Boston",
                        "query": "from the row",
                        "discovery_method": "",
                        "searched_at": "2026-01-02",
                    },
                    {
                        "url": "https://example.com/defaulted",
                        "study_area": "",
                        "query": "",
                        "discovery_method": "",
                        "searched_at": "",
                    },
                    {
                        "url": "https://example.com/bad-date",
                        "study_area": "Boston",
                        "searched_at": "2026-01-02T00:00:00",
                    },
                ],
            )
            defaults = ImportDefaults(
                study_area="NYC",
                discovery_method="grok_bot",
                query="from the command",
                searched_at="2026-05-01T00:00:00Z",
            )
            summary = import_path(
                source,
                db_path=database,
                report_dir=root / "reports",
                defaults=defaults,
            )
            self.assertEqual(summary.accepted, 2)
            self.assertEqual(summary.rejected, 1)
            rows = {row["normalized_url"]: row for row in self._rows(database)}
            row = rows["https://example.com/row"]
            self.assertEqual(row["study_area"], "boston")
            self.assertEqual(row["study_area_raw"], "Boston")
            self.assertEqual(row["query"], "from the row")
            self.assertEqual(row["searched_at"], "2026-01-02")
            self.assertEqual(row["discovery_method"], "grok_bot")
            self.assertIsNone(row["discovery_method_raw"])
            defaulted = rows["https://example.com/defaulted"]
            self.assertEqual(defaulted["study_area"], "new_york_city")
            self.assertIsNone(defaulted["study_area_raw"])
            self.assertEqual(defaulted["query"], "from the command")
            self.assertEqual(defaulted["searched_at"], "2026-05-01T00:00:00Z")
            self.assertIsNone(defaulted["result_rank"])
            connection = self._connection(database)
            try:
                stored_defaults = json.loads(
                    connection.execute("SELECT defaults_json FROM import_batches").fetchone()[0]
                )
            finally:
                connection.close()
            self.assertEqual(stored_defaults["study_area"], "NYC")

    def test_txt_uses_line_numbers_and_skips_blank_lines(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "urls.txt"
            source.write_text(
                "https://example.com/one\n\n  https://example.com/two  \n",
                encoding="utf-8",
            )
            database = root / "news.sqlite"
            summary = import_path(
                source,
                db_path=database,
                report_dir=root / "reports",
                defaults=ImportDefaults(study_area="SF", discovery_method="publisher_search"),
            )
            self.assertEqual(summary.accepted, 2)
            self.assertEqual(summary.warnings, 0)
            rows = self._rows(database)
            self.assertEqual([row["input_record_number"] for row in rows], [1, 3])
            self.assertEqual(rows[1]["original_url"], "  https://example.com/two  ")
            self.assertEqual(rows[1]["normalized_url"], "https://example.com/two")
            self.assertEqual(rows[0]["study_area"], "san_francisco")

    def test_distinct_hosts_schemes_and_tracking_params_are_not_merged(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "distinct.csv"
            database = root / "news.sqlite"
            write_csv(
                source,
                [
                    {"url": "https://www.example.com/a"},
                    {"url": "https://example.com/a"},
                    {"url": "http://example.com/a"},
                    {"url": "https://example.com/a?utm_source=digest&topic=trucks"},
                    {"url": "https://example.com/A"},
                ],
            )
            summary = import_path(source, db_path=database, report_dir=root / "reports")
            self.assertEqual(summary.accepted, 5)
            self.assertEqual(summary.repeated_urls, 0)

    def test_dry_run_writes_nothing_and_still_sees_existing_repeats(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            database = root / "nested" / "news.sqlite"
            reports = root / "reports"
            first = root / "first.csv"
            second = root / "second.csv"
            write_csv(first, [{"url": "https://example.com/existing", "study_area": "Miami"}])
            write_csv(
                second,
                [
                    {"url": "https://example.com/existing#later", "study_area": "Miami"},
                    {"url": "https://example.com/new", "study_area": "Miami"},
                    {"url": "ftp://example.com/bad"},
                ],
            )
            untouched = import_path(second, db_path=database, report_dir=reports, dry_run=True)
            self.assertTrue(untouched.dry_run)
            self.assertIsNone(untouched.batch_id)
            self.assertEqual(untouched.accepted, 2)
            self.assertEqual(untouched.rejected, 1)
            self.assertFalse(database.exists())
            self.assertFalse(reports.exists())
            self.assertFalse((root / "nested").exists())

            import_path(first, db_path=database, report_dir=reports)
            before = database.read_bytes()
            names_before = sorted(path.name for path in database.parent.iterdir())
            reports_before = sorted(path.name for path in reports.iterdir())
            preview = import_path(second, db_path=database, report_dir=reports, dry_run=True)
            self.assertEqual(preview.repeated_urls, 1)
            self.assertEqual(preview.accepted, 2)
            self.assertEqual(database.read_bytes(), before)
            self.assertEqual(sorted(path.name for path in database.parent.iterdir()), names_before)
            self.assertEqual(sorted(path.name for path in reports.iterdir()), reports_before)
            self.assertEqual(self._count(database, "discoveries"), 1)

    def test_malformed_csv_does_not_write_a_batch(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            database = root / "news.sqlite"
            broken = root / "broken.csv"
            broken.write_text('url,title\n"https://example.com/a,Title\n', encoding="utf-8")
            with self.assertRaises(ImporterError) as raised:
                import_path(broken, db_path=database, report_dir=root / "reports")
            self.assertIn("malformed CSV", str(raised.exception))
            self.assertFalse(database.exists())

            existing = root / "ok.csv"
            write_csv(existing, [{"url": "https://example.com/ok"}])
            import_path(existing, db_path=database, report_dir=root / "reports")
            extra = root / "wide.csv"
            extra.write_text("url,title\nhttps://example.com/new,Title,EXTRA\n", encoding="utf-8")
            with self.assertRaises(ImporterError) as raised_wide:
                import_path(extra, db_path=database, report_dir=root / "reports")
            self.assertIn("more columns", str(raised_wide.exception))
            self.assertEqual(self._count(database, "import_batches"), 1)
            self.assertEqual(self._count(database, "discoveries"), 1)

            missing = root / "no-url.csv"
            missing.write_text("title\nHello\n", encoding="utf-8")
            with self.assertRaises(ImporterError) as raised_missing:
                import_path(missing, db_path=database, report_dir=root / "reports")
            self.assertIn("url", str(raised_missing.exception))

    def test_database_failure_rolls_back_the_batch(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            database = root / "news.sqlite"
            connection = connect(database)
            ensure_schema(connection)
            connection.execute(
                """
                CREATE TRIGGER fail_discoveries
                BEFORE INSERT ON discoveries
                BEGIN
                    SELECT RAISE(ABORT, 'forced failure');
                END
                """
            )
            connection.close()
            source = root / "one.csv"
            write_csv(source, [{"url": "https://example.com/a"}, {"url": "https://example.com/b"}])
            with self.assertRaises(ImporterError) as raised:
                import_path(source, db_path=database, report_dir=root / "reports")
            self.assertIn("forced failure", str(raised.exception))
            self.assertEqual(self._count(database, "import_batches"), 0)
            self.assertEqual(self._count(database, "discoveries"), 0)
            self.assertFalse((root / "reports").exists())

    def test_export_preserves_ids_and_metadata_without_changing_status(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            database = root / "news.sqlite"
            summary = import_path(
                SAMPLE_CSV,
                db_path=database,
                report_dir=root / "reports",
            )
            self.assertEqual(summary.accepted, 13)
            self.assertEqual(summary.rejected, 0)
            self.assertEqual(summary.repeated_urls, 1)
            self.assertEqual(summary.warnings, 2)
            from news_importer.db import export_pending

            handle = io.StringIO()
            count = export_pending(database, handle)
            self.assertEqual(count, 13)
            handle.seek(0)
            exported = list(csv.DictReader(handle))
            self.assertEqual(list(exported[0].keys()), EXPORT_COLUMNS)
            stored = self._rows(database)
            exported_ids = [row["discovery_id"] for row in exported]
            stored_ids = [row["id"] for row in stored]
            self.assertEqual(exported_ids, stored_ids)
            self.assertTrue(all(row["crawl_status"] == "pending" for row in stored))
            boston = next(row for row in exported if "gps-truck-ban" in row["original_url"])
            self.assertIn("utm_source=digest&topic=trucks", boston["original_url"])
            self.assertEqual(boston["original_url"], boston["normalized_url"])
            miami = next(row for row in exported if row["notes"].startswith("Fictional café"))
            self.assertIn("café", miami["notes"])
            self.assertEqual(json.loads(miami["extra_metadata_json"])["collector"], "publisher site")
            la = next(row for row in exported if row["original_url"].endswith("/la/canyon-traffic"))
            warning_fields = [item["field"] for item in json.loads(la["warnings_json"])]
            self.assertEqual(warning_fields, ["searched_at", "result_rank"])
            seattle = [row for row in exported if row["normalized_url"].endswith("/seattle/ferry-queue")]
            self.assertEqual(len(seattle), 2)
            self.assertNotEqual(seattle[0]["discovery_id"], seattle[1]["discovery_id"])
            self.assertEqual({row["is_repeat"] for row in seattle}, {"0", "1"})
            sf = next(row for row in exported if row["original_url"].endswith(".pdf"))
            self.assertEqual(sf["study_area"], "san_francisco")
            self.assertEqual(sf["study_area_raw"], "SF")
            self.assertEqual(self._count(database, "discoveries"), 13)

    def test_sample_text_file_and_missing_study_area_warning(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            database = root / "news.sqlite"
            summary = import_path(
                SAMPLE_TXT,
                db_path=database,
                report_dir=root / "reports",
                defaults=ImportDefaults(
                    study_area="SF",
                    discovery_method="grok_bot",
                    query="San Francisco routing app restrictions",
                    searched_at="2026-04-01",
                ),
            )
            self.assertEqual((summary.accepted, summary.rejected, summary.warnings), (3, 0, 0))
            rows = {row["input_record_number"]: row for row in self._rows(database)}
            self.assertEqual(set(rows), {1, 2, 4})
            pdf = rows[4]
            self.assertEqual(pdf["original_url"], "https://example.com/sf/great-highway.pdf#page=2")
            self.assertEqual(pdf["normalized_url"], "https://example.com/sf/great-highway.pdf")
            self.assertEqual(pdf["query"], "San Francisco routing app restrictions")
            self.assertIsNone(pdf["result_rank"])

    def test_import_does_not_open_a_socket(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "one.csv"
            write_csv(source, [{"url": "https://example.com/offline", "study_area": "Chicago"}])

            def fail_socket(*_args, **_kwargs):
                raise AssertionError("import opened a network socket")

            import socket

            original = socket.socket
            socket.socket = fail_socket  # type: ignore[assignment]
            try:
                summary = import_path(
                    source,
                    db_path=root / "news.sqlite",
                    report_dir=root / "reports",
                )
            finally:
                socket.socket = original
            self.assertEqual(summary.accepted, 1)

    def test_schema_has_no_classification_columns(self) -> None:
        with TemporaryDirectory() as tmp:
            database = Path(tmp) / "news.sqlite"
            source = Path(tmp) / "one.csv"
            write_csv(source, [{"url": "https://example.com/a"}])
            import_path(source, db_path=database, report_dir=Path(tmp) / "reports")
            connection = self._connection(database)
            columns = {row[1] for row in connection.execute("PRAGMA table_info(discoveries)")}
            connection.close()
            self.assertIn("crawl_status", columns)
            self.assertIn("original_record_json", columns)
            for forbidden in (
                "credibility",
                "relevance",
                "novelty",
                "publication_date",
                "summary",
                "category",
                "paywall",
            ):
                self.assertNotIn(forbidden, columns)

    def _connection(self, database: Path) -> sqlite3.Connection:
        connection = sqlite3.connect(database)
        connection.row_factory = sqlite3.Row
        return connection

    def _rows(self, database: Path) -> list[sqlite3.Row]:
        connection = self._connection(database)
        try:
            return list(
                connection.execute(
                    "SELECT * FROM discoveries ORDER BY rowid"
                ).fetchall()
            )
        finally:
            connection.close()

    def _count(self, database: Path, table: str) -> int:
        if table not in {"discoveries", "import_batches"}:
            raise AssertionError(table)
        connection = self._connection(database)
        try:
            return int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        finally:
            connection.close()


class TestCli(unittest.TestCase):
    def test_import_list_export_and_dry_run(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            database = root / "news.sqlite"
            reports = root / "reports"
            exported = root / "pending.csv"
            first = self._run(
                [
                    "import",
                    str(SAMPLE_CSV),
                    "--db",
                    str(database),
                    "--report-dir",
                    str(reports),
                ]
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertIn("accepted: 13", first.stdout)
            self.assertIn("rejected: 0", first.stdout)
            self.assertIn("repeated_urls: 1", first.stdout)
            self.assertIn("warnings: 2", first.stdout)
            self.assertIn("https://example.com/seattle/ferry-queue", first.stdout)

            listed = self._run(
                ["list", "--db", str(database), "--study-area", "NYC", "--limit", "10"]
            )
            self.assertEqual(listed.returncode, 0, listed.stderr)
            self.assertIn("showing 1 of 1 discoveries", listed.stdout)
            self.assertIn("New York City (new_york_city)", listed.stdout)
            self.assertIn("study_area_raw: NYC", listed.stdout)
            self.assertIn("congestion-routing?ref=newsletter", listed.stdout)

            dry = self._run(
                [
                    "import",
                    str(SAMPLE_CSV),
                    "--db",
                    str(database),
                    "--report-dir",
                    str(reports),
                    "--dry-run",
                ]
            )
            self.assertEqual(dry.returncode, 0, dry.stderr)
            self.assertIn("dry run: no database changes and no report written", dry.stdout)
            self.assertIn("repeated_urls: 13", dry.stdout)
            self.assertEqual(len(list(reports.glob("*.json"))), 1)

            output = self._run(
                ["export", "--db", str(database), "--output", str(exported)]
            )
            self.assertEqual(output.returncode, 0, output.stderr)
            self.assertIn("exported 13 pending discoveries", output.stderr)
            with exported.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 13)
            self.assertTrue(all(row["discovery_id"].startswith("disc_") for row in rows))
            self.assertTrue(all(row["crawl_status"] == "pending" for row in rows))

            missing = root / "missing-column.csv"
            missing.write_text("title\nHello\n", encoding="utf-8")
            failed = self._run(["import", str(missing), "--db", str(database)])
            self.assertEqual(failed.returncode, 1)
            self.assertIn("error:", failed.stderr)
            self.assertIn("url", failed.stderr)

            bad_time = self._run(
                [
                    "import",
                    str(SAMPLE_TXT),
                    "--db",
                    str(root / "unused.sqlite"),
                    "--searched-at",
                    "yesterday",
                ]
            )
            self.assertEqual(bad_time.returncode, 1)
            self.assertIn("searched_at", bad_time.stderr)
            self.assertFalse((root / "unused.sqlite").exists())

    def test_list_shows_the_later_import_when_timestamps_match(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            database = root / "news.sqlite"
            older = root / "older.txt"
            newer = root / "newer.txt"
            older.write_text("\n\n\n\nhttps://example.com/older\n", encoding="utf-8")
            newer.write_text("https://example.com/newer\n", encoding="utf-8")
            stamp = "2026-01-01T00:00:00Z"

            def same_time() -> str:
                return stamp

            import news_importer.importer as importer_module

            original = importer_module.utc_now
            importer_module.utc_now = same_time
            try:
                import_path(older, db_path=database, report_dir=root / "reports")
                import_path(newer, db_path=database, report_dir=root / "reports")
            finally:
                importer_module.utc_now = original
            from news_importer.db import list_discoveries

            rows, total = list_discoveries(database, batch_id=None, study_area=None, limit=1)
            self.assertEqual(total, 2)
            self.assertEqual(rows[0]["original_url"], "https://example.com/newer")

    def test_text_import_command(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            database = root / "news.sqlite"
            completed = self._run(
                [
                    "import",
                    str(SAMPLE_TXT),
                    "--db",
                    str(database),
                    "--report-dir",
                    str(root / "reports"),
                    "--study-area",
                    "SF",
                    "--discovery-method",
                    "grok_bot",
                    "--query",
                    "San Francisco routing app restrictions",
                    "--searched-at",
                    "2026-04-01",
                ]
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("accepted: 3", completed.stdout)
            self.assertIn("warnings: 0", completed.stdout)

    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "news_importer", *args],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )


if __name__ == "__main__":
    unittest.main()
