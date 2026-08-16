"""Minimal compatibility smoke test for mlflow."""

import tempfile
import mlflow

with tempfile.TemporaryDirectory() as tmp:
    mlflow.set_tracking_uri(f"file:{tmp}")
    with mlflow.start_run():
        mlflow.log_param("alpha", 0.5)
        mlflow.log_metric("rmse", 1.23)

    run = mlflow.last_active_run()
    assert run is not None, "mlflow run was not recorded"
    print("mlflow: OK")
