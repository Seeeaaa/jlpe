ARG PYTHON_VERSION=3.13.5-slim-bookworm
FROM python:${PYTHON_VERSION} AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV VENV_PATH=/opt/poetry/venv

ARG POETRY_VERSION=2.1.3

RUN python3 -m venv $VENV_PATH
RUN $VENV_PATH/bin/pip install -U pip setuptools
RUN $VENV_PATH/bin/pip install poetry==$POETRY_VERSION
RUN ln -s $VENV_PATH/bin/poetry /usr/local/bin/poetry

WORKDIR /app
COPY pyproject.toml ./

RUN poetry install

EXPOSE 8888

ENTRYPOINT ["bash"]
