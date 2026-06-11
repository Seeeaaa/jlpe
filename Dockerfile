FROM python:3.13.14-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ENV POETRY_VENV=/opt/poetry/venv
ENV PATH="$POETRY_VENV/bin:$PATH"

ENV POETRY_CACHE_DIR=/opt/.cache
ENV POETRY_VIRTUALENVS_CREATE=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=0
ENV POETRY_VIRTUALENVS_PATH=/opt/project-venvs

ARG POETRY_VERSION=2.4.1

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential libgomp1 git postgresql-client && \
    rm -rf /var/lib/apt/lists/*

RUN python -m venv $POETRY_VENV && \
    $POETRY_VENV/bin/pip install -U pip setuptools && \
    $POETRY_VENV/bin/pip install "poetry==$POETRY_VERSION"

WORKDIR /app
COPY pyproject.toml ./
RUN poetry install --no-root && rm -rf $POETRY_CACHE_DIR

EXPOSE 8888
ENTRYPOINT ["bash"]
