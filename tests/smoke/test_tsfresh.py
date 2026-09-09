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
    )
    assert not features.empty
    print("tsfresh: OK")


if __name__ == "__main__":
    main()