# main.py

import streamlit as st
from section1 import show_section1, random_filter_selection as random_section1
from section2 import show_section2, random_origin_dest as random_section2
from section3 import show_section3, random_origin_dest as random_section3  # Asegúrate de importar la función correcta
from section4 import show_section4

FRIENDLY_FILTER_NAMES = {
    "generation": "Generación",
    "sex": "Sexo",
    "education": "Educación"
}

def main():
    st.set_page_config(layout="wide")

    with st.sidebar.container(border=True):
        st.markdown("### Acciones")

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("Ejemplo", key="random_main", help="Carga filtros de ejemplo"):
                random_section1()
                random_section2()
                random_section3()
                st.rerun()

        with col_btn2:
            if st.button("🔄", key="refresh_main", help="Recargar"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()

    st.sidebar.markdown("### Filtros activos")
    selected_vars = st.session_state.get("selected_vars", [])
    if selected_vars:
        badge_text = ", ".join(FRIENDLY_FILTER_NAMES.get(v, v.capitalize()) for v in selected_vars)
        st.sidebar.markdown(f"**🔖 Selección actual:** {badge_text}")
    else:
        st.sidebar.info("Sin filtros seleccionados. Usa *Filtro principal* para empezar.")

    # -----------------------------------------------------------------
    # TABS
    # -----------------------------------------------------------------
    tab1, tab2, tab3, tab4 = st.tabs(["Movilidad", "Evolución Temporal", 
                                      "¿Qué clase soy?",
                                      "Pobre a Rico"])

    with tab1:
        show_section1()
    with tab2:
        show_section2()
    with tab3:
        show_section3()
    with tab4:
        show_section4()

if __name__ == "__main__":
    main()
