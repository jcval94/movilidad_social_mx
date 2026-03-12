import pytest

from src.backtest.cost_model import CostConfig, CostModel
from src.backtest.execution_simulator import ExecutionConfig
from src.execution.paper_executor import PaperExecutorConfig
from src.notifications.ntfy_notifier import NtfyConfig, NtfyNotifier
from src.notifications.resend_notifier import ResendConfig, ResendNotifier
from src.notifications.telegram_notifier import TelegramConfig, TelegramNotifier


def test_backtest_config_validation_rejects_negative_costs():
    with pytest.raises(ValueError):
        CostModel(CostConfig(commission_bps=-1))

    with pytest.raises(ValueError):
        ExecutionConfig(fill_ratio=1.5).validate()


def test_paper_executor_default_live_disabled_and_paper_enabled():
    cfg = PaperExecutorConfig()
    cfg.validate()

    with pytest.raises(ValueError):
        PaperExecutorConfig(paper_trading_enabled=False).validate()

    with pytest.raises(ValueError):
        PaperExecutorConfig(live_trading_enabled=True).validate()


def test_notifier_configs_require_mandatory_fields_when_enabled():
    with pytest.raises(ValueError):
        TelegramNotifier(TelegramConfig(enabled=True, bot_token="", primary_chat_id="")).send("msg")

    with pytest.raises(ValueError):
        NtfyNotifier(NtfyConfig(enabled=True, primary_topic="")).send("msg")

    with pytest.raises(ValueError):
        ResendNotifier(ResendConfig(enabled=True, api_key="", from_email="", primary_to="")).send("s", "m")
