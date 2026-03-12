from datetime import datetime, timezone

from src.storage.export_pages_data import export_pages_dataset


def test_export_pages_removes_sensitive_fields(tmp_path):
    out = export_pages_dataset(
        base_dir=str(tmp_path),
        dataset="dashboard_overview",
        records=[
            {
                "ticker": "AAA",
                "score": 0.9,
                "api_key": "SECRET",
                "token": "SHOULD_NOT_LEAK",
                "internal_notes": "private",
            }
        ],
        ts=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
    )

    latest_json = (tmp_path / "dashboard_overview" / "latest" / "latest.json").read_text(encoding="utf-8")

    assert "api_key" not in latest_json
    assert "token" not in latest_json
    assert "internal_notes" not in latest_json
    assert "ticker" in latest_json
    assert out["json_latest"].endswith("latest.json")
