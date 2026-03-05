import re
import json
from pathlib import Path
from textwrap import dedent

import joblib
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sklearn.impute import SimpleImputer
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from utils.diccionarios import get_data_desc, get_nuevo_diccionario
from utils.func_s4 import construir_descripciones_cluster
from llm.gemini_explainer import generate_explanation

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


def _render_question_header(descripcion, variable):
    st.markdown(
        (
            f"**{descripcion}** "
            f"<span style=\"font-size:0.82rem;color:#6b7280;font-weight:500;\">v: {variable}</span>"
        ),
        unsafe_allow_html=True,
    )


def preguntar_opciones_streamlit(i, variable, descripcion, opciones):
    key_uid = f"opt_{variable}_{i}"
    _render_question_header(descripcion, variable)
    lista = [f"{k} - {v}" for k, v in opciones.items()]
    sel = st.selectbox(" ", lista, key=key_uid, label_visibility="collapsed")
    cod = int(sel.split(" - ")[0])
    return cod, opciones[cod]


def preguntar_numero_streamlit(i, variable, descripcion):
    key_uid = f"num_{variable}_{i}"
    _render_question_header(descripcion, variable)
    val = st.number_input(" ", value=0.0, step=1.0, key=key_uid, label_visibility="collapsed")
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
                match_obs = re.search(r"\((\d+)\s+obs\)", conf_val)
                summary_data["obs"] = match_obs.group(1) if match_obs else "no disponible"
                conf_numeric = conf_val.split("(", 1)[0].strip()
                summary_data["confianza"] = map_confidence(conf_numeric)
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
                categories_raw = line.split(":", 1)[1].strip()
                if "|" in categories_raw:
                    parts = categories_raw.split("|")
                else:
                    parts = categories_raw.split(",")

                cat_values = []
                for part in parts:
                    if "=" in part:
                        cat_values.append(part.split("=", 1)[1].strip())
                var_info["categorias"] = " | ".join(cat_values)
            elif line.startswith("- ¿Puedo cambiarlo yo?:"):
                val = line.split(":", 1)[1].strip()
                var_info["change_level"] = val
                if val.lower() != "no_aplica":
                    extra_props.append(f"¿Puedo cambiarlo yo?: {val}")
            elif line.startswith("- Involucrados:"):
                var_info["involucrados"] = line.split(':', 1)[1].strip()
                extra_props.append(f"Involucrados: {line.split(':', 1)[1].strip()}")
            elif line.startswith("- Recursos:"):
                val = line.split(":", 1)[1].strip()
                var_info["recursos"] = val
                if val.lower() != "no_aplica":
                    extra_props.append(f"Recursos: {val}")

        if "descripcion" in var_info and "categorias" in var_info:
            variables.append(
                {
                    "descripcion": var_info["descripcion"],
                    "categorias": var_info["categorias"],
                    "change_level": var_info.get("change_level", "no disponible"),
                    "involucrados": var_info.get("involucrados", "no disponible"),
                    "recursos": var_info.get("recursos", "no disponible"),
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
        return "<p class='app-meta' style='margin:0'>No se encontraron variables clave.</p>"

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
        obs = summary.get("obs", "N/D")

        scenario_cols += f"""
        <div style="min-width:170px;border-left:1px solid #e5e7eb;padding-left:12px;padding-right:8px">
          <div class="app-meta">Escenario {scenario.get('nombre')}</div>
          <div class="app-meta" style="margin-bottom:2px">Incremento</div>
          <div style="font-weight:700;color:{incremento.get('color', '#666666')};margin-bottom:8px">{incremento.get('text', 'N/D')}</div>
          <div class="app-meta" style="margin-bottom:2px">Probabilidad</div>
          <div style="font-weight:700;margin-bottom:8px">{probabilidad}</div>
          <div class="app-meta" style="margin-bottom:2px">Confianza</div>
          <div style="font-weight:700">{confianza}</div>
          <div class="app-meta" style="margin-bottom:2px;margin-top:8px">Obs</div>
          <div style="font-weight:700">{obs}</div>
        </div>
        """

    return dedent(
        f"""
        <div class="app-card">
          <h4>Grupo de Variables Clave #{group_idx}</h4>
          <div style="display:flex;align-items:flex-start;gap:12px;overflow-x:auto">
            <div style="min-width:420px;max-width:520px;padding-right:10px">
              <div class="app-meta">Variables clave (identificador)</div>
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


def has_low_reliability(groups):
    for group in groups:
        for scenario in group.get("scenarios", []):
            confidence = str(scenario.get("summary", {}).get("confianza", "")).strip().lower()
            if confidence == "baja":
                return True
    return False


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


def get_gemini_api_key():
    try:
        for key in ("gemini_api_key", "GEMINI_API_KEY"):
            if key in st.secrets and str(st.secrets[key]).strip():
                return str(st.secrets[key]).strip()
    except Exception:
        pass
    return ""


def get_active_filters_from_session():
    filters = []
    selected_vars = st.session_state.get("selected_vars", [])
    for var in selected_vars:
        values = st.session_state.get(f"cats_{var}", [])
        filters.append({"variable": var, "values": values})
    return filters


@st.cache_data(ttl=1800, show_spinner=False)
def cached_generate_explanation(app_state_json: str):
    return generate_explanation(json.loads(app_state_json))


def _parse_percent(value):
    if value is None:
        return np.nan
    txt = str(value).strip().replace('%', '').replace(',', '.')
    match = re.search(r"[-+]?\d*\.?\d+", txt)
    return float(match.group(0)) if match else np.nan


def _normalize_confidence_for_size(confidence):
    value = str(confidence).strip().lower()
    mapping = {
        "baja": 1,
        "media": 2,
        "alta": 3,
        "muy alta": 4,
    }
    if value in mapping:
        return mapping[value]
    try:
        return float(confidence)
    except Exception:
        return 2


def _scenario_short_label(group_name, scenario_name):
    group_match = re.search(r"(\d+)", str(group_name))
    scenario_match = re.search(r"(\d+)", str(scenario_name))
    g = group_match.group(1) if group_match else str(group_name)
    s = scenario_match.group(1) if scenario_match else str(scenario_name)
    return f"G{g}-E{s}"


@st.cache_data(ttl=1800, show_spinner=False)
def build_prioritization_points(grouped_results_json: str):
    grouped_results = json.loads(grouped_results_json)
    rows = []
    for group_idx, group_data in enumerate(grouped_results, start=1):
        group_name = f"Grupo #{group_idx}"
        vars_desc = [v.get("descripcion", "") for v in group_data.get("variables", []) if v.get("descripcion")]
        cambiable = any(
            str(v.get("change_level", "")).strip().lower() in {"fácil", "moderado", "difícil", "si", "sí"}
            for v in group_data.get("variables", [])
        )

        for scenario in group_data.get("scenarios", []):
            summary = scenario.get("summary", {})
            incremento = _parse_percent(summary.get("incremento", {}).get("text"))
            prob = _parse_percent(summary.get("probabilidad"))
            confianza = summary.get("confianza", "N/D")
            rows.append(
                {
                    "group": group_name,
                    "scenario": f"Escenario {scenario.get('nombre', 'N/D')}",
                    "incremento": incremento,
                    "prob": prob,
                    "confianza": confianza,
                    "confianza_num": _normalize_confidence_for_size(confianza),
                    "cambiable": cambiable,
                    "variables": " | ".join(vars_desc) if vars_desc else "N/D",
                }
            )

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df = df.dropna(subset=["incremento", "prob"]).copy()
    df["expected_score"] = df["incremento"] * (df["prob"] / 100.0)
    df["short_label"] = df.apply(
        lambda row: _scenario_short_label(row["group"], row["scenario"]),
        axis=1,
    )
    return df


def _infer_population_probability(df_plot):
    valid = df_plot.dropna(subset=["incremento", "prob"])
    if valid.empty:
        return 0.01

    if valid["incremento"].nunique() < 2:
        predicted = float(valid["prob"].median())
    else:
        slope, intercept = np.polyfit(valid["incremento"].astype(float), valid["prob"].astype(float), 1)
        predicted = float(intercept)

    return max(predicted, 0.01)


def render_prioritization_map(grouped_results):
    st.write("### Mapa de priorización: Incremento vs Probabilidad")

    points_df = build_prioritization_points(json.dumps(grouped_results, ensure_ascii=False, sort_keys=True))
    if points_df.empty:
        st.info("No hay datos suficientes para construir el mapa de priorización.")
        return

    df_plot = points_df.copy().sort_values("expected_score", ascending=False)
    top_idx = df_plot.head(5).index
    df_plot["is_top"] = df_plot.index.isin(top_idx)

    x_med = float(df_plot["prob"].median())
    y_med = float(df_plot["incremento"].median())

    palette = [
        "#6D28D9",  # morado intenso
        "#8B5CF6",  # violeta
        "#A78BFA",  # lila
        "#C4B5FD",  # lila claro
        "#DDD6FE",  # lavanda
        "#5EEAD4",  # menta
        "#99F6E4",  # menta claro
        "#2DD4BF",  # turquesa-menta
        "#7C3AED",  # morado medio
        "#14B8A6",  # menta oscuro
    ]
    groups_sorted = sorted(points_df["group"].unique())
    color_map = {g: palette[i % len(palette)] for i, g in enumerate(groups_sorted)}

    col_plot, col_legend = st.columns([3.2, 1.2])
    with col_legend:
        show_population = st.button("¿Donde está la población?", key="s4_show_population")
        st.markdown("**Cómo leerla**")
        st.caption("Arriba-derecha = mayor prioridad (alto incremento y alta probabilidad).")

    fig = go.Figure()
    for group_name, gdf in df_plot.groupby("group"):
        marker_sizes = 10 + (gdf["confianza_num"].fillna(2).astype(float) * 4)
        fig.add_trace(
            go.Scatter(
                x=gdf["prob"],
                y=gdf["incremento"],
                mode="markers+text",
                name=group_name,
                text=np.where(gdf["is_top"], gdf["short_label"], ""),
                textposition="top center",
                marker={
                    "size": marker_sizes,
                    "color": color_map[group_name],
                    "opacity": np.where(gdf["cambiable"], 0.9, 0.35),
                    "line": {
                        "width": np.where(gdf["is_top"], 2.6, 0.6),
                        "color": np.where(gdf["is_top"], "#111827", "#ffffff"),
                    },
                },
                customdata=np.stack(
                    [
                        gdf["group"],
                        gdf["scenario"],
                        gdf["expected_score"],
                        gdf["confianza"],
                        gdf["cambiable"],
                        gdf["variables"],
                    ],
                    axis=-1,
                ),
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "%{customdata[1]}<br>"
                    "Incremento: %{y:.2f}%<br>"
                    "Probabilidad: %{x:.2f}%<br>"
                    "Impacto esperado: %{customdata[2]:.2f}<br>"
                    "Confianza: %{customdata[3]}<br>"
                    "Cambiable: %{customdata[4]}<br>"
                    "Variables: %{customdata[5]}"
                    "<extra></extra>"
                ),
            )
        )

    top_df = df_plot[df_plot["is_top"]]
    fig.add_trace(
        go.Scatter(
            x=top_df["prob"],
            y=top_df["incremento"],
            mode="markers",
            marker={
                "size": 26,
                "color": "rgba(255,255,255,0)",
                "line": {"width": 3, "color": "rgba(17,24,39,0.25)"},
            },
            hoverinfo="skip",
            showlegend=False,
        )
    )

    if show_population:
        population_prob = _infer_population_probability(df_plot)
        fig.add_trace(
            go.Scatter(
                x=[population_prob],
                y=[0.0],
                mode="markers+text",
                name="Población",
                text=["Población"],
                textposition="top center",
                marker={
                    "size": 18,
                    "color": "#dc2626",
                    "line": {"width": 2, "color": "#7f1d1d"},
                },
                hovertemplate=(
                    "<b>Población</b><br>"
                    "Incremento: 0.00%<br>"
                    "Probabilidad inferida (LR): %{x:.2f}%"
                    "<extra></extra>"
                ),
            )
        )

    fig.add_vline(x=x_med, line_dash="dash", line_color="#9ca3af")
    fig.add_hline(y=y_med, line_dash="dash", line_color="#9ca3af")

    fig.add_annotation(x=0.98, y=0.97, xref="paper", yref="paper", text="ALTO inc / ALTA prob", showarrow=False, font={"size": 11, "color": "#374151"})
    fig.add_annotation(x=0.02, y=0.97, xref="paper", yref="paper", text="ALTO inc / BAJA prob", showarrow=False, font={"size": 11, "color": "#374151"}, xanchor="left")
    fig.add_annotation(x=0.98, y=0.04, xref="paper", yref="paper", text="BAJO inc / ALTA prob", showarrow=False, font={"size": 11, "color": "#374151"})
    fig.add_annotation(x=0.02, y=0.04, xref="paper", yref="paper", text="BAJO inc / BAJA prob", showarrow=False, font={"size": 11, "color": "#374151"}, xanchor="left")

    fig.update_layout(
        xaxis_title="Probabilidad (%)",
        yaxis_title="Incremento (%)",
        template="plotly_white",
        legend_title_text="Grupo",
        margin={"l": 20, "r": 20, "t": 20, "b": 20},
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(148,163,184,0.2)")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(148,163,184,0.2)")

    with col_plot:
        st.plotly_chart(fig, width="stretch")

    return show_population

def _collapse_questionnaire_after_submit():
    st.session_state["section4_form_expanded"] = False


def _reset_section4_cached_output():
    for key in ["section4_payload_json", "section4_show_results"]:
        st.session_state.pop(key, None)


def show_section4():
    assets = load_section4_assets(str(BASE_PATH))

    targets = list(assets["df_valiosas_dict"].keys())
    opciones = [(valor, TARGET_LABELS.get(valor, valor)) for valor in targets]
    retorno_user = st.selectbox(
        " ",
        options=opciones,
        format_func=lambda x: x[1],
        key="section4_target_select",
        label_visibility="collapsed",
    )
    user_selected_target = retorno_user[0]

    if st.session_state.get("section4_last_target") != user_selected_target:
        st.session_state["section4_last_target"] = user_selected_target
        st.session_state["section4_form_expanded"] = True
        _reset_section4_cached_output()

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

    with st.expander("Cuestionario", expanded=st.session_state.get("section4_form_expanded", True)):
        with st.form("cuestionario_form"):
            df_respuestas = cuestionario_general(data_desc_usable, cols_per_row=3)
            ejecutar = st.form_submit_button(
                "Conocer mi diagnóstico",
                on_click=_collapse_questionnaire_after_submit,
            )

    if ejecutar:
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

        grouped_results = format_all_clusters(resultado)

        app_state = {
            "target": user_selected_target,
            "target_label": TARGET_LABELS.get(user_selected_target, user_selected_target),
            "active_filters": get_active_filters_from_session(),
            "questionnaire": df_respuestas.to_dict(orient="records"),
            "results": grouped_results,
            "gemini_api_key": get_gemini_api_key(),
        }
        app_state_json = json.dumps(app_state, ensure_ascii=False, sort_keys=True)

        with st.spinner("Generando diagnóstico..."):
            cached_generate_explanation(app_state_json)

        st.session_state["section4_payload_json"] = app_state_json
        st.session_state["section4_show_results"] = True

    if not st.session_state.get("section4_show_results"):
        return

    payload_json = st.session_state.get("section4_payload_json")
    if not payload_json:
        st.info("No hay resultados en memoria. Ejecuta nuevamente el diagnóstico.")
        return

    payload = json.loads(payload_json)
    grouped_results = payload.get("results", [])
    explanation = cached_generate_explanation(payload_json)

    st.write("### Explicación personalizada (IA)")
    st.markdown(explanation)

    render_prioritization_map(grouped_results)

    if has_low_reliability(grouped_results):
        st.warning(
            "⚠️ Confiabilidad baja detectada en al menos un escenario. "
            "Interpreta el diagnóstico con prudencia y valida con más experimentos en la app."
        )

    st.write("### Resultados:")
    for group_idx, group_data in enumerate(grouped_results, start=1):
        st.markdown(
            format_grouped_scenarios_card(group_idx, group_data),
            unsafe_allow_html=True,
        )
