# section4.py

import streamlit as st
import joblib
import pandas as pd

def show_section4():
    if 'df_valiosas_dict' not in st.session_state:
        st.session_state['df_valiosas_dict'] = joblib.load('df_valiosas_dict.joblib')
    if 'df_feature_importances_total' not in st.session_state:
        st.session_state['df_feature_importances_total'] = joblib.load('df_feature_importances_total.joblib')
    if 'df_clusterizados_total_origi' not in st.session_state:
        st.session_state['df_clusterizados_total_origi'] = pd.read_csv('/content/df_clusterizados_total_origi.csv')

    st.write("Sección 4")
    TARGETS = list(st.session_state['df_valiosas_dict'].keys())
    target = st.selectbox("Target", TARGETS, index=0)

    df_datos_descript_valiosas = st.session_state['df_valiosas_dict'][target]
    prefix = f"{target}_"
    df_cluster_target = st.session_state['df_clusterizados_total_origi'].rename(
        columns={
            c: c.replace(prefix,"") 
            for c in st.session_state['df_clusterizados_total_origi'].columns 
            if c.startswith(prefix)
        }
    )

    df_feature_importances_total = st.session_state['df_feature_importances_total']
    best_val = [x.split('-')[0].strip() for x in df_feature_importances_total[f"{target}_importance"].sort_values(ascending=False).index][:10]
    best_val = [x for x in best_val if x not in ['p133','CIUO2']]

    preguntas_lista_ = ['p05','p86','p33_f','p43','p43m','p13','p98','p151','p64']
    preguntas_lista = sorted(list(set(preguntas_lista_+best_val)))

    # Ejemplo de "df_respuestas" en Streamlit (simplificado):
    st.write("Respuestas hipotéticas (demo):")
    df_respuestas = pd.DataFrame([{p: 0 for p in preguntas_lista}])

    # Mocks de las funciones referidas (ajustar a tu código real)
    def obtener_vecinos_de_mi_respuesta(a,b,c,n_vecinos=51): return a
    def construir_descripciones_cluster(a,b,c,**kwargs): return a.head(5)
    def get_n_closest_values(a,b,c,d,e,f): return []

    # Filtrado
    opciones_filtro = {
        'cambio': lambda df: df[(df['cambio_yo_moderado']>0)|(df['cambio_yo_difícil']>0)|(df['cambio_yo_fácil']>0)].sort_values('N_probabilidad', ascending=False),
        'gobierno': lambda df: df[df['involucrados_gobierno']>0],
        'extenso': lambda df: df[((df['cambio_yo_moderado']>0)|(df['cambio_yo_difícil']>0)|(df['cambio_yo_fácil']>0))&(df['nivel_de_confianza_cluster']==0)&(df['N_probabilidad']>1)],
        'confidence': lambda df: df[((df['cambio_yo_moderado']>0)|(df['cambio_yo_difícil']>0)|(df['cambio_yo_fácil']>0))&(df['nivel_de_confianza_cluster']>0)]
    }

    user_choice = st.selectbox("Filtrar por", list(opciones_filtro.keys()), index=0)

    if st.button("Conocer mi diagnóstico"):
        df_datos_descript_valiosas_respuestas = obtener_vecinos_de_mi_respuesta(
            df_respuestas, 
            df_cluster_target, 
            df_datos_descript_valiosas
        )
        df_datos_descript_valiosas_respuestas['nivel_de_confianza_cluster'] = pd.qcut(
            df_datos_descript_valiosas_respuestas['Soporte'], q=4, labels=False
        )
        df_filtrado = opciones_filtro[user_choice](df_datos_descript_valiosas_respuestas)
        resultado = construir_descripciones_cluster(df_filtrado, None, None, language='es', show_N_probabilidad=True, show_Probabilidad=True)
        st.dataframe(resultado)
