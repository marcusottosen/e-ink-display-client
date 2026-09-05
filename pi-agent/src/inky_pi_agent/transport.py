"""HTTP client for the outbound Pi-pull host API."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote, urljoin, urlsplit

import httpx

from .config import AgentSettings
from inky_contract import ArtifactDescriptor, DesiredState, JobEvent
from .spool import AgentSpool


class HostClient:
    """Only makes outbound requests from the Pi to the configured host."""

    def __init__(self, settings: AgentSettings, client: httpx.Client | None = None) -> None:
        self._settings = settings
        self._client = client or httpx.Client(
            timeout=settings.request_timeout_seconds,
            follow_redirects=False,
        )

    def close(self) -> None:
        self._client.close()

    def desired_state(self, current_revision: int) -> DesiredState | None:
        response = self._client.get(
            self._url(f"/api/v1/displays/{self._display_path}/desired"),
            params={"current_revision": current_revision},
            headers=self._headers(),
        )
        if response.status_code == httpx.codes.NO_CONTENT:
            return None
        response.raise_for_status()
        payload = response.json()
        if payload is None or payload == {}:
            return None
        if not isinstance(payload, dict):
            raise ValueError("desired-state response must be a JSON object")
        return DesiredState.from_mapping(payload)

    def download_artifact(self, descriptor: ArtifactDescriptor, spool: AgentSpool) -> Path:
        with self._client.stream("GET", self._url(descriptor.url), headers=self._headers()) as response:
            response.raise_for_status()
            return spool.install_download(descriptor, response.iter_bytes())

    def heartbeat(self, current_revision: int, artifact_sha256: str | None) -> None:
        response = self._client.post(
            self._url(f"/api/v1/displays/{self._display_path}/heartbeat"),
            headers=self._headers(),
            json={
                "current_revision": current_revision,
                "last_successful_artifact_sha256": artifact_sha256,
                "sent_at": datetime.now(UTC).isoformat(),
            },
        )
        response.raise_for_status()

    def acknowledge(
        self,
        job_id: str,
        event: JobEvent,
        *,
        revision: int | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        response = self._client.post(
            self._url(f"/api/v1/displays/{self._display_path}/jobs/{quote(job_id, safe='')}/{event.value}"),
            headers=self._headers(),
            json={
                "event": event.value,
                "completed_revision": revision if event is JobEvent.COMPLETED else None,
                "error_code": error_code,
                "error_message": error_message,
                "occurred_at": datetime.now(UTC).isoformat(),
            },
        )
        response.raise_for_status()

    @property
    def _display_path(self) -> str:
        return quote(self._settings.display_id, safe="")

    def _headers(self) -> dict[str, str]:
        token = self._settings.device_token
        return {"Authorization": f"Bearer {token}"} if token else {}

    def _url(self, path: str) -> str:
        if urlsplit(path).scheme:
            return path
        return urljoin(self._settings.base_url + "/", path.lstrip("/"))
