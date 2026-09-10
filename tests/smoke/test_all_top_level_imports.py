"""Smoke test: every top-level dependency group package is importable.

Parses pyproject.toml at runtime (so the test never drifts when a package is
added or removed), extracts the distribution name from each pinned spec, maps
it to its import name, and imports it. This catches a package that resolved
into the lock but whose import then fails at runtime - the "resolution
breakage" contract - including the packages no dedicated smoke test touches
(e.g. nb-clean, jupyter-ruff, tqdm, catppuccin-jupyterlab, optuna, duckdb,
catboost, colorcet).
"""

import importlib
import pathlib
import tomllib

# Distribution name -> import name for packages whose import differs from the
# default (dashes replaced with underscores). Omit entries that already match
# that default.
NAME_TO_IMPORT = {
    "scikit-learn": "sklearn",
}


def top_level_dist_names() -> list[str]:
    # The test runs as `python - < file` inside the container, so __file__ is
    # "<stdin>" and cannot be used to locate the repo. pyproject.toml is copied
    # to the container's WORKDIR (/app), so read it from the current directory.
    data = tomllib.loads(pathlib.Path("pyproject.toml").read_text())
    names: list[str] = []
    for group in data["dependency-groups"].values():
        for spec in group:
            # Strip extras and version: "pandas[performance]==3.0.5" -> "pandas".
            base = spec.split("[")[0].split("==")[0].split(">=")[0].split("<=")[0].split("~=")[0].strip()
            if base and base not in names:
                names.append(base)
    return names


def main() -> None:
    names = top_level_dist_names()
    failed: list[str] = []
    for dist in names:
        import_name = NAME_TO_IMPORT.get(dist, dist.replace("-", "_"))
        try:
            importlib.import_module(import_name)
            print(f"ok  {dist} (as {import_name})")
        except Exception as exc:  # noqa: BLE001 - report, then fail loudly at the end
            failed.append(f"{dist} -> {import_name}: {exc!r}")
    if failed:
        raise SystemExit("the following top-level packages failed to import:\n" + "\n".join(failed))
    print(f"all {len(names)} top-level packages importable: OK")


if __name__ == "__main__":
    main()