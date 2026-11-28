"""Smoke test for scipy, sklearn, statsmodels, optuna, sqlalchemy, dask.

Each library is exercised through a real computation rather than a bare
import, because the failure mode that matters is a broken compiled
extension (BLAS/LAPACK bindings, Cython estimator code, a drifted
transitive dependency), not a missing module name.
"""

import numpy as np
import pandas as pd
import scipy
import scipy.linalg
import sklearn
from sklearn.linear_model import LinearRegression
import statsmodels
import statsmodels.api as sm
import optuna
from sqlalchemy import create_engine
import dask.dataframe as dd


def main() -> None:
    # scipy: invert a small well-conditioned matrix -- this exercises the
    # BLAS/LAPACK bindings, which is where scipy installs most often break
    # (wrong wheel, missing shared libs), unlike a bare import
    a = np.array([[3.0, 1.0], [1.0, 2.0]])
    inv_a = scipy.linalg.inv(a)
    assert np.allclose(a @ inv_a, np.eye(2), atol=1e-8)
    print(f"scipy {scipy.__version__}: OK (linalg.inv)")

    # sklearn: fit a trivial linear model -- exercises the Cython-compiled
    # estimator code, not just the pure-Python package layer
    X = np.array([[1.0], [2.0], [3.0], [4.0]])
    y = np.array([2.0, 4.0, 6.0, 8.0])
    model = LinearRegression().fit(X, y)
    assert abs(model.coef_[0] - 2.0) < 1e-6
    print(f"sklearn {sklearn.__version__}: OK (LinearRegression fit)")

    # statsmodels: fit OLS on a trivial dataset and check the recovered slope
    X_sm = sm.add_constant(np.array([1.0, 2.0, 3.0, 4.0]))
    result = sm.OLS(y, X_sm).fit()
    assert abs(result.params[1] - 2.0) < 1e-6
    print(f"statsmodels {statsmodels.__version__}: OK (OLS fit)")

    # optuna: exercise study execution without asserting optimizer quality.
    # A seeded sampler makes the trial sequence reproducible; trial count and
    # finiteness checks avoid a probabilistic convergence threshold.
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    def objective(trial):
        x = trial.suggest_float("x", -10, 10)
        return (x - 2) ** 2

    sampler = optuna.samplers.TPESampler(seed=10)
    study = optuna.create_study(sampler=sampler)
    study.optimize(objective, n_trials=20)
    assert len(study.trials) == 20
    assert np.isfinite(study.best_value)
    print(f"optuna {optuna.__version__}: OK (20 deterministic trials)")

    # dask pulls a large dependency tree that can silently break against
    # pinned pandas/numpy versions, so this executes a real computation
    # instead of just importing
    ddf = dd.from_pandas(pd.DataFrame({"a": [1, 2, 3]}), npartitions=1)
    assert ddf["a"].sum().compute() == 6
    print("dask: OK")

    # create_engine does not open a connection, it only validates
    # that the psycopg driver is registered and importable via sqlalchemy
    create_engine("postgresql+psycopg://")
    print("sqlalchemy + psycopg driver: OK")


if __name__ == "__main__":
    main()