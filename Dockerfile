ARG PYTHON_VERSION=3.11.9-slim-bookworm

FROM python:${PYTHON_VERSION} AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# RUN mkdir -p /opt/poetry/.config
# ENV POETRY_CONFIG_DIR=/opt/poetry/.config
# RUN mkdir /opt/poetry/data
# ENV POETRY_DATA_DIR=/opt/poetry/data
# RUN mkdir /opt/poetry/.cache
# ENV POETRY_CACHE_DIR=/opt/poetry/.cache
ENV VENV_PATH=/opt/poetry/venv
# ENV POETRY_NO_INTERACTION=1
# ENV POETRY_VIRTUALENVS_IN_PROJECT=1
# ENV POETRY_VIRTUALENVS_CREATE=1

ARG POETRY_VERSION=1.8.3

RUN python3 -m venv $VENV_PATH
RUN $VENV_PATH/bin/pip install -U pip setuptools
RUN $VENV_PATH/bin/pip install poetry==$POETRY_VERSION
RUN ln -s $VENV_PATH/bin/poetry /usr/local/bin/poetry

# RUN pip install poetry==$POETRY_VERSION

WORKDIR /petproject

COPY pyproject.toml poetry.lock ./

# RUN touch README.md
RUN poetry install
#  && rm -rf $POETRY_CACHE_DIR


EXPOSE 8888
ENTRYPOINT ["bash"]
# CMD ["poetry", "run", "jupyter", "lab", "--allow-root", "--no-browser", "--ip=0.0.0.0"]
# , "--port=8888"]
