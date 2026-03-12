import math

import plotly.graph_objects as go
import streamlit as st

from config import POSSIBLE_VARS, VAR_CATEGORIES
from data_utils import load_and_process_data

SMALL_SAMPLE_THRESHOLD = 30

DESTINATIONS = [
    {"label": "Baja Baja", "hex": "#dc2626", "text_col": "#b91c1c", "q": 1},
    {"label": "Baja Alta", "hex": "#f97316", "text_col": "#c2410c", "q": 2},
    {"label": "Media Baja", "hex": "#f59e0b", "text_col": "#b45309", "q": 3},
    {"label": "Media Alta", "hex": "#14b8a6", "text_col": "#0f766e", "q": 4},
    {"label": "Alta", "hex": "#2563eb", "text_col": "#1d4ed8", "q": 5},
]


def random_filter_selection():
    import random

    for var in POSSIBLE_VARS:
        st.session_state[f"cats_{var}"] = []

    chosen_vars = random.sample(POSSIBLE_VARS, 2)
    st.session_state["selected_vars"] = chosen_vars

    for var in chosen_vars:
        cat_options = VAR_CATEGORIES.get(var, [])
        if cat_options:
            chosen_cats = random.sample(cat_options, random.randint(1, min(3, len(cat_options))))
            st.session_state[f"cats_{var}"] = chosen_cats


def get_100_dots(percentages):
    clean_percentages = [p if isinstance(p, (int, float)) and math.isfinite(p) and p > 0 else 0.0 for p in percentages]
    total_percentage = sum(clean_percentages)

    if total_percentage <= 0:
        return [0] * 100

    scaled_percentages = [p * 100 / total_percentage for p in clean_percentages]

    dots, remainders = [], []
    total = 0
    for i, p in enumerate(scaled_percentages):
        count = math.floor(p)
        total += count
        dots.extend([i] * count)
        remainders.append({"index": i, "rem": p - count})

    remainders.sort(key=lambda x: x["rem"], reverse=True)
    needed = 100 - total
    for i in range(needed):
        dots.append(remainders[i]["index"])

    dots.sort()
    return dots


def render_waffle_chart(dots, title, subtitle):
    html = f"""
    <div style="background-color:white;padding:25px;border-radius:15px;border:1px solid #e2e8f0;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,0.05);">
        <h3 style="margin:0 0 5px 0;color:#1e293b;font-family:sans-serif;text-transform:uppercase;font-size:1.2rem;font-weight:900;">{title}</h3>
        <p style="margin:0 0 20px 0;color:#64748b;font-size:0.9rem;font-family:sans-serif;">{subtitle}</p>
        <div style="display:grid;grid-template-columns:repeat(10, 1fr);gap:6px;max-width:380px;margin:0 auto;">
    """
    for d in dots:
        color = DESTINATIONS[d]["hex"]
        label = DESTINATIONS[d]["label"]
        person_color = "#0f172a" if is_light_hex(color) else "#f8fafc"
        html += (
            f'<div style="background-color:{color};height:32px;border-radius:6px;display:flex;align-items:center;justify-content:center;'
            f'color:{person_color};font-size:16px;box-shadow:0 1px 2px rgba(0,0,0,0.1);" title="Destino: {label}">●</div>'
        )

    html += "</div></div>"
    st.markdown(html, unsafe_allow_html=True)


def render_divergent_bar_chart(current_vals, base_vals, title):
    labels = [d["label"] for d in DESTINATIONS]
    diffs = [c - b for c, b in zip(current_vals, base_vals)]
    text_labels = [f"+{d:.1f} pp" if d > 0 else f"{d:.1f} pp" for d in diffs]
    text_labels = [t if t not in ["+0.0 pp", "0.0 pp", "-0.0 pp"] else "" for t in text_labels]
    bar_colors = ["#10b981" if d > 0 else "#f43f5e" for d in diffs]

    max_abs_diff = max([abs(d) for d in diffs] + [1.0])
    axis_limit = min(60, max(6, math.ceil((max_abs_diff + 1) / 5) * 5))

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=diffs[::-1],
            y=labels[::-1],
            orientation="h",
            marker_color=bar_colors[::-1],
            text=text_labels[::-1],
            textposition="outside",
            textfont=dict(size=12, color="gray", family="sans-serif"),
            hoverinfo="x+y",
        )
    )

    fig.update_layout(
        title=dict(text=f"Cambio vs Promedio ({title})", font=dict(size=14, color="#64748b")),
        margin=dict(l=0, r=40, t=40, b=0),
        height=250,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            title="Diferencia en Puntos Porcentuales (pp)",
            zeroline=True,
            zerolinewidth=2,
            zerolinecolor="#cbd5e1",
            showgrid=False,
            range=[-axis_limit, axis_limit],
            tickfont=dict(color="#94a3b8"),
        ),
        yaxis=dict(showgrid=False, tickfont=dict(size=13, color="#334155", family="sans-serif")),
        showlegend=False,
    )

    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})



def is_light_hex(hex_color):
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return luminance > 0.6


def get_origin_distribution(df, origin_quintile):
    subset = df[df["a_los_14_quintile"] == origin_quintile]
    n = len(subset)
    if n == 0:
        return [0.0] * len(DESTINATIONS), 0

    dist = subset["actualmente_quintile"].value_counts(normalize=True).sort_index() * 100
    values = [float(dist.get(d["q"], 0.0)) for d in DESTINATIONS]
    return values, n


def show_section1():
    if "selected_vars" not in st.session_state:
        st.session_state["selected_vars"] = []
    for var in POSSIBLE_VARS:
        st.session_state.setdefault(f"cats_{var}", [])

    st.session_state["selected_vars"] = st.sidebar.multiselect(
        "Selecciona las variables (máximo 3)",
        options=POSSIBLE_VARS,
        default=st.session_state["selected_vars"],
        max_selections=3,
    )

    for var in st.session_state["selected_vars"]:
        st.session_state[f"cats_{var}"] = st.sidebar.multiselect(
            f"{var.capitalize()}:",
            VAR_CATEGORIES.get(var, []),
            default=st.session_state[f"cats_{var}"],
        )

    df = load_and_process_data()
    df_filter = apply_dynamic_filter(df)

    st.sidebar.markdown("---")
    cambiar_base = st.sidebar.checkbox("Cambiar base", value=False)
    df_base = show_base_filters(df) if cambiar_base else df

    baja_vals, baja_n = get_origin_distribution(df_filter, 1)
    alta_vals, alta_n = get_origin_distribution(df_filter, 5)
    base_baja_vals, _ = get_origin_distribution(df_base, 1)
    base_alta_vals, _ = get_origin_distribution(df_base, 5)

    st.markdown(
        """
        <div style="margin-bottom: 2rem;">
            <p style="color: #475569; font-size: 1.1rem;">
                Si 100 personas nacieran hoy en distintas clases sociales de México, ¿cuál sería su destino final?
                Selecciona un perfil y observa cómo cambian sus oportunidades.
                <strong style="color: #059669;">(Verde = Movilidad Ascendente, Rojo = Trampa de Pobreza)</strong>.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption(f"Tamaño de muestra (filtro): Origen clase baja n={baja_n}, origen clase alta n={alta_n}.")
    if min(baja_n, alta_n) < SMALL_SAMPLE_THRESHOLD:
        st.warning("⚠️ Muestra chica en al menos uno de los grupos filtrados. Interpretar con cautela.")

    col_waffle_baja, col_waffle_alta = st.columns(2)
    with col_waffle_baja:
        render_waffle_chart(get_100_dots(baja_vals), "Cuna: Clase Baja", "De 100 personas nacidas en la base...")
    with col_waffle_alta:
        render_waffle_chart(get_100_dots(alta_vals), "Cuna: Clase Alta", "De 100 personas nacidas en la cima...")

    st.markdown("<br>", unsafe_allow_html=True)
    col_stat_baja, col_stat_alta = st.columns(2)

    with col_stat_baja:
        st.markdown("#### Cuna: Clase Baja · Cambio vs base (pp)")
        render_divergent_bar_chart(baja_vals, base_baja_vals, "Origen Baja")

    with col_stat_alta:
        st.markdown("#### Cuna: Clase Alta · Cambio vs base (pp)")
        render_divergent_bar_chart(alta_vals, base_alta_vals, "Origen Alta")


def apply_dynamic_filter(df):
    dff = df.copy()
    for var in st.session_state["selected_vars"]:
        chosen_cats = st.session_state.get(f"cats_{var}", [])
        if chosen_cats:
            dff = dff[dff[var].isin(chosen_cats)]
    return dff


def show_base_filters(df):
    st.session_state.setdefault("base_selected_vars", [])
    for var in POSSIBLE_VARS:
        st.session_state.setdefault(f"base_cats_{var}", [])

    st.sidebar.markdown("**Base personalizada**:")
    st.session_state["base_selected_vars"] = st.sidebar.multiselect(
        "Variables base:",
        options=POSSIBLE_VARS,
        default=st.session_state["base_selected_vars"],
        max_selections=3,
    )

    for var in st.session_state["base_selected_vars"]:
        st.session_state[f"base_cats_{var}"] = st.sidebar.multiselect(
            f"{var.capitalize()} (base):",
            VAR_CATEGORIES.get(var, []),
            default=st.session_state[f"base_cats_{var}"],
        )

    dff = df.copy()
    for var in st.session_state["base_selected_vars"]:
        chosen_cats = st.session_state.get(f"base_cats_{var}", [])
        if chosen_cats:
            dff = dff[dff[var].isin(chosen_cats)]
    return dff
