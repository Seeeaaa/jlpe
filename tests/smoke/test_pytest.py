"""Smoke test for pytest.

pytest is the image's test runner. The meaningful check runs the real
runner end to end via pytest.main on a synthetic parametrized test
module (exit code 0), and asserts the core API surface (raises,
fixture, mark) is importable and usable. The cache provider is disabled
so nothing is written except a temp-dir test file that is cleaned up.
Deterministic, no network.
"""

import tempfile
from pathlib import Path

import pytest


def main() -> None:
    # Core API surface importable and usable. pytest.mark itself is a
    # MarkGenerator namespace and is intentionally NOT callable; the
    # meaningful check is that attribute access yields a real decorator.
    assert callable(pytest.raises), "pytest.raises missing"
    assert callable(pytest.fixture), "pytest.fixture missing"
    decorator = pytest.mark.parametrize("value", [1, 2])
    assert callable(decorator), "pytest.mark.parametrize did not yield a decorator"

    # Run the real runner on a synthetic module that exercises the mark
    # machinery: two parametrized items, both expected to pass.
    with tempfile.TemporaryDirectory() as tmp:
        test_file = Path(tmp) / "test_smoke_probe.py"
        test_file.write_text(
            "import pytest\n"
            "\n"
            "\n"
            "@pytest.mark.parametrize('value', [1, 2])\n"
            "def test_positive(value):\n"
            "    assert value > 0\n",
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
