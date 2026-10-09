"""Smoke test for tsfresh.

Extracts a minimal feature set from a synthetic time-series panel to
exercise the real feature-extraction code path, not just the import.
"""

import pandas as pd
from tsfresh import extract_features
from tsfresh.feature_extraction import MinimalFCParameters


def main() -> None:
    df = pd.DataFrame({
        "id": [1] * 10,
        "time": range(10),
        "value": [1, 2, 3, 4, 5, 4, 3, 2, 1, 0],
    })
    features = extract_features(
        df, column_id="id", column_sort="time",
        default_fc_parameters=MinimalFCParameters(),
        disable_progressbar=True,
        # Serial extraction on purpose. The default (n_jobs = cpu count)
        # routes through MultiprocessingDistributor, whose worker pool broke
        # on CPython 3.14: the default Linux start method changed from fork
        # to forkserver, and forkserver/spawn workers re-import __main__ by
        # path. This harness pipes the test via stdin (docker exec -i
        # python - < script), so __main__ lives at '<stdin>' and the worker
        # dies with FileNotFoundError trying to import '/app/<stdin>'
        # (seen on the migrate-python-3.14 PRs). Switching the start method
        # does not help: spawn re-imports __main__ the same way. n_jobs=1
        # selects tsfresh's MapDistributor, which still exercises the full
        # feature-extraction path (chunking, calculators, the pandas
        # round-trip) without any multiprocessing, matching the smoke
        # contract: deterministic, hermetic, API-surface integrity.
        n_jobs=1,
    )
    assert not features.empty
    print("tsfresh: OK")


if __name__ == "__main__":
    main()