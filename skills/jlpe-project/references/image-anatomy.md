# JLPE image anatomy (Sep-Oct 2026 findings)

Full image-layer and dependency-tree findings, verified against the published
image. The always-on summary lives in SKILL.md; this file is the depth loaded
on demand.

## Published-image verification procedure

- OWNER RULING (2026-10-01): image verification does NOT use local Docker -
  everything is configured to run in GH cloud. Verify via the Docker Hub v2
  tags API (https://hub.docker.com/v2/repositories/vyxan/jlpe_image/tags)
  cross-checked against origin/main HEAD's sha tag (they must match;
  origin/main HEAD is always the newest published image), plus gh/REST for
  CI and PR state. Local docker run probes are banned for this purpose; a
  docker pull that already succeeded before the ruling stands as verified
  evidence.
- The local Docker :latest can lag the published image by days. A
  workflow-only PR never triggers a build by design, so origin/main HEAD can
  legitimately sit AHEAD of the newest pushed Docker Hub tag - that lag form
  is benign; only a content-file merge leaves main behind the newest tag.
- Docker Desktop's Linux engine can die mid-session (npipe
  dockerDesktopLinuxEngine vanishes, com.docker.* processes gone): recovery =
  relaunch 'C:\Program Files\Docker\Docker\Docker Desktop.exe' (via
  powershell.exe Start-Process - the terminal tool rejects shell-level
  background wrappers, and background=true exe launches die silently);
  engine pipe returns ~2-4 minutes later. Do not conclude 'docker broken'
  from one failed call - check tasklist for com.docker.* processes first.
  sc.exe query com.docker.service shows STOPPED even while the engine works
  (exit code 1077 = service never started, benign).

## Layer and venv findings

- Pre-Sep-22 images carried pip 26.2.1 in BOTH the base python and the
  project venv; the pip-removal commit (6dfceba, Sep 22) cleared both in
  images built after it. Clean check (local docker era): docker run --rm
  --entrypoint python vyxan/jlpe_image:latest -m pip --version must print
  "No module named pip" (venv python at /opt/project-venv/bin/python
  likewise). Hub-API cross-check VERIFIED 2026-10-01: pip absent from both
  pythons in the published image (digest dd5abd45).
- The 941 MB (compressed) uv sync layer rebuild on every main push was FIXED
  by the VERSION-file restructure (PR #234, 2026-09-26): the version lives in
  the VERSION file (tag form), pyproject's version is a static 0.0.0
  placeholder (uv embeds any pyproject version value into uv.lock's root jlpe
  entry, so a dynamic version there invalidated the COPY layer daily), COPY
  VERSION sits AFTER the uv sync layer, stamp_and_commit writes VERSION only,
  build.yml fullver reads cat VERSION, both path filters include VERSION.
  Stamp-only pushes rebuild only the VERSION + label layers. Transition:
  when pyproject's version changes in a PR, uv sync --locked fails until
  update-lock.yml auto-commits the regenerated lock (self-healing, verified
  on #234).
- Layer sizes (docker history, fd0bdf0 build): uv sync 2.43 GB, apt (upgrade
  + install) 112 MB, uv binary 56.5 MB; venv 2322 MB, /opt 2377 MB, image
  2664 MB on disk / 1047 MB compressed on Hub (Hub sizes from the v2 tags API
  images[].size, not docker images).
- Dockerfile ordering: static labels top (cache forever), apt RUN with the
  load-bearing 'echo "$APT_BUST" &&' (BuildKit only includes a declared ARG
  in the cache key when a RUN references it), uv sync, then COPY VERSION,
  then the dynamic ARG/LABEL block last (a stamp rewrites only the cheap
  label layer).

## GPU / CUDA findings

- xgboost's Linux wheels statically link the CUDA runtime
  (libcudart_static_* inside libxgboost.so) and dynamically load only
  libcuda.so.1 (host driver, injected by Docker's --gpus all) plus NCCL from
  PyPI (nvidia-nccl-cu13, ~345 MB under the venv's nvidia/ dir). VERIFIED
  2026-09-24: docker run --gpus all ... xgb.train({'device': 'cuda'}, ...)
  trains on GPU with no fallback warning; bare --runtime nvidia alone does
  NOT inject libcuda and xgboost silently falls back to CPU. No
  nvidia-container-toolkit or CUDA base image needed. Keep xgboost (not
  xgboost-cpu) when GPU xgboost is a real usage; xgboost-cpu==3.4.1 (5.8 MB
  wheel) remains the disk-pressure fallback and drops the whole nvidia stack.
- torch on PyPI for Linux is the full CUDA build (2.14.0, 554.6 MB cp313
  wheel). CPU-only torch requires the explicit pytorch-cpu index
  ([[tool.uv.index]] + [tool.uv.sources], explicit = true) per uv's PyTorch
  guide; the index carries torch 2.14.0+cpu for cp313 linux x86_64 and a
  2.9.1+cpu cp313 x86_64 wheel measures 184.4 MB (direct wheel URLs 403
  without the download-r2.pytorch.org host). CUDA torch in this image is not
  sensible (+2.5-3 GB, needs nvidia-container-toolkit + host GPU).
- libcuda.so.1 loads fine as non-root; GPU compute as non-root was NOT
  confirmed end-to-end (device nodes not injected in the probe invocation).

## Dependency tree findings

- Nothing in the lock compiles from source: prophet bundles its compiled stan
  model (prophet_model.bin, verified in the image), every other package ships
  cp313/abi3 linux or universal wheels. build-essential was REMOVED from the
  apt layer (PR #225, 2026-09-24; CI green, lightgbm/prophet smoke tests pass
  without it; originally added in ccf2ce3, 2025-05-12, direct to main, no
  PR). Of 21 realistic ad-hoc libs probed, only orbit-ml and filterpy lack
  linux wheels; Python.h stays in the base image either way.
- libgomp1 is NOT optional and installs standalone (depends only on
  gcc-14-base + libc6, both in slim-trixie; VERIFIED 2026-09-24 required at
  runtime by lightgbm's lib_lightgbm.so and by numba's parallel layer,
  threading layer = omp).
- The two ldd 'not found' entries in the venv are benign: numba's tbbpool is
  the optional TBB layer (tbb absent, omp selected) and shapely's geos
  resolves via its bundled RPATH, which plain ldd does not apply.
- numba+llvmlite (~190 MB) enter the lock from THREE sources: shap, tsfresh's
  required stumpy dep, and the pandas[performance] extra (bottleneck, numba,
  numexpr). Removing shap alone keeps numba (stumpy needs it); removing shap
  AND tsfresh still keeps numba (pandas[performance] requires it); freeing
  the pair needs shap + tsfresh + the performance extra all dropped (plain
  pandas). mlflow drags the widest tree (92-package closure) but installs
  only ~47 MB; uvloop (~16 MB) comes in via ccxt's required deps.
- ccxt exact-pins urllib3 (4.5.84 -> urllib3==2.7.0; 4.5.85 ->
  urllib3==2.8.0): a requirer's exact pin caps the transitive through the
  nightly uv lock --upgrade. See references/audit-ledger.md for the triage.
