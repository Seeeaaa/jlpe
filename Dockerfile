FROM ghcr.io/astral-sh/uv:0.12.17@sha256:10787c682e4184e4f290de1171fd4703dc63de99221f10fe1c99002ce7fa9acc AS uv
FROM python:3.13.15-slim-trixie@sha256:8d9d0b8bcf6506481eae4907c18f5e3e7902e629f5f6d684f9e7c32e85e3ddf0

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
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        build-essential libgomp1 git postgresql-client && \
    rm -rf /var/lib/apt/lists/*

COPY --from=uv /uv /uvx /bin/

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project --all-groups && rm -rf $UV_CACHE_DIR

# Dynamic OCI metadata. VERSION/REVISION/CREATED are passed by build.yml
# from the stamped pyproject version, commit sha and UTC date; defaults stay
# empty so local builds never carry misleading labels. These layers sit
# AFTER the apt and uv sync layers on purpose: build.yml stamps VERSION on
# every merge to main, and any ARG change invalidates its own layer and
# everything below it. Placed at the top, that rebuilt the whole image on
# every stamp; placed last, a fresh stamp only rewrites the cheap label
# layer and the heavy system/dependency install cache survives. The uv sync
# layer itself still misses by design whenever the stamp touches
# pyproject.toml / uv.lock bytes.
ARG VERSION=""
ARG REVISION=""
ARG CREATED=""
LABEL org.opencontainers.image.version=$VERSION \
      org.opencontainers.image.revision=$REVISION \
      org.opencontainers.image.created=$CREATED

EXPOSE 8888
ENTRYPOINT ["bash"]