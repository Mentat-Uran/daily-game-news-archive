from pathlib import Path
import tempfile
import unittest

from scripts.validate_archive_index import validate_archive_index


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class ArchiveIndexTests(unittest.TestCase):
    def test_current_archive_is_complete(self):
        report_count, errors = validate_archive_index(REPOSITORY_ROOT)
        self.assertGreater(report_count, 0)
        self.assertEqual(errors, [])

    def test_reports_missing_from_index_are_reported(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            report = root / "reports" / "2026" / "10" / "2026-10-03.md"
            report.parent.mkdir(parents=True)
            report.write_text("# Report\n", encoding="utf-8")
            (root / "index.md").write_text("# Index\n", encoding="utf-8")

            _, errors = validate_archive_index(root)
            self.assertIn("Report is not indexed: reports/2026/10/2026-10-03.md", errors)

    def test_missing_targets_and_duplicate_links_are_reported(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            report = root / "reports" / "2026" / "10" / "2026-10-03.md"
            report.parent.mkdir(parents=True)
            report.write_text("# Report\n", encoding="utf-8")
            index = root / "index.md"
            index.write_text(
                "# Index\n\n"
                "- [2026-10-03](reports/2026/10/2026-10-03.md)\n"
                "- [2026-10-03](reports/2026/10/2026-10-03.md)\n"
                "- [2026-10-04](reports/2026/10/2026-10-04.md)\n",
                encoding="utf-8",
            )

            _, errors = validate_archive_index(root)
            self.assertTrue(any("indexed 2 times" in error for error in errors))
            self.assertIn("Report link does not exist: reports/2026/10/2026-10-04.md", errors)

    def test_report_links_reject_wrong_labels_and_parent_paths(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            report = root / "reports" / "2026" / "10" / "2026-10-03.md"
            report.parent.mkdir(parents=True)
            report.write_text("# Report\n", encoding="utf-8")
            (root / "index.md").write_text(
                "# Index\n\n"
                "- [2026-10-04](reports/2026/10/2026-10-03.md)\n"
                "- [escape](reports/../outside.md)\n",
                encoding="utf-8",
            )

            _, errors = validate_archive_index(root)
            self.assertTrue(any("does not match its file date" in error for error in errors))
            self.assertIn("Invalid report link path: reports/../outside.md", errors)

    def test_report_path_must_match_its_calendar_directory(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            report = root / "reports" / "2026" / "09" / "2026-10-03.md"
            report.parent.mkdir(parents=True)
            report.write_text("# Report\n", encoding="utf-8")
            (root / "index.md").write_text(
                "# Index\n\n- [2026-10-03](reports/2026/09/2026-10-03.md)\n",
                encoding="utf-8",
            )

            _, errors = validate_archive_index(root)
            self.assertTrue(
                any("Report path does not follow" in error for error in errors)
            )


if __name__ == "__main__":
    unittest.main()
