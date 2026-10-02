"""Smoke test for the apt-layer system tools.

The apt layer installs git, postgresql-client, and libgomp1 on top of the
dependency layers. The meaningful check here is that the apt-layer content
is present at runtime: the two tool binaries resolve on PATH and the
OpenMP runtime shared object loads by soname. Network-free and
deterministic: filesystem and loader checks only, no live requests, no
apt calls (apt data changes daily by design via the APT_BUST cache-bust).
"""

import ctypes
import shutil


def main() -> None:
    # git: installed by the apt layer, used at runtime by nb-clean and
    # notebook commit workflows.
    git = shutil.which("git")
    assert git, "git not found on PATH (apt layer content missing?)"
    print("system tools: git OK (%s)" % git)

    # psql: postgresql-client's binary, installed by the apt layer.
    psql = shutil.which("psql")
    assert psql, "psql not found on PATH (postgresql-client missing?)"
    print("system tools: psql OK (%s)" % psql)

    # libgomp1: the runtime OpenMP library required by lightgbm's
    # lib_lightgbm.so and numba's parallel threading layer. Loading it by
    # soname proves the shared object exists and its dependencies
    # (gcc-14-base, libc6) resolve through the loader.
    try:
        ctypes.CDLL("libgomp.so.1")
    except OSError as e:
        raise AssertionError("libgomp.so.1 failed to load: %s" % e)
    print("system tools: libgomp OK (libgomp.so.1 loadable)")


if __name__ == "__main__":
    main()
