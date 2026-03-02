# main.py

import streamlit as st
from section1 import show_section1, random_filter_selection as random_section1
from section2 import show_section2, random_origin_dest as random_section2
from section3 import show_section3, random_origin_dest as random_section3  # Asegúrate de importar la función correcta
from section4 import show_section4


def apply_global_styles():
    st.markdown(
        """
        <style>
        :root {
            --ui-radius: 10px;
            --ui-border: #e5e7eb;
            --ui-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
            --ui-shadow-hover: 0 4px 14px rgba(15, 23, 42, 0.10);
        }

        .stButton > button,
        .stFormSubmitButton > button,
        .stLinkButton > a {
            min-height: 42px;
            border-radius: var(--ui-radius);
            font-weight: 500;
            border: 1px solid var(--ui-border);
            transition: all 0.2s ease;
        }
        .stButton > button:hover,
        .stFormSubmitButton > button:hover,
        .stLinkButton > a:hover {
            transform: translateY(-1px);
            box-shadow: var(--ui-shadow-hover);
            border-color: #cbd5e1;
        }
        .stButton > button:focus,
        .stFormSubmitButton > button:focus,
        .stLinkButton > a:focus {
            outline: none;
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.18);
        }
        .stButton > button:disabled,
        .stFormSubmitButton > button:disabled {
            opacity: 0.55;
            transform: none;
            box-shadow: none;
            cursor: not-allowed;
        }

        .stFormSubmitButton > button {
            background-color: #7c3aed;
            color: #ffffff;
            border-color: #7c3aed;
        }
        .stFormSubmitButton > button:hover {
            background-color: #6d28d9;
            border-color: #6d28d9;
        }

        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div,
        textarea {
            border-radius: 10px !important;
            border: 1px solid var(--ui-border) !important;
            box-shadow: none !important;
            background: #ffffff;
        }
        div[data-baseweb="select"] > div:focus-within,
        div[data-baseweb="input"] > div:focus-within,
        textarea:focus {
            border-color: #93c5fd !important;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15) !important;
        }

        .stAlert {
            border-radius: 10px;
            border: 1px solid var(--ui-border);
        }

        .stDataFrame, .stTable {
            border: 1px solid var(--ui-border);
            border-radius: 10px;
            box-shadow: var(--ui-shadow);
            overflow: hidden;
        }

        .app-card {
            border: 1px solid var(--ui-border);
            border-radius: 12px;
            padding: 14px;
            margin-bottom: 14px;
            background: #ffffff;
            box-shadow: var(--ui-shadow);
        }
        .app-card h4 {
            margin: 0 0 10px 0;
            color: #111827;
            font-size: 1rem;
        }
        .app-meta {
            font-size: 0.82rem;
            color: #6b7280;
            margin-bottom: 8px;
            font-weight: 500;
        }
        .app-icon-link {
            text-decoration:none;
            color:#0f172a;
            font-weight:500;
            display:inline-flex;
            align-items:center;
            gap:8px;
        }
        .app-icon-link .icon {
            width: 22px;
            height: 22px;
            border-radius: 999px;
            border: 1px solid #d1d5db;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

def main():
    st.set_page_config(layout="wide")
    apply_global_styles()

    sections = [
        "¿Qué clase soy?",
        "Pobre a Rico",
        "Movilidad",
        "Evolución Temporal",
    ]
    selected_section = st.radio(
        "Secciones",
        options=sections,
        horizontal=True,
        label_visibility="collapsed",
    )

    show_sidebar_filters = selected_section in {"Movilidad", "Evolución Temporal"}

    # -----------------------------------------------------------------
    # BARRA LATERAL (parte superior): Botones Refresh y Random
    # -----------------------------------------------------------------
    if show_sidebar_filters:
        col_btn1, col_btn2 = st.sidebar.columns([0.5, 0.5])
        with col_btn1:
            if st.button("⟳ Refresh", key="refresh_main", help="Recargar la app"):
                # Limpia todo el session_state y recarga
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()

        with col_btn2:
            if st.button("🎲 Random", key="random_main", help="Selección aleatoria"):
                # Aplica la lógica de random a Sección 1 (Movilidad)
                random_section1()
                # Aplica la lógica de random a Sección 2 (Evolución Temporal)
                random_section2()

                random_section3()
                st.rerun()

        st.sidebar.subheader("Filtro actual (filtro principal):")

    if selected_section == "¿Qué clase soy?":
        show_section3()
    elif selected_section == "Pobre a Rico":
        show_section4()
    elif selected_section == "Movilidad":
        show_section1()
    else:
        show_section2()

if __name__ == "__main__":
    main()
