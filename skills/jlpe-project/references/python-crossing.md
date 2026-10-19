# Python minor crossing (base-image pin change)

Use when changing the pinned python minor in the JLPE Dockerfile - either
via the automated path (the python-minor ladder in check-upstream.yml) or a
deliberate manual pin move (upgrade, or a temporary downgrade to exercise
the ladder). Always-on rules live in SKILL.md; this file is the procedure
and decision depth, loaded when a crossing is actually being done.

## Feasibility probe - run BEFORE any pin change

Sweep EVERY locked package (uv.lock, the full 200+ set, not just top-level
pins) against PyPI. Both conditions must hold for each pinned version or the
crossing is not viable without manual dependency work:

1. Metadata floor: the pinned version's `Requires-Python` must admit the
   target (a `>=3.13` floor blocks a 3.12 downgrade even when wheels exist).
2. Prebuilt artifact for the target on linux x86_64 - the image has NO
   compiler, so an sdist-only package is a hard blocker, not an inconvenience
   (the runner has a toolchain, which is exactly why this must be probed
   rather than discovered via a failing build):
   - `cp3XY-cp3XY` wheel matching the target minor exactly (NOT the `t`
     free-threaded variant: `-cp314-cp314t-` does not install on a regular
     interpreter; anchor the match with trailing dashes)
   - `cp3N-abi3` wheel with N <= target minor (stable ABI is
     forward-compatible). The baseline N sits in the PYTHON tag component
     (`...-cp312-abi3-...`), not the ABI component - classify from the
     python tag; an abi-component parse misses forward-compatible wheels
     and reports false blockers
   - `py3-none-any.whl` (pure)
   - `py3-none-manylinux` x86_64 (version-independent binary; xgboost,
     lightgbm, prophet, duckdb ship these). manylinux = glibc, matching
     slim-trixie; a musllinux-only package does NOT install in this image.
3. Marker-conditional dependencies: a dep declared with a
   `python_version < "3.14"` style marker (ccxt -> coincurve is the live
   example) drops OUT of the resolve when the window widens past the marker
   and re-enters when it narrows. That is legal resolver behavior, not a
   failure - but verify the requirer's usage is function-local with a
   documented fallback (grep the wheel's sources for the import; ccxt's
   coincurve calls sit inside methods that fall back to `cryptography`)
   before declaring the drop safe. In the lock file the marker-normalized
   dep then appears/disappears with the window (coincurve is present in a
   3.12 lock, absent in a 3.14 lock).
4. Re-run the probe the DAY OF the change: top-level pins drift daily via
   Dependabot (four pins moved in four days in one observed window) and a
   fresh pin can carry a floor the previous sweep never saw.

`scripts/py-minor-feasibility.py` runs the whole sweep; the marker analysis
(step 3) stays manual.

## Manual pin-change procedure

The ladder performs all of this automatically. Do it by hand only for a
deliberate experiment (e.g. a temporary downgrade so the ladder has real
multi-rung data to walk):

1. Branch from fresh origin/main (`git fetch origin main` first - main moves
   several times a day here). Edit in a worktree if the main checkout is
   dirty on another branch.
2. Fresh digest for the target tag via the registry token flow:
   `auth.docker.io/token?service=registry.docker.io&scope=repository:library/python:pull`,
   then GET `registry-1.docker.io/v2/library/python/manifests/<tag>` with an
   Accept header covering both OCI and docker manifest-list media types; the
   `Docker-Content-Digest` response header is the pin. Run it with curl in
   the terminal (urllib can hit a gzip'd JSON reply from the auth endpoint).
3. Edit exactly three files:
   - Dockerfile FROM: `python:<X.Y.Z>-slim-trixie@sha256:<fresh digest>`
   - pyproject.toml: `requires-python = ">=<minor>,<<next minor>"` (keep the
     one-minor-window convention; a further crossing must stay deliberate)
   - README.md: ONLY the feature line and the supported-tags table row.
     Boundary-guard the sed: `([^.0-9]|$)` after the minor (the historical
     versioning example contains a full version like `Python 3.13.14` and a
     bare minor match mangles it) and `/lgbm_gpu/!` negation (the outdated
     tag row keeps the old minor forever).
   - Do NOT touch uv.lock: update-lock regenerates it on the branch (the
     required check commits `chore: regenerate uv.lock` within minutes).
4. Expect that regenerate commit to trigger a second same-minute
   synchronize run; the two runs race in the concurrency group and the
   cancelled duplicate's queued jobs can display as `fail` in the PR checks
   rollup until the live run finishes. Read per-run job conclusions
   (`gh run view <id> --json jobs`), not `gh pr checks` alone.
5. Verify the CI-generated lock: `requires-python = "==<minor>.*"` and the
   marker-conditional deps moved as predicted (coincurve present in a 3.12
   lock, absent in a 3.14 lock).
6. Known cost of a downgrade window: `latest` on Docker Hub moves DOWN to
   the old image until the ladder walks back up; stale tags are pruned by
   the owner manually per repo convention. State it in the PR body.
7. Expect a Dockerfile conflict on the crossing PR whenever a uv base
   bump merges to main first: the uv FROM (line 1) and the python FROM
   (line 2) sit adjacent with no blank-line buffer, so edits to either
   line share context and git refuses the auto-merge. Resolution is
   mechanical: keep main's uv FROM line and the branch's python FROM
   line - the two pins are independent.
8. Build any conflict resolution from origin/<branch>, not the local ref:
   `git worktree add <path> <branch>` checks out the LOCAL branch, which
   can lag origin by the CI regenerate commit and bot merge-main
   commits. A merge built on the stale ref silently drops the
   CI-generated lock from the PR with no push error. Fetch
   origin <branch>, reset the worktree onto it, merge, resolve, then
   re-run the step-5 lock check on the MERGED tree (requires-python
   window, marker deps) before pushing.

## Reviewing the automated crossing PR

Each migrate-python-<minor> PR is machine-generated and force-updated
nightly; review it with this checklist. All of it is scriptable - never
eyeball the multi-hundred-line lock diff.

1. Head alignment: green checks must belong to the reviewed head. Take
   headRefOid from `gh pr view <n> --json headRefOid,mergeStateStatus` and
   compare with the head_sha of the run behind the green jobs (run id is in
   the check-run URL; `gh api repos/<owner>/<repo>/actions/runs/<id> --jq
   .head_sha`). Superseded same-minute runs leave stale conclusions in the
   rollup (per-run rule in SKILL.md).
2. Diff shape: exactly four files. Dockerfile changes ONLY the python FROM
   (uv FROM untouched), pyproject.toml ONLY the requires-python one-minor
   window, README ONLY the feature line and supported-tags row (lgbm_gpu
   row intact), uv.lock CI-generated on the branch.
3. Digest freshness: re-derive the registry digest for the pinned tag (the
   token flow in the manual procedure above) and compare with the
   Dockerfile pin - the branch can predate an in-place rebuild of the tag.
4. Lock transcription check: parse the [[package]] blocks (name/version
   regex per block) and assert - header requires-python == "<minor>.*";
   zero version deltas; zero added packages; drops are exactly the
   predicted marker-conditional set; cp3OLD wheel URLs re-tagged cp3NEW
   with abi3 and pure counts unchanged; every URL still on
   pypi.org/files.pythonhosted.org.
5. Marker drops are safe: the requirer's PyPI requires_dist carries the
   python_version marker, and the wheel sources import the dropped package
   function-local with a documented fallback (extract the wheel, grep the
   sources).
6. Blind spot: the multiprocessing-sensitive smokes carry the serial-path
   fix on main, and the PR's smoke-test job passed on the reviewed head.
7. Rung freshness: the pinned patch equals the newest published
   `<minor>.x-<suffix>` tag (registry tags list or the official-images
   library file). If a newer patch exists, wait for the nightly
   force-update instead of hand-editing the branch; a clean review is
   valid for one headRefOid - re-run steps 3-5 after any force-push.

## The gate's blind spot - runtime behavior on the new interpreter

The ladder's gate proves resolve + install + top-level imports; it cannot
see behavior that only manifests inside a library call at runtime. Only
the in-container smoke loop exercises that, so treat a smoke-only failure
on a crossing PR as an interpreter-behavior delta first, not a bad
crossing:

- CPython 3.14 changes the Linux default multiprocessing start method from
  fork to forkserver. build.yml pipes each smoke via stdin
  (`docker exec -i python - < script`), so `__main__` lives at `<stdin>`;
  a forkserver worker re-imports the main module from that path, finds no
  file, and the pool dies with FileNotFoundError + ConnectionResetError.
  Any smoke whose library internally builds a multiprocessing Pool
  (tsfresh's extract_features is the known case) passes the gate and fails
  the smoke on 3.14, while passing both on 3.12/3.13.
- Traceback signature: `multiprocessing/forkserver.py` plus a `<stdin>`
  main path. Read the smoke-test job log before changing anything.
- Fix the smoke, not the delivery: the smoke contract asserts API-surface
  integrity, not parallelism - pin the library call to its serial path
  (tsfresh: n_jobs=1 selects the serial MapDistributor).
  set_start_method("spawn") is NOT a fix: spawn re-imports the main
  module the same way and fails identically under stdin. Replacing the
  stdin piping with file delivery in build.yml is a separate contract
  change - propose it only if a library has no serial path.
- Sequencing: a smoke-only failure does not invalidate the ladder. Land
  the smoke fix on main; the next nightly walk re-evaluates and the
  crossing PR for that minor rebuilds green.

## Ladder behavior around merges - expect these, do not debug them

- Merging ANY workflow change that adds a PR-creating job to check-upstream
  fires that job on the merge's own push (the push trigger includes the
  workflow file path): the auto-PR appears within minutes. Verified live:
  the ladder's own merge fired the job and opened the crossing PR a minute
  later. Before a follow-up experiment that moves the pin, close the stale
  auto-PR - branch deletion is harmless for create-pull-request-owned PRs
  (the next run rebuilds the branch from current main), unlike the
  shared-head duplicate case in the dispatch trap.
- A fresh .0 minor with no cp wheels yet for the heavy stack fails the gate
  and queues with a green job and a Summary verdict table: designed waiting
  state, nightly re-verification. Do not investigate it as an outage. The
  wheel-gap prognosis is probeable ahead of time: sweep the heavy stack's
  installable-artifact classes on PyPI for the target minor (the same
  wheel-classification the feasibility probe uses) - a cp-only binary
  package with no cp3XY/abi3/pure/py3-none-manylinux artifact for the
  target is the queued state's visible cause, and the wait ends when THAT
  package ships wheels (observed: 3.15.0 published upstream with duckdb and
  catboost wheel-less on the day the image tag itself had not even
  appeared yet). Split the blockers when forecasting the wait: a package
  whose PIN lacks target wheels but whose newest upstream release ships
  them self-clears through the normal Dependabot pin bump (pyarrow at the
  3.15 rung), while a package where even upstream-latest has no target
  artifact is a rung-floor - the wait ends only when that project
  publishes wheels (catboost, duckdb at the 3.15 rung: pinned == latest,
  cp314 the newest artifact).
- A CPython .0 release does not create a ladder candidate on release day:
  the ladder's tag source is the docker-library official-images file and
  its filter is digits-only, so rc/alpha/beta tags (3.15.0rc3-slim-trixie
  etc.) can never match, and the final `X.Y.0-<suffix>` tag typically
  lags the upstream release by days. 'No candidates above the pin' right
  after a minor release is the expected reading, not a filter bug - probe
  PyPI for wheel gaps (the actionable half) and let the tag appear.
- The two-rung case is proven in production: with the pin at 3.12 and both
  3.13.16 and 3.14.8 published upstream, the walk chose 3.13.16 and opened
  migrate-python-3.13 - nearest viable rung, no skip to the newest. The
  crossing PR's uv.lock diff is then pure platform transcription: the SAME
  versions, cp312 wheel URLs replaced by cp313 ones plus the
  requires-python header - verify "version changes: none" when reviewing,
  and expect a real dependency-tree delta only when a version-conditional
  marker drops a package out (coincurve leaves the tree at the 3.14 rung).
- Same-tag digest drift is separate from versioning: docker-library rebuilds
  a published tag in place, so bump-base can open "refresh pinned digest for
  python:<same version>" - the version never changed, only the image behind
  the tag. Do not reconstruct a version-bump history from a refresh title.
- The gate and the smoke suite cover different layers, so a crossing minor
  can pass one and fail the other - that gap is why both exist. The
  sequencing that ends an experiment cleanly: land the smoke fix on main ->
  let the nightly (or a paths-matching merge) rebuild the crossing PR from
  main containing the fix -> the crossing PR comes back fully green ->
  merge. Do not merge a crossing PR whose only red is the known
  blind-spot smoke; do not hold a green crossing PR waiting for a smoke
  fix that is already on main.
