import re


def construir_descripciones_cluster(
    variables_cambio,
    data_desc,
    nuevo_diccionario,
    language='es',
    show_N_probabilidad=True,
    show_Probabilidad=True
):
    """
    Construye descripciones concisas de cada 'cluster_descripcion' en variables_cambio.

    Parámetros
    ----------
    variables_cambio : pd.DataFrame
        Debe contener las columnas:
          - 'cluster_descripcion' (ej: "2.5 <= p133 ... AND 0.5 <= p126p ...")
          - 'cluster_N_Proba' (float, incremento de prob. respecto a la media)
          - 'cluster_ef_sample' (float, probabilidad de pertenecer a ese grupo)
    data_desc : dict
        Diccionario con la descripción de cada variable (por ej. 'p133') y
        una lista de valores y etiquetas.
    nuevo_diccionario : dict
        Diccionario con información extra para cada variable, por ejemplo:
        {
          'p133': (
              {'puedo_cambiarlo_yo': 'difícil'},
              {'puede_cambiarlo_gobierno': 'no_aplica'},
              {'involucrados': ['yo', 'entorno']},
              {'recursos_necesarios': ['Tiempo','Dinero']}
          ),
          ...
        }
    language : str, opcional
        'es' para generar el texto en español, 'en' para inglés. Por defecto 'es'.
    show_N_probabilidad : bool, opcional
        Si True, se muestra el valor de 'cluster_N_Proba' de cada cluster.
    show_Probabilidad : bool, opcional
        Si True, se muestra la 'cluster_ef_sample' de cada cluster.

    Retorna
    -------
    dict
        Diccionario cuyo índice corresponde al índice de la fila en 'variables_cambio'
        y cuyo valor es un string descriptivo (en el idioma seleccionado).
    """

    # Función auxiliar para intentar convertir valores a int o float
    def try_convert(val):
        try:
            return int(val)
        except ValueError:
            try:
                return float(val)
            except ValueError:
                return val  # Retorna el valor original si no es numérico

    # Mensajes en español/inglés según el parámetro `language`
    if language == 'es':
        txt_cluster = "Cluster"
        txt_original = "Descripción original"
        txt_condiciones = "Variables y rangos:"
        txt_prob = "Probabilidad"
        txt_conf = "Nivel de confianza (Baja:0, Alta 3)"
        txt_N_prob = "Incremento de probabilidad respecto a la media"
        txt_variable = "Variable"
        txt_range = "Rango"
        txt_desc = "Descripción"
        txt_cat = "Categorías en rango"
        txt_no_cat = "No categorías identificadas en este rango"
        txt_puedo = "¿Puedo cambiarlo yo?"
        txt_gob = "¿Puede cambiarlo el gobierno?"
        txt_invol = "Involucrados"
        txt_recursos = "Recursos"
    else:
        txt_cluster = "Group"
        txt_original = "Original description"
        txt_condiciones = "Variables and ranges:"
        txt_prob = "Probability"
        txt_conf = "Confidence Level (Low: 0, High: 3)"
        txt_N_prob = "Probability increment over average"
        txt_variable = "Variable"
        txt_range = "Range"
        txt_desc = "Description"
        txt_cat = "Categories in range"
        txt_no_cat = "No categories identified in this range"
        txt_puedo = "Can I change it?"
        txt_gob = "Can the government change it?"
        txt_invol = "Involved"
        txt_recursos = "Resources"

    # Regex para extraer límites y variable:
    # Ejemplo: "2.5 <= p133 - Ingreso total... <= 10.0"
    patron_intervalo = re.compile(
        r'([0-9.]+)\s*<=\s*(p[\w\d]+)\s*-\s*(.*?)\s*<=\s*([0-9.]+)'
    )
    patron_intervalo = re.compile(
        r'([+\-]?\d+(?:\.\d+)?)\s*<=\s*([^\s]+)\s*<=\s*([+\-]?\d+(?:\.\d+)?)'
    )

    descripciones_por_cluster = {}

    for idx, row in variables_cambio.iterrows():
        desc_cruda = row['cluster_descripcion']

        # Extraer N_probabilidad y Probabilidad (si existen)
        n_prob_value = row.get('cluster_N_Proba', None)
        prob_value = row.get('cluster_ef_sample', None)
        n_samp_val = row.get('cluster_n_sample', None)

        conf_val = str(row.get('nivel_de_confianza_cluster', None))

        # Dividir en sub-condiciones por "AND"
        condiciones = [c.strip() for c in desc_cruda.split('AND')]

        # Construir un encabezado conciso
        texto = []
        # Ej: "**Cluster 1**" o "**Group 1**"
        texto.append(f"**{txt_cluster} {idx}**")

        # Mostrar N_probabilidad y Probabilidad si se pide
        if show_N_probabilidad and (n_prob_value is not None):
            texto.append(f"- {txt_N_prob}: {n_prob_value:.2f}")
        if show_Probabilidad and (prob_value is not None):
            # Asumimos que Probabilidad es un decimal de 0 a 1. Mostramos en porcentaje.
            texto.append(f"- {txt_prob}: {prob_value:.1%}")

        texto.append(f"- {txt_conf}: {conf_val} ({n_samp_val} obs)")

        # Agregar descripción original (concisa)
        texto.append(f"- {txt_original}: {desc_cruda}")
        texto.append(f"- {txt_condiciones}")

        # Procesar cada condición
        for cond in condiciones:
            match = patron_intervalo.search(cond)
            if match:
                limite_inferior, variable, limite_superior = match.groups()

                # Info de data_desc
                if variable in data_desc:
                    desc_variable = data_desc[variable].get('Descripción', '')
                    # Intentar convertir los valores posibles
                    valores_originales = data_desc[variable].get('Valores', [])
                    valores_posibles = [try_convert(v) for v in valores_originales]
                    etiquetas_valores = data_desc[variable].get('Etiquetas', [])
                else:
                    desc_variable = ""
                    valores_posibles = []
                    etiquetas_valores = []

                # Info de nuevo_diccionario
                info_extra_plano = {}
                if variable in nuevo_diccionario:
                    for d in nuevo_diccionario[variable]:
                        info_extra_plano.update(d)

                # Construir texto corto de la variable
                subtexto = []
                subtexto.append(f"  - {txt_variable}: {variable}")

                # Agregamos su descripción si existe
                if desc_variable:
                    subtexto.append(f"    - {txt_desc}: {desc_variable}")

                # Agregar el rango
                subtexto.append(f"    - {txt_range}: {limite_inferior} a {limite_superior}")

                # Intentar mapear categorías
                cat_in_range = []
                for val, etiq in zip(valores_posibles, etiquetas_valores):
                    # Verificar si 'val' es numérico
                    if isinstance(val, (int, float)):
                        try:
                            li = float(limite_inferior)
                            ls = float(limite_superior)
                            if li <= val <= ls:
                                cat_in_range.append(f"{val}={etiq}")
                        except:
                            continue  # En caso de error en conversión, saltar
                    else:
                        # Si 'val' es una cadena (ej: '25-64'), verificar superposición
                        # Esto puede ser complejo; para simplificar, listamos todas las categorías no numéricas
                        cat_in_range.append(f"{val}={etiq}")

                if cat_in_range:
                    subtexto.append(f"    - {txt_cat}: {' | '.join(cat_in_range)}")
                else:
                    subtexto.append(f"    - {txt_no_cat}")

                # Info extra: ¿Puedo cambiarlo? etc.
                if 'puedo_cambiarlo_yo' in info_extra_plano:
                    subtexto.append(f"      - {txt_puedo}: {info_extra_plano['puedo_cambiarlo_yo']}")
                if 'puede_cambiarlo_gobierno' in info_extra_plano:
                    subtexto.append(f"      - {txt_gob}: {info_extra_plano['puede_cambiarlo_gobierno']}")
                if 'involucrados' in info_extra_plano:
                    inv_str = ', '.join(info_extra_plano['involucrados'])
                    subtexto.append(f"      - {txt_invol}: {inv_str}")
                if 'recursos_necesarios' in info_extra_plano:
                    rec_str = ', '.join(info_extra_plano['recursos_necesarios'])
                    subtexto.append(f"      - {txt_recursos}: {rec_str}")

                # Unir y agregar al texto global
                texto.extend(subtexto)
            else:
                # Si no se parseó (formato distinto)
                texto.append(f"  - {cond}")

        # Unir todo el texto en un solo bloque
        descripciones_por_cluster[idx] = "\n".join(texto)

    return descripciones_por_cluster
