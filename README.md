# JupyterLab Portable Environment
I created these Docker images to use the same fully configured JupyterLab environment across multiple machines.

## Features
- **Python version**: based on official Python images (`python:<version>-slim-trixie`). The `latest` tag points to `3.13`; other versions are available via Docker tags (`3.11`, `3.12`).
- **Package Manager**: [Poetry](https://github.com/python-poetry/poetry).
- **Environment**: [JupyterLab](https://github.com/jupyterlab/jupyterlab).
- **Libraries:** data manipulation, visualization, and ML packages.

### Versioning
- The repository contains a single `Dockerfile` and `pyproject.toml`.
- The Python version is defined at build time via Docker ARG.
- Each Docker tag corresponds to a specific Python version.

### Supported Tags
|Tag|Description|
|-|-|
|`3.11`|Full environment built on Python 3.11|
|`3.12`|Full environment built on Python 3.12|
|`3.13`|Full environment built on Python 3.13|
|`latest`|Points to the current default Python version|

For a complete list of dependencies and their versions, refer to `pyproject.toml` in the `main` branch.

## Usage
Containers run as root by default.

**Pull Image**
```bash
docker pull vyxan/jlpe_image:<tag>
```
Example:
```bash
docker pull vyxan/jlpe_image:3.13
```

**Run Container**:
```bash
docker run -it -p 8888:8888 vyxan/jlpe_image:<tag>
```
Example:
```bash
docker run -it -p 8888:8888 vyxan/jlpe_image:3.13
```

### Mount directories and start JupyterLab
If you want to mount a project directory and JupyterLab settings ([by default located](https://jupyterlab.readthedocs.io/en/stable/user/directories.html#jupyterlab-user-settings-directory) at `$HOME/.jupyter`), and start JupyterLab, run the container with the following command:

#### Windows
```powershell
docker run -it -p 8888:8888 `
--mount type=bind,source=C:/project_directory,target=/app/project_directory `
--mount type=bind,source=C:/Users/User/.jupyter,target=/root/.jupyter `
vyxan/jlpe_image:<tag> -c "poetry run jupyter lab --allow-root --no-browser --ip=0.0.0.0 --port=8888"
```

#### Linux/MacOS
```bash
docker run -it -p 8888:8888 \
--mount type=bind,source=/path/to/project_directory,target=/app/project_directory \
--mount type=bind,source=/path/to/.jupyter,target=/root/.jupyter \
vyxan/jlpe_image:<tag> -c "poetry run jupyter lab --allow-root --no-browser --ip=0.0.0.0 --port=8888"
```

#### VS Code integration
To connect via VS Code (for attaching to a running container), add:
`--IdentityProvider.token="" --ServerApp.disable_check_xsrf=True`

This is required because the VS Code Jupyter integration does not fully support Jupyter Server XSRF checks.

> **Note:** These flags are intended for local development only. Do not use them when exposing Jupyter Server to external networks.

## Links

[GitHub](https://github.com/Seeeaaa/jlpe)

[DockerHub](https://hub.docker.com/r/vyxan/jlpe_image)
