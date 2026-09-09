"""Smoke test for narwhals.

Narwhals is a dependency-free compatibility layer over dataframe
libraries. The meaningful check here is a round-trip through the native
backends already pinned in the image (pandas and polars): wrap a
DataFrame with nw.from_native, run a dataframe-agnostic expression that
would break on a version/API mismatch, and unwrap with to_native. A bare
import would catch nothing, since narwhals has no compiled extensions;
it only breaks at the API boundary against a specific backend version.
"""

import pandas as pd
import polars as pl
import narwhals as nw


def add_category(df_native):
    # Dataframe-agnostic operation exercised against both pandas and polars.
    return (
        nw.from_native(df_native)
        .with_columns(
            category=nw.when(nw.col("value") > 10)
            .then(nw.lit("high"))
            .otherwise(nw.lit("low"))
        )
        .to_native()
    )


def main() -> None:
    pdf = pd.DataFrame({"name": ["a", "b", "c"], "value": [1, 15, 8]})

    # pandas round-trip
    out_pd = add_category(pdf)
    assert isinstance(out_pd, pd.DataFrame), f"expected pandas DataFrame, got {type(out_pd)}"
    assert set(out_pd["category"]) == {"high", "low"}, f"unexpected categories: {set(out_pd['category'])}"
    print("narwhals: OK (pandas round-trip)")

    # polars round-trip, same agnostic function
    pldf = pl.DataFrame({"name": ["a", "b", "c"], "value": [1, 15, 8]})
    out_pl = add_category(pldf)
    assert isinstance(out_pl, pl.DataFrame), f"expected polars DataFrame, got {type(out_pl)}"
    assert set(out_pl["category"].to_list()) == {"high", "low"}, "unexpected categories via polars"
    print("narwhals: OK (polars round-trip)")


if __name__ == "__main__":
    main()