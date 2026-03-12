from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional


@dataclass(frozen=True)
class NtfyConfig:
    enabled: bool = False
    server_url: str = "https://ntfy.sh"
    primary_topic: str = ""
    secondary_topic: Optional[str] = None
    auth_token: Optional[str] = None


class NtfyNotifier:
    def __init__(self, config: NtfyConfig, sender: Optional[Callable[[str, str, Dict[str, str]], None]] = None):
        self.config = config
        self._sender = sender or self._default_sender

    def send(self, message: str, title: str = "alert") -> Dict[str, bool]:
        if not self.config.enabled:
            return {"primary": False, "secondary": False}
        if not self.config.primary_topic:
            raise ValueError("Ntfy enabled but primary_topic is missing")

        self._sender(self._topic_url(self.config.primary_topic), message, self._headers(title))
        sent_secondary = False
        if self.config.secondary_topic:
            self._sender(self._topic_url(self.config.secondary_topic), message, self._headers(title))
            sent_secondary = True
        return {"primary": True, "secondary": sent_secondary}

    def _topic_url(self, topic: str) -> str:
        return f"{self.config.server_url.rstrip('/')}/{topic}"

    def _headers(self, title: str) -> Dict[str, str]:
        headers = {"Title": title}
        if self.config.auth_token:
            headers["Authorization"] = f"Bearer {self.config.auth_token}"
        return headers

    @staticmethod
    def _default_sender(url: str, message: str, headers: Dict[str, str]) -> None:
        from urllib.request import Request, urlopen

        req = Request(url, data=message.encode("utf-8"), headers=headers, method="POST")
        with urlopen(req, timeout=10):
            pass
