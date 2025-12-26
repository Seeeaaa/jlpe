ARG PYTHON_VERSION=3.14.2-slim-bookworm
FROM python:${PYTHON_VERSION} AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV VENV_PATH=/opt/poetry/venv

ARG POETRY_VERSION=2.2.1

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential libgomp1 git && \
    rm -rf /var/lib/apt/lists/*

RUN python3 -m venv $VENV_PATH && \
    $VENV_PATH/bin/pip install -U pip setuptools && \
    $VENV_PATH/bin/pip install poetry==$POETRY_VERSION && \
    ln -s $VENV_PATH/bin/poetry /usr/local/bin/poetry

WORKDIR /app
COPY pyproject.toml ./

RUN poetry install

EXPOSE 8888

ENTRYPOINT ["bash"]
