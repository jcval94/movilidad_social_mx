import json
from pathlib import Path

import joblib
import pandas as pd


MODEL_PATH = Path("models/modelo_entrenado.joblib")


def run_class_inference(payload_json: str) -> dict:
    payload = json.loads(payload_json)
    data = payload.get("features", {})

    model = joblib.load(MODEL_PATH)
    df_usuario = pd.DataFrame([data])

    if hasattr(model, "feature_names_in_"):
        model_features = list(model.feature_names_in_)
    else:
        model_features = list(df_usuario.columns)

    for feat in model_features:
        if feat not in df_usuario.columns:
            df_usuario[feat] = 0
    df_usuario = df_usuario[model_features]

    if not hasattr(model, "predict_proba"):
        raise RuntimeError("El modelo no soporta predict_proba")

    probabilities = model.predict_proba(df_usuario)[0].tolist()
    classes = model.classes_.tolist()
    return {"probabilities": probabilities, "classes": classes}
