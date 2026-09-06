"""Minimal compatibility smoke test for statsforecast.

Exercises the real StatsForecast API end-to-end: instantiate a forecaster
with two models (AutoETS + a seasonal naive), fit on a long-format panel
with unique_id / ds / y columns, and forecast h steps ahead. The goal is
to catch resolution / ABI / pinned-deps breakage -- not to validate
forecast accuracy -- so the data is synthetic and assertions check shape
and finiteness, not exact values.
"""

import numpy as np
import pandas as pd
from statsforecast import StatsForecast
from statsforecast.models import AutoETS, SeasonalNaive


def make_panel(n_series: int, n_periods: int, season_length: int) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    rows = []
    for sid in range(n_series):
        base = rng.normal(0, 1, n_periods).cumsum() + sid
        seasonal = np.sin(np.arange(n_periods) * 2 * np.pi / season_length) * 2
        y = base + seasonal + rng.normal(0, 0.1, n_periods)
        for t in range(n_periods):
            rows.append((f"id_{sid:02d}", pd.Timestamp("2025-01-01") + pd.Timedelta(days=t), float(y[t])))
    return pd.DataFrame(rows, columns=["unique_id", "ds", "y"])


def main() -> None:
    season_length = 7
    df = make_panel(n_series=2, n_periods=season_length * 6, season_length=season_length)

    sf = StatsForecast(
        models=[AutoETS(season_length=season_length), SeasonalNaive(season_length=season_length)],
        freq="D",
        n_jobs=1,
    )

    sf.fit(df)
    h = season_length
    forecast = sf.predict(h=h)

    expected_ids = set(df["unique_id"].unique())
    forecast_ids = set(forecast["unique_id"].unique())
    assert forecast_ids == expected_ids, f"forecast ids mismatch: {forecast_ids} vs {expected_ids}"

    # AutoETS and SeasonalNaive each produce one forecast column.
    model_cols = [c for c in forecast.columns if c not in {"unique_id", "ds"}]
    assert len(model_cols) == 2, f"expected 2 model columns, got: {model_cols}"
    assert len(forecast) == h * len(expected_ids), f"unexpected forecast row count: {len(forecast)}"
    assert np.isfinite(forecast[model_cols].to_numpy()).all(), "forecast contains non-finite values"

    print(f"statsforecast: OK (forecasted h={h} for {len(expected_ids)} series, models={model_cols})")


if __name__ == "__main__":
    main()