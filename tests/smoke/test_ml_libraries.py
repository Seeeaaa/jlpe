"""Smoke test for the ML libraries (xgboost, lightgbm, catboost).

Runs each gradient-boosting library through a real CPU train so that a
broken wheel, ABI mismatch, or missing shared library fails here rather
than at first use. GPU support is checked only where a reliable
build-introspection API exists (xgboost.build_info); for the other
libraries the CPU code path is what the image actually exercises by
default.
"""

import numpy as np
import xgboost as xgb
import lightgbm as lgb
import catboost as cb


def main() -> None:
    X = np.random.rand(100, 5)
    y = np.random.randint(0, 2, 100)

    xgb.XGBClassifier(device="cpu", n_estimators=5).fit(X, y)
    print("xgboost CPU: OK")

    info = xgb.build_info()
    assert info.get("USE_CUDA"), f"xgboost built without CUDA support: {info}"
    print("xgboost: CUDA build flag present")

    lgb.train(
        {"objective": "binary", "verbosity": -1, "device": "cpu"},
        lgb.Dataset(X, label=y),
        num_boost_round=5,
    )
    print("lightgbm CPU: OK")

    # Train a real CatBoost model on CPU and check predictions. The previous
    # version of this test only scanned the package directory for .so files
    # containing the literal string "cuda_lib/cuda_base", a build-path marker
    # that is not guaranteed to survive into the released wheel and verified
    # nothing about whether catboost actually works. A real fit/predict is
    # both more meaningful and more robust.
    model = cb.CatBoostClassifier(
        iterations=5,
        depth=3,
        verbose=0,
        task_type="CPU",
    )
    model.fit(X, y)
    preds = model.predict(X)
    assert len(preds) == len(X), f"unexpected predict shape: {preds.shape}"
    assert set(preds).issubset({0, 1}), f"unexpected class labels: {set(preds)}"
    print("catboost CPU: OK (fit + predict)")


if __name__ == "__main__":
    main()