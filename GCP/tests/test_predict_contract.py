import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from GCP.api.main import app, get_model_service
from GCP.api.schemas import PredictResponse, Probability


class StubModelService:
    def readiness(self):
        return {"status": "ready", "model_version": "stub", "features": 2}

    def predict(self, request):
        return PredictResponse(
            request_id=request.request_id,
            predicted_class=3,
            predicted_label="Media Baja",
            predicted_probability=0.7,
            probabilities=[
                Probability(class_id=1, label="Baja Baja", probability=0.3),
                Probability(class_id=3, label="Media Baja", probability=0.7),
            ],
            model_version="stub",
            feature_order=["p126d", "p131"],
        )


def test_health_and_ready_contract():
    app.dependency_overrides[get_model_service] = lambda: StubModelService()
    client = TestClient(app)

    health = client.get("/healthz")
    ready = client.get("/readyz")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert ready.status_code == 200
    assert ready.json() == {"status": "ready", "model_version": "stub", "features": 2}
    app.dependency_overrides.clear()


def test_predict_contract():
    app.dependency_overrides[get_model_service] = lambda: StubModelService()
    client = TestClient(app)

    response = client.post("/v1/predict", json={"request_id": "contract-1", "features": {"p126d": 1, "p131": 0}})

    assert response.status_code == 200
    payload = response.json()
    assert payload["request_id"] == "contract-1"
    assert payload["predicted_label"] == "Media Baja"
    assert payload["predicted_probability"] == 0.7
    assert payload["model_version"] == "stub"
    assert payload["feature_order"] == ["p126d", "p131"]
    assert payload["probabilities"][0] == {"class_id": 1, "label": "Baja Baja", "probability": 0.3}
    app.dependency_overrides.clear()


def test_predict_rejects_extra_top_level_fields():
    client = TestClient(app)
    response = client.post("/v1/predict", json={"features": {"p126d": 1}, "unexpected": True})

    assert response.status_code == 422
    assert response.json()["error"] == "validation_error"
