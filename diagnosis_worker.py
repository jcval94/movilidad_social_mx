import json
import time
import warnings
from pathlib import Path

import joblib
import pandas as pd
from sklearn.exceptions import InconsistentVersionWarning
from sklearn.impute import SimpleImputer
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from llm.gemini_explainer import generate_explanation
from utils.diccionarios import get_data_desc, get_nuevo_diccionario
from utils.func_s4 import construir_descripciones_cluster

BASE_PATH = Path("data")
EXCLUDED_IMPORTANCE_VARS = {"p133", "CIUO2", "p23"}
BASE_QUESTIONS = ["p05", "p86", "p33_f"]


def load_assets(base_path: str = "data"):
    base = Path(base_path)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=InconsistentVersionWarning)
        return {
            "df_valiosas_dict": joblib.load(base / "df_valiosas_dict.joblib"),
            "df_feature_importances_total": joblib.load(base / "df_feature_importances_total.joblib"),
            "df_clusterizados_total_origi": pd.read_csv(base / "df_clusterizados_total_origi.csv"),
        }


def build_cluster_target_frame(df_cluster, user_selected_target):
    prefix = f"{user_selected_target}_"
    rename_map = {
        col: col.replace(prefix, "")
        for col in df_cluster.columns
        if col.startswith(prefix)
    }
    return df_cluster.rename(columns=rename_map)


def obtener_vecinos_de_mi_respuesta(df_respuestas, df_datos_clusterizados, df_datos_descript_valiosas, n_vecinos=20):
    datos_validos = df_datos_clusterizados[df_datos_clusterizados["cluster"] != -1].copy()

    variables_usuario = df_respuestas["variable"].tolist()
    variables_usuario = [v for v in variables_usuario if v in datos_validos.columns]
    if not variables_usuario:
        return df_datos_descript_valiosas.iloc[0:0].copy()

    respuesta_usuario = df_respuestas.set_index("variable")["respuesta_codigo"].to_dict()
    user_vector = pd.Series(respuesta_usuario, index=variables_usuario).values.reshape(1, -1)
    X = datos_validos[variables_usuario].values

    imputer = SimpleImputer(strategy="mean")
    X = imputer.fit_transform(X)
    user_vector = imputer.transform(user_vector)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    user_vector_scaled = scaler.transform(user_vector)

    knn = NearestNeighbors(n_neighbors=n_vecinos, metric="euclidean")
    knn.fit(X_scaled)
    distances, indices = knn.kneighbors(user_vector_scaled)

    vecinos = datos_validos.iloc[indices[0]].copy()
    vecinos["distancia"] = distances[0]

    df_clusters = vecinos["cluster"].value_counts().reset_index()
    df_clusters.columns = ["cluster", "count"]

    return df_datos_descript_valiosas.merge(df_clusters, on="cluster", how="inner").sort_values(
        by="count", ascending=False
    )


def filter_cluster_results(df):
    required = ["cambio_yo_moderado", "cambio_yo_difícil", "cambio_yo_fácil", "nivel_de_confianza_cluster"]
    if not all(col in df.columns for col in required):
        return df
    return df[
        (
            (df["cambio_yo_moderado"] > 0)
            | (df["cambio_yo_difícil"] > 0)
            | (df["cambio_yo_fácil"] > 0)
        )
        & (df["nivel_de_confianza_cluster"] > 0)
    ]


def get_question_pool(df_feature_import, user_selected_target):
    top_vars = [
        x.split("-")[0].strip()
        for x in df_feature_import[f"{user_selected_target}_importance"].sort_values(ascending=False).index
    ][:7]
    top_vars = [x for x in top_vars if x not in EXCLUDED_IMPORTANCE_VARS]
    return sorted(set(BASE_QUESTIONS + top_vars))



def parse_cluster_description(raw_desc):
    lines = raw_desc.split("\n")
    summary_data = {}
    var_blocks = []
    current_block = []
    in_variables_section = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- Variables y rangos:"):
            in_variables_section = True
            continue

        if not in_variables_section:
            if stripped.startswith("- Incremento de probabilidad") or stripped.startswith("- Incremento respecto a la población"):
                try:
                    incremento = float(stripped.split(":", 1)[1].strip())
                    diff_percent = (incremento - 1.0) * 100
                    summary_data["incremento"] = {"text": f"{diff_percent:+.0f}%"}
                except Exception:
                    summary_data["incremento"] = {"text": stripped}
            elif stripped.startswith("- Probabilidad:") or stripped.startswith("- Probabilidad final de cambiar de clase:"):
                summary_data["probabilidad"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("- Nivel de confianza"):
                conf_val = stripped.split(":", 1)[1].strip()
                summary_data["confianza"] = conf_val.split("(", 1)[0].strip()
                summary_data["obs"] = conf_val
            continue

        if stripped.startswith("- Variable:"):
            if current_block:
                var_blocks.append(current_block)
            current_block = [stripped]
        elif current_block:
            current_block.append(stripped)

    if current_block:
        var_blocks.append(current_block)

    variables = []
    for block in var_blocks:
        var_info = {}
        for line in block:
            if line.startswith("- Descripción:"):
                var_info["descripcion"] = line.split(":", 1)[1].strip()
            elif line.startswith("- Categorías en rango:"):
                var_info["categorias"] = line.split(":", 1)[1].strip()
            elif line.startswith("- ¿Puedo cambiarlo yo?:"):
                var_info["change_level"] = line.split(":", 1)[1].strip()
            elif line.startswith("- Involucrados:"):
                var_info["involucrados"] = line.split(":", 1)[1].strip()
            elif line.startswith("- Recursos:"):
                var_info["recursos"] = line.split(":", 1)[1].strip()
        if "descripcion" in var_info and "categorias" in var_info:
            variables.append(var_info)

    return {"summary": summary_data, "variables": variables}


def group_clusters_by_variables(parsed_clusters):
    grouped = {}
    for cluster_name, cluster_data in parsed_clusters.items():
        signature = tuple((v.get("descripcion", ""), v.get("categorias", "")) for v in cluster_data.get("variables", []))
        if signature not in grouped:
            grouped[signature] = {"variables": cluster_data.get("variables", []), "scenarios": []}
        grouped[signature]["scenarios"].append({"nombre": str(cluster_name), "summary": cluster_data.get("summary", {})})
    return list(grouped.values())


def format_all_clusters(resultado):
    parsed_clusters = {cluster_id: parse_cluster_description(desc) for cluster_id, desc in resultado.items()}
    return group_clusters_by_variables(parsed_clusters)

def compute_diagnosis(payload_json: str) -> dict:
    payload = json.loads(payload_json)
    target = payload["target"]
    df_respuestas = pd.DataFrame(payload["questionnaire"])

    assets = load_assets(str(BASE_PATH))
    data_desc_global = get_data_desc()

    timings = {}

    t0 = time.perf_counter()
    df_cluster_target = build_cluster_target_frame(assets["df_clusterizados_total_origi"], target)
    _ = get_question_pool(assets["df_feature_importances_total"], target)
    timings["prepare_data_s"] = round(time.perf_counter() - t0, 3)

    t1 = time.perf_counter()
    df_valiosas = assets["df_valiosas_dict"][target]
    df_resultados = obtener_vecinos_de_mi_respuesta(df_respuestas, df_cluster_target, df_valiosas, n_vecinos=50)
    if not df_resultados.empty and "cluster_N_Proba" in df_resultados.columns:
        df_resultados["nivel_de_confianza_cluster"] = pd.qcut(
            df_resultados["cluster_N_Proba"],
            q=4,
            labels=False,
            duplicates="drop",
        )
    df_filtrado = filter_cluster_results(df_resultados)
    timings["nearest_neighbors_s"] = round(time.perf_counter() - t1, 3)

    t2 = time.perf_counter()
    resultado = construir_descripciones_cluster(
        df_filtrado,
        data_desc_global,
        get_nuevo_diccionario(),
        language="es",
        show_N_probabilidad=True,
        show_Probabilidad=True,
    )
    timings["cluster_descriptions_s"] = round(time.perf_counter() - t2, 3)

    grouped_results = format_all_clusters(resultado)

    worker_debug = {
        "question_count": int(len(df_respuestas)),
        "neighbors_rows": int(len(df_resultados)),
        "filtered_rows": int(len(df_filtrado)),
        "cluster_groups": int(len(grouped_results)),
    }

    t3 = time.perf_counter()
    payload_with_results = {**payload, "results": grouped_results}
    explanation = generate_explanation(payload_with_results)
    timings["llm_explanation_s"] = round(time.perf_counter() - t3, 3)

    slow_actions = [name for name, duration in timings.items() if duration > 1.5]

    return {
        "grouped_results": grouped_results,
        "explanation": explanation,
        "timings": timings,
        "slow_actions": slow_actions,
        "worker_debug": worker_debug,
    }
