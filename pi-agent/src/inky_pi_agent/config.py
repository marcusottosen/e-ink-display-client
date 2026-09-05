"""Environment-based configuration for the Pi agent."""

from __future__ import annotations

import os
import shlex
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from . import __version__


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            raise ValueError(f"invalid configuration line {line_number} in {path}")
        key, raw_value = line.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"invalid configuration line {line_number} in {path}")
        parsed = shlex.split(raw_value, comments=True)
        values[key] = parsed[0] if parsed else ""
    return values


def _bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"invalid boolean value: {value}")


@dataclass(frozen=True)
class AgentSettings:
    server_url: str = "http://192.168.0.101:8000"
    display_id: str = "inky-main"
    data_dir: Path = Path("/var/lib/inky-agent")
    device_token: str = ""
    poll_interval_seconds: int = 10
    heartbeat_interval_seconds: int = 60
    request_timeout_seconds: float = 30.0
    retry_initial_seconds: float = 2.0
    retry_max_seconds: float = 60.0
    hardware_enabled: bool = True
    agent_version: str = __version__

    @classmethod
    def from_env(cls, env_file: Path = Path("/etc/inky-agent/config.env")) -> AgentSettings:
        values = _read_env_file(env_file)
        prefix = "INKY_AGENT_"
        values.update({key: value for key, value in os.environ.items() if key.startswith(prefix)})

        def get(name: str, default: str) -> str:
            return values.get(prefix + name, default)

        settings = cls(
            server_url=get("SERVER_URL", cls.server_url),
            display_id=get("DISPLAY_ID", cls.display_id),
            data_dir=Path(get("DATA_DIR", str(cls.data_dir))),
            device_token=get("DEVICE_TOKEN", cls.device_token),
            poll_interval_seconds=int(get("POLL_INTERVAL_SECONDS", str(cls.poll_interval_seconds))),
            heartbeat_interval_seconds=int(get("HEARTBEAT_INTERVAL_SECONDS", str(cls.heartbeat_interval_seconds))),
            request_timeout_seconds=float(get("REQUEST_TIMEOUT_SECONDS", str(cls.request_timeout_seconds))),
            retry_initial_seconds=float(get("RETRY_INITIAL_SECONDS", str(cls.retry_initial_seconds))),
            retry_max_seconds=float(get("RETRY_MAX_SECONDS", str(cls.retry_max_seconds))),
            hardware_enabled=_bool(get("HARDWARE_ENABLED", str(cls.hardware_enabled))),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        parsed = urlsplit(self.server_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("INKY_AGENT_SERVER_URL must be an http:// or https:// URL")
        if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            raise ValueError("INKY_AGENT_SERVER_URL must not include a path, query, or fragment")
        if not self.display_id:
            raise ValueError("INKY_AGENT_DISPLAY_ID must not be empty")
        if self.poll_interval_seconds < 5 or self.heartbeat_interval_seconds < 5:
            raise ValueError("poll and heartbeat intervals must be at least five seconds")
        if self.request_timeout_seconds <= 0:
            raise ValueError("request timeout must be positive")
        if self.retry_initial_seconds <= 0 or self.retry_max_seconds < self.retry_initial_seconds:
            raise ValueError("retry intervals are invalid")

    @property
    def base_url(self) -> str:
        return self.server_url.rstrip("/")
