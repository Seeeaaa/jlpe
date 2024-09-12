ARG PYTHON_VERSION=3.11.9-slim-bookworm

FROM python:${PYTHON_VERSION} AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV VENV_PATH=/opt/poetry/venv

ARG POETRY_VERSION=1.8.3

RUN python3 -m venv $VENV_PATH
RUN $VENV_PATH/bin/pip install -U pip setuptools
RUN $VENV_PATH/bin/pip install poetry==$POETRY_VERSION
RUN ln -s $VENV_PATH/bin/poetry /usr/local/bin/poetry

WORKDIR /root
COPY .jupyter ./

WORKDIR /app

COPY pyproject.toml poetry.lock ./

RUN poetry install

EXPOSE 8888
ENTRYPOINT ["bash"]
