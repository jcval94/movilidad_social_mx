<div align="center">

# 🇲🇽 Movilidad Social en México
### *Plataforma interactiva basada en EMOVI 2017*

[![Streamlit App](https://img.shields.io/badge/Streamlit-Producción-ff4b4b?logo=streamlit&logoColor=white)](https://movilidadsocialmx-cfha5gdjbcohddyg9c3ftb.streamlit.app/)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![Status](https://img.shields.io/badge/Estado-Activo-2ea44f)](#)

**Explora, compara e interpreta trayectorias de movilidad socioeconómica de forma visual, clara y accionable.**

</div>

---

## ✨ Sitio en producción

> Accede a la aplicación desplegada aquí:  
> **🔗 https://movilidadsocialmx-cfha5gdjbcohddyg9c3ftb.streamlit.app/**

---

## 🧭 Tabla de contenido

- [🎯 ¿Qué resuelve este proyecto?](#qué-resuelve-este-proyecto)
- [🏗️ Arquitectura funcional](#arquitectura-funcional)
- [🚀 Inicio rápido](#inicio-rápido)
- [🖥️ Guía completa por ventanas](#guía-completa-por-ventanas)
  - [1) Movilidad](#1-movilidad)
  - [2) Evolución Temporal](#2-evolución-temporal)
  - [3) ¿Qué clase soy?](#3-qué-clase-soy)
  - [4) Pobre a Rico](#4-pobre-a-rico)
- [🧠 Cómo interpretar resultados correctamente](#cómo-interpretar-resultados-correctamente)
- [🗂️ Datos, modelos y artefactos](#datos-modelos-y-artefactos)
- [📁 Estructura del repositorio](#estructura-del-repositorio)
- [🛠️ Solución de problemas](#solución-de-problemas)

---

## 🎯 ¿Qué resuelve este proyecto?

Esta aplicación permite analizar movilidad social con una experiencia amigable para perfiles técnicos y no técnicos.

### Capacidades clave

| Capacidad | ¿Para qué sirve? |
|---|---|
| Comparación entre grupos | Contrastar movilidad entre segmentos poblacionales usando filtros. |
| Evolución intergeneracional | Observar cambios por cohorte de nacimiento. |
| Estimación de clase | Inferir probabilidades de clase socioeconómica con un modelo supervisado. |
| Recomendaciones por objetivo | Identificar variables asociadas a metas de movilidad (ej. “de pobre a rico”). |

---

## 🏗️ Arquitectura funcional

El proyecto está organizado de forma modular:

- **`app.py`**: orquestador principal, layout, tabs y controles globales.
- **`section1.py`**: análisis comparativo de movilidad con filtros y base de referencia.
- **`section2.py`**: series de transición por cohorte (origen → destino).
- **`section3.py`**: formulario de activos del hogar + predicción probabilística.
- **`section4.py`**: motor de recomendaciones por target con KNN + clusters.
- **`data_utils.py` / `config.py`**: carga de datos, mapeos y catálogos de variables.

> 💡 **Diseño del flujo**: un filtro principal alimenta varias vistas para favorecer comparabilidad entre ventanas.

---

## 🚀 Inicio rápido

### 1) Requisitos

- Python **3.9+** (recomendado 3.10+)
- `pip`

### 2) Instalación

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3) Ejecución local

```bash
streamlit run app.py
```

La app abrirá normalmente en: `http://localhost:8501`

---

## 🖥️ Guía completa por ventanas

### Controles globales (sidebar)

Antes de entrar a cada pestaña, hay tres elementos transversales:

- **⟳ Refresh**: reinicia estado (`session_state`) y recarga la app.
- **🎲 Random**: genera selecciones aleatorias útiles para exploración rápida.
- **Filtro principal**: concentra segmentación dinámica que impacta varias visualizaciones.

---

## 1) Movilidad

### Objetivo
Comparar la distribución de destino socioeconómico para personas que parten de:

- **Origen Clase Baja (Q1)**
- **Origen Clase Alta (Q5)**

### ¿Qué ve el usuario?

- Selector de variables (máx. 3) y categorías asociadas.
- Opción **Cambiar base** para definir benchmark personalizado.
- Visual de barras comparando **Base vs Filtro** en dos subplots (Q1 y Q5).
- Encabezado con descripción textual de filtros activos.

### Clave de lectura

✅ Úsala para evaluar brechas relativas entre grupos.  
⚠️ Si filtras demasiado, revisa estabilidad por tamaño de muestra.

---

## 2) Evolución Temporal

### Objetivo
Medir el porcentaje de personas que transitan de clase(s) de **origen** a clase(s) de **destino**, por cohorte.

### ¿Qué ve el usuario?

- Multiselect de **Origen** y **Destino**.
- Gráfica de líneas con marcadores:
  - Eje X: cohorte de nacimiento.
  - Eje Y: probabilidad/porcentaje de transición.
  - Color: grupos derivados de filtros.

### Clave de lectura

- Pendientes positivas/negativas muestran cambios generacionales.
- Diferencias de color reflejan heterogeneidad entre segmentos.

---

## 3) ¿Qué clase soy?

### Objetivo
Estimar la clase socioeconómica mediante un formulario de condiciones/activos del hogar.

### ¿Qué ve el usuario?

- Checkboxes de variables del hogar (ej. automóvil, lavadora, microondas, agua entubada).
- Botón **Procesar**.
- Gráfica de barras con probabilidad por clase.
- Mensaje con la clase de mayor probabilidad.

### Clave de lectura

> El resultado es **probabilístico**, no determinístico.  
> Si varias clases quedan cercanas, interpreta con cautela.

---

## 4) Pobre a Rico

> Aunque la pestaña se llama “Pobre a Rico”, permite múltiples **targets** (subir, bajar, permanecer, etc.).

### Objetivo
Generar recomendaciones interpretables para un objetivo específico de movilidad social.

### ¿Qué ve el usuario?

1. Selector de **Target** con nombres amigables.
2. Cuestionario dinámico (preguntas según variables relevantes).
3. Botón **Ejecutar**.
4. Resultados por cluster con:
   - incremento/probabilidad,
   - nivel de confianza,
   - variables y rangos,
   - señales accionables (quién puede cambiarlo, involucrados, recursos).

### Clave de lectura

- Interpreta los resultados como **patrones en perfiles similares**, no como reglas universales.
- Prioriza clusters con mayor señal y mayor confianza.

---

## 🧠 Cómo interpretar resultados correctamente

Para un uso responsable del análisis:

- **No confundir correlación con causalidad**.
- **Evitar sobresegmentar** (muestras pequeñas → estimaciones inestables).
- **Comparar contra base** (general o personalizada) para contexto.
- **Triangular con evidencia externa** (contexto regional, histórico y política pública).

---

## 🗂️ Datos, modelos y artefactos

### Datos base

- `data/ESRU-EMOVI 2017 Entrevistado.dta`
- `data/ESRU-EMOVI 2017 Hogar.dta`

### Modelo de clasificación

- `models/modelo_entrenado.joblib`

### Artefactos analíticos (sección 4)

- `data/df_valiosas_dict.joblib`
- `data/df_feature_importances_total.joblib`
- `data/df_clusterizados_total_origi.csv`

> ℹ️ Si cambian preprocesamiento, features o modelos, los resultados de la app pueden variar de forma significativa.

---

## 📁 Estructura del repositorio

```text
.
├── app.py
├── section1.py
├── section2.py
├── section3.py
├── section4.py
├── data_utils.py
├── config.py
├── cuestionario.py
├── utils/
│   ├── diccionarios.py
│   └── func_s4.py
├── data/
│   ├── ESRU-EMOVI 2017 Entrevistado.dta
│   ├── ESRU-EMOVI 2017 Hogar.dta
│   ├── df_clusterizados_total_origi.csv
│   ├── df_feature_importances_total.joblib
│   └── df_valiosas_dict.joblib
├── models/
│   └── modelo_entrenado.joblib
└── requirements.txt
```

---

## 🛠️ Solución de problemas

### 1) La app no inicia

- Verifica entorno activo y dependencias:
  - `source .venv/bin/activate`
  - `pip install -r requirements.txt`
- Asegúrate de ejecutar desde la raíz del repo:
  - `streamlit run app.py`

### 2) Faltan archivos (`.joblib`, `.csv`, `.dta`)

- Revisa rutas y existencia de archivos en `data/` y `models/`.
- Confirma permisos de lectura.

### 3) Resultados vacíos

- Reduce filtros.
- Usa **⟳ Refresh** para reiniciar estado.

### 4) Sección 4 tarda en responder

- Es esperable por el cálculo de vecinos y construcción de descripciones por cluster.
- Evita ejecuciones consecutivas con combinaciones muy complejas en equipos limitados.

---

<div align="center">

### Hecho con datos, visualización y enfoque de movilidad social 📊

Si quieres, en la siguiente iteración puedo convertir este README en una versión **con capturas por ventana** y mini tutorial visual paso a paso.

</div>
