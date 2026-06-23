FROM python:3.13.14-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ENV UV_PROJECT_ENVIRONMENT=/opt/project-venv
ENV UV_CACHE_DIR=/opt/.cache/uv
ENV UV_PYTHON_DOWNLOADS=never
ENV PATH="$UV_PROJECT_ENVIRONMENT/bin:$PATH"

ARG UV_VERSION=0.11.23

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential libgomp1 git postgresql-client && \
    rm -rf /var/lib/apt/lists/*

RUN pip install "uv==$UV_VERSION"

WORKDIR /app
COPY pyproject.toml ./
RUN uv sync --no-install-project --all-groups && rm -rf $UV_CACHE_DIR

EXPOSE 8888
ENTRYPOINT ["bash"]