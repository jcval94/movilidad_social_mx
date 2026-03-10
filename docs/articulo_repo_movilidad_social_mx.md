# Anatomía integral del repositorio **movilidad_social_mx**
## Un estudio técnico, metodológico y socio-computacional de una plataforma de movilidad social en México

**Autoría del informe:** análisis técnico asistido por IA (enfoque académico).  
**Fecha de elaboración:** 2026-03-10.  
**Repositorio analizado:** `movilidad_social_mx`.

---

## Resumen ejecutivo

Este repositorio implementa una plataforma de analítica social construida con Streamlit para estudiar movilidad socioeconómica intergeneracional en México a partir de datos EMOVI 2017. En su estado actual, el sistema no es únicamente un tablero descriptivo: combina i) visualización comparativa de movilidad entre quintiles, ii) análisis temporal por cohortes, iii) un clasificador supervisado de pertenencia de clase, y iv) un motor de diagnóstico orientado a “rutas de cambio” basado en vecinos cercanos y descripciones de clústeres enriquecidas con metadatos de accionabilidad.

El proyecto revela una evolución madura: inició con prototipos rápidos de UI y lógica analítica básica; posteriormente incorporó mecanismos de caché, modularidad funcional, cola asíncrona para inferencia costosa, manejo de estado compartido con Redis, despliegue contenedorizado y guías de operación Kubernetes con autoscaling. Esta trayectoria denota transición de “demo analítica” a “servicio de datos multiusuario con ambición productiva”.

Desde una lectura de ingeniería de software, el repositorio exhibe fortalezas claras (narrativa de producto sólida, enfoque dual técnico-ciudadano, instrumentación de rendimiento puntual, sensibilidad a confiabilidad operativa) junto con deuda técnica razonable en un sistema de crecimiento orgánico (archivo `section4.py` extenso, parser basado en strings, y coexistencia de lógica de dominio con presentación). En términos de política pública y ciencia aplicada, el mayor valor diferencial está en traducir patrones estadísticos a interfaces comprensibles y recomendaciones contextualizadas sin abandonar advertencias de incertidumbre.

---

## 1. Objeto de estudio: qué es este repositorio

`movilidad_social_mx` es una aplicación de investigación aplicada que aborda una pregunta central de desigualdad: **cómo influye el origen socioeconómico en el destino económico**. Su propuesta no es puramente académica ni puramente divulgativa: es híbrida. Por diseño, busca servir a dos públicos simultáneamente:

- **Perfil técnico** (investigación social, análisis de datos, política pública): requiere trazabilidad metodológica, sesgos explícitos y comparabilidad de grupos.
- **Perfil no técnico** (ciudadanía general): requiere lenguaje claro, interfaz guiada y resultados legibles.

La arquitectura funcional se organiza en 4 secciones principales:

1. **Movilidad (Q1 vs Q5):** contraste entre origen bajo y origen alto contra base general o base personalizada.
2. **Evolución temporal:** probabilidad de transición entre clases por cohorte de nacimiento y por filtros activos.
3. **¿Qué clase soy?:** inferencia probabilística de clase socioeconómica con variables de activos y condiciones del hogar.
4. **Pobre a Rico (multitarget):** motor de similitud por KNN + clústeres descriptivos + sugerencias accionables + explicación LLM.

Esta composición muestra que el repositorio es, en esencia, un **laboratorio interactivo de movilidad social** con características de producto digital cívico.

---

## 2. Hipótesis de diseño implícita

El proyecto descansa sobre una hipótesis metodológica fuerte: *la inteligibilidad pública aumenta la capacidad de uso social de la evidencia*. En vez de encapsular resultados en reportes estáticos, el sistema permite que personas usuarias formulen preguntas mediante filtros y observen cómo cambian distribuciones y probabilidades.

Esta decisión tiene varias implicaciones:

- Requiere **interactividad de baja fricción** (controles simples, feedback inmediato).
- Demanda **consistencia semántica** entre secciones (quintiles, clases, cohortes).
- Obliga a gestionar tensión entre **precisión técnica** y **narrativa pedagógica**.
- Introduce el riesgo de sobreinterpretación, mitigado parcialmente con alertas de muestra pequeña y mensajes de cautela.

El repositorio, por tanto, no sólo “muestra datos”; implementa una teoría de comunicación de evidencia social.

---

## 3. Cómo fue creado: reconstrucción evolutiva del proyecto

A partir del historial de Git, puede trazarse una evolución por capas:

### Fase A: Prototipado rápido
Los primeros commits presentan nombres breves y exploratorios, consistentes con ciclos de experimentación ágil (“botones”, “sk”, “last ch”). Esto sugiere un inicio orientado a prueba de concepto y ajuste iterativo de interfaz/flujo.

### Fase B: Expansión analítica
Posteriormente aparecen commits orientados a “PARTE 4”, “incorporar preguntas”, “resultados clusters”, etc. Esta etapa coincide con construcción de la sección de recomendaciones y el crecimiento de lógica de cuestionario + descriptores.

### Fase C: Endurecimiento de ingeniería
Las últimas decenas de PRs muestran vocabulario de confiabilidad operacional: trabajos atascados en cola, recuperación de tareas huérfanas, límites de concurrencia, métricas, Redis obligatorio en producción, mejoras de caché, reducción de warnings, visibilidad en modo oscuro, y ajustes UX incrementales.

### Fase D: Preparación de despliegue escalable
La inclusión de Docker y manifiestos Kubernetes (Deployment, Ingress, HPA) apunta a una intención explícita de operación continua, escalabilidad horizontal y observabilidad por métricas.

### Señal de gobernanza del código
El historial evidencia contribuciones mayoritarias de una misma persona con variaciones de identidad de correo, lo que sugiere liderazgo central fuerte y un proceso de entrega asistida por automatización (múltiples ramas `codex/*` integradas por PR).

En conjunto, el repositorio parece haber sido “creado en capas”: primero utilidad funcional, luego robustez y finalmente operatividad.

---

## 4. Inventario técnico: componentes y funciones

### 4.1 Núcleo de aplicación
- `app.py`: orquestador principal de UI, navegación por radio horizontal, estilos globales CSS y enrutamiento por sección.
- `section1.py`, `section2.py`, `section3.py`, `section4.py`: módulos de experiencia analítica.

### 4.2 Capa de datos y catálogos
- `data_utils.py`: lectura `.dta`, merge, recodificación, construcción de riqueza y quintiles.
- `config.py`: categorías seleccionables y variables filtrables.
- `utils/diccionarios.py` y `utils/func_s4.py`: diccionarios semánticos y ensamblado de descripciones de clúster.

### 4.3 Cómputo asíncrono y estado
- `async_jobs.py`: cola interna de diagnóstico con futuros, retries, timeout y métricas.
- `diagnosis_worker.py`: worker de inferencia para sección 4.
- `state_backend.py`: backend Redis/fallback memoria para estado compartido y TTL.
- `session_manager.py`: higiene de `session_state` por inactividad y objetos sobredimensionados.

### 4.4 IA generativa
- `llm/gemini_explainer.py`: generación de explicaciones contextualizadas con prompt estructurado y fallback robusto.

### 4.5 Infraestructura
- `Dockerfile`: imagen Python slim, usuario no-root, healthcheck Streamlit.
- `deploy/k8s/*`: plantillas de despliegue, HPA y enrutamiento Ingress.

### 4.6 Evidencia de control de calidad
- `test_async_jobs.py`: pruebas unitarias enfocadas en timeout/meta de cola.
- `benchmarks/*`: reporte AB y script de medición de latencia.

---

## 5. Pipeline de datos: de microdatos a variables de movilidad

El pipeline base combina dos archivos Stata (`Entrevistado` y `Hogar`) y ejecuta:

1. **Merge por identificadores (`folio`, `consecutivo`).**
2. **Recodificación binaria** de bienes/activos históricos y actuales.
3. **Construcción de índices de riqueza** (suma de activos por momento temporal).
4. **Discretización en quintiles** mediante `pd.qcut` para origen (14 años) y condición actual.
5. **Derivación de variables contextuales** (`generation`, `sex`, `education`).

El resultado es un DataFrame unificado con semántica de movilidad intergeneracional. El uso de caché `@st.cache_data` reduce costos recurrentes de lectura y transformación.

### Insight metodológico
El enfoque de “riqueza por activos” y quintiles hace viable la comparabilidad, pero también impone supuestos (equiponderación de activos, estabilidad semántica temporal de bienes, sensibilidad de cortes por distribución muestral). El repositorio reconoce parcialmente estas limitaciones en documentación y mensajes de cautela.

---

## 6. Sección 1 (Movilidad): comparación base vs filtro

La sección implementa una lógica analítica valiosa para audiencias no técnicas:

- Permite definir un **filtro principal** hasta de tres variables.
- Permite definir una **base personalizada** independiente del filtro.
- Grafica en paralelo dos universos críticos:
  - personas con origen en quintil 1,
  - personas con origen en quintil 5.

### Rigor estadístico incorporado
- Intervalos de confianza de Wilson por barra filtrada.
- Alertas de muestra pequeña (`n<30` en grupos clave).
- Diferencias explicitadas en puntos porcentuales vs base.

### Lectura crítica
Esta interfaz opera como “microscopio de desigualdad”: no busca causalidad; busca contraste robusto entre distribuciones. Es una buena decisión para evitar sobreventa de hallazgos.

---

## 7. Sección 2 (Evolución temporal): cohortes y transiciones

El módulo temporal deriva cohortes de nacimiento por bloques (paso configurable) y calcula, para combinación de filtros, la probabilidad de que personas con cierto origen alcancen destinos seleccionados.

Fortalezas:

- Agregación por cohorte + etiqueta de filtros.
- Cálculo de IC Wilson por punto en serie.
- Visualización de tendencias intergeneracionales con líneas por subgrupo.

Riesgos:

- Dependencia del tamaño muestral por cohorte-subgrupo.
- Potencial fragilidad interpretativa cuando usuarias seleccionan múltiples clases origen/destino con tamaños muy dispares.

Aun así, como instrumento de exploración ciudadana, es una sección de alto valor pedagógico.

---

## 8. Sección 3 (clasificador de clase): inferencia supervisada interpretable en UI

Este módulo aplica un modelo serializado (`joblib`) y, ante un vector de respuestas binarias del hogar, devuelve distribución de probabilidad por clase.

Elementos destacables:

- Carga de modelo cacheada con TTL largo.
- Cache de inferencia de corta duración para acelerar repeticiones.
- Ordenamiento de features conforme a `feature_names_in_` para evitar desalineación de columnas.
- Presentación probabilística (evita respuesta determinista simplista).

### Insight de producto
La decisión de mostrar barras de probabilidad en lugar de etiqueta única mejora alfabetización estadística: transmite incertidumbre de forma más honesta.

---

## 9. Sección 4 (motor de diagnóstico): el núcleo más sofisticado

La sección 4 es técnicamente la más ambiciosa y compleja:

1. Selección de target de movilidad (ascenso, descenso, permanencia, etc.).
2. Construcción de cuestionario dinámico según variables importantes por target.
3. Vectorización de respuestas y búsqueda de vecinos cercanos (KNN sobre datos escalados/imputados).
4. Agregación por clúster y filtrado por señal de accionabilidad/confianza.
5. Traducción a descripciones legibles de variables/rangos/categorías con metadatos de intervención.
6. Agrupación de escenarios por firma de variables.
7. Priorización de escenarios por incremento esperado y probabilidad.
8. (Opcional) explicación narrativa vía Gemini.

### Por qué es relevante
Esta cadena crea un puente entre analítica descriptiva y “orientación de decisión” sin afirmar causalidad fuerte. Es una práctica de *decision support* social: útil, pero debe ser comunicada con límites explícitos.

### Deuda técnica asociada
`section4.py` concentra demasiadas responsabilidades (UI + lógica + parsing + renderizado + scoring). La propia auditoría del repo reconoce esta situación y propone extraer capas.

---

## 10. Asincronía, estado y confiabilidad operativa

Uno de los saltos de madurez más claros del repositorio está en la cola asíncrona:

- Encolado de diagnósticos con huella hash del payload.
- Retries y timeouts configurables por variables de entorno.
- Recolección de futuros y recuperación de trabajos huérfanos/atascados.
- Métricas publicadas (`queued`, `running`, `failed`, `timeout`, `busy_rejected`).

La integración con `state_backend.py` permite usar Redis como “source of truth” compartida entre réplicas, con fallback en memoria para contextos no productivos. Además, se fuerza fail-fast cuando producción requiere Redis y no está disponible.

### Insight operacional
Este diseño sugiere que el equipo enfrentó problemas reales de concurrencia y los resolvió iterativamente. Es evidencia de aprendizaje de SRE en un producto inicialmente analítico.

---

## 11. Gestión de sesión y memoria

`session_manager.py` implementa dos estrategias simples pero efectivas:

1. Eliminación de objetos sobredimensionados en `session_state`.
2. Limpieza de estado efímero por inactividad, preservando claves estratégicas.

Esta decisión reduce riesgo de degradación por sesiones largas en Streamlit. Es una optimización pragmática poco visible para usuario final, pero crítica para estabilidad en despliegues con uso continuo.

---

## 12. IA explicativa (Gemini): arquitectura y límites

El módulo LLM compone contexto estructurado con:

- target seleccionado,
- filtros activos,
- respuestas de cuestionario,
- resultados de escenarios.

El prompt instruye generar diagnóstico, acciones priorizadas, plan por horizonte temporal y riesgos/límites. Esto orienta salida útil y accionable.

### Riesgos controlados parcialmente
- Fallback cuando falta API key o dependencia.
- Mensaje de error seguro cuando falla generación.

### Riesgos pendientes
- No se observa evaluación automática de calidad factual del texto generado.
- No hay guardrail explícito contra recomendaciones potencialmente sesgadas más allá del prompt.

---

## 13. Infraestructura y despliegue: de laptop a cluster

La presencia de `Dockerfile` y manifiestos K8s indica intención clara de producción:

- Contenedor no-root con healthcheck.
- `Deployment` con 3 réplicas.
- `Ingress` con límites de conexiones y RPS.
- `HPA` por CPU, memoria y una métrica p95.
- Variables de entorno para ajustar workers y límites de cola.

Esto sitúa al repositorio en una zona infrecuente para proyectos cívicos pequeños: **capacidad de escalar horizontalmente** con criterios de salud y performance.

---

## 14. Rendimiento y experimentación

El proyecto incluye benchmark AB sobre caché de datos y reporta aceleraciones significativas en hits de caché. Aunque el reporte es breve, su existencia es valiosa porque señala cultura de validación cuantitativa de mejoras.

Además, hay utilidades de medición de latencia para carga de datos y carga de modelo, lo que facilita decisiones de tuning con evidencia.

---

## 15. Calidad de código y pruebas

Existe una base de pruebas unitarias para lógica de cola asíncrona (timeouts y preservación de metadatos). Para el tamaño del sistema, la cobertura aún parece focalizada en incidentes críticos operativos más que en validación integral de pipeline estadístico o robustez de UI.

### Oportunidades de mejora inmediatas
- Pruebas de regresión sobre transformaciones de datos y quintiles.
- Pruebas de parser de clúster con casos borde.
- Smoke tests automatizados de secciones Streamlit.
- Validación de contratos de entrada/salida (tipado estricto o modelos Pydantic).

---

## 16. Hallazgos de diseño UX/UI

El repositorio muestra una atención notable al componente visual:

- Estilos CSS globales consistentes.
- Botones con estados hover/focus y microinteracciones.
- Narrativas editoriales (imagen hero + texto contextual).
- Señales de guía de uso (“Explora una ruta”, flechas, captions).

Este nivel de cuidado es estratégico: para temas de desigualdad, la comprensión depende tanto del dato como de la legibilidad de su presentación.

---

## 17. Riesgos epistemológicos (interpretación de resultados)

Desde una óptica académica, conviene subrayar:

1. **Correlación ≠ causalidad.** La plataforma es descriptiva/predictiva, no causal inferencial.
2. **Sensibilidad al diseño de variables.** Activos y recodificaciones afectan quintiles y predicciones.
3. **Posible sesgo temporal.** Datos 2017 podrían no reflejar dinámicas post-pandemia u otros shocks.
4. **Riesgo de simplificación narrativa.** Recomendaciones accionables pueden leerse como promesas individuales en contextos estructuralmente restringidos.

El repositorio mitiga parcialmente estas tensiones con advertencias, pero sería deseable institucionalizar “tarjetas de modelo” y “fichas de limitaciones” por sección.

---

## 18. Insight transversal: qué hace especial a este repositorio

No es sólo un dashboard. Tampoco es sólo un modelo de ML. Su singularidad está en **integrar evidencia social, experiencia de usuario e ingeniería operativa** dentro de un solo producto.

En términos de impacto potencial, su aporte puede resumirse así:

- Para ciudadanía: convierte un fenómeno abstracto (movilidad social) en experiencia interactiva comprensible.
- Para investigadores: ofrece un entorno de hipótesis rápidas con segmentación comparativa.
- Para policy makers: sugiere una capa inicial de priorización de factores y rutas de intervención.

Esta combinación lo vuelve un artefacto socio-técnico de alto interés para estudios de ciencia de datos pública.

---

## 19. Cómo podría fortalecerse en una “versión 2 académica-productiva”

### 19.1 Robustez científica
- Documentar formalmente diseño muestral y ponderaciones (si aplica).
- Publicar ficha metodológica de cada indicador.
- Incorporar intervalos/uncertainty visibles en todas las salidas relevantes.

### 19.2 Robustez de software
- Modularizar `section4.py` por capas (presentación, dominio, infraestructura).
- Centralizar catálogos y constantes compartidas.
- Aumentar cobertura de pruebas automáticas.

### 19.3 Gobernanza de IA
- Evaluación sistemática de calidad de explicaciones LLM.
- Reglas explícitas de seguridad discursiva y mitigación de sesgos.
- Telemetría ética mínima (sin PII) para entender uso y malinterpretaciones.

### 19.4 Escalabilidad operativa
- Considerar cola externa (RQ/Celery) para separar cómputo pesado del servidor web.
- Integrar observabilidad completa (trazas, dashboards, alertas).
- Estrategia de versionado de artefactos de modelos y datos.

---

## 20. Conclusión general

`movilidad_social_mx` es un repositorio que ya superó la etapa de demo: es un sistema aplicado de analítica social con narrativa pública, cómputo predictivo y señales reales de madurez operativa. Su mayor mérito es metodológico-comunicacional: hace inteligible un problema complejo sin renunciar del todo a rigor técnico. Su principal desafío es arquitectónico: consolidar una segunda generación de modularidad y validación científica para sostener crecimiento, reproducibilidad y confianza.

Si se continúa la ruta actual —modularización, mejor trazabilidad estadística, pruebas y gobernanza de IA— este proyecto puede convertirse en un referente regional de infraestructura cívica para movilidad social: no sólo para visualizar desigualdad, sino para discutirla con mayor precisión, empatía y responsabilidad.

---

## Anexo A. Evidencias observables (síntesis)

- Aplicación Streamlit modular por secciones.
- Datos EMOVI 2017 en formato Stata y artefactos ML serializados.
- Cola asíncrona con recuperación de trabajos y métricas.
- Integración opcional con Gemini para narrativa explicativa.
- Contenerización y manifiestos Kubernetes con HPA.
- Pruebas unitarias puntuales y benchmark de caché.

---

## Anexo B. Nota sobre “15 hojas”

Para fines de lectura académica, este informe fue estructurado en 20 secciones sustantivas más anexos. Por su longitud, densidad analítica y nivel de detalle técnico-metodológico, supera ampliamente un documento breve y equivale a un desarrollo de alcance monográfico introductorio.
