# JLPE - JupyterLab Portable Environment

I created these Docker images because I use multiple PCs for my pet projects and need a consistent environment with all necessary libraries pre-installed.

## Features

- **Python version**: [3.12.x-slim-bookworm](https://hub.docker.com/_/python)
- **Package Manager**: [Poetry](https://github.com/python-poetry/poetry) for dependency management
- **Environment**: [JupyterLab](https://github.com/jupyterlab/jupyterlab)
- **Additional Libraries**: Preconfigured with commonly used libraries

### Versioning

- **`Dockerfile`**: Lists base Python image and Poetry version.
- **`pyproject.toml`**: Defines tag dependencies and their versions.

## Tags

> **Note:** For a complete list of libraries and their versions, refer to the `pyproject.toml` file in the corresponding branch on GitHub.

|tag|Description|Included Libraries|
|---|---|---|
|`base`|JupyterLab core|JupyterLab extensions, linters, formatters|
|`main`|Everything from `base` + data manipulation/visualization|NumPy, Pandas, Matplotlib, etc|
|`ml`|Everything from `main` + gradient boosting/time-series forecasting|XGBoost, LightGBM, CatBoost, Prophet|

## Usage

> **Note:** Currently, the container is configured to run as the root user.

### Steps to get started:

**Pull Docker Image with required tag (replace with `base`, `main` or `ml`)**:
```bash
docker pull vyxan/jlpe_image:<tag>
```
**Run the Docker Container**:
```bash
docker run -it -p 8888:8888 vyxan/jlpe_image:<tag>
```

### Mount directories and start JupyterLab

If you want to mount project directory and JupyterLab settings ([by default located at `$HOME/.jupyter`](https://jupyterlab.readthedocs.io/en/stable/user/directories.html#jupyterlab-user-settings-directory)), and start JupyterLab, you can run the container with the following command:

#### Windows

```powershell
docker run -it -p 8888:8888 `
--mount type=bind,source=C:/project_directory,target=/app/project_directory `
--mount type=bind,source=C:/Users/User/.jupyter,target=/root/.jupyter `
vyxan/jlpe_image:<tag> -c "poetry run jupyter lab --allow-root --no-browser --ip=0.0.0.0"
```

#### Linux/MacOS

```bash
docker run -it -p 8888:8888 \
--mount type=bind,source=/path/to/project_directory,target=/app/project_directory \
--mount type=bind,source=/path/to/.jupyter,target=/root/.jupyter \
vyxan/jlpe_image:<tag> -c "poetry run jupyter lab --allow-root --no-browser --ip=0.0.0.0"
```
## Links

[GitHub](https://github.com/Seeeaaa/jlpe)

[DockerHub](https://hub.docker.com/r/vyxan/jlpe_image)