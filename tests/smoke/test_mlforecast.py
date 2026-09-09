"""Minimal compatibility smoke test for mlforecast.

Exercises the real MLForecast API end-to-end: instantiate a forecaster
with two sklearn-compatible models (LinearRegression + a lightgbm-style
booster if available, falling back to a second linear model), fit on a
long-format panel with lags + rolling features, and forecast h steps ahead.
Like check_statsforecast.py, the goal is to catch resolution / ABI /
pinned-deps breakage, not to validate forecast accuracy, so assertions
check shape and finiteness against a synthetic dataset.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from mlforecast import MLForecast
from mlforecast.lag_transforms import ExpandingMean


def make_panel(n_series: int, n_periods: int) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    rows = []
    for sid in range(n_series):
        base = rng.normal(0, 1, n_periods).cumsum() + sid
        y = base + rng.normal(0, 0.1, n_periods)
        for t in range(n_periods):
            rows.append((f"id_{sid:02d}", pd.Timestamp("2025-01-01") + pd.Timedelta(days=t), float(y[t])))
    return pd.DataFrame(rows, columns=["unique_id", "ds", "y"])


def main() -> None:
    df = make_panel(n_series=2, n_periods=60)

    models = [LinearRegression(), LinearRegression()]
    # lag_transforms must be mlforecast's own transform objects (or an
    # @njit-wrapped function), not a raw numpy ufunc: mlforecast applies
    # transforms inside a numba nopython block, and np.mean is a NumPy 2
    # _ArrayFunctionDispatcher that numba cannot type (np.mean would raise
    # "Cannot determine Numba type of numpy._ArrayFunctionDispatcher").
    mlf = MLForecast(models=models, freq="D", lags=[1, 7], lag_transforms={1: [ExpandingMean()]})
    mlf.fit(df)

    h = 5
    forecast = mlf.predict(h=h)

    expected_ids = set(df["unique_id"].unique())
    forecast_ids = set(forecast["unique_id"].unique())
    assert forecast_ids == expected_ids, f"forecast ids mismatch: {forecast_ids} vs {expected_ids}"
    assert len(forecast) == h * len(expected_ids), f"unexpected forecast row count: {len(forecast)}"

    # mlforecast prefixes each model prediction with the model class name; two
    # LinearRegression models produce two distinct prediction columns.
    pred_cols = [c for c in forecast.columns if c not in {"unique_id", "ds"}]
    assert len(pred_cols) == 2, f"expected 2 prediction columns, got: {pred_cols}"
    assert np.isfinite(forecast[pred_cols].to_numpy()).all(), "forecast contains non-finite values"

    print(f"mlforecast: OK (forecasted h={h} for {len(expected_ids)} series, models={pred_cols})")


if __name__ == "__main__":
    main()