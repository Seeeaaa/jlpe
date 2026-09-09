"""Smoke test for prophet.

Fits a Prophet model on a trivial 30-day series and produces a 5-step
forecast, exercising the full fit -> predict path.
"""

import pandas as pd
from prophet import Prophet


def main() -> None:
    df = pd.DataFrame({
        "ds": pd.date_range("2026-01-01", periods=30),
        "y": range(30),
    })
    model = Prophet()
    model.fit(df)
    forecast = model.predict(df.tail(5))
    assert len(forecast) == 5
    print("prophet: OK")


if __name__ == "__main__":
    main()