ARG PYTHON_VERSION=3.13.11-slim-bookworm
FROM python:${PYTHON_VERSION} AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV POETRY_HOME=/opt/poetry
ENV POETRY_CACHE_DIR=/opt/.cache
ENV PATH="$POETRY_HOME/bin:$PATH"

ENV POETRY_VIRTUALENVS_IN_PROJECT=1
ENV POETRY_VIRTUALENVS_CREATE=1

ARG POETRY_VERSION=2.2.1

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential libgomp1 git && \
    rm -rf /var/lib/apt/lists/* && \
    pip install -U pip setuptools && \
    pip install "poetry==$POETRY_VERSION"

WORKDIR /app
COPY pyproject.toml ./
RUN poetry install

EXPOSE 8888
ENTRYPOINT ["bash"]
