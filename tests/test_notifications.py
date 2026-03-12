from datetime import datetime, timezone

from src.notifications.message_builder import MessageContext, NotificationEvent, build_message
from src.notifications.ntfy_notifier import NtfyConfig, NtfyNotifier
from src.notifications.resend_notifier import ResendConfig, ResendNotifier
from src.notifications.telegram_notifier import TelegramConfig, TelegramNotifier


def test_message_builder_includes_required_fields_for_open():
    ctx = MessageContext(
        event=NotificationEvent.OPEN,
        timestamp=datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc),
        strategy_name="alpha",
        session_id="sess-1",
        top_picks=["AAA", "BBB"],
        top_blocks=["CCC"],
        expected_floor=-0.01,
        expected_ceiling=0.03,
        expected_bucket="BULLISH",
        reward_risk=2.4,
        recommended_action="increase exposure",
        risk_changes=["volatility up"],
        actions_taken=["hedge reduced"],
    )

    msg = build_message(ctx)
    assert "[OPEN]" in msg
    assert "top_picks=AAA, BBB" in msg
    assert "top_blocks=CCC" in msg
    assert "piso_esperado=-1.00%" in msg
    assert "techo_esperado=3.00%" in msg
    assert "bucket_esperado=BULLISH" in msg
    assert "reward_risk=2.40" in msg
    assert "accion_recomendada=increase exposure" in msg


def test_message_builder_supports_all_events():
    for event in NotificationEvent:
        msg = build_message(
            MessageContext(
                event=event,
                timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
                strategy_name="s",
                session_id="x",
            )
        )
        assert event.value in msg


def test_telegram_notifier_primary_and_secondary():
    sent = []

    def fake_sender(url, payload):
        sent.append((url, payload))

    notifier = TelegramNotifier(
        TelegramConfig(enabled=True, bot_token="tok", primary_chat_id="1", secondary_chat_id="2"),
        sender=fake_sender,
    )
    result = notifier.send("hello")

    assert result == {"primary": True, "secondary": True}
    assert len(sent) == 2
    assert all("sendMessage" in url for url, _ in sent)


def test_ntfy_notifier_primary_only():
    sent = []

    def fake_sender(url, message, headers):
        sent.append((url, message, headers))

    notifier = NtfyNotifier(
        NtfyConfig(enabled=True, server_url="https://ntfy.sh", primary_topic="main"),
        sender=fake_sender,
    )
    result = notifier.send("body", title="OPEN")

    assert result == {"primary": True, "secondary": False}
    assert len(sent) == 1
    assert sent[0][2]["Title"] == "OPEN"


def test_resend_notifier_secondary_optional():
    sent = []

    def fake_sender(url, payload, headers):
        sent.append((url, payload, headers))

    notifier = ResendNotifier(
        ResendConfig(
            enabled=True,
            api_key="k",
            from_email="bot@example.com",
            primary_to="a@example.com",
            secondary_to="b@example.com",
        ),
        sender=fake_sender,
    )
    result = notifier.send("subject", "body")

    assert result == {"primary": True, "secondary": True}
    assert len(sent) == 2
