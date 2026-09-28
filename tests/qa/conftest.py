"""These QA scripts are not pytest tests.

`test_04..test_08` are manual scripts driven by tests/qa/QA_PLAN.md: none of
them defines a `test_*` function, and their `check()` helper only counts
PASS/FAIL and prints. Because their filenames match `test_*.py`, pytest imports
them while collecting `pytest tests/` (what `make test` runs) and therefore
executes their module-level code — allocating ffmpeg fixtures and, in test_08,
running the whole 7-stage end-to-end pipeline — without reporting a single test
result.

Ignoring them here keeps `pytest tests/` to real tests. To run the QA scripts
on purpose:

    python tests/qa/test_08_end_to_end.py
"""

collect_ignore_glob = [
    "test_04_*.py",
    "test_05_*.py",
    "test_06_*.py",
    "test_07_*.py",
    "test_08_*.py",
]
