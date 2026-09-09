"""Smoke test for shap.

Computes SHAP values for a small random-forest model and checks the
output shape. Exercises the explainer -> model integration path, not just
the import.
"""

import numpy as np
from sklearn.ensemble import RandomForestRegressor
import shap


def main() -> None:
    X = np.random.rand(50, 4)
    y = X[:, 0] * 2 + X[:, 1]
    model = RandomForestRegressor(n_estimators=10, random_state=0).fit(X, y)

    explainer = shap.Explainer(model)
    values = explainer(X[:5])

    assert values.values.shape == (5, 4), f"unexpected shap output shape: {values.values.shape}"
    print("shap: OK")


if __name__ == "__main__":
    main()