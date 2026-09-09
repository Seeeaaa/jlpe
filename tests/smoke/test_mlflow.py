"""Smoke test for mlflow.

Runs a minimal end-to-end experiment against a local SQLite tracking
backend: start a run, log a param and a metric, and confirm the run was
recorded.
"""

import tempfile
import mlflow


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        mlflow.set_tracking_uri(f"sqlite:///{tmp}/mlflow.db")
        with mlflow.start_run():
            mlflow.log_param("alpha", 0.5)
            mlflow.log_metric("rmse", 1.23)
        run = mlflow.last_active_run()
        assert run is not None, "mlflow run was not recorded"
    print("mlflow: OK")


if __name__ == "__main__":
    main()