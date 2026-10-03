#!/usr/bin/env python3
"""Check that the report index and archived daily files are in sync."""

from collections import Counter
from datetime import date
from pathlib import Path, PurePosixPath
import re
import sys


DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _date_from_path(relative_path):
    path = PurePosixPath(relative_path)
    if len(path.parts) != 4 or path.parts[0] != "reports":
        return None
    year, month, filename = path.parts[1:]
    label = Path(filename).stem
    if not DATE_PATTERN.fullmatch(label):
        return None
    try:
        parsed = date.fromisoformat(label)
    except ValueError:
        return None
    if year != f"{parsed.year:04d}" or month != f"{parsed.month:02d}" or filename != f"{label}.md":
        return None
    return label


def validate_archive_index(repository_root):
    root = Path(repository_root).resolve()
    errors = []
    indexes = [root / name for name in ("index.md", "INDEX.md") if (root / name).is_file()]
    if len(indexes) != 1:
        return 0, [f"Expected exactly one root index.md or INDEX.md file, found {len(indexes)}."]

    report_root = root / "reports"
    if not report_root.is_dir():
        return 0, ["Missing reports/ directory."]

    report_paths = set()
    for report in report_root.rglob("*.md"):
        if not report.is_file():
            continue
        relative_path = report.relative_to(root).as_posix()
        if _date_from_path(relative_path) is None:
            errors.append(f"Report path does not follow reports/YYYY/MM/YYYY-MM-DD.md: {relative_path}")
        report_paths.add(relative_path)

    index = indexes[0]
    indexed_paths = []
    for label, target in LINK_PATTERN.findall(index.read_text(encoding="utf-8")):
        if not target.startswith("reports/"):
            continue
        target_path = PurePosixPath(target)
        if target_path.is_absolute() or ".." in target_path.parts or target_path.as_posix() != target:
            errors.append(f"Invalid report link path: {target}")
            continue
        if target_path.suffix != ".md":
            errors.append(f"Report link must target a Markdown file: {target}")
            continue

        resolved = (root / Path(*target_path.parts)).resolve()
        try:
            resolved.relative_to(root)
        except ValueError:
            errors.append(f"Report link escapes the repository: {target}")
            continue
        if not resolved.is_file():
            errors.append(f"Report link does not exist: {target}")
            continue

        expected_label = _date_from_path(target)
        if expected_label is None:
            errors.append(f"Report link path does not follow reports/YYYY/MM/YYYY-MM-DD.md: {target}")
        elif label != expected_label:
            errors.append(f"Report link label {label!r} does not match its file date {expected_label!r}: {target}")
        indexed_paths.append(target)

    counts = Counter(indexed_paths)
    for path, count in sorted(counts.items()):
        if count > 1:
            errors.append(f"Report is indexed {count} times: {path}")

    indexed_set = set(indexed_paths)
    for path in sorted(report_paths - indexed_set):
        errors.append(f"Report is not indexed: {path}")
    for path in sorted(indexed_set - report_paths):
        errors.append(f"Indexed file is not an archived report: {path}")

    return len(report_paths), errors


def main():
    repository_root = Path(__file__).resolve().parents[1]
    report_count, errors = validate_archive_index(repository_root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Archive index is complete: {report_count} reports indexed exactly once.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
