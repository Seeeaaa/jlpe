FROM ghcr.io/astral-sh/uv:0.12.5@sha256:e85be844203885286c60ffad8a858d48afb6c5a5c237ca0e67f12e74b8f174b1 AS uv
FROM python:3.13.15-slim-trixie@sha256:afd91e25d0d1b40e4c92bf716154ec3c4a9f0de1ce2a5c3663007fb6918eaf9c

# OCI image metadata. VERSION/REVISION/CREATED are passed by build.yml from
# the stamped pyproject version, commit sha and UTC date; defaults stay empty
# so local builds never carry misleading labels.
ARG VERSION=""
ARG REVISION=""
ARG CREATED=""
LABEL org.opencontainers.image.title="JLPE" \
      org.opencontainers.image.description="JupyterLab Portable Environment" \
      org.opencontainers.image.source="https://github.com/Seeeaaa/jlpe" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version=$VERSION \
      org.opencontainers.image.revision=$REVISION \
      org.opencontainers.image.created=$CREATED

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
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential libgomp1 git postgresql-client && \
    rm -rf /var/lib/apt/lists/*

COPY --from=uv /uv /uvx /bin/

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project --all-groups && rm -rf $UV_CACHE_DIR

EXPOSE 8888
ENTRYPOINT ["bash"]