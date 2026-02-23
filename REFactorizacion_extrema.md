# Auditoría para refactorización extrema

## 1) Hallazgos críticos (alto impacto)

1. **`section4.py` concentra demasiadas responsabilidades (782 líneas).**
   - Mezcla UI de Streamlit, lógica de cuestionario, preparación de datos, KNN y formateo de texto.
   - Tiene funciones duplicadas en el mismo archivo (`cuestionario_general`, `generar_lista_preguntas`, `preguntar_opciones_streamlit`, `preguntar_numero_streamlit`), elevando riesgo de inconsistencias.
   - **Refactor propuesto:** dividir en módulos: `ui/section4_view.py`, `services/neighbors.py`, `services/cluster_formatter.py`, `domain/questionnaire.py`.

2. **Carga de datos pesada se repite y no está cacheada.**
   - `load_and_process_data()` lee dos `.dta`, hace `merge`, recodifica y recalcula quintiles en cada invocación.
   - `show_section1()` y `show_section2()` llaman esa función de forma independiente.
   - **Refactor propuesto:** `@st.cache_data` para datasets procesados y separación de pipeline puro (sin Streamlit) para testabilidad.

3. **Acoplamiento fuerte a `st.session_state` en lógica de negocio.**
   - Varias funciones combinan lectura de estado + cálculo + render.
   - **Refactor propuesto:** pasar filtros como dataclasses (`FilterConfig`) y mantener funciones puras para transformación.

4. **Código muerto / legado dentro de archivos activos.**
   - Bloques enormes comentados en `section4.py` y funciones demo en `cuestionario.py` que no parecen formar parte del flujo principal.
   - **Refactor propuesto:** eliminar o mover a `legacy/` y mantener rama/tag histórica.

5. **Duplicación de constantes y catálogos de clase social.**
   - `CLASS_TO_QUINTILES` existe en `section2.py` y `section3.py`.
   - **Refactor propuesto:** centralizar en `constants.py`.

## 2) Riesgos funcionales / bugs potenciales

6. **`section4.py` define la misma función varias veces.**
   En Python, prevalece la última definición: comportamiento confuso y difícil de depurar.

7. **Manejo de rutas relativo/inconsistente.**
   - Hay rutas tipo `data/...`, `models/...`, y en `cuestionario.py` una absoluta de Colab (`/content/...`).
   - **Refactor propuesto:** capa de configuración de paths (`pathlib.Path`, `BASE_DIR`).

8. **No hay validación robusta para archivos faltantes en todas las secciones.**
   - Solo algunas rutas validan existencia antes de cargar.
   - **Refactor propuesto:** `DataRepository` con errores tipados y mensajes uniformes.

9. **Posible fragilidad en formateo/parsing de descripciones de clúster.**
   - Se usa regex sobre strings complejos y hay múltiples versiones de lógica en archivos.
   - **Refactor propuesto:** parser formal con tests de casos reales.

10. **Transformaciones in-place sobre DataFrames en funciones UI.**
   - Puede generar advertencias (`SettingWithCopy`) y efectos secundarios difíciles de rastrear.

## 3) Rendimiento

11. **Uso intensivo de `DataFrame.apply(..., axis=1)` para labels en `section2.py`.**
   - Escala mal con datasets grandes.
   - **Refactor propuesto:** vectorización con `agg` sobre columnas seleccionadas.

12. **KNN se recalcula cada ejecución del formulario en `section4.py`.**
   - Escalado + imputación + fit de `NearestNeighbors` en cada submit.
   - **Refactor propuesto:** precomputar/serializar pipeline (`imputer+scaler+index`) y solo consultar en runtime.

13. **Cálculos de distribuciones repetidos y no reutilizados en `section1.py`.**
   - **Refactor propuesto:** helper genérico para construir comparativas base/filtro.

## 4) Arquitectura objetivo (extrema, pero sostenible)

14. **Separación por capas:**
   - `presentation/` (Streamlit puro)
   - `application/` (casos de uso)
   - `domain/` (reglas)
   - `infrastructure/` (carga archivos/joblib/dta)

15. **Contrato de datos con modelos tipados.**
   - Usar `pydantic` o `dataclasses` para respuestas de cuestionario, filtros y resultados de clúster.

16. **Repositorio de datos único.**
   - Unificar `load_and_process_data`, cargas de joblib/csv y catálogos.

17. **Registro y trazabilidad.**
   - Logging estructurado para tiempos de carga, número de filas post-filtro y errores.

## 5) Calidad de código y mantenimiento

18. **Estandarizar estilo y checks automáticos.**
   - `ruff`, `black`, `isort`, `mypy` (mínimo gradual), pre-commit.

19. **Agregar suite de pruebas mínima por valor.**
   - Unit tests para recodificación/quintiles/generaciones.
   - Snapshot tests para formateo de clúster.
   - Test de integración liviano para pipeline de `section4`.

20. **Eliminar imports no usados y comentarios obsoletos.**
   - Mejora señal/ruido y velocidad de lectura.

## 6) Plan sugerido por fases

### Fase 0 (rápida: 1-2 días)
- Quitar duplicados de funciones en `section4.py`.
- Centralizar constantes (`CLASS_TO_QUINTILES`, labels de quintiles, paths base).
- Introducir cache en carga de datos pesada.

### Fase 1 (media: 3-5 días)
- Extraer capa `services/` para cálculos de movilidad y vecinos.
- Volver puras funciones clave (sin `session_state`).
- Añadir pruebas unitarias de cálculo.

### Fase 2 (profunda: 1-2 semanas)
- Reorganización por capas + repositorio de datos.
- Parser robusto de descripciones de clúster.
- Instrumentación de rendimiento y calidad CI.

## 7) ROI esperado

- **Tiempo de carga menor** (cache + preprocesado único).
- **Menos regresiones** (funciones puras + tests).
- **Mayor velocidad de evolución** (módulos pequeños y claros).
- **Mejor confiabilidad** en resultados y explicación de clusters.
