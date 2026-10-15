#!/usr/bin/env python3
"""Build the current, source-complete submission without local history or binaries.

The explicit manifest prevents local editor settings, build products, and archived
report revisions from entering a public or submitted source package. Fixed ZIP
metadata makes repeated packaging of identical inputs byte-for-byte reproducible.
"""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "MOBA_Matchmaking_Submission.zip"
PREFIX = "MOBA_Matchmaking"
FILES = (
    ".clang-format",
    ".github/workflows/ci.yml",
    ".gitignore",
    "LICENSE",
    "Makefile",
    "README.md",
    "benchmarks.cpp",
    "docs/REPOSITORY_STRUCTURE.md",
    "experiment_results.json",
    "experiments.cpp",
    "main.cpp",
    "matchmaker.hpp",
    "output/figures/Algorithm_Overview.png",
    "output/figures/Queue_Residence.png",
    "output/figures/Results_Tradeoff.png",
    "output/pdf/MOBA_Matchmaking_Report.pdf",
    "reference/matchmaker_before.hpp",
    "report/build_report.py",
    "report/charts.py",
    "report/figure_design_notes.md",
    "report/overview.py",
    "report/paper_statistics.py",
    "requirements-report.txt",
    "research/README.md",
    "research/validation.txt",
    "research/waiting_aware_matchmaker.hpp",
    "research/waiting_extension.cpp",
    "results/benchmark_after.json",
    "results/benchmark_before.json",
    "results/paper_statistics.json",
    "results/report_revision.txt",
    "results/verification.txt",
    "results/waiting_extension.json",
    "scripts/package_submission.py",
    "tests.cpp",
    "tests_cli.py",
)


def main() -> None:
    files = list(FILES)
    if (ROOT / "repository.json").is_file():
        files.append("repository.json")
    missing = [name for name in files if not (ROOT / name).is_file()]
    if missing:
        raise SystemExit("Missing submission files:\n" + "\n".join(missing))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".zip.tmp")
    try:
        with ZipFile(temporary, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
            for name in sorted(files):
                info = ZipInfo(f"{PREFIX}/{name}", date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                archive.writestr(info, (ROOT / name).read_bytes(), compresslevel=9)
        temporary.replace(OUTPUT)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Created {OUTPUT.relative_to(ROOT)} ({len(files)} files)")


if __name__ == "__main__":
    main()
