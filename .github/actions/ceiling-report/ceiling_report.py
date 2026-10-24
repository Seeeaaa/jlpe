"""Dependency ceiling report for the intermediate-deps job.

Reads the lock file the nightly `uv lock --upgrade` just produced, compares
every locked package against its PyPI latest release, and classifies each
below-latest package by why the resolver left it behind:

- yanked latest: uv refuses yanked releases unless forced
- python-version cap: the latest release's requires-python excludes the
  image's pinned python
- capping requirer: a package that requires this one, at its own locked
  version, declares a spec that excludes the latest release (including
  exact `==` pins)
- second-order conflict: the latest release's own requirements clash with
  the version the lock resolves for one of its dependencies (e.g. the
  latest release requires python-dateutil<3 while the lock resolves
  python-dateutil 3.0.0, because nothing else caps it)
- unknown: no direct cause found at these two levels

Advisory by design: a stuck dependency is a documented ceiling state and
must never turn the nightly run red (same reasoning as the probe
update-availability gate in check-upstream.yml). Data problems degrade a
package to a footnote; only an unreadable lock or pyproject fails the run.

Output: markdown on stdout. The composite action copies it into the job
step summary and appends it to the lock PR body when one exists, so the
bump table (what moved) and the ceiling table (what cannot move, and why)
are reviewed together.
"""

import argparse
import concurrent.futures
import json
import re
import sys
import tomllib
import urllib.error
import urllib.request
from collections import defaultdict

from packaging.markers import default_environment
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

FETCH_TIMEOUT = 20
FETCH_RETRIES = 2
WORKERS = 12
USER_AGENT = "jlpe-ceiling-report"


def fetch_json(path):
    """Fetch a PyPI JSON API document with one retry; 404 is permanent."""
    url = f"https://pypi.org/pypi/{path}"
    last = None
    for _ in range(FETCH_RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise
            last = e
        except Exception as e:
            last = e
    raise last


def image_python(dockerfile_path):
    """Read the pinned python version from the Dockerfile FROM line.

    Requirement markers are evaluated against the image environment, not
    the runner's: the image runs the Dockerfile's pinned CPython minor on
    linux x86_64, and a spec like 'python_version < "3.15"' must engage (or
    not) exactly as it would inside the image.
    """
    try:
        with open(dockerfile_path, "r", encoding="utf-8") as f:
            m = re.search(r"^FROM python:(\d+\.\d+(?:\.\d+)?)-", f.read(), re.MULTILINE)
        if m:
            return m.group(1)
    except OSError:
        pass
    print("::warning::could not read the python pin from the Dockerfile; assuming 3.14")
    return "3.14"


def marker_env(python_version):
    env = dict(default_environment())
    parts = python_version.split(".")
    env["python_version"] = ".".join(parts[:2])
    env["python_full_version"] = python_version
    env["sys_platform"] = "linux"
    env["platform_system"] = "Linux"
    env["platform_machine"] = "x86_64"
    env["implementation_name"] = "cpython"
    # Extra-only specs never engage in a runtime resolve; packaging raises
    # on a marker referencing an absent 'extra', so provide the empty one.
    env["extra"] = ""
    return env


def load_lock(path, exclude):
    """Return (name -> locked version, name -> set of requirer (name, version))."""
    with open(path, "rb") as f:
        lock = tomllib.load(f)
    versions = {}
    requirers = defaultdict(set)
    for pkg in lock.get("package", []):
        name = canonicalize_name(pkg["name"])
        if name == exclude:
            # The project's own placeholder block: it pins the direct deps
            # by design and its spec must not surface as a "capping requirer".
            continue
        versions[name] = pkg["version"]
        for key in ("dependencies", "dev-dependencies"):
            for dep in pkg.get(key) or []:
                if isinstance(dep, dict) and dep.get("name"):
                    dep_name = canonicalize_name(dep["name"])
                    if dep_name != exclude:
                        requirers[dep_name].add((name, pkg["version"]))
        for dep_list in (pkg.get("optional-dependencies") or {}).values():
            if isinstance(dep_list, list):
                for dep in dep_list:
                    if isinstance(dep, dict) and dep.get("name"):
                        dep_name = canonicalize_name(dep["name"])
                        if dep_name != exclude:
                            requirers[dep_name].add((name, pkg["version"]))
    return versions, requirers


def load_direct(path):
    """Return (set of canonical direct dep names, canonical project name)."""
    with open(path, "rb") as f:
        proj = tomllib.load(f)
    direct = set()
    for deps in proj.get("dependency-groups", {}).values():
        for dep in deps:
            base = re.split(r"[\[<>=!~; ]", dep.strip())[0]
            if base:
                direct.add(canonicalize_name(base))
    project = canonicalize_name(proj.get("project", {}).get("name", ""))
    return direct, project


def latest_meta(name):
    """PyPI metadata for the newest release: version, yanked, requirements."""
    data = fetch_json(f"{name}/json")
    info = data.get("info") or {}
    latest = info.get("version") or ""
    files = (data.get("releases") or {}).get(latest) or []
    return {
        "latest": latest,
        "requires_python": info.get("requires_python") or "",
        "requires_dist": info.get("requires_dist") or [],
        "yanked": any(f.get("yanked") for f in files),
    }


class RequirerMeta:
    """Cached requires_dist lookup at a requirer's locked version."""

    def __init__(self):
        self._cache = {}

    def requires_dist(self, name, version):
        key = (name, version)
        if key not in self._cache:
            try:
                info = fetch_json(f"{name}/{version}/json").get("info") or {}
                self._cache[key] = info.get("requires_dist") or []
            except Exception:
                self._cache[key] = None
        return self._cache[key]


def allows(specifier, version):
    """True when the specifier admits the version; unevaluable -> True.

    An unevaluable comparison must never claim a cap that may not exist.
    """
    try:
        return specifier.contains(str(version), prereleases=True)
    except Exception:
        return True


def is_newer(candidate, reference):
    """True when candidate parses above reference; None when unparsable."""
    try:
        return Version(candidate) > Version(reference)
    except InvalidVersion:
        return None


def classify(name, meta, requirer_pairs, lock_versions, direct, env, requirer_meta):
    """Root-cause one below-latest package; returns the cause string."""
    latest = meta["latest"]
    notes = []
    if name in direct:
        notes.append("direct pin (bump via the Dependabot/probe path)")
    if meta["yanked"]:
        notes.append(f"latest {latest} is yanked; the resolver refuses it")
        return "; ".join(notes)
    if meta["requires_python"]:
        try:
            if not SpecifierSet(meta["requires_python"]).contains(env["python_full_version"]):
                notes.append(
                    f"latest requires-python '{meta['requires_python']}' "
                    f"excludes the image python {env['python_full_version']}")
                return "; ".join(notes)
        except Exception:
            pass
    # First level: a requirer's own spec (at its locked version) excludes
    # the latest release. Names are matched canonically because upstreams
    # spell dependencies with both dashes and underscores (mlflow-skinny
    # declares 'importlib_metadata<10'; ccxt pins 'charset_normalizer==3.4.7').
    caps = []
    for requirer, requirer_version in sorted(requirer_pairs):
        rd = requirer_meta.requires_dist(requirer, requirer_version)
        if rd is None:
            continue
        for line in rd:
            try:
                req = Requirement(line)
            except Exception:
                continue
            if canonicalize_name(req.name) != name:
                continue
            if req.marker is not None and not req.marker.evaluate(env):
                continue
            if not allows(req.specifier, latest):
                caps.append(f"capped by {requirer}=={requirer_version}: `{line}`")
    notes.extend(caps)
    # Second level: the latest release's own requirements clash with what
    # the fresh lock resolves for one of its dependencies.
    for line in meta["requires_dist"]:
        try:
            req = Requirement(line)
        except Exception:
            continue
        if req.marker is not None and not req.marker.evaluate(env):
            continue
        dep = canonicalize_name(req.name)
        if dep not in lock_versions:
            continue
        dep_locked = lock_versions[dep]
        if not allows(req.specifier, dep_locked):
            notes.append(f"latest requires `{line}` but the lock resolves {dep}=={dep_locked}")
    if not notes:
        if name in direct:
            notes.append("no capping requirer found")
        else:
            notes.append("no direct cap found (fresh release or deeper tree conflict)")
    return "; ".join(notes)


def main():
    ap = argparse.ArgumentParser(
        description="List locked packages below their PyPI latest, with causes.")
    ap.add_argument("--lock", default="uv.lock")
    ap.add_argument("--pyproject", default="pyproject.toml")
    ap.add_argument("--dockerfile", default="Dockerfile")
    args = ap.parse_args()

    direct, project = load_direct(args.pyproject)
    lock_versions, requirers = load_lock(args.lock, project)
    env = marker_env(image_python(args.dockerfile))
    requirer_meta = RequirerMeta()

    metas = {}
    failures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(latest_meta, name): name for name in sorted(lock_versions)}
        for fut, name in futs.items():
            try:
                metas[name] = fut.result()
            except Exception as e:
                failures.append((name, repr(e)[:60]))

    rows = []
    for name in sorted(metas):
        meta = metas[name]
        locked = lock_versions[name]
        latest = meta["latest"]
        if not latest or locked == latest:
            continue
        newer = is_newer(latest, locked)
        kind = "direct" if name in direct else "transitive"
        if newer is None:
            cause = "version strings differ but do not parse as PEP 440; manual check"
        elif newer:
            cause = classify(name, meta, requirers.get(name, set()),
                             lock_versions, direct, env, requirer_meta)
        else:
            # Locked already at or above the PyPI latest (pre-release edge).
            continue
        rows.append((name, locked, latest, kind, cause))

    total = len(lock_versions)
    print("## Dependency ceiling report")
    print()
    if failures:
        print(f"*PyPI lookups failed for {len(failures)} of {total} packages; this report is incomplete:* {', '.join(n for n, _ in failures[:8])}")
        print()
    if rows:
        print(f"{len(rows)} of {total} locked packages sit below their PyPI latest; the resolver left them behind for the reasons below.")
        print()
        print("| package | locked | latest | kind | cause |")
        print("| --- | --- | --- | --- | --- |")
        for name, locked, latest, kind, cause in sorted(
                rows, key=lambda r: (r[3] != "direct", r[0])):
            cause = cause.replace("|", "\\|")
            print(f"| `{name}` | `{locked}` | `{latest}` | {kind} | {cause} |")
        print()
        print('"Latest" is the PyPI JSON API\'s newest non-prerelease release. Causes come from first-level requirer specs and the latest release\'s own requirements; a "deeper tree conflict" needs the manual resolve walk.')
    else:
        print(f"All {total - len(failures)} successfully-looked-up packages are at their PyPI latest.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        print(f"::error::ceiling report failed: {repr(e)[:200]}", file=sys.stderr)
        sys.exit(1)
