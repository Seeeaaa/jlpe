"""Smoke test: every top-level dependency group package is present/importable.

Parses pyproject.toml at runtime (so the test never drifts when a package is
added or removed), extracts the distribution name from each pinned spec, and
verifies each one. For genuine Python libraries it does a real import (the
"resolution breakage" contract: a package resolved into the lock but whose
import then fails). For JupyterLab extensions/themes it checks distribution
presence via importlib.metadata instead: their Python packages are install
shims that do side-effecting work on import (e.g. locating a bundled
package.json under the extension dir), so a bare import is not a valid test and
would falsely fail even though the package installed correctly.
"""

import importlib
import importlib.metadata
import pathlib
import tomllib

# Distribution names whose Python module must NOT be imported directly because
# it is a JupyterLab extension/theme shim (import triggers runtime work, or the
# module is pure metadata). These are verified by distribution presence below.
EXTENSION_DIST_NAMES = {
    "catppuccin-jupyterlab",
    "jupyterlab-execute-time",
    "jupyter-resource-usage",
    "jupyter-ruff",
}

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
        if dist in EXTENSION_DIST_NAMES:
            # Extension shim: verify the distribution is installed, not importable.
            try:
                version = importlib.metadata.version(dist)
                print(f"ok  {dist} (distribution {version})")
            except importlib.metadata.PackageNotFoundError:
                failed.append(f"{dist}: distribution not installed")
            except Exception as exc:  # noqa: BLE001
                failed.append(f"{dist}: {exc!r}")
            continue
        import_name = NAME_TO_IMPORT.get(dist, dist.replace("-", "_"))
        try:
            importlib.import_module(import_name)
            print(f"ok  {dist} (as {import_name})")
        except Exception as exc:  # noqa: BLE001 - report, then fail loudly at the end
            failed.append(f"{dist} -> {import_name}: {exc!r}")
    if failed:
        raise SystemExit("the following top-level packages failed to verify:\n" + "\n".join(failed))
    print(f"all {len(names)} top-level packages verified: OK")


if __name__ == "__main__":
    main()