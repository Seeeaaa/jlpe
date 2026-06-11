# syntax=docker/dockerfile:1

# Stage 1: CUDA devel for compile
FROM nvidia/cuda:12.9.2-devel-ubuntu24.04 AS lgbm-gpu-builder

ENV CUDA_HOME=/usr/local/cuda
ENV PATH=/usr/local/cuda/bin:${PATH}
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:${LD_LIBRARY_PATH}

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 python3-pip git \
        build-essential cmake ninja-build && \
    rm -rf /var/lib/apt/lists/*

ARG LIGHTGBM_VERSION=4.6.0
RUN git clone --recursive --branch v${LIGHTGBM_VERSION} --depth 1 \
    https://github.com/microsoft/LightGBM /lgbm-src

# scikit-build-core expects LICENSE next to python-package/pyproject.toml
RUN ln -s /lgbm-src/LICENSE /lgbm-src/python-package/LICENSE

# Build GPU wheel
RUN pip3 install --break-system-packages build && \
    cd /lgbm-src/python-package && \
    CMAKE_BUILD_PARALLEL_LEVEL=$(nproc) \
    CMAKE_ARGS="-DUSE_CUDA=ON -DCMAKE_CUDA_COMPILER=/usr/local/cuda/bin/nvcc" \
    python3 -m build --wheel \
        --config-setting "cmake.source-dir=.." \
        --outdir /lgbm-gpu-wheel/

# Verify CUDA in the resulting wheel
RUN python3 <<'EOF'
import zipfile, glob, sys
whl = glob.glob('/lgbm-gpu-wheel/lightgbm*.whl')[0]
print('Wheel:', whl)
with zipfile.ZipFile(whl) as z:
    so_files = [n for n in z.namelist() if n.endswith('.so')]
    print('SO files:', so_files)
    for so_name in so_files:
        data = z.read(so_name)
        if any(m in data for m in [b'CUDATreeLearner', b'cudaMemcpy', b'cudart']):
            print('OK: CUDA verified in', so_name)
            sys.exit(0)
    print('ERROR: CUDA not compiled in - recheck CMAKE_ARGS')
    sys.exit(1)
EOF

# Stage 2: JLPE runtime image
FROM python:3.13.13-slim-trixie AS jlpe-runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ENV POETRY_VENV=/opt/poetry/venv
ENV PATH="$POETRY_VENV/bin:$PATH"
ENV POETRY_CACHE_DIR=/opt/.cache
ENV POETRY_VIRTUALENVS_CREATE=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=0
ENV POETRY_VIRTUALENVS_PATH=/opt/project-venvs

ARG POETRY_VERSION=2.4.1

# Only ocl-icd-libopencl1 is new vs. the original - the ICD loader that
# at runtime discovers the driver injected by NVIDIA Container Runtime.
# No -dev packages, no CUDA, no driver binaries.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential libgomp1 git postgresql-client && \
    rm -rf /var/lib/apt/lists/*

RUN python -m venv $POETRY_VENV && \
    $POETRY_VENV/bin/pip install -U pip setuptools && \
    $POETRY_VENV/bin/pip install "poetry==$POETRY_VERSION"

WORKDIR /app
COPY pyproject.toml ./

RUN poetry install --no-root && rm -rf $POETRY_CACHE_DIR

# Copy only the CUDA runtime lib from builder
COPY --from=lgbm-gpu-builder /usr/local/cuda/lib64/libcudart.so* /usr/local/cuda/lib64/
COPY --from=lgbm-gpu-builder /usr/local/cuda/lib64/stubs/libcuda.so /usr/local/cuda/lib64/stubs/
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64

# Install GPU wheel from Stage 1
COPY --from=lgbm-gpu-builder /lgbm-gpu-wheel/ /tmp/lgbm-gpu-wheel/
RUN VENV_PATH=$(poetry env info --path) && \
    $VENV_PATH/bin/pip install --force-reinstall --no-deps \
        /tmp/lgbm-gpu-wheel/lightgbm*.whl && \
    rm -rf /tmp/lgbm-gpu-wheel/

EXPOSE 8888
ENTRYPOINT ["bash"]
