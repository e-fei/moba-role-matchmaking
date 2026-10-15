# Source and artifact guide

The repository keeps the original C++ include paths and build commands so that
the report, experiments, and tests use the same implementation. Generated
executables, temporary previews, editor settings, historical report revisions,
and submission ZIP files are excluded from version control.

| Path | Purpose |
| --- | --- |
| `matchmaker.hpp` | Baseline queue and exact five-role team optimizer. |
| `main.cpp` | Interactive command-line interface. |
| `tests.cpp`, `tests_cli.py` | Exhaustive-oracle comparisons, edge cases, and malformed-command checks. |
| `experiments.cpp`, `experiment_results.json` | Deterministic baseline replay and its saved results. |
| `benchmarks.cpp`, `reference/` | Local timing driver and the earlier matcher used for comparison. |
| `research/` | Isolated waiting-aware extension, its exhaustive checks, and explanatory notes. |
| `results/` | Saved benchmark, statistical, extension, and verification records. |
| `report/` | PDF typesetting, vector illustrations, plots, statistics, and figure design notes. |
| `output/pdf/` | Current English report. |
| `output/figures/` | Standalone previews of the report's vector figures. |
| `requirements-report.txt` | Python packages for report generation and PDF inspection. |
| `.github/workflows/ci.yml` | GCC/Clang verification and deterministic-result checks on Linux. |
| `scripts/package_submission.py` | Explicit, reproducible manifest for the current submission ZIP. |
| `LICENSE` | MIT terms for reuse and redistribution. |
| `repository.json` | Public repository URL used by the report. |

## Build and validate

The C++ program needs a C++17 compiler and Make. The command-parser check and
statistics script use Python 3 without additional packages.

```sh
make CXX=g++ test
make CXX=g++ experiment
make CXX=g++ waiting-experiment
python3 report/paper_statistics.py
```

Use `CXX=clang++` to repeat these checks with Clang. The waiting-aware executable
checks its independent exhaustive oracle before writing its results. The saved
experiment JSON files are deterministic for the documented fixed seeds.
Microbenchmark timings depend on the machine, compiler, and current system load;
`make benchmark-compare` intentionally produces fresh local timing measurements.

## Rebuild the report and submission

```sh
python3 -m pip install -r requirements-report.txt
python3 report/build_report.py
python3 scripts/package_submission.py
```

The PDF generator reads the committed baseline, benchmark, and waiting-extension
JSON files. Its required fonts are documented in the main README. Report
generation is separate from portable C++ verification because the typography
depends on local fonts. The report is committed so that readers can inspect it
without installing the typesetting dependencies.

The packaging script requires every source, current figure, data file, and report
in its explicit manifest to exist. It includes `repository.json` and uses fixed ZIP timestamps and permissions. Repeated runs on identical inputs
produce the same archive bytes. Review the manifest when adding a new source file;
files are never discovered recursively for submission.
