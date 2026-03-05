from llm.gemini_explainer import generate_explanation
from section4 import (
    build_cluster_target_frame,
    filter_cluster_results,
    format_all_clusters,
    get_nuevo_diccionario,
    get_data_desc,
    load_section4_assets,
    obtener_vecinos_de_mi_respuesta,
)
from utils.func_s4 import construir_descripciones_cluster
from async_jobs.store import upsert_result


def run_section4_diagnostic_job(payload: dict) -> dict:
    idempotency_key = payload["idempotency_key"]
    try:
        assets = load_section4_assets(payload.get("base_path", "data"))
        user_selected_target = payload["target"]

        df_cluster_target = build_cluster_target_frame(
            assets["df_clusterizados_total_origi"],
            user_selected_target,
        )
        df_valiosas = assets["df_valiosas_dict"][user_selected_target]

        questionnaire_rows = payload["questionnaire"]
        import pandas as pd

        df_respuestas = pd.DataFrame(questionnaire_rows)
        df_resultados = obtener_vecinos_de_mi_respuesta(
            df_respuestas,
            df_cluster_target,
            df_valiosas,
            n_vecinos=50,
        )

        if not df_resultados.empty and "cluster_N_Proba" in df_resultados.columns:
            df_resultados["nivel_de_confianza_cluster"] = pd.qcut(
                df_resultados["cluster_N_Proba"],
                q=4,
                labels=False,
                duplicates="drop",
            )

        df_filtrado = filter_cluster_results(df_resultados)
        data_desc_global = get_data_desc()

        resultado = construir_descripciones_cluster(
            df_filtrado,
            data_desc_global,
            get_nuevo_diccionario(),
            language="es",
            show_N_probabilidad=True,
            show_Probabilidad=True,
        )
        grouped_results = format_all_clusters(resultado)

        app_state = {
            "target": user_selected_target,
            "target_label": payload["target_label"],
            "active_filters": payload["active_filters"],
            "questionnaire": questionnaire_rows,
            "results": grouped_results,
            "gemini_api_key": payload.get("gemini_api_key", ""),
        }
        explanation = generate_explanation(app_state)

        final_result = {
            "grouped_results": grouped_results,
            "explanation": explanation,
        }
        upsert_result(idempotency_key=idempotency_key, status="finished", result=final_result)
        return final_result
    except Exception as exc:
        upsert_result(idempotency_key=idempotency_key, status="failed", error_message=str(exc))
        raise
