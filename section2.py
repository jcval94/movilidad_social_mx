# section2.py

import streamlit as st
import pandas as pd
import plotly.express as px

from data_utils import load_and_process_data

# Diccionario para mapear clases a quintiles
CLASS_TO_QUINTILES = {
    "Baja Baja": [1],
    "Baja Alta": [2],
    "Media Baja": [3],
    "Media Alta": [4],
    "Alta": [5]
}

def random_origin_dest():
    """
    Elige aleatoriamente 1..2 clases para ORIGEN y 1..2 para DESTINO.
    Se invoca al dar clic en el botón "Random" en main.py.
    """
    import random
    classes = list(CLASS_TO_QUINTILES.keys())
    # Origen
    n_orig = random.randint(1, 2)
    origin = random.sample(classes, n_orig)
    # Destino
    n_dest = random.randint(1, 2)
    dest   = random.sample(classes, n_dest)

    st.session_state["origin_default"] = origin
    st.session_state["dest_default"]   = dest

def show_section2():
    """
    Evolución Temporal (Sección 2)
    Aplica los filtros de la barra lateral excepto 'generation'.
    """
    # 1) Cargar y procesar datos
    df = load_and_process_data()
    df = add_cohort_5y_column(df, step=3)

    # 2) Filtro excepto generation
    df_filtered = apply_filter_except_generation(df)

    # 3) Controles Origen y Destino (multiselect)
    #    Con valores por defecto si no existen en session_state
    if "origin_default" not in st.session_state:
        st.session_state["origin_default"] = ["Media Alta"]
    if "dest_default" not in st.session_state:
        st.session_state["dest_default"] = ["Alta"]

    colA, colB = st.columns(2)
    with colA:
        origin_multisel = st.multiselect(
            "Clase de origen",
            options=list(CLASS_TO_QUINTILES.keys()),
            default=st.session_state["origin_default"],
            key="origin_multisel"
        )
    with colB:
        dest_multisel = st.multiselect(
            "Clase de destino",
            options=list(CLASS_TO_QUINTILES.keys()),
            default=st.session_state["dest_default"],
            key="dest_multisel"
        )

    # Guardamos la última selección
    st.session_state["origin_default"] = origin_multisel
    st.session_state["dest_default"]   = dest_multisel

    # 4) Armamos el "group_label" para color (multilíneas si hay más filtros)
    color_column = create_label_column(df_filtered)

    # 5) Filtramos quienes estaban en 'Origen'
    origin_quintiles = set()
    for cls in origin_multisel:
        origin_quintiles.update(CLASS_TO_QUINTILES[cls])
    dest_quintiles = set()
    for cls in dest_multisel:
        dest_quintiles.update(CLASS_TO_QUINTILES[cls])

    df_filtered['in_origin'] = df_filtered['a_los_14_quintile'].isin(origin_quintiles)
    df_filtered['in_dest']   = df_filtered['actualmente_quintile'].isin(dest_quintiles)

    df_origin = df_filtered[df_filtered['in_origin'] == True].copy()

    # 6) Group by cohorte + color_column
    grouped = df_origin.groupby(['cohort_5y', color_column], dropna=False)
    n_origin = grouped.size().rename("n_origin")
    n_dest   = grouped['in_dest'].sum().rename("n_dest")

    df_stats = pd.concat([n_origin, n_dest], axis=1).reset_index()
    df_stats['pct_dest'] = (df_stats['n_dest'] / df_stats['n_origin']) * 100

    # Convertir cohort_5y a valor numérico
    df_stats['cohort_start'] = df_stats['cohort_5y'].apply(get_lower_year)
    df_stats.sort_values('cohort_start', inplace=True)
    df_stats.dropna(subset=['cohort_start'], inplace=True)

    # 7) Gráfica
    if not origin_multisel:
        origin_multisel = ["(Ninguno)"]
    if not dest_multisel:
        dest_multisel = ["(Ninguno)"]
    origin_str = ", ".join(origin_multisel)
    dest_str = ", ".join(dest_multisel)

    chart_title = f"Porcentaje de {origin_str} que se mueven a {dest_str}"

    fig = px.line(
        df_stats,
        x='cohort_start',
        y='pct_dest',
        color=color_column,
        markers=True,
        title=chart_title,
        labels={
            'cohort_start': "Año de nacimiento",
            'pct_dest': "Probabilidad de cambio",
            color_column: "Categoría"
        }
        # Podrías definir color_discrete_sequence para "igualar" la paleta
        # color_discrete_sequence=["gray","skyblue","salmon","green","red",...]
    )
    fig.update_layout(
        width=800,
        height=600,
        legend_title_text="Categoría",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)

    st.plotly_chart(fig, use_container_width=True)

    # 8) Logos finales
    st.markdown("---")
    c1, c2 = st.columns([0.5, 0.5])
    with c1:
        st.markdown(
            """
            <a href='https://github.com/jcval94chat/movilidad_social' target='_blank'
               class='app-icon-link'>
                <span class='icon'>↗</span>
                <span>Repositorio</span>
            </a>
            """,
            unsafe_allow_html=True
        )
    with c2:
        st.markdown(
            """
            <a href='https://github.com/jcval94chat/movilidad_social' target='_blank'
               class='app-icon-link'>
                <span class='icon'>↗</span>
                <span>Repositorio</span>
            </a>
            """,
            unsafe_allow_html=True
        )

def add_cohort_5y_column(df, base_year=2017, step=3):
    def assign_cohort_5y(age):
        if pd.isna(age):
            return "NA"
        birth_year = base_year - int(age)
        lower_bound = (birth_year // step) * step
        upper_bound = lower_bound + (step - 1)
        return f"{lower_bound}-{upper_bound}"
    df['cohort_5y'] = df['p05h'].apply(assign_cohort_5y)
    return df

def get_lower_year(cohort_str):
    if cohort_str == "NA" or pd.isna(cohort_str):
        return None
    return int(cohort_str.split('-')[0])

def apply_filter_except_generation(df):
    if 'selected_vars' not in st.session_state:
        return df
    dff = df.copy()
    for var in st.session_state['selected_vars']:
        if var == 'generation':
            continue
        chosen_cats = st.session_state.get(f"cats_{var}", [])
        if chosen_cats:
            dff = dff[dff[var].isin(chosen_cats)]
    return dff

def create_label_column(df):
    """
    Combina las variables seleccionadas (except generation) para 'color'.
    """
    if 'selected_vars' not in st.session_state:
        df['group_label'] = "All"
        return 'group_label'
    chosen_vars = [v for v in st.session_state['selected_vars'] if v != 'generation']
    if not chosen_vars:
        df['group_label'] = "All"
        return 'group_label'

    def make_label(row):
        parts = []
        for v in chosen_vars:
            parts.append(f"{v}={row[v]}")
        return " | ".join(parts)

    df['group_label'] = df.apply(make_label, axis=1)
    return 'group_label'
