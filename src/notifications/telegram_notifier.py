from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional


@dataclass(frozen=True)
class TelegramConfig:
    enabled: bool = False
    bot_token: str = ""
    primary_chat_id: str = ""
    secondary_chat_id: Optional[str] = None


class TelegramNotifier:
    def __init__(self, config: TelegramConfig, sender: Optional[Callable[[str, Dict[str, str]], None]] = None):
        self.config = config
        self._sender = sender or self._default_sender

    def send(self, message: str) -> Dict[str, bool]:
        if not self.config.enabled:
            return {"primary": False, "secondary": False}

        if not self.config.bot_token or not self.config.primary_chat_id:
            raise ValueError("Telegram enabled but missing bot_token or primary_chat_id")

        primary_payload = {"chat_id": self.config.primary_chat_id, "text": message}
        self._sender(self._endpoint(), primary_payload)
        sent_secondary = False

        if self.config.secondary_chat_id:
            secondary_payload = {"chat_id": self.config.secondary_chat_id, "text": message}
            self._sender(self._endpoint(), secondary_payload)
            sent_secondary = True

        return {"primary": True, "secondary": sent_secondary}

    def _endpoint(self) -> str:
        return f"https://api.telegram.org/bot{self.config.bot_token}/sendMessage"

    @staticmethod
    def _default_sender(url: str, payload: Dict[str, str]) -> None:
        import json
        from urllib.request import Request, urlopen

        data = json.dumps(payload).encode("utf-8")
        req = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(req, timeout=10):
            pass
