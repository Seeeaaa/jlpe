# JupyterLab Portable Environment
I created this Docker image to provide a consistent, fully configured JupyterLab environment across multiple machines.

## Features
- **Python version**: based on the official `python:3.13-slim-trixie` Docker image
- **Package manager**: [uv](https://github.com/astral-sh/uv)
- **Environment**: [JupyterLab](https://github.com/jupyterlab/jupyterlab)
- **Libraries:** data manipulation, visualization, and machine learning libraries

### Versioning
- Each Docker tag corresponds to a specific JLPE version.
- The repository contains a single `Dockerfile` and a `pyproject.toml`.
I try to update the image whenever a new library version or a new Python minor version is released. When a new library version conflicts with existing dependencies, I resolve the issue on a case-by-case basis. For example, during the migration to pandas 3.0, shap and mlflow were temporarily excluded from the build.

### Supported tags
|Tag|Python|Package manager|Description|
|-|-|-|-|
|`uv`, `latest`|`3.13`|`uv`|Full environment built with `uv`, instead of `Poetry`|
|`3.13`|`3.13`|`Poetry`|Full environment built on `Python 3.13` with `Poetry`|
|`lgbm_gpu`|`3.13`|`Poetry`|Full environment `[outdated]` built with GPU-compatible `LGBM` framework|
<!-- |`3.12`|Full environment built on Python 3.12|
|`latest`|`3.13`|`Poetry`|Points to the current default Python version|
|`3.11`|Full environment built on Python 3.11| -->


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

**Run container**:
```bash
docker run -it -p 8888:8888 vyxan/jlpe_image:<tag>
```
Example:
```bash
docker run -it -p 8888:8888 vyxan/jlpe_image:3.13
```
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

This is required because the VS Code's Jupyter integration does not fully support Jupyter Server XSRF protection checks.

> **Note:** These flags are intended for local development only. Do not use them when exposing Jupyter Server to external networks.

## Links

[GitHub](https://github.com/Seeeaaa/jlpe)

[DockerHub](https://hub.docker.com/r/vyxan/jlpe_image)
