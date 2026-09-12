"""Build the markdown bump table for a ``uv lock --upgrade`` run.

Compares the committed ``uv.lock`` (HEAD, read via ``git show``) against the
upgraded ``uv.lock`` in the working directory and prints, for every package
whose resolved version changed, the previous and new versions plus the
top-level dependency group entries that transitively pull it in. Packages
added or removed outright are listed under their own headings.

Runs from the repository root: it reads ``uv.lock`` and ``pyproject.toml``
from the current directory and expects ``git`` to be available. Invoked by
the ``.github/actions/summarize-deps`` composite action; its stdout is the
markdown body handed to ``create-pull-request`` via ``body-path``.
"""

import re
import subprocess
import tomllib


def parse_lock(text: str) -> dict[str, dict]:
    data = tomllib.loads(text)
    return {
        p["name"]: {
            "version": p["version"],
            "deps": [d["name"] for d in p.get("dependencies", [])],
        }
        for p in data.get("package", [])
    }


def top_level_names(text: str) -> list[str]:
    data = tomllib.loads(text)
    names = set()
    for group in data.get("dependency-groups", {}).values():
        for spec in group:
            m = re.match(r"^([A-Za-z0-9_.-]+)", spec)
            if m:
                names.add(m.group(1))
    return sorted(names)


def reachable(start: str, target: str, lock: dict, seen: set) -> bool:
    if start == target:
        return True
    if start in seen or start not in lock:
        return False
    seen.add(start)
    return any(reachable(d, target, lock, seen) for d in lock[start]["deps"])


def main() -> None:
    pre = parse_lock(subprocess.run(
        ["git", "show", "HEAD:uv.lock"], capture_output=True, text=True, check=True
    ).stdout)
    post = parse_lock(open("uv.lock", encoding="utf-8").read())
    top = top_level_names(open("pyproject.toml", encoding="utf-8").read())

    rows = []
    for name in sorted(set(pre) & set(post)):
        old, new = pre[name]["version"], post[name]["version"]
        if old == new:
            continue
        hits = sorted(t for t in top if reachable(t, name, post, set()))
        shown = hits[:3]
        suffix = ", ..." if len(hits) > 3 else ""
        dep = ", ".join(shown) + suffix if shown else "-"
        rows.append((name, old, new, dep))

    added = sorted(set(post) - set(pre))
    removed = sorted(set(pre) - set(post))

    if rows:
        print("| package | previous | new | top-level dependents |")
        print("|---|---|---|---|")
        for name, old, new, dep in rows:
            print(f"| `{name}` | {old} | {new} | {dep} |")

    if added:
        print("")
        print("**Added packages**")
        for name in added:
            hits = sorted(t for t in top if reachable(t, name, post, set()))
            shown = hits[:3]
            suffix = ", ..." if len(hits) > 3 else ""
            dep = ", ".join(shown) + suffix if shown else "-"
            print(f"- `{name}` {post[name]['version']} (top-level dependents: {dep})")

    if removed:
        print("")
        print("**Removed packages**")
        for name in removed:
            print(f"- `{name}` {pre[name]['version']}")


if __name__ == "__main__":
    main()