<div align="center">

# 🌍🇲🇽 Movilidad Social en México
### *Una plataforma de análisis ciudadano para entender oportunidades, brechas y trayectorias de vida*

[![Demo en Streamlit](https://img.shields.io/badge/Demo-Streamlit-ff4b4b?logo=streamlit&logoColor=white)](https://movilidadsocialmx-cfha5gdjbcohddyg9c3ftb.streamlit.app/)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![Datos](https://img.shields.io/badge/Datos-EMOVI%202017-0a7ea4)](#-datos-y-modelos)
[![Estado](https://img.shields.io/badge/Estado-Activo-2ea44f)](#)

**Diseñado para dos públicos al mismo tiempo:**

🧠 **Personas técnicas (investigación, análisis y política pública)** → evidencia, metodología y trazabilidad.  
👨‍👩‍👧‍👦 **Público general** → explicaciones claras, visuales y accionables.

</div>

---

## 🚀 Ver la aplicación en vivo

> ### 🔗 https://movilidadsocialmx-cfha5gdjbcohddyg9c3ftb.streamlit.app/
>
> Puedes abrirla directamente en navegador, sin instalación local.

---

## 🧭 Índice

- [1) ¿Por qué este proyecto importa?](#1-por-qué-este-proyecto-importa)
- [2) ¿Qué problema resuelve?](#2-qué-problema-resuelve)
- [3) ¿Qué hace diferente a esta propuesta?](#3-qué-hace-diferente-a-esta-propuesta)
- [4) Arquitectura de la solución](#4-arquitectura-de-la-solución)
- [5) Guía de uso por ventanas](#5-guía-de-uso-por-ventanas)
  - [5.1 Controles globales](#51-controles-globales)
  - [5.2 Ventana 1: Movilidad](#52-ventana-1-movilidad)
  - [5.3 Ventana 2: Evolución Temporal](#53-ventana-2-evolución-temporal)
  - [5.4 Ventana 3: ¿Qué clase soy?](#54-ventana-3-qué-clase-soy)
  - [5.5 Ventana 4: Pobre a Rico](#55-ventana-4-pobre-a-rico)
- [6) Cómo interpretar resultados sin errores comunes](#6-cómo-interpretar-resultados-sin-errores-comunes)
- [7) Datos y modelos](#7-datos-y-modelos)
- [8) Ejecución local (paso a paso)](#8-ejecución-local-paso-a-paso)
- [9) Estructura del repositorio](#9-estructura-del-repositorio)
- [10) Limitaciones y próximos pasos](#10-limitaciones-y-próximos-pasos)
- [11) Solución de problemas](#11-solución-de-problemas)

---

## 1) ¿Por qué este proyecto importa?

La movilidad social no es sólo un tema económico: es una pregunta sobre **justicia de oportunidades**.  
Este proyecto traduce datos complejos en una experiencia visual que ayuda a responder una duda clave:

> **¿Qué tanto influye el origen social en el destino de las personas en México?**

Con esta app, cualquier persona puede explorar patrones de movilidad y comparar grupos de forma transparente.

---

## 2) ¿Qué problema resuelve?

Muchas herramientas de análisis social son difíciles de usar fuera del ámbito técnico. Esta plataforma cierra esa brecha al ofrecer:

- ✅ **Interfaz intuitiva** para usuarios no especialistas.
- ✅ **Rigor analítico** para análisis técnico y toma de decisiones.
- ✅ **Comparaciones claras** entre filtros, cohortes y objetivos de movilidad.
- ✅ **Resultados interpretables** (no sólo métricas abstractas).

---

## 3) ¿Qué hace diferente a esta propuesta?

### Enfoque dual: “impacto + entendibilidad”

| Elemento | Valor para personas técnicas | Valor para público general |
|---|---|---|
| Visualizaciones comparativas | Permiten contrastes entre base y subgrupos | Se entienden en segundos |
| Series por cohorte | Muestran tendencias intergeneracionales | Ayudan a “contar historias” de cambio |
| Modelo probabilístico de clase | Introduce predicción con trazabilidad de variables | Da retroalimentación inmediata y concreta |
| Recomendaciones por target | Conecta perfiles similares con acciones posibles | Traduce análisis en lenguaje práctico |

### Principios de diseño

- **Claridad antes que complejidad.**
- **Interpretabilidad antes que opacidad.**
- **Decisiones con contexto, no con números aislados.**

---

## 4) Arquitectura de la solución

La aplicación está construida en **Streamlit** y organizada por módulos:

- `app.py` → layout principal, barra lateral y tabs.
- `section1.py` → comparación de movilidad (Q1 vs Q5) con filtros/base.
- `section2.py` → evolución temporal por cohorte (origen → destino).
- `section3.py` → clasificación probabilística de clase socioeconómica.
- `section4.py` → recomendaciones de cambio por target (KNN + clusters descriptivos).
- `data_utils.py` y `config.py` → procesamiento base y catálogos.

> 🔍 El diseño modular permite auditar, extender y mantener cada componente por separado.

---

## 5) Guía de uso por ventanas

## 5.1 Controles globales

En la barra lateral aparecen controles que afectan varias vistas:

- **⟳ Refresh**: reinicia el estado de la sesión.
- **🎲 Random**: genera filtros/selecciones aleatorias para exploración rápida.
- **Filtro principal**: define segmentaciones para análisis comparado.

---

## 5.2 Ventana 1: Movilidad

### ¿Qué responde?

Compara cómo se distribuye el destino socioeconómico para quienes vienen de:

- **Origen Clase Baja (Q1)**
- **Origen Clase Alta (Q5)**

### ¿Qué ves en pantalla?

- Selección de hasta 3 variables de filtro.
- Selección de categorías por variable.
- Opción **Cambiar base** para benchmark personalizado.
- Gráfica con barras **Base vs Filtro** en dos subplots (Q1 y Q5).

### ¿Cómo leerla bien?

- Si **Filtro** se aleja de **Base**, hay diferencias relevantes entre grupos.
- Evita conclusiones fuertes cuando el filtro deja pocos casos.

---

## 5.3 Ventana 2: Evolución Temporal

### ¿Qué responde?

¿Qué porcentaje de personas pasa de una(s) clase(s) de **origen** a una(s) de **destino** en distintas cohortes?

### ¿Qué ves en pantalla?

- Multiselect de clases de **Origen**.
- Multiselect de clases de **Destino**.
- Serie de líneas con marcadores:
  - Eje X: cohorte de nacimiento.
  - Eje Y: probabilidad/porcentaje de transición.
  - Color: grupos según filtros activos.

### ¿Cómo leerla bien?

- Cambios de pendiente reflejan variación intergeneracional.
- Diferencias entre líneas muestran desigualdades entre subgrupos.

---

## 5.4 Ventana 3: ¿Qué clase soy?

### ¿Qué responde?

Estimación de la probabilidad de pertenecer a una clase socioeconómica con base en condiciones/activos del hogar.

### ¿Qué ves en pantalla?

- Formulario de checkboxes (ej. automóvil, lavadora, microondas, agua entubada).
- Botón **Procesar**.
- Barras de probabilidad por clase.
- Clase más probable como resumen textual.

### ¿Cómo leerla bien?

> Resultado **probabilístico**, no determinista.  
> Si dos clases aparecen cercanas, la diferencia puede no ser concluyente.

---

## 5.5 Ventana 4: Pobre a Rico

> Aunque el tab se llama “Pobre a Rico”, internamente admite múltiples **targets**: subir, bajar, permanecer, etc.

### ¿Qué responde?

¿Qué variables y combinaciones de condiciones se asocian con un objetivo de movilidad para perfiles similares?

### ¿Qué ves en pantalla?

1. Selector de **Target**.
2. Cuestionario dinámico.
3. Botón **Ejecutar**.
4. Resultados por cluster con:
   - probabilidad/incremento,
   - nivel de confianza,
   - variables clave y rangos,
   - factores accionables (involucrados, recursos, posibilidad de cambio).

### ¿Cómo leerla bien?

- Son **patrones descriptivos**, no garantías individuales.
- Prioriza clusters con mayor señal y mayor confianza.

---

## 6) Cómo interpretar resultados sin errores comunes

Para evitar malas conclusiones:

1. **No confundir correlación con causalidad.**
2. **No sobresegmentar** (muestras pequeñas elevan ruido).
3. **Comparar siempre contra una base** (general o personalizada).
4. **Triangular con contexto social y territorial**.
5. **Usar la app como brújula analítica**, no como sentencia definitiva.

---

## 7) Datos y modelos

### Fuentes de datos

- `data/ESRU-EMOVI 2017 Entrevistado.dta`
- `data/ESRU-EMOVI 2017 Hogar.dta`

### Modelo de clasificación

- `models/modelo_entrenado.joblib`

### Artefactos para recomendaciones (Sección 4)

- `data/df_valiosas_dict.joblib`
- `data/df_feature_importances_total.joblib`
- `data/df_clusterizados_total_origi.csv`

> ℹ️ Cambios en preprocesamiento o entrenamiento pueden alterar los resultados.

---

## 8) Ejecución local (paso a paso)

### Requisitos

- Python 3.9+
- `pip`

### Instalación

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configurar Gemini (explicación personalizada IA)

Agrega la clave en `.streamlit/secrets.toml` (o en los secretos de Streamlit Cloud). La app acepta ambos nombres (`gemini_api_key` o `GEMINI_API_KEY`):

```toml
gemini_api_key = "TU_CLAVE"
# o equivalente:
# GEMINI_API_KEY = "TU_CLAVE"
```

> Recomendado: `gemini_api_key`. Nunca subas esta clave al repositorio ni la imprimas en logs.

### Levantar la aplicación

```bash
streamlit run app.py
```

Por defecto abre en `http://localhost:8501`.

---

## 9) Estructura del repositorio

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

## 10) Limitaciones y próximos pasos

### Limitaciones actuales

- Dependencia de datos históricos (EMOVI 2017).
- Resultados sensibles al diseño de variables y filtros.
- Recomendaciones de la sección 4 son descriptivas, no causales.

### Próximas mejoras sugeridas

- Integrar métricas de incertidumbre visibles para cada gráfica.
- Añadir glosario interactivo para términos socioeconómicos.
- Publicar ejemplos guiados por perfil de usuario (estudiante, policy maker, investigador).
- Incorporar comparaciones regionales más finas en una nueva ventana.

---

## 11) Solución de problemas

### La app no arranca

- Activa tu entorno virtual.
- Reinstala dependencias con `pip install -r requirements.txt`.
- Ejecuta `streamlit run app.py` desde la raíz del proyecto.

### No aparecen resultados

- Reduce filtros para aumentar tamaño de muestra.
- Usa **Refresh** para reiniciar estado.

### Falta un archivo de datos/modelo

- Verifica contenido de `data/` y `models/`.
- Revisa rutas relativas y permisos de lectura.

---

<div align="center">

## 💡 Mensaje final

Este proyecto busca algo simple pero poderoso:  
**convertir datos de movilidad social en decisiones más informadas, más humanas y más útiles para todos.**

</div>


---

## 12) Despliegue escalable en contenedores

Se añadió una base de despliegue productiva en `Dockerfile` y `deploy/k8s/`:

- **Containerización optimizada** con usuario no-root y `HEALTHCHECK`.
- **Kubernetes con múltiples réplicas** (`Deployment`).
- **Balanceador con NGINX Ingress** frente al `Service`.
- **Sin afinidad de sesión** (arquitectura stateless).
- **Autoscaling** con HPA por CPU, memoria y latencia p95.

Consulta `deploy/k8s/README.md` para pasos de build/push y aplicación de manifiestos.

---

## 12) Procesamiento asíncrono (Sección 4)

Para evitar bloqueos de UI (>1–2s), el diagnóstico de la sección **Pobre a Rico** ahora se ejecuta en cola con **RQ + Redis**.

### Acciones movidas a background

- Cálculo de vecinos/cluster y filtrado de escenarios.
- Construcción de descripciones por cluster.
- Generación de explicación con Gemini.

### Flujo

1. Streamlit encola el job con `idempotency_key` (hash del payload).
2. La app responde de inmediato con estado **"Procesando"** y hace polling cada 2s.
3. Worker separado consume la cola `diagnostics`.
4. Resultado/error se persiste en SQLite (`data/job_results.sqlite`) para reutilizar cómputos.

### Timeouts, reintentos e idempotencia

- Timeout por job: `JOB_TIMEOUT_SECONDS` (default: `90`).
- Reintentos: `JOB_RETRIES` (default: `2`, intervalos 5s y 20s).
- Idempotencia: `job_id == idempotency_key` para evitar duplicados.

### Ejecutar localmente

```bash
# 1) Levantar Redis (ejemplo rápido)
docker run -p 6379:6379 redis:7

# 2) Instalar dependencias
pip install -r requirements.txt

# 3) Correr worker en terminal separada
python -m async_jobs.worker

# 4) Correr streamlit
streamlit run app.py
```
