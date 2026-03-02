import json
import os
from typing import Any

SYSTEM_PROMPT_EXPLAINER = (
    "Eres un asistente de interpretación de resultados de un modelo de movilidad social. "
    "Convierte el INPUT y OUTPUT de la aplicación en una explicación clara, humana y accionable para el usuario.\n\n"
    "Reglas:\n"
    "- No inventes datos: usa únicamente lo que venga del contexto proporcionado por la app.\n"
    "- No prometas resultados; explica que son asociaciones del modelo, no garantías.\n"
    "- No recomiendes cambiar atributos inmutables; úsalos solo como contexto.\n"
    "- Recomienda SOLO acciones sobre variables marcadas como cambiables (p. ej., ‘fácil’, ‘medio’, ‘difícil’). Si es ‘imposible’, NO es recomendación.\n"
    "- Evita asesoría financiera de alto riesgo. Nada de inversiones específicas o endeudamiento agresivo.\n"
    "- Si la confianza/obs es baja, advierte inestabilidad.\n\n"
    "Cómo interpretar:\n"
    "- Grupo de Variables Clave = condiciones que deben cumplirse (AND entre variables; OR dentro de una variable con ‘|’).\n"
    "- Escenario: Incremento = relativo vs media; Probabilidad = absoluta; Confianza/obs = robustez.\n\n"
    "Formato obligatorio de respuesta:\n"
    "1) Resumen (3–5 líneas): Target, idea principal, probabilidad y comparación con la media.\n"
    "2) Qué significa este Grupo: condiciones; inmutables vs accionables; explicar ‘|’.\n"
    "3) Confiabilidad del diagnóstico (obligatoria):\n"
    "   - Nivel: Alta/Media/Baja.\n"
    "   - Justificación: explícitamente basada en Confianza y Obs de los escenarios.\n"
    "   - Recomendación de prudencia: indica qué tan conservador debe ser el usuario según el nivel.\n"
    "4) Acciones accionables (solo accionables): pasos concretos + dificultad + involucrados + recursos + señales de avance. Prioriza por impacto probable y facilidad.\n"
    "5) Plan por horizonte: 7 días; 30–90 días; 6–12 meses.\n"
    "6) Advertencias y cómo validar en la app: límites + 3–5 experimentos cambiando solo variables accionables disponibles.\n\n"
    "Tono: español natural, cercano, respetuoso; cero moralina; cero prejuicios."
)

DEFAULT_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-3-flash-preview")
GENERATION_FALLBACK_MSG = "No se pudo generar explicación, reintenta."


def _safe_text(value: Any) -> str:
    if value is None:
        return "no disponible"
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False)
    text = str(value).strip()
    return text if text else "no disponible"


def _format_filters(filters: list[dict[str, Any]]) -> str:
    if not filters:
        return "- No hay filtros activos."

    lines = []
    for filtro in filters:
        nombre = _safe_text(filtro.get("variable"))
        valores = filtro.get("values")
        if isinstance(valores, list) and valores:
            valor_txt = " | ".join(str(v) for v in valores)
        else:
            valor_txt = "no disponible"
        lines.append(f"- {nombre}: {valor_txt}")
    return "\n".join(lines)


def _format_questionnaire(questionnaire_rows: list[dict[str, Any]]) -> str:
    if not questionnaire_rows:
        return "- no disponible"

    lines = []
    for row in questionnaire_rows:
        desc = _safe_text(row.get("descripcion"))
        variable = _safe_text(row.get("variable"))
        respuesta = _safe_text(row.get("respuesta_texto"))
        lines.append(f"- {desc} ({variable}): {respuesta}")
    return "\n".join(lines)


def _format_results(groups: list[dict[str, Any]]) -> str:
    if not groups:
        return "- No hubo resultados del modelo para explicar."

    rendered_groups = []
    for idx, group in enumerate(groups, start=1):
        group_lines = [f"- Grupo #{idx}", "  - Variables clave:"]
        variables = group.get("variables", [])
        if not variables:
            group_lines.append("    - no disponible")
        for var in variables:
            descripcion = _safe_text(var.get("descripcion"))
            categorias = _safe_text(var.get("categorias"))
            cambio_yo = _safe_text(var.get("change_level"))
            involucrados = _safe_text(var.get("involucrados"))
            recursos = _safe_text(var.get("recursos"))
            group_lines.append(f"    - {descripcion}: {categorias}")
            group_lines.append(f"      - ¿Puedo cambiarlo yo?: {cambio_yo}")
            group_lines.append(f"      - Involucrados: {involucrados}")
            group_lines.append(f"      - Recursos: {recursos}")

        group_lines.append("  - Escenarios asociados:")
        scenarios = group.get("scenarios", [])
        if not scenarios:
            group_lines.append("    - no disponible")

        for scenario in scenarios:
            summary = scenario.get("summary", {})
            group_lines.append(
                "    - "
                f"Escenario { _safe_text(scenario.get('nombre')) }: "
                f"incremento={_safe_text((summary.get('incremento') or {}).get('text'))}, "
                f"probabilidad={_safe_text(summary.get('probabilidad'))}, "
                f"Confianza={_safe_text(summary.get('confianza'))}, "
                f"Obs={_safe_text(summary.get('obs'))}"
            )
        rendered_groups.append("\n".join(group_lines))

    return "\n\n".join(rendered_groups)


def build_context_text(app_state: dict[str, Any]) -> str:
    target = _safe_text(app_state.get("target_label") or app_state.get("target"))
    return (
        f"### TARGET\n- {target}\n\n"
        f"### FILTROS\n{_format_filters(app_state.get('active_filters', []))}\n\n"
        f"### CUESTIONARIO (INPUT)\n{_format_questionnaire(app_state.get('questionnaire', []))}\n\n"
        f"### RESULTADOS (OUTPUT)\n{_format_results(app_state.get('results', []))}"
    )


def generate_explanation(app_state: dict[str, Any]) -> str:
    gemini_api_key = (
        app_state.get("gemini_api_key")
        or os.getenv("GEMINI_API_KEY")
        or os.getenv("gemini_api_key")
    )
    if not gemini_api_key:
        return (
            "No se encontró la clave de Gemini. Configúrala en `st.secrets` "
            "como `gemini_api_key` o `GEMINI_API_KEY` para habilitar la explicación personalizada."
        )

    try:
        from google import genai
        from google.genai import types
    except Exception:
        return (
            "Falta la dependencia `google-genai`. Instálala con "
            "`pip install -U google-genai`."
        )

    context_text = build_context_text(app_state)

    try:
        os.environ["GEMINI_API_KEY"] = gemini_api_key
        client = genai.Client()
        response = client.models.generate_content(
            model=app_state.get("model_name", DEFAULT_MODEL_NAME),
            contents=context_text,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT_EXPLAINER,
            ),
        )
        text = getattr(response, "text", None)
        if text:
            return text
        return GENERATION_FALLBACK_MSG
    except Exception:
        return GENERATION_FALLBACK_MSG
