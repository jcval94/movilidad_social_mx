import json

from data_utils import load_and_process_data_uncached


def build_mobility_dataset_payload(_: str) -> dict:
    df = load_and_process_data_uncached()
    return {
        "records": df.to_dict(orient="records"),
        "columns": list(df.columns),
        "row_count": len(df),
    }
