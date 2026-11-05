"""Smoke test for pytest.

pytest is the image's test runner. The meaningful check runs the real
runner end to end via pytest.main on a synthetic one-test file (exit
code 0), and asserts the core API surface (raises, fixture, mark) is
importable. The cache provider is disabled so nothing is written except
a temp-dir test file that is cleaned up. Deterministic, no network.
"""

import tempfile
from pathlib import Path

import pytest


def main() -> None:
    # Core API surface importable and callable.
    assert callable(pytest.raises), "pytest.raises missing"
    assert callable(pytest.fixture), "pytest.fixture missing"
    assert callable(pytest.mark), "pytest.mark missing"

    # Run the real runner on a synthetic passing test.
    with tempfile.TemporaryDirectory() as tmp:
        test_file = Path(tmp) / "test_smoke_probe.py"
        test_file.write_text(
            "def test_pass():\n"
            "    assert 1 + 1 == 2\n",
            encoding="utf-8",
        )
        exit_code = pytest.main(["-q", "-p", "no:cacheprovider", str(test_file)])
        assert exit_code == 0, f"pytest.main exited {exit_code}"

    # raises actually works at runtime.
    with pytest.raises(ValueError):
        raise ValueError("probe")
    print("pytest: OK (runner + API surface)")


if __name__ == "__main__":
    main()
