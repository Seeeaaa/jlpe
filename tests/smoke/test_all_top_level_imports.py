"""Smoke test: every top-level dependency group package is present/importable.

Parses pyproject.toml at runtime (so the test never drifts when a package is
added or removed), extracts the distribution name from each pinned spec, and
verifies each one. For genuine Python libraries it does a real import (the
"resolution breakage" contract: a package resolved into the lock but whose
import then fails). For JupyterLab extensions/themes it checks distribution
presence via importlib.metadata instead: their Python packages are install
shims that do side-effecting work on import (e.g. locating a bundled
package.json under the extension dir), so a bare import is not a valid test and
would falsely fail even though the package installed correctly. For CLI-only
distributions it verifies distribution presence plus a runnable binary: their
wheels contain no importable Python module at all, so an import is the wrong
contract.
"""

import importlib
import importlib.metadata
import pathlib
import shutil
import subprocess
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

# Distribution names that ship only a command-line executable with no
# importable Python module. nb-clean 5.0.0 ported the tool from Python to
# Rust: PyPI wheels install a native binary via the .data/scripts scheme and
# the nb_clean module no longer exists, so an import is the wrong contract.
# Verified by distribution presence plus a runnable binary (--help exits 0 on
# both the argparse 4.x CLI and the clap 5.x CLI; --version does not exist on
# 4.x and the bare "version" command was dropped in 5.x).
CLI_ONLY_DIST_NAMES = {
    "nb-clean",
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
        if dist in CLI_ONLY_DIST_NAMES:
            # CLI-only: verify the distribution is installed and its binary runs.
            try:
                version = importlib.metadata.version(dist)
            except importlib.metadata.PackageNotFoundError:
                failed.append(f"{dist}: distribution not installed")
                continue
            except Exception as exc:  # noqa: BLE001
                failed.append(f"{dist}: {exc!r}")
                continue
            if shutil.which(dist) is None:
                failed.append(f"{dist}: distribution {version} installed but '{dist}' binary not on PATH")
                continue
            probe = subprocess.run([dist, "--help"], capture_output=True, timeout=30)
            if probe.returncode != 0:
                stderr = probe.stderr.decode(errors="replace").strip()
                failed.append(f"{dist}: CLI '{dist} --help' exited {probe.returncode}: {stderr}")
                continue
            print(f"ok  {dist} (distribution {version}, CLI probe exit 0)")
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