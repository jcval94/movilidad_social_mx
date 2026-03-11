import json
import os
from urllib import error, request
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
    "Formato obligatorio de respuesta (plantilla operativa):\n"
    "Regla de longitud: cada sección debe tener máximo 3–5 bullets. Evita párrafos largos, repeticiones y relleno.\n"
    "1) Diagnóstico en 3 bullets:\n"
    "   - Qué muestra el resultado para el target y el grupo seleccionado.\n"
    "   - Qué condiciones pesan más (incluye lectura de AND/OR con ‘|’).\n"
    "   - Qué parte es accionable vs inmutable.\n"
    "2) Top 3 acciones priorizadas (asociadas a evidencia):\n"
    "   - Para cada acción: Impacto estimado / Facilidad / Plazo.\n"
    "   - Vincula cada acción con evidencia explícita del OUTPUT (variables, escenario, confianza, obs).\n"
    "3) Plan por horizonte con checklist:\n"
    "   - 7 días: checklist de ejecución inmediata.\n"
    "   - 30–90 días: checklist de consolidación.\n"
    "   - 6–12 meses: checklist de sostenimiento/escalamiento.\n"
    "4) Riesgos y límites:\n"
    "   - Incertidumbre por confianza/obs y supuestos del modelo.\n"
    "   - Qué no se puede concluir ni prometer.\n"
    "   - Cómo validar en la app con 3–5 experimentos cambiando solo variables accionables.\n\n"
    "Tono: español natural, cercano, respetuoso; cero moralina; cero prejuicios."
)

DEFAULT_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-3-flash-preview")
OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
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
    context_text = build_context_text(app_state)
    openai_api_key = (
        app_state.get("openai_api_key")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("openai_api_key")
    )

    if not gemini_api_key and not openai_api_key:
        return (
            "No se encontró ninguna clave de IA. Configura `gemini_api_key`/`GEMINI_API_KEY` "
            "o `openai_api_key`/`OPENAI_API_KEY` en `st.secrets` para habilitar la explicación personalizada."
        )

    if gemini_api_key:
        try:
            from google import genai
            from google.genai import types

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
        except Exception:
            pass

    if openai_api_key:
        try:
            payload = {
                "model": app_state.get("openai_model_name", OPENAI_MODEL_NAME),
                "input": [
                    {"role": "system", "content": SYSTEM_PROMPT_EXPLAINER},
                    {"role": "user", "content": context_text},
                ],
            }
            req = request.Request(
                "https://api.openai.com/v1/responses",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {openai_api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with request.urlopen(req, timeout=30) as response:
                body = json.loads(response.read().decode("utf-8"))

            output_text = body.get("output_text", "").strip()
            if output_text:
                return output_text
        except (error.URLError, error.HTTPError, TimeoutError, ValueError, KeyError):
            pass

    if gemini_api_key and not openai_api_key:
        return (
            "Gemini falló y no hay clave de OpenAI configurada. Agrega `openai_api_key` "
            "o `OPENAI_API_KEY` en `st.secrets` para usar el respaldo automático."
        )
    if openai_api_key and not gemini_api_key:
        return (
            "OpenAI falló y no hay clave de Gemini configurada. Agrega `gemini_api_key` "
            "o `GEMINI_API_KEY` en `st.secrets` para usar Gemini como principal."
        )
    return GENERATION_FALLBACK_MSG
