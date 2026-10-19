# JLPE security audit ledger (chronological, verified findings)

Full findings list from the Sep-Oct 2026 audits. Each entry: status, evidence
anchor, resolution. The always-on summary lives in SKILL.md; this file is the
historical depth loaded on demand.

## Audit 2026-10-11 (comprehensive image/CI audit at ea03e52; report delivered, decisions pending)

- multidict Dependabot alert #4 (medium, items-view ref leak, fixed 6.9.1):
  root cause is ccxt==4.5.85 requires-dist exact-pinning multidict==6.7.1
  (verified via PyPI metadata), the same pattern as the ccxt urllib3 cap.
  aiohttp 3.14.4 allows <7.0, yarl >=4.0, and 6.9.1 ships cp313 manylinux
  wheels, so nothing else blocks the bump; the nightly uv lock --upgrade
  cannot lift it (fresh PR #291, Oct 10, leaves 6.7.1). NOT a pipeline
  defect; self-heals when ccxt bumps (urllib3 precedent, PR #242 merge).
- build.yml has NO schedule trigger: builds fire only on push/PR/dispatch,
  so the PUBLISHED image can go days without an apt security refresh in a
  quiet week (daily checks exist; rebuilds are event-driven). Proposed to
  the owner: a daily scheduled rebuild+publish without a stamp (version tag
  stays content-identity, CREATED label advances per build; diff = schedule
  trigger + push-job if clause, stamp-date stays push-only). Owner decision
  pending.
- Timestamp machinery audit: the stamp is already inside build.yml (the
  stamp-date job, not a separate workflow) and already the LAST content
  layer (COPY VERSION at Dockerfile:84, after the apt and uv sync layers;
  the ARG/LABEL/EXPOSE/ENTRYPOINT tail is config-only). No change proposed;
  alternative shapes (no-commit build-time stamp, or version back in
  pyproject) documented as worse: non-reproducible version tags, or daily
  uv.lock churn plus a full 2.4 GB layer rebuild per stamp.
- PyTorch question re-asked (2026-10-11): ruling of record (2026-10-04)
  restated with numbers - CUDA wheel 554.6 MB plus 2.5-3 GB nvidia stack,
  cpu wheel ~185 MB via the explicit pytorch-cpu index, overlay image is
  the path if a use case appears. Owner decision pending.
- Caching re-verified live: 30 actions caches, ~2.18 GB total (two ~900 MB
  buildkit blobs, trivy DBs 86+85 MB); latest main build timings: changes 5s,
  stamp 7s, build 399s, smoke 135s, push 163s. No change.

## External-audit verification + fixes (2026-10-04, PR #262 + sha_pinning_required)

Verified external audit findings against live data before acting:

- SARIF severity filter WAS broken in reconcile-code-scanning-alerts.yml: trivy-action v0.36.0 entrypoint.sh unsets TRIVY_SEVERITY when format=sarif without limit-severities-for-sarif: 'true' (log: "Building SARIF report with all severities"). Confirmed 3 ways: entrypoint source at pinned SHA ed142fd0, live 2026-10-03 23:44 run log (INPUT_LIMIT_SEVERITIES_FOR_SARIF empty), and the analysis itself: 249 results = HIGH 55, MEDIUM 87, LOW 102, UNKNOWN 5, CRITICAL 0. Scope is reconcile ONLY - build.yml's log-only scan runs format: table, unaffected.
- Fix in PR #262: limit-severities-for-sarif: 'true' + inline comment; expected first-upload effect: ~194 MEDIUM/LOW/UNKNOWN alerts close as "fixed" (accepted). TWO follow-up traps: (1) after the fix LOW/MEDIUM findings are tracked on NO CI surface - full picture needs a manual trivy run; (2) the empty-scan guard now also trips if the image ever becomes genuinely HIGH/CRITICAL-clean - 0 filtered results is indistinguishable from a DB outage, guard fails loudly (acceptable) but needs a rethink when the image is clean.
- Dependabot github-actions branch STALLED on bare-major comments: pins with `# v4` comment got no bump for 16-18 days while live releases existed (codeql-action v4.38.0 pin from 2026-09-09 vs v4.38.2 from 2026-09-24; setup-buildx v4.4.0 from 2026-09-15 vs v4.4.1 from 2026-09-16). Known dependabot-core flakiness with SHA pins whose version comment is a bare major (#7912/#8011). PR #262 bumps both manually and rewrites comments to exact versions (# v4.38.2, # v4.4.1) - the signal Dependabot reads. Audit lesson: a sweep must resolve EVERY pinned SHA against latest tag commit, not only the action named in the report (the original report named codeql, the sweep found buildx too; 13 of 15 other pins were current).
- sha_pinning_required flipped ON via API (PUT repos/Seeeaaa/jlpe/actions/permissions; read current, write back enabled+allowed_actions unchanged + flag). All external uses verified full-40-hex first (grep + regex assertion); PR #262's CI ran green under the new rule, proving compliance. Corollary: any future tag-ref `uses:` will fail at workflow parse - that is the point.
- PR #259 is the uv 0.12.22->0.12.23 bump-base PR (create-pull-request, PAT author shows as owner), NOT a codeql bump - do not cite it as one.

## Audit 2026-10-04 (architecture/cache sweep; owner ruling: zero changes)

- setup-uv wheel-cache for intermediate-deps/probe jobs: CONSIDERED AND REJECTED
  (measured, not projected). uv sync --locked --all-groups takes 7-22s on a fresh
  GH runner (223 packages, ~1 GB, Fastly bandwidth); Astral's own prune-cache
  docs say pre-built wheels re-download faster than a multi-GB cache restores.
  A 2.4 GB entry per lock-hash (lock moves 1-3x/day) would churn the 10 GB LRU
  and risk evicting the buildkit-blobs (1.99 GB) that save 70-100s per build.
  The accidental current state is near-optimal: intermediate-deps saves a
  ~17 MB metadata cache under the shared key; probes restore it (primary hit
  helps uv add resolve) and save nothing, which is correct for wheels.
- Dockerfile tail order (ARG VERSION/REVISION/CREATED + LABEL + EXPOSE +
  ENTRYPOINT after COPY VERSION): ARG/LABEL/EXPOSE/ENTRYPOINT are config-only
  instructions, create NO layers (buildx logs show no #N build steps after
  COPY VERSION). Reordering EXPOSE/ENTRYPOINT above the dynamic block is pure
  style with zero measurable effect; do not spend a PR on it.
- Known cosmetic cache litter (accepted, owner declined the fix):
  update-lock.yml's setup-uv saves a ~1.1-1.4 KB junk entry per branch state
  (uv lock without --upgrade downloads no metadata -> empty cache -> new key).
- SARIF cutover verified post-#258: exactly one analysis on refs/heads/main
  (category .github/workflows/build.yml:build). 249 open alerts = 225 legacy
  (Aug 30 / Sep 4 / Sep 9-12, pre-cutover unfixed-in-trixie ledger) + 24
  fresh from the 2026-10-03 upload, including the first venv-path findings
  (ccxt pro/xt.py, bullish.py: jwt-token x4, CVE-2026-82560 x4,
  CVE-2026-102010 x4). Native dedupe works as designed; no action.
- uv 0.12.23 out vs pinned 0.12.22: nightly bump-base opens the PR; one-step
  drift never needs manual action.
- README still lists a lgbm_gpu tag that no longer exists on Hub (docs cleanup
  offered 2026-10-04, owner declined).
- Full-audit answers of record: PyTorch stays OUT of the main image (CUDA
  wheel 554 MB + 2.5-3 GB nvidia stack vs the verified xgboost GPU path;
  CPU torch needs the pytorch-cpu index and breaks the single-index scheme);
  overlay image is the path if a torch use-case ever appears. Timestamp
  mechanics confirmed correct: %Y%m%d%H%M minute precision, stamped inside
  stamp_and_commit (build.yml, not a separate workflow), baked via COPY
  VERSION after the apt layer - the only layer it rewrites is the 0B config
  tail.

## Audit 2026-10-01 (dual pass: main session + analyst subagent; origin/main c3538a88)

### Resolved by PRs from this audit (all verified green before merge)

- F-01 timeout-minutes: absent from all 14 jobs in 5 workflows (360-min
  default). FIXED via #243 (ci/add-timeout-minutes, commit 7e8f25a, 14
  insertions): 10-15 min light jobs, 30-45 registry/lock/trivy, 60 build and
  probe. Authoring gotcha hit: the exact-match anchor '  push:' also matches
  the on: trigger block, silently skipping one insertion; caught by the
  structural verify pass, fixed with a disambiguated two-line anchor
  ('  push:' + its needs: line).
- F-02 bump-base unvalidated external interpolation (medium, the highest
  open item): latest from curl|grep|sed|tail and jq tag_name validated only
  for emptiness, crane digest output unvalidated, all interpolated into
  sed -i Dockerfile FROM rewrites. FIXED via #247 (ci/validate-bump-base-
  inputs, commit 0e79af9, 4 edits / 36 insertions): tag validated against
  ^v?[0-9.]+$, digest against ^sha256:[0-9a-f]{64}$, sed interpolations
  moved to env: indirection (NEW_REF/NEW_DIGEST/CUR_VERSION_RE/CUR_SUFFIX),
  loose metacharacter guard on the probe's pypi lookup. Verified by offline
  simulation (legit shapes pass, $(evil) and 1.2;rm -rf / fail) and by a
  manual dispatch on the PR branch (run 36925826195, both bump-base legs
  success, Update Dockerfile/Create PR correctly skipped - both bases up to
  date). NO happy-path behavior change; malformed input now fails loudly.
- F-03 update-lock.yml unused contents: write (PAT does the writes). FIXED
  via #244 (commit 6e07d8a): workflow permissions dropped to contents: read.
- F-04 update-pr-branches.yml over-broad job perms (PAT does the merges;
  GITHUB_TOKEN only does read-only test runs). FIXED via #245 (commit
  199fd64): job-level block scoped to pull-requests: read + contents: read.
- F-05 unseeded np.random in test_ml_libraries.py:18-19 and test_shap.py:14
  (random_state=0 seeds only the model, not the data). FIXED via #246 (test/
  seed-smoke-tests, commit 9a49ac0): np.random.seed(10) before data
  generation in both (owner chose the seed value).

### Open by design (no action planned)

- Container runs as root (no USER directive) - by-design per owner ruling; a
  naive USER switch was analyzed and REJECTED (see the tradeoffs below).
- JupyterLab smoke uses --allow-root --token='' --ip=0.0.0.0 (build.yml:407):
  accepted for hermetic CI (container never exposed); escalates to high only
  if 8888 were published on a shared network.
- 20 open Trivy IMAGE-scan alerts (util-linux CVE-2026-78410 et al, 'Fixed
  Version:' empty, all created Sep 4 from stale digests): the unfixed/
  deferred category the apt-based gate correctly does not block on; they
  clear only via the reconcile cycle after a rebuild that actually clears
  them. Not stale alerts to dismiss.
- Code-scanning re-triage (Oct 2 2026, verified against the CURRENT published
  image d1e85c8b via a manual reconcile dispatch): 53 open Trivy image-scan
  alerts (util-linux family x4 CVEs, curl-gnutls, systemd, ncurses, perl,
  expat, acl - ALL base-image Debian packages), created Aug 30 (17) + Sep 4
  (36), both BEFORE the SARIF drop -> the count is a frozen ledger, nothing
  new created since. Verdict: ACTUAL, not stale - manual reconcile says
  'dismissed 0, still present 53'; every tuple present in today's image.
  Every alert has empty 'Fixed Version:' (no fix available in Debian trixie)
  and the apt gate passes - consistent: Debian has not shipped these fixes,
  nothing to apt-get, no rebuild clears them yet. Self-healing: Debian ships
  -> APT_BUST + apt-get upgrade pull them in -> gate enforces -> reconcile
  auto-dismisses. Current scan shows 55 findings vs the 53-alert ledger: 2
  findings exist without open alerts (no SARIF since Sep 4; build logs only,
  by design). Mass-dismissal would hide real findings; re-enabling SARIF
  recreates the never-closing per-digest ledger - leave as-is.
- No checkout sets persist-credentials: false (13 checkouts; only stamp-
  date's PAT checkout legitimately needs persistence for its git push).
  Low; not PR'd (owner did not select it).

### Verified clean (2026-10-01)

- All 29/35 external uses: refs full 40-hex SHA pins; trivy-action v0.36.0
  (post-incident safe line); PAT_FOR_BOTS reaches only SHA-pinned steps.
- Secrets: no token-like strings in tracked files or history since 2026-09-01
  (scan patterns: ghp_, github_pat_, AKIA, PRIVATE KEY blocks); no trace-echo
  (shell default has no -x); Docker Hub creds only in the push login step;
  the 'Bearer ***' at check-upstream.yml:182/184 is a read-tool redaction
  artifact of ${{ secrets.GITHUB_TOKEN }}, not a leak (byte-verified via od).
- uv.lock: 223 packages, all 999 URL lines on pypi.org/files.pythonhosted.org,
  zero foreign domains.
- Test contract: all 13 smoke/probe files network-free (only comments mention
  the avoided calls); dep-probe tests seeded default_rng(0).
- .dockerignore covers the whole tracked surface; Dockerfile COPYs only
  pyproject.toml, uv.lock, VERSION; no remote ADD / curl|sh; both FROM
  digest-pinned; pip purge intact (Dockerfile:11-12); APT_BUST wired
  (Dockerfile:61, fix #241).
- dependabot.yml: daily, cooldown 0, no weakening ignore-conditions.
- Publish chain live: origin/main HEAD == Docker Hub newest sha tag
  (Hub v2 tags API cross-check), labels revision/version/created match, pip
  absent from both pythons.
- Stale merged origin/* branches: RESOLVED (0 merged-stale; only lgbm_gpu
  unmerged, main, upgrade-intermediate-deps remain).

## urllib3 Dependabot alerts triage (Oct 1 2026)

- Alerts #1 (GHSA-vxq7-64xx-v4gw, high), #2 (GHSA-8988-9cw3-xx77, high),
  #3 (GHSA-gh4c-6fx4-qh6g, moderate): all fixed in 2.8.0, all REAL - uv.lock
  pins urllib3 2.7.0 (inside <2.8.0).
- Root cause: ccxt==4.5.84 (pyproject:55) exact-pins urllib3==2.7.0 while
  requests 2.34.2 (<3,>=1.26), docker 7.2.0 (>=1.26.0), databricks-sdk
  (<3,>=1.26) all allow 2.8.0. The nightly uv lock --upgrade cannot lift it
  (PR #242's bump table lacks urllib3 - merging #242 does NOT close the
  alerts).
- OWNER DECISION executed and RESOLVED (verified Oct 2 2026): Dependabot's
  ccxt bump landed as part of #242's merge (main now carries ccxt==4.5.85,
  pyproject:55, and urllib3 2.8.0 in uv.lock); all three urllib3 Dependabot
  alerts are CLOSED (dependabot alerts?state=open returns empty). The
  prediction held: no manual PR was needed, the alerts closed after merge +
  image rebuild (published digest d1e85c8b, Oct 2 06:16 UTC, == main HEAD
  f5f2d81 by the Hub v2 tags API cross-check).
- Method for root-causing a locked transitive: scan requirers' PyPI
  requires-dist metadata - awk over uv.lock [[package]] blocks for requirers
  ('/^name = /{name=$3} /{ name = "X"/{print name}'), strip TOML quotes from
  the pinned version, then curl pypi.org/pypi/<pkg>/<ver>/json per requirer.
  NOT local resolution: linux-only environments make uv pip compile return
  an empty set on the Windows host (structurally impossible, not a bug).

## The #247 test dispatch created PR #248 (duplicate, wrong base) - Oct 1 2026

- Timeline: 21:01:35 dispatch of check-upstream on ci/validate-bump-base-
  inputs (run 36925826195) to test #247 pre-merge; 21:01:57 the
  intermediate-deps job (selected in the FULL run - empty checks input = all
  jobs) ran uv lock --upgrade, found changes, create-pull-request executed;
  ~21:02-21:07 the action force-pushed the fresh lock onto the EXISTING
  upgrade-intermediate-deps branch (owned by open PR #242) 5 times
  (1635fcb -> 06436b8) instead of creating a new branch; ~21:07 GitHub
  opened PR #248 from that branch with base = the dispatch ref
  (ci/validate-bump-base-inputs, main-at-dispatch-time), not main; the
  automatic base-change event (-> main) failed; #247 merged (main e105afe).
- Net state: #242 base main head 06436b8 MERGEABLE/CLEAN; #248 base
  ci/validate-bump-base-inputs, SAME head sha 06436b8, uv.lock-only diff.
- RESOLUTION: #248 closed WITHOUT branch deletion (deleting would kill
  #242's head; create-pull-request's delete-branch fires only on merge);
  #242 kept as the canonical PR.
- Lessons: (1) a manual dispatch of a multi-job check workflow selects ALL
  jobs including PR-creating ones; to live-test one job pass the checks
  input (checks=python,uv for bump-base only). (2) create-pull-request
  updates an existing branch by force-pushing onto it - any run of a
  workflow whose branch: name collides with an open PR's head can rewrite
  that PR's head. (3) the base of a PR created from a workflow_dispatch is
  the dispatch ref, not necessarily main.

## Sep 2026 audit (fd0bdf0 + live image) - superseded entries kept for history

- APT_BUST never worked since 45a991b (Aug 22): ARG declared but never
  referenced inside the apt RUN (BuildKit only busts a layer when a declared
  ARG is USED). Sep 29: Debian libpcre2-8-0 deb13u3 published while the
  frozen layer carried u2 -> every PR build gate failed from Sep 29 23:14
  UTC, no bump PR appeared (correct: no version drift). FIXED via #241
  (merged 2026-09-30 20:32 UTC, commit 60db0d9): all post-merge main builds
  passed the gate, published image dd5abd45 (Oct 1 07:50 UTC) carries the
  fix by gate logic.
- The open msgpack 1.1.2 / setuptools 70.3.0 Trivy alerts were pip's VENDORED
  copies (pip/_vendor); removed pip from the image at the root (commit
  6dfceba, Sep 22) -> alerts dismissed by reconciliation.
- Reconcile triggers fire BEFORE the build published by that same push
  finishes (~12 min): reconcile scans the PREVIOUS published image. Safe
  direction; workflow comments claiming 'new image is live' are inaccurate.
- Root -> non-root tradeoffs (verified empirically as --user 1000): apt gate
  dies vacuously (fix --user 0 on the probe), /app and venv stay root-owned
  (fix useradd -m + chown + MPLCONFIGDIR), GPU compute as non-root NOT
  confirmed. A naive USER-only switch is worse than staying root.
- Merge-chain cancels during the Oct 1 sequential merge session were verified
  correct supersessions: read required checks on the MERGED head SHA.
