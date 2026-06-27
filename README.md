# JupyterLab Portable Environment
I created this Docker image to provide a consistent, fully configured JupyterLab environment across multiple machines.

## Features
- **Python version**: based on the official `python:3.13.x-slim-trixie` Docker image
- **Package manager**: [uv](https://github.com/astral-sh/uv)
- **Notebook IDE**: [JupyterLab](https://github.com/jupyterlab/jupyterlab)
- **Libraries:** data manipulation, visualization, and machine learning

### Versioning
- The version format is `{python_version}+{image_variant}.{build_date}` — for example, `3.13.14+slim-trixie.20260623` means Python 3.13.14, built on the `slim-trixie` Debian image, released on 2026-06-23.
- Each Docker tag corresponds to a specific JLPE version.
- The repository contains a single `Dockerfile` and a `pyproject.toml`.
I try to update the image whenever a new library version or a new Python patch version is released. When a new library version conflicts with existing dependencies, I resolve the issue on a case-by-case basis. For example, when migrating to pandas 3.0, shap and mlflow were excluded due to compatibility issues and may be re-added once resolved.

### Supported tags
|Tag|Python|Package manager|Description|
|-|-|-|-|
|`latest`, `3.13`|`python:3.13.x-slim-trixie`|`uv`|Full environment built on `Python 3.13` with `uv`|
|`lgbm_gpu`|`python:3.13.x-slim-trixie`|`Poetry`|Full environment *(outdated)* built with GPU-compatible `LGBM` framework|

For a complete list of dependencies and their versions, refer to `pyproject.toml` in [JLPE GitHub repository](https://github.com/Seeeaaa/jlpe).

## Usage
Containers run as root by default.

**Pull image**
```bash
docker pull vyxan/jlpe_image:<tag>
```
Example:
```bash
docker pull vyxan/jlpe_image:3.13
```

**Run container** (without mounts):
```bash
docker run -it -p 8888:8888 vyxan/jlpe_image:uv -c "jupyter lab --allow-root --no-browser --ip=0.0.0.0 --port=8888"
```
After starting, open the URL shown in the terminal (e.g. `http://127.0.0.1:8888/lab?token=...`) in your browser.

> **Note:** The container entrypoint is `bash`. Without a `-c` command, the container opens an interactive shell.

### Mounting directories and starting JupyterLab
If you want to mount a project directory and JupyterLab configuration ([located by default](https://jupyterlab.readthedocs.io/en/stable/user/directories.html#jupyterlab-user-settings-directory) at `$HOME/.jupyter`), and start JupyterLab, run the container with the following command:

#### Windows
```powershell
docker run -it -p 8888:8888 `
--mount type=bind,source=C:/project_directory,target=/app/project_directory `
--mount type=bind,source=C:/Users/<username>/.jupyter,target=/root/.jupyter `
vyxan/jlpe_image:<tag> -c "jupyter lab --allow-root --no-browser --ip=0.0.0.0 --port=8888"
```

#### Linux / MacOS
```bash
docker run -it -p 8888:8888 \
--mount type=bind,source=/path/to/project_directory,target=/app/project_directory \
--mount type=bind,source=/path/to/.jupyter,target=/root/.jupyter \
vyxan/jlpe_image:<tag> -c "jupyter lab --allow-root --no-browser --ip=0.0.0.0 --port=8888"
```

#### Poetry-based images (older versions)
If the image was built with Poetry, add `poetry run` before `jupyter lab`. Windows example:
```powershell
docker run -it -p 8888:8888 `
--mount type=bind,source=C:/project_directory,target=/app/project_directory `
--mount type=bind,source=C:/Users/<username>/.jupyter,target=/root/.jupyter `
vyxan/jlpe_image:<tag> -c "poetry run jupyter lab --allow-root --no-browser --ip=0.0.0.0 --port=8888"
```

#### VS Code integration
To connect from VS Code to a running Jupyter server, add:
`--IdentityProvider.token="" --ServerApp.disable_check_xsrf=True`

This is required because VS Code's Jupyter integration does not fully support Jupyter Server XSRF protection checks.

> **Note:** These flags are intended for local development only. Do not use them when exposing Jupyter Server to external networks.

## Links

[GitHub](https://github.com/Seeeaaa/jlpe)

[DockerHub](https://hub.docker.com/r/vyxan/jlpe_image)
