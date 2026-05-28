from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier

from GCP.api.model_service import CLASS_LABELS, ModelService
from GCP.api.schemas import PredictRequest


def _write_model(path: Path) -> None:
    x = np.array(
        [
            [0, 0, 0],
            [1, 0, 0],
            [1, 1, 0],
            [1, 1, 1],
            [0, 1, 1],
        ]
    )
    y = np.array([1, 2, 3, 4, 5])
    model = RandomForestClassifier(n_estimators=20, random_state=7)
    model.fit(x, y)
    model.feature_names_in_ = np.array(["p126d", "p131", "p125d"])
    joblib.dump(model, path)


def test_predict_returns_probabilities_for_all_classes(tmp_path):
    model_path = tmp_path / "modelo.joblib"
    _write_model(model_path)
    service = ModelService(model_path)

    response = service.predict(PredictRequest(request_id="unit-test", features={"p126d": 1, "p131": 0}))

    assert response.request_id == "unit-test"
    assert response.predicted_label in set(CLASS_LABELS.values())
    assert response.feature_order == ["p126d", "p131", "p125d"]
    assert len(response.probabilities) == 5
    assert sum(item.probability for item in response.probabilities) == 1


def test_predict_rejects_unknown_features(tmp_path):
    model_path = tmp_path / "modelo.joblib"
    _write_model(model_path)
    service = ModelService(model_path)

    try:
        service.predict(PredictRequest(features={"no_existe": 1}))
    except Exception as exc:
        assert "Variables no reconocidas" in str(exc)
    else:
        raise AssertionError("Se esperaba error por variable desconocida")
