"""Smoke test for the data-processing stack.

Exercises the real pandas -> pyarrow -> duckdb interop path, the
polars -> pyarrow -> duckdb path, geopandas geometry construction, and
psycopg import. The assertions check actual computed values, not bare
imports, so a broken wheel or ABI mismatch fails here rather than at
first use in a notebook.
"""

import geopandas as gpd
import numpy as np
import pandas as pd
import polars as pl
import pyarrow as pa
import duckdb
import psycopg


def main() -> None:
    df = pd.DataFrame({"a": [1, 2, 3], "b": [4.0, 5.0, 6.0]})

    arrow_tbl = pa.Table.from_pandas(df)
    result = duckdb.sql("select sum(a) from arrow_tbl").fetchone()
    assert result[0] == 6, f"unexpected duckdb result: {result}"
    print("pandas -> pyarrow -> duckdb: OK")

    pl_df = pl.from_pandas(df)
    pl_arrow = pl_df.to_arrow()
    result_pl = duckdb.sql("select sum(a) from pl_arrow").fetchone()
    assert result_pl[0] == 6, f"unexpected polars/duckdb result: {result_pl}"
    print("pandas -> polars -> pyarrow -> duckdb: OK")

    gdf = gpd.GeoDataFrame({"geometry": gpd.points_from_xy([0, 1], [0, 1])})
    assert len(gdf) == 2
    print("geopandas: OK")

    print("psycopg import: OK")


if __name__ == "__main__":
    main()