#!/usr/bin/env python3
"""Feasibility probe for a python minor crossing in the JLPE repo.

Sweeps every package pinned in uv.lock against PyPI and reports whether each
pinned version still installs on the TARGET CPython minor, linux x86_64, from
prebuilt artifacts only (the image has no compiler - sdist-only is a blocker).
Checks, per locked package:
  1. metadata: the pinned version's Requires-Python must admit the target;
  2. artifact: cp wheel for the exact target minor (NOT the `t` free-threaded
     variant), or abi3 wheel with baseline <= target, or pure py3-none-any,
     or py3-none-manylinux (glibc; musllinux does not match slim-trixie).

Marker-conditional dependencies (python_version markers, e.g. ccxt ->
coincurve) are NOT analyzed here - check them by hand per
references/python-crossing.md.

Run right before any base-image pin change, manual or as ground truth for a
python-minor ladder experiment. Network required (PyPI JSON API). Exit 0
when every locked version is viable, 1 when any is blocked or a lookup
failed (problems and warnings are printed either way).

Usage:
    python scripts/py-minor-feasibility.py --target 3.12 [--lock uv.lock]
    python scripts/py-minor-feasibility.py --target 3.14 --lock C:/Fragments/jlpe/uv.lock
"""

import argparse
import concurrent.futures
import json
import re
import sys
import tomllib
import urllib.request


def rp_admits(rp, cur):
    """True/False when requires-python decides for cur; None when unparsable."""
    if not rp:
        return True
    ok = None
    for part in re.split(r"\s*,\s*", rp.strip()):
        m = re.match(r"^(>=|<=|<|>|==|~=|!=)\s*([\d.]+)(\.\*)?$", part)
        if not m:
            return None
        op, ver_s, star = m.group(1), m.group(2), m.group(3)
        tgt = tuple(int(x) for x in ver_s.split("."))
        if star:
            t2 = tgt[:2] if len(tgt) >= 3 else tgt
            c2 = cur[:2]
            r = {"==": c2 == t2, "!=": c2 != t2, "<": c2 < t2,
                 "<=": c2 <= t2, ">": c2 > t2, ">=": c2 >= t2,
                 "~=": c2 >= t2[:2]}[op]
        else:
            if op in ("==", "!="):
                n = min(len(cur), len(tgt))
                r = (cur[:n] == tgt[:n]) == (op == "==")
            else:
                r = {">=": cur >= tgt, "<=": cur <= tgt, "<": cur < tgt,
                     ">": cur > tgt, "~=": cur >= tgt[:2]}[op]
        ok = r if ok is None else (ok and r)
    return ok


def wheel_kind(filenames, target):
    """Installable artifact kind on linux x86_64 glibc for the target, or None."""
    major, minor = target
    cp = f"cp{major}{minor}"
    for f in filenames:
        # exact-minor cp wheel; trailing dashes exclude the cpXYt free-threaded tag
        if re.search(rf"-{cp}-cp{major}{minor}-", f) and "x86_64" in f and "manylinux" in f:
            return "cp wheel"
        # abi3 baseline sits in the PYTHON tag component (cp312-abi3), not
        # the abi component - classify from the python tag or
        # forward-compatible wheels read as blockers
        m = re.search(r"-cp3(\d+)-abi3-", f)
        if m and int(m.group(1)) <= minor and "x86_64" in f and "manylinux" in f:
            return "abi3 wheel"
        if f.endswith("py3-none-any.whl"):
            return "pure wheel"
        if "-py3-none-manylinux" in f and "x86_64" in f:
            return "py3 binary wheel"
    return None


def check_one(item, target):
    name, ver = item
    if name == "jlpe":
        return (name, ver, "root placeholder, not on PyPI", "skip")
    url = f"https://pypi.org/pypi/{name}/{ver}/json"
    req = urllib.request.Request(url, headers={"User-Agent": "jlpe-feasibility/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.load(r)
    except Exception as e:
        return (name, ver, f"PyPI lookup failed: {type(e).__name__} {e}", "error")
    rp_raw = d["info"].get("requires_python")
    rp_ok = rp_admits(rp_raw, target)
    kind = wheel_kind([f["filename"] for f in d.get("urls", [])], target)
    if rp_ok is False:
        return (name, ver, f"Requires-Python {rp_raw!r} excludes the target", "blocked")
    if kind is None:
        return (name, ver, "no prebuilt artifact for the target on linux x86_64 glibc (sdist-only or wrong ABI tags)", "blocked")
    if rp_ok is None:
        return (name, ver, f"unparsed Requires-Python {rp_raw!r} - check by hand (wheel: {kind})", "warn")
    return (name, ver, kind, "ok")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--target", required=True, help="target python minor, e.g. 3.12 (a full version like 3.12.15 also works)")
    ap.add_argument("--lock", default="uv.lock", help="path to uv.lock (default: uv.lock in the current directory)")
    ap.add_argument("--workers", type=int, default=12, help="parallel PyPI lookups (default 12)")
    args = ap.parse_args()

    parts = args.target.split(".")
    if len(parts) < 2 or not all(p.isdigit() for p in parts[:3]):
        sys.exit(f"--target must look like 3.12 or 3.12.15, got {args.target!r}")
    target = (int(parts[0]), int(parts[1]))

    with open(args.lock, "rb") as f:
        lock = tomllib.load(f)
    pkgs = {p["name"]: p["version"] for p in lock["package"]}
    print(f"lock: {args.lock} ({len(pkgs)} packages), target: python {'.'.join(map(str, target))}.x, linux x86_64 glibc, prebuilt-only")

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        for r in ex.map(lambda it: check_one(it, target), sorted(pkgs.items())):
            results.append(r)

    ok = [r for r in results if r[3] == "ok"]
    blocked = [r for r in results if r[3] == "blocked"]
    errors = [r for r in results if r[3] == "error"]
    warns = [r for r in results if r[3] == "warn"]
    skips = [r for r in results if r[3] == "skip"]

    if blocked:
        print(f"\nBLOCKED ON TARGET ({len(blocked)}):")
        for n, v, why, _ in blocked:
            print(f"  {n}=={v}: {why}")
    if errors:
        print(f"\nLOOKUP ERRORS ({len(errors)}):")
        for n, v, why, _ in errors:
            print(f"  {n}=={v}: {why}")
    if warns:
        print(f"\nWARNINGS - verify by hand ({len(warns)}):")
        for n, v, why, _ in warns:
            print(f"  {n}=={v}: {why}")

    from collections import Counter
    kinds = Counter(r[2] for r in ok)
    print(f"\nsummary: {len(ok)} viable " + str(dict(kinds)))
    if skips:
        print(f"  ({len(skips)} root placeholder skipped)")
    if blocked or errors:
        print("verdict: NOT viable as-is")
        sys.exit(1)
    print("verdict: viable - every locked version installs on the target from prebuilt artifacts")
    print("remember the manual steps: marker-conditional deps (e.g. coincurve) and re-run on the day of the change")


if __name__ == "__main__":
    main()
