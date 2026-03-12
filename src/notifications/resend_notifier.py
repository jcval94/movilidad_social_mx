from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional


@dataclass(frozen=True)
class ResendConfig:
    enabled: bool = False
    api_key: str = ""
    from_email: str = ""
    primary_to: str = ""
    secondary_to: Optional[str] = None


class ResendNotifier:
    def __init__(self, config: ResendConfig, sender: Optional[Callable[[str, Dict[str, object], Dict[str, str]], None]] = None):
        self.config = config
        self._sender = sender or self._default_sender

    def send(self, subject: str, message: str) -> Dict[str, bool]:
        if not self.config.enabled:
            return {"primary": False, "secondary": False}
        if not self.config.api_key or not self.config.from_email or not self.config.primary_to:
            raise ValueError("Resend enabled but api_key/from_email/primary_to missing")

        self._sender(
            "https://api.resend.com/emails",
            {
                "from": self.config.from_email,
                "to": [self.config.primary_to],
                "subject": subject,
                "text": message,
            },
            {"Authorization": f"Bearer {self.config.api_key}", "Content-Type": "application/json"},
        )
        sent_secondary = False
        if self.config.secondary_to:
            self._sender(
                "https://api.resend.com/emails",
                {
                    "from": self.config.from_email,
                    "to": [self.config.secondary_to],
                    "subject": subject,
                    "text": message,
                },
                {"Authorization": f"Bearer {self.config.api_key}", "Content-Type": "application/json"},
            )
            sent_secondary = True
        return {"primary": True, "secondary": sent_secondary}

    @staticmethod
    def _default_sender(url: str, payload: Dict[str, object], headers: Dict[str, str]) -> None:
        import json
        from urllib.request import Request, urlopen

        req = Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urlopen(req, timeout=10):
            pass
