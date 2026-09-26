FROM ghcr.io/astral-sh/uv:0.12.19@sha256:04d046b13e60d6bcec73cbc5e1cad25d680dea90c8573340950a0ac2d1aef424 AS uv
FROM python:3.13.15-slim-trixie@sha256:7c61056e61ac89e852de05f3dc6fa51a6dd2181797bceed46aa725dd7cb2cd3b

# ensurepip bundles pip into the base image's site-packages, and pip's
# vendored dependency copies under pip/_vendor are reported by image
# vulnerability scanners as findings of their own. uv owns all package
# management in this image and nothing needs pip, so remove it here:
# this deletes the vendored copies at the root, so scanners no longer see
# them and stale alerts are dismissed by the reconciliation workflow.
# Static layer: its content never changes, so it caches forever.
RUN python -m pip uninstall -y pip && \
    rm -f /usr/local/bin/pip /usr/local/bin/pip3

# Static OCI metadata: these values never change, so the layer caches
# forever. Dynamic labels live at the bottom of the file (see there).
LABEL org.opencontainers.image.title="JLPE" \
      org.opencontainers.image.description="JupyterLab Portable Environment" \
      org.opencontainers.image.source="https://github.com/Seeeaaa/jlpe" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ENV UV_PROJECT_ENVIRONMENT=/opt/project-venv
ENV UV_CACHE_DIR=/opt/.cache/uv
ENV UV_PYTHON_DOWNLOADS=never
ENV PATH="$UV_PROJECT_ENVIRONMENT/bin:$PATH"

# Cache-bust for the apt layer only: build.yml passes the UTC date, so this
# ARG changes once a day and refreshes system packages without invalidating
# the (much heavier) uv sync layers below.
ARG APT_BUST=0
# `upgrade` (not just `install`) is what actually ingests Debian security
# fixes for packages that are already present in the base image (e.g.
# libpcre2-8-0): `apt-get install <list>` only adds missing packages and
# leaves already-installed transitive deps at their base-image version, so
# without upgrading, a published fix (say 10.46-1~deb13u2 for a security
# release) would never reach the image regardless of how often APT_BUST
# busts the cache. upgrade -y pulls forward every installed package to the
# latest available in the trixie archive, which is what makes the
# apt-based publish gate (see build.yml) meaningful.
# No build-essential: every locked package installs from a prebuilt wheel
# (prophet bundles its compiled stan model, verified in the image), so the
# dependency install never compiles from source. libgomp1 is kept
# deliberately: it is the runtime OpenMP library required by lightgbm
# (lib_lightgbm.so has a hard NEEDED entry for libgomp.so.1) and by numba's
# parallel threading layer (threading layer = omp). Installing libgomp1
# alone works on the clean base: it depends only on gcc-14-base and libc6,
# both already present in slim-trixie, so nothing from build-essential is
# required to provision it.
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        libgomp1 git postgresql-client && \
    rm -rf /var/lib/apt/lists/*

COPY --from=uv /uv /uvx /bin/

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project --all-groups && rm -rf $UV_CACHE_DIR

# The image version is COPYed AFTER the uv sync layer on purpose: it changes
# on every stamp (build.yml writes a fresh timestamp into VERSION and pushes
# a stamp commit), while pyproject.toml / uv.lock stay byte-stable. Placed
# above the sync layer, a stamp would invalidate the COPY and rebuild the
# 2.4 GB dependency layer daily; placed here, a stamp only rewrites this
# cheap layer (and the label layer below). build.yml reads the tag form from
# this file; the pyproject version field is a static placeholder (see there).
COPY VERSION ./

# Dynamic OCI metadata. REVISION/CREATED are passed by build.yml from the
# commit sha and UTC date; the version label comes from the stamped VERSION
# file (see the COPY above). ARG defaults stay empty so local builds never
# carry misleading labels. These layers sit AFTER the apt and uv sync layers
# on purpose: build.yml stamps VERSION on every merge to main, and any ARG
# change invalidates its own layer and everything below it. Placed at the
# top, that rebuilt the whole image on every stamp; placed last, a fresh
# stamp only rewrites the cheap label layer and the heavy system/dependency
# install cache survives.
ARG VERSION=""
ARG REVISION=""
ARG CREATED=""
LABEL org.opencontainers.image.version=$VERSION \
      org.opencontainers.image.revision=$REVISION \
      org.opencontainers.image.created=$CREATED

EXPOSE 8888
ENTRYPOINT ["bash"]