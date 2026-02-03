# JupyterLab Portable Environment

I created these Docker images because I use multiple PCs for my pet projects and need a consistent environment with all necessary libraries pre-installed.

## Features

- **Python version**: [3.12.12-slim-trixie](https://hub.docker.com/_/python).
- **Package Manager**: [Poetry](https://github.com/python-poetry/poetry) for dependency management.
- **Environment**: [JupyterLab](https://github.com/jupyterlab/jupyterlab).
- **Additional Libraries**: commonly used data science and ML libraries.

### Versioning

- **`Dockerfile`**: lists base Python image and Poetry version.
- **`pyproject.toml`**: defines tag dependencies and their versions.

### Tags

> **Note:** For a complete list of libraries and their versions, refer to the `pyproject.toml` file in the corresponding branch on GitHub.

|tag|Description|Included Libraries|
|---|---|---|
|`base`|JupyterLab core|[JupyterLab extensions, linters, formatters](https://github.com/Seeeaaa/jlpe/blob/3.13.base/pyproject.toml)|
|`main`|Everything from `base` + data manipulation/visualization|[NumPy, Pandas, Matplotlib, etc](https://github.com/Seeeaaa/jlpe/blob/3.13.main/pyproject.toml)|
|`ml`|Everything from `main` + gradient boosting/time-series forecasting|[XGBoost, LightGBM, CatBoost, Prophet](https://github.com/Seeeaaa/jlpe/blob/3.13.ml/pyproject.toml)|

## Usage

> **Note:** currently, containers are configured to run as the root user.

### Steps to get started:

**Pull Docker Image**
Replace <tag> with `base`, `main`, or `ml` to pull the corresponding image:
```bash
docker pull vyxan/jlpe_image:<tag>
```
**Run the Docker Container**:
```bash
docker run -it -p 8888:8888 vyxan/jlpe_image:<tag>
```

### Mount directories and start JupyterLab

If you want to mount a project directory and JupyterLab settings ([by default located](https://jupyterlab.readthedocs.io/en/stable/user/directories.html#jupyterlab-user-settings-directory) at `$HOME/.jupyter`), and start JupyterLab, you can run the container with the following command:

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
If you want to connect to the Jupyter Server via VS Code, add two additional flags to the command:

`--IdentityProvider.token="" --ServerApp.disable_check_xsrf=True`

This is required because the VS Code Jupyter integration does not fully support Jupyter Server XSRF checks, unlike web browsers.

> **Note:** These flags are intended for local development only. Do not use them when exposing Jupyter Server to external networks.

## Links

[GitHub](https://github.com/Seeeaaa/jlpe)

[DockerHub](https://hub.docker.com/r/vyxan/jlpe_image)
