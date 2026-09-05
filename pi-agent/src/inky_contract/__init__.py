"""Shared wire models for the Docker host and Raspberry Pi agent contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import re
from typing import Any, Mapping
from urllib.parse import urlsplit


class ContractError(ValueError):
    """Raised when a host response is outside the published contract."""


class JobEvent(str, Enum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"


def _required_string(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ContractError(f"{key} must be a non-empty string")
    return value


def _required_int(data: Mapping[str, Any], key: str) -> int:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractError(f"{key} must be an integer")
    return value


def _optional_datetime(data: Mapping[str, Any], key: str) -> datetime | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ContractError(f"{key} must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ContractError(f"{key} must be an ISO-8601 string") from error
    if parsed.tzinfo is None:
        raise ContractError(f"{key} must include a timezone")
    return parsed


@dataclass(frozen=True)
class ArtifactDescriptor:
    sha256: str
    url: str
    format: str
    media_type: str
    width: int
    height: int
    palette: tuple[str, ...]
    renderer_version: str

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> ArtifactDescriptor:
        sha256 = _required_string(data, "sha256").lower()
        if not re.fullmatch(r"[0-9a-f]{64}", sha256):
            raise ContractError("sha256 must be a 64-character hexadecimal digest")
        width = _required_int(data, "width")
        height = _required_int(data, "height")
        artifact_format = _required_string(data, "format")
        media_type = _required_string(data, "media_type")
        if (width, height) != (800, 480):
            raise ContractError("the Pi agent only supports 800x480 artifacts")
        if artifact_format != "rgb-png":
            raise ContractError("the host artifact format must be rgb-png")
        if media_type != "image/png":
            raise ContractError("the host artifact media type must be image/png")
        url = _required_string(data, "url")
        parsed_url = urlsplit(url)
        if not url.startswith("/") or parsed_url.scheme or parsed_url.netloc:
            raise ContractError("artifact url must be a relative path")
        raw_palette = data.get("palette")
        if not isinstance(raw_palette, list) or not raw_palette or not all(
            isinstance(colour, str) and colour for colour in raw_palette
        ):
            raise ContractError("palette must be a non-empty list of colour names")
        return cls(
            sha256=sha256,
            url=url,
            format=artifact_format,
            media_type=media_type,
            width=width,
            height=height,
            palette=tuple(raw_palette),
            renderer_version=_required_string(data, "renderer_version"),
        )


@dataclass(frozen=True)
class DesiredState:
    api_version: str
    display_id: str
    revision: int
    job_id: str
    artifact: ArtifactDescriptor
    not_before: datetime | None
    expires_at: datetime | None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> DesiredState:
        api_version = _required_string(data, "api_version")
        if api_version != "v1":
            raise ContractError(f"unsupported desired-state API version: {api_version}")
        raw_artifact = data.get("artifact")
        if not isinstance(raw_artifact, Mapping):
            raise ContractError("artifact must be an object")
        revision = _required_int(data, "revision")
        if revision < 0:
            raise ContractError("revision must not be negative")
        return cls(
            api_version=api_version,
            display_id=_required_string(data, "display_id"),
            revision=revision,
            job_id=_required_string(data, "job_id"),
            artifact=ArtifactDescriptor.from_mapping(raw_artifact),
            not_before=_optional_datetime(data, "not_before"),
            expires_at=_optional_datetime(data, "expires_at"),
        )
