# section1.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from data_utils import load_and_process_data
from config import VAR_CATEGORIES, POSSIBLE_VARS

FILTER_LABELS = {
    "generation": "Generación",
    "sex": "Sexo",
    "education": "Educación"
}

def pretty_label(var_name):
    return FILTER_LABELS.get(var_name, var_name.capitalize())


def random_filter_selection():
    """
    Elige aleatoriamente 2 variables y 1..3 categorías de cada una (para Sección 1).
    Se invoca desde main.py al pulsar el botón "Random".
    """
    import random
    for var in POSSIBLE_VARS:
        st.session_state[f"cats_{var}"] = []

    # Elegimos 2 variables al azar
    num_vars = 2
    chosen_vars = random.sample(POSSIBLE_VARS, num_vars)
    st.session_state['selected_vars'] = chosen_vars

    # Para cada variable elegida, seleccionamos entre 1..3 categorías
    for var in chosen_vars:
        cat_options = VAR_CATEGORIES.get(var, [])
        if cat_options:
            num_cats = random.randint(1, min(3, len(cat_options)))
            chosen_cats = random.sample(cat_options, num_cats)
            st.session_state[f"cats_{var}"] = chosen_cats

def show_section1():
    """
    Sección Movilidad: "Movilidad Socioeconómica Q1 vs Q5".
    """
    if 'selected_vars' not in st.session_state:
        st.session_state['selected_vars'] = []
    for var in POSSIBLE_VARS:
        if f"cats_{var}" not in st.session_state:
            st.session_state[f"cats_{var}"] = []

    # ----------------
    # Barra lateral: (Ya tenemos los botones en main.py)
    # ----------------

    # 1) Filtros organizados en bloques plegables
    with st.sidebar.expander("Filtro principal", expanded=True):
        st.session_state['selected_vars'] = st.multiselect(
            "Variables (máximo 3)",
            options=POSSIBLE_VARS,
            default=st.session_state['selected_vars'],
            max_selections=3,
            help="Elige hasta 3 dimensiones para segmentar resultados."
        )

        if st.session_state['selected_vars']:
            st.caption(f"✅ {len(st.session_state['selected_vars'])} variable(s) activa(s)")
        else:
            st.caption("ℹ️ No hay variables seleccionadas todavía.")

        for var in st.session_state['selected_vars']:
            cat_options = VAR_CATEGORIES.get(var, [])
            st.session_state[f"cats_{var}"] = st.multiselect(
                f"{pretty_label(var)}",
                cat_options,
                default=st.session_state[f"cats_{var}"],
                placeholder="Selecciona una o más categorías"
            )

            selected_count = len(st.session_state[f"cats_{var}"])
            if selected_count:
                st.caption(f"🔹 {pretty_label(var)}: {selected_count} categoría(s) seleccionada(s)")
            else:
                st.caption(f"▫️ {pretty_label(var)}: sin categorías seleccionadas (usa todas)")

    # 2) Cargar datos
    df = load_and_process_data()

    # 3) Filtro principal
    df_filter = apply_dynamic_filter(df)

    with st.sidebar.expander("Comparación base", expanded=False):
        cambiar_base = st.checkbox("Activar comparación contra base", value=False)
        if cambiar_base:
            show_base_filters(df)
            df_base = st.session_state.get('df_base', df)
            st.caption("✅ Comparación activa")
        else:
            df_base = df
            st.caption("ℹ️ Usando base general")

    with st.sidebar.expander("Opciones avanzadas", expanded=False):
        st.caption("Vista rápida del estado de filtros:")
        if main_filters_selected(st.session_state['selected_vars']):
            st.markdown("- **Principal:** activo")
        else:
            st.markdown("- **Principal:** sin selección")
        st.markdown(f"- **Comparación base:** {'activa' if cambiar_base else 'apagada'}")

    # 5) Construir el título a partir de los filtros
    filter_desc = describe_filter_selection(st.session_state['selected_vars'], prefix="Filtro: ")
    if cambiar_base and 'base_selected_vars' in st.session_state and st.session_state['base_selected_vars']:
        base_desc = describe_filter_selection(st.session_state['base_selected_vars'], prefix="Base: ", base=True)
        main_title = f"{filter_desc} vs {base_desc}"
    else:
        main_title = filter_desc or "Sin Filtro (Base General)"

    # 6) Plot interactivo con Plotly
    fig = plot_mobility_interactive(df_filter, df_base)

    # Colocamos el título principal arriba de la figura
    # st.markdown("## Movilidad Socioeconómica Q1 vs Q5")
    st.write(f"*{main_title}*")

    st.plotly_chart(fig, use_container_width=True)

    # 7) Logos al final
    st.markdown("---")
    c1, c2 = st.columns([0.5, 0.5])
    with c1:
        st.markdown(
            """
            <a href='https://github.com/jcval94chat/movilidad_social' target='_blank'
               style='text-decoration:none;'>
                <img src='https://cdn-icons-png.flaticon.com/512/1384/1384060.png'
                     height='25' style='vertical-align:middle;' />
                <span style='font-size:14px; margin-left:6px;'>Repositorio</span>
            </a>
            """,
            unsafe_allow_html=True
        )
    with c2:
        st.markdown(
            """
            <a href='https://github.com/jcval94chat/movilidad_social' target='_blank'
               style='text-decoration:none;'>
                <img src='https://cdn-icons-png.flaticon.com/512/1384/1384063.png'
                     height='25' style='vertical-align:middle;' />
                <span style='font-size:14px; margin-left:6px;'>Repositorio</span>
            </a>
            """,
            unsafe_allow_html=True
        )

def apply_dynamic_filter(df):
    dff = df.copy()
    for var in st.session_state['selected_vars']:
        chosen_cats = st.session_state.get(f"cats_{var}", [])
        if chosen_cats:
            dff = dff[dff[var].isin(chosen_cats)]
    return dff

def show_base_filters(df):
    if 'base_selected_vars' not in st.session_state:
        st.session_state['base_selected_vars'] = []
    for var in POSSIBLE_VARS:
        key_base_cats = f"base_cats_{var}"
        if key_base_cats not in st.session_state:
            st.session_state[key_base_cats] = []

    st.markdown("**Base personalizada**")
    st.session_state['base_selected_vars'] = st.multiselect(
        "Variables para la base",
        options=POSSIBLE_VARS,
        default=st.session_state['base_selected_vars'],
        max_selections=3
    )

    if st.session_state['base_selected_vars']:
        st.caption(f"✅ {len(st.session_state['base_selected_vars'])} variable(s) de base activa(s)")
    else:
        st.caption("ℹ️ Base sin filtros específicos (equivale a base general).")

    for var in st.session_state['base_selected_vars']:
        cat_options = VAR_CATEGORIES.get(var, [])
        st.session_state[f"base_cats_{var}"] = st.multiselect(
            f"{pretty_label(var)} (base)",
            cat_options,
            default=st.session_state[f"base_cats_{var}"]
        )

    dff = df.copy()
    for var in st.session_state['base_selected_vars']:
        chosen_cats = st.session_state.get(f"base_cats_{var}", [])
        if chosen_cats:
            dff = dff[dff[var].isin(chosen_cats)]
    st.session_state['df_base'] = dff

def describe_filter_selection(selected_vars, prefix="", base=False):
    parts = []
    for var in selected_vars:
        chosen_cats = st.session_state.get(f"{'base_cats_' if base else 'cats_'}{var}", [])
        if chosen_cats:
            cats_str = ", ".join(chosen_cats)
            parts.append(f"{pretty_label(var)}={cats_str}")

    if parts:
        return prefix + "[" + "; ".join(parts) + "]"
    else:
        return prefix + "(Sin selección)"

def main_filters_selected(selected_vars):
    for var in selected_vars:
        if st.session_state.get(f"cats_{var}", []):
            return True
    return False

def plot_mobility_interactive(df_filter, df_base):
    """
    Crea 2 subplots: Origen Clase Baja (Q1) y Origen Clase Alta (Q5),
    con barra "Base" y "Filtro". Se usan anotaciones personalizadas para
    que la diferencia sea roja (si <0) o verde (si >0). Se mantiene la
    misma escala en ambos y en Q5 se oculta el eje Y.
    Además, se deja ~10% de margen vertical extra para no recortar etiquetas.
    """

    # Cálculo: Q1 base/filtro
    q1_base = df_base[df_base['a_los_14_quintile'] == 1]
    q1_dist_base = q1_base['actualmente_quintile'].value_counts(normalize=True)*100
    q1_dist_base = q1_dist_base.sort_index()

    q1_filter = df_filter[df_filter['a_los_14_quintile'] == 1]
    q1_dist_filter = q1_filter['actualmente_quintile'].value_counts(normalize=True)*100
    q1_dist_filter = q1_dist_filter.sort_index()

    # Cálculo: Q5 base/filtro
    q5_base = df_base[df_base['a_los_14_quintile'] == 5]
    q5_dist_base = q5_base['actualmente_quintile'].value_counts(normalize=True)*100
    q5_dist_base = q5_dist_base.sort_index()

    q5_filter = df_filter[df_filter['a_los_14_quintile'] == 5]
    q5_dist_filter = q5_filter['actualmente_quintile'].value_counts(normalize=True)*100
    q5_dist_filter = q5_dist_filter.sort_index()

    quintil_labels = {
        1: "Baja Baja",
        2: "Baja Alta",
        3: "Media Baja",
        4: "Media Alta",
        5: "Alta"
    }

    x_q1 = list(q1_dist_base.index.union(q1_dist_filter.index))
    x_q5 = list(q5_dist_base.index.union(q5_dist_filter.index))

    fig = make_subplots(rows=1, cols=2, shared_yaxes=True,
                        subplot_titles=("Origen Clase Baja", "Origen Clase Alta"))

    # Subplot 1: Q1
    fig.add_trace(
        go.Bar(
            x=[quintil_labels.get(k, str(k)) for k in x_q1],
            y=[q1_dist_base.get(k, 0) for k in x_q1],
            name="Base",
            marker_color="gray",
            opacity=0.4
        ),
        row=1, col=1
    )
    fig.add_trace(
        go.Bar(
            x=[quintil_labels.get(k, str(k)) for k in x_q1],
            y=[q1_dist_filter.get(k, 0) for k in x_q1],
            name="Filtro",
            marker_color="skyblue"
        ),
        row=1, col=1
    )

    # Subplot 2: Q5
    fig.add_trace(
        go.Bar(
            x=[quintil_labels.get(k, str(k)) for k in x_q5],
            y=[q5_dist_base.get(k, 0) for k in x_q5],
            name="Base",
            marker_color="gray",
            opacity=0.4
        ),
        row=1, col=2
    )
    fig.add_trace(
        go.Bar(
            x=[quintil_labels.get(k, str(k)) for k in x_q5],
            y=[q5_dist_filter.get(k, 0) for k in x_q5],
            name="Filtro",
            marker_color="salmon"
        ),
        row=1, col=2
    )

    # Ajustar layout
    # - Aumentar 10% en el eje Y
    max_val_q1 = max(q1_dist_base.max(), q1_dist_filter.max(), 0)
    max_val_q5 = max(q5_dist_base.max(), q5_dist_filter.max(), 0)
    overall_max = max(max_val_q1, max_val_q5)
    fig.update_yaxes(range=[0, overall_max * 1.1], row=1, col=1)
    # - Eje Y en Q5 invisible pero escalado igual
    fig.update_yaxes(matches='y', row=1, col=2, visible=False)

    fig.update_layout(
        barmode='group',
        showlegend=True,
        width=900,
        height=600
    )
    fig.update_yaxes(title_text="Probabilidad de moverse a otra Clase", row=1, col=1)

    # Añadir anotaciones para mostrar la diferencia en colores
    # en la subgráfica Q1
    for i, k in enumerate(x_q1):
        val_b = q1_dist_base.get(k, 0)
        val_f = q1_dist_filter.get(k, 0)
        diff  = val_f - val_b
        x_label = quintil_labels.get(k, str(k))
        color = 'green' if diff >= 0 else 'red'
        text_str = f"{val_f:.1f}%<br>({diff:+.1f}%)"
        fig.add_annotation(
            x=x_label,
            y=val_f + 1,  # un poco arriba
            text=f"<span style='color:{color}; font-size:12px;'>{text_str}</span>",
            showarrow=False,
            row=1, col=1
        )

    # en la subgráfica Q5
    for i, k in enumerate(x_q5):
        val_b = q5_dist_base.get(k, 0)
        val_f = q5_dist_filter.get(k, 0)
        diff  = val_f - val_b
        x_label = quintil_labels.get(k, str(k))
        color = 'green' if diff >= 0 else 'red'
        text_str = f"{val_f:.1f}%<br>({diff:+.1f}%)"
        fig.add_annotation(
            x=x_label,
            y=val_f + 1,
            text=f"<span style='color:{color}; font-size:12px;'>{text_str}</span>",
            showarrow=False,
            row=1, col=2
        )

    return fig
