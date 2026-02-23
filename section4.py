import re
from pathlib import Path
from textwrap import dedent

import joblib
import numpy as np
import pandas as pd
import streamlit as st
from sklearn.impute import SimpleImputer
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from utils.diccionarios import get_data_desc, get_nuevo_diccionario
from utils.func_s4 import construir_descripciones_cluster

BASE_PATH = Path("data")
TARGET_LABELS = {
    "OBJ_pobre_a_rico": "De Pobre a Rico",
    "OBJ_rico_a_pobre": "De Rico a Pobre",
    "OBJ_siguie_siendo_rico": "Permanece Rico",
    "OBJ_siguie_siendo_pobre": "Permanece Pobre",
    "OBJ_sigue_siendo_clase_media": "Permanece Clase Media",
    "OBJ_clase_media_a_rico": "De Clase Media a Rico",
    "OBJ_clase_media_a_pobre": "De Clase Media a Pobre",
    "OBJ_subieron": "Ascendieron",
    "OBJ_bajaron": "Descendieron",
}
EXCLUDED_IMPORTANCE_VARS = {"p133", "CIUO2", "p23"}
BASE_QUESTIONS = ["p05", "p86", "p33_f"]


@st.cache_resource(show_spinner=False)
def load_section4_assets(base_path: str = "data"):
    base = Path(base_path)
    return {
        "df_valiosas_dict": joblib.load(base / "df_valiosas_dict.joblib"),
        "df_feature_importances_total": joblib.load(base / "df_feature_importances_total.joblib"),
        "df_clusterizados_total_origi": pd.read_csv(base / "df_clusterizados_total_origi.csv"),
    }


def generar_lista_preguntas(data_desc):
    preguntas = []
    for var, info in data_desc.items():
        desc = info.get("Descripción", var)
        vals = info.get("Valores", [])
        etiq = info.get("Etiquetas", [])
        if vals and etiq and len(vals) == len(etiq):
            preguntas.append(
                {
                    "variable": var,
                    "descripcion": desc,
                    "tipo": "opciones",
                    "opciones": dict(zip(vals, etiq)),
                }
            )
        else:
            preguntas.append({"variable": var, "descripcion": desc, "tipo": "numeric"})
    return preguntas


def preguntar_opciones_streamlit(i, variable, descripcion, opciones):
    key_uid = f"opt_{variable}_{i}"
    st.write(f"**{variable}**: {descripcion}")
    lista = [f"{k} - {v}" for k, v in opciones.items()]
    sel = st.selectbox("", lista, key=key_uid, label_visibility="collapsed")
    cod = int(sel.split(" - ")[0])
    return cod, opciones[cod]


def preguntar_numero_streamlit(i, variable, descripcion):
    key_uid = f"num_{variable}_{i}"
    st.write(f"**{variable}**: {descripcion}")
    val = st.number_input("", value=0.0, step=1.0, key=key_uid, label_visibility="collapsed")
    return val, str(val)


def aplicar_cuestionario_en_columnas(preguntas, cols_per_row=3):
    respuestas = []
    for i in range(0, len(preguntas), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(preguntas):
                continue
            pregunta = preguntas[idx]
            with col:
                if pregunta["tipo"] == "opciones":
                    rcod, rtxt = preguntar_opciones_streamlit(
                        idx,
                        pregunta["variable"],
                        pregunta["descripcion"],
                        pregunta["opciones"],
                    )
                else:
                    rcod, rtxt = preguntar_numero_streamlit(
                        idx,
                        pregunta["variable"],
                        pregunta["descripcion"],
                    )
            respuestas.append(
                {
                    "variable": pregunta["variable"],
                    "descripcion": pregunta["descripcion"],
                    "respuesta_codigo": rcod,
                    "respuesta_texto": rtxt,
                }
            )
    return pd.DataFrame(respuestas)


def cuestionario_general(data_desc, cols_per_row=3):
    preguntas = generar_lista_preguntas(data_desc)
    return aplicar_cuestionario_en_columnas(preguntas, cols_per_row)


def build_cluster_target_frame(df_cluster, user_selected_target):
    prefix = f"{user_selected_target}_"
    rename_map = {
        col: col.replace(prefix, "")
        for col in df_cluster.columns
        if col.startswith(prefix)
    }
    return df_cluster.rename(columns=rename_map)


def get_question_pool(df_feature_import, user_selected_target):
    top_vars = [
        x.split("-")[0].strip()
        for x in df_feature_import[f"{user_selected_target}_importance"]
        .sort_values(ascending=False)
        .index
    ][:7]
    top_vars = [x for x in top_vars if x not in EXCLUDED_IMPORTANCE_VARS]
    return sorted(set(BASE_QUESTIONS + top_vars))


def obtener_vecinos_de_mi_respuesta(
    df_respuestas,
    df_datos_clusterizados,
    df_datos_descript_valiosas,
    n_vecinos=20,
):
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


def get_color_for_increment(diff):
    min_diff, max_diff = -0.5, 0.5
    clamped = max(min_diff, min(max_diff, diff))
    ratio = (clamped - min_diff) / (max_diff - min_diff)
    r = int((1 - ratio) * 255)
    g = int(ratio * 255)
    return f"#{r:02x}{g:02x}00"


def map_confidence(value):
    try:
        val = float(value)
    except Exception:
        return value
    if val <= 0:
        return "Baja"
    if val == 1:
        return "Media"
    if val == 2:
        return "Alta"
    return "Muy Alta"


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
            if stripped.startswith("- Incremento de probabilidad"):
                try:
                    incremento = float(stripped.split(":", 1)[1].strip())
                    diff_percent = (incremento - 1.0) * 100
                    summary_data["incremento"] = {
                        "text": f"{diff_percent:+.0f}%",
                        "color": get_color_for_increment(incremento - 1.0),
                    }
                except Exception:
                    summary_data["incremento"] = {"text": stripped, "color": "#666666"}
            elif stripped.startswith("- Probabilidad:"):
                summary_data["probabilidad"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("- Nivel de confianza"):
                conf_val = stripped.split(":", 1)[1].strip()
                summary_data["confianza"] = map_confidence(conf_val)
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
        extra_props = []
        for line in block:
            if line.startswith("- Descripción:"):
                var_info["descripcion"] = line.split(":", 1)[1].strip()
            elif line.startswith("- Categorías en rango:"):
                cat_values = []
                for part in line.split(":", 1)[1].strip().split(","):
                    if "=" in part:
                        cat_values.append(part.split("=", 1)[1].strip())
                var_info["categorias"] = ", ".join(cat_values)
            elif line.startswith("- ¿Puedo cambiarlo yo?:"):
                val = line.split(":", 1)[1].strip()
                if val.lower() != "no_aplica":
                    extra_props.append(f"¿Puedo cambiarlo yo?: {val}")
            elif line.startswith("- Involucrados:"):
                extra_props.append(f"Involucrados: {line.split(':', 1)[1].strip()}")
            elif line.startswith("- Recursos:"):
                val = line.split(":", 1)[1].strip()
                if val.lower() != "no_aplica":
                    extra_props.append(f"Recursos: {val}")

        if "descripcion" in var_info and "categorias" in var_info:
            variables.append(
                {
                    "descripcion": var_info["descripcion"],
                    "categorias": var_info["categorias"],
                    "extras": extra_props,
                }
            )

    return {"summary": summary_data, "variables": variables}


def normalize_variable_signature(variables):
    signature_items = []
    for item in variables:
        signature_items.append(
            (
                item.get("descripcion", ""),
                item.get("categorias", ""),
                tuple(item.get("extras", [])),
            )
        )
    return tuple(signature_items)


def group_clusters_by_variables(parsed_clusters):
    grouped = {}
    for cluster_name, cluster_data in parsed_clusters.items():
        signature = normalize_variable_signature(cluster_data.get("variables", []))
        if signature not in grouped:
            grouped[signature] = {
                "variables": cluster_data.get("variables", []),
                "scenarios": [],
            }
        grouped[signature]["scenarios"].append(
            {
                "nombre": str(cluster_name),
                "summary": cluster_data.get("summary", {}),
            }
        )
    return list(grouped.values())


def render_variables_column(variables):
    if not variables:
        return "<p style='margin:0;color:#6b7280'>No se encontraron variables clave.</p>"

    variables_html = ""
    for item in variables:
        extras_html = "".join(
            f"<li style='margin-top:4px;color:#4b5563;font-size:0.9rem'>{extra}</li>"
            for extra in item.get("extras", [])
        )
        variables_html += (
            "<li style='margin-bottom:10px'>"
            f"<strong>{item.get('descripcion', 'Variable')}</strong><br>"
            f"<span style='color:#374151'>{item.get('categorias', 'N/D')}</span>"
            f"<ul style='margin-top:5px'>{extras_html}</ul>"
            "</li>"
        )
    return f"<ul style='margin:0 0 0 18px;padding:0'>{variables_html}</ul>"


def format_grouped_scenarios_card(group_idx, group_data):
    scenario_cols = ""
    for scenario in group_data.get("scenarios", []):
        summary = scenario.get("summary", {})
        incremento = summary.get("incremento", {"text": "N/D", "color": "#666666"})
        probabilidad = summary.get("probabilidad", "N/D")
        confianza = summary.get("confianza", "N/D")

        scenario_cols += f"""
        <div style="min-width:160px;border-left:1px solid #e5e7eb;padding-left:12px;padding-right:8px">
          <div style="font-size:0.82rem;color:#6b7280;margin-bottom:8px">Escenario {scenario.get('nombre')}</div>
          <div style="font-size:0.82rem;color:#6b7280">Incremento</div>
          <div style="font-weight:700;color:{incremento.get('color', '#666666')};margin-bottom:8px">{incremento.get('text', 'N/D')}</div>
          <div style="font-size:0.82rem;color:#6b7280">Probabilidad</div>
          <div style="font-weight:700;margin-bottom:8px">{probabilidad}</div>
          <div style="font-size:0.82rem;color:#6b7280">Confianza</div>
          <div style="font-weight:700">{confianza}</div>
        </div>
        """

    return dedent(
        f"""
        <div style="border:1px solid #e5e7eb;border-radius:12px;padding:14px;margin-bottom:14px;background:#fff;box-shadow:0 1px 2px rgba(0,0,0,0.05)">
          <div style="font-weight:700;margin-bottom:10px;color:#111827">Grupo de Variables Clave #{group_idx}</div>
          <div style="display:flex;align-items:flex-start;gap:12px;overflow-x:auto">
            <div style="min-width:420px;max-width:520px;padding-right:10px">
              <div style="font-size:0.86rem;color:#6b7280;margin-bottom:6px">Variables Clave (identificador)</div>
              {render_variables_column(group_data.get('variables', []))}
            </div>
            {scenario_cols}
          </div>
        </div>
        """
    ).strip()


def format_all_clusters(resultado):
    parsed_clusters = {cluster_id: parse_cluster_description(desc) for cluster_id, desc in resultado.items()}
    return group_clusters_by_variables(parsed_clusters)


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


def show_section4():
    assets = load_section4_assets(str(BASE_PATH))

    targets = list(assets["df_valiosas_dict"].keys())
    opciones = [(valor, TARGET_LABELS.get(valor, valor)) for valor in targets]
    retorno_user = st.selectbox("Target", options=opciones, format_func=lambda x: x[1])
    user_selected_target = retorno_user[0]

    df_cluster_target = build_cluster_target_frame(
        assets["df_clusterizados_total_origi"],
        user_selected_target,
    )

    preguntas_lista = get_question_pool(
        assets["df_feature_importances_total"],
        user_selected_target,
    )
    data_desc_global = get_data_desc()
    data_desc_usable = {k: data_desc_global[k] for k in preguntas_lista if k in data_desc_global}

    with st.form("cuestionario_form"):
        df_respuestas = cuestionario_general(data_desc_usable, cols_per_row=3)
        ejecutar = st.form_submit_button("Ejecutar")

    if not ejecutar:
        return

    df_valiosas = assets["df_valiosas_dict"][user_selected_target]
    df_resultados = obtener_vecinos_de_mi_respuesta(
        df_respuestas,
        df_cluster_target,
        df_valiosas,
        n_vecinos=50,
    )

    if not df_resultados.empty and "cluster_N_Proba" in df_resultados.columns:
        df_resultados["nivel_de_confianza_cluster"] = pd.qcut(
            df_resultados["cluster_N_Proba"],
            q=4,
            labels=False,
            duplicates="drop",
        )

    df_filtrado = filter_cluster_results(df_resultados)

    resultado = construir_descripciones_cluster(
        df_filtrado,
        data_desc_global,
        get_nuevo_diccionario(),
        language="es",
        show_N_probabilidad=True,
        show_Probabilidad=True,
    )

    st.write("### Resultados:")
    grouped_results = format_all_clusters(resultado)
    for group_idx, group_data in enumerate(grouped_results, start=1):
        st.markdown(
            format_grouped_scenarios_card(group_idx, group_data),
            unsafe_allow_html=True,
        )
