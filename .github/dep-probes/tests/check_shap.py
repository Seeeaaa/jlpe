"""Minimal compatibility smoke test for shap.

Not a coverage test: resolution succeeding does not guarantee shap actually
runs against the currently pinned numpy/scikit-learn, so this exercises the
one code path that matters most - building an explainer and getting values
back in the expected shape.
"""

import numpy as np
from sklearn.ensemble import RandomForestRegressor
import shap

X = np.random.rand(50, 4)
y = X[:, 0] * 2 + X[:, 1]
model = RandomForestRegressor(n_estimators=10, random_state=0).fit(X, y)

explainer = shap.Explainer(model)
values = explainer(X[:5])

assert values.values.shape == (
    5,
    4,
), f"unexpected shap output shape: {values.values.shape}"
print("shap: OK")
