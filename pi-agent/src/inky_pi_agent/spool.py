"""Crash-safe local artifact and state storage for the Pi agent."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from uuid import uuid4

from PIL import Image

from inky_contract import ArtifactDescriptor, JobEvent

EXPECTED_ARTIFACT_DIMENSIONS = (800, 480)


@dataclass(frozen=True)
class PendingAcknowledgement:
    event: str
    job_id: str
    revision: int
    error_code: str | None = None
    error_message: str | None = None

    @property
    def job_event(self) -> JobEvent:
        return JobEvent(self.event)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> PendingAcknowledgement:
        return cls(
            event=str(data["event"]),
            job_id=str(data["job_id"]),
            revision=int(str(data["revision"])),
            error_code=str(data["error_code"]) if data.get("error_code") else None,
            error_message=str(data["error_message"]) if data.get("error_message") else None,
        )


@dataclass(frozen=True)
class AgentState:
    current_revision: int = 0
    last_successful_artifact_sha256: str | None = None
    last_heartbeat_at: str | None = None
    pending_acknowledgement: PendingAcknowledgement | None = None

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> AgentState:
        pending = data.get("pending_acknowledgement")
        return cls(
            current_revision=int(str(data.get("current_revision", 0))),
            last_successful_artifact_sha256=(
                str(data["last_successful_artifact_sha256"])
                if data.get("last_successful_artifact_sha256")
                else None
            ),
            last_heartbeat_at=str(data["last_heartbeat_at"]) if data.get("last_heartbeat_at") else None,
            pending_acknowledgement=PendingAcknowledgement.from_dict(pending) if isinstance(pending, dict) else None,
        )


class AgentSpool:
    """Keeps verified artifacts and state durable through agent restarts."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.artifacts = root / "artifacts"
        self.tmp = root / "tmp"
        self.state_path = root / "state.json"
        for directory in (self.root, self.artifacts, self.tmp):
            directory.mkdir(parents=True, exist_ok=True)

    def load_state(self) -> AgentState:
        if not self.state_path.exists():
            return AgentState()
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("agent state must be an object")
            return AgentState.from_dict(data)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return AgentState()

    def save_state(self, state: AgentState) -> None:
        payload = json.dumps(asdict(state), sort_keys=True).encode("utf-8") + b"\n"
        self._atomic_write_bytes(self.state_path, payload)

    def artifact_path(self, sha256: str) -> Path:
        return self.artifacts / sha256[:2] / f"{sha256}.png"

    def has_artifact(self, sha256: str | None) -> bool:
        return sha256 is not None and self.artifact_path(sha256).is_file()

    def install_download(self, descriptor: ArtifactDescriptor, chunks: Iterable[bytes]) -> Path:
        """Verify a streamed download, then atomically install it by checksum."""

        destination = self.artifact_path(descriptor.sha256)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.tmp / f"{uuid4()}.download"
        digest = hashlib.sha256()
        try:
            with temporary.open("xb") as output:
                for chunk in chunks:
                    if not isinstance(chunk, bytes):
                        raise ValueError("artifact download yielded non-bytes data")
                    digest.update(chunk)
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            if digest.hexdigest() != descriptor.sha256:
                raise ValueError("artifact SHA-256 checksum does not match desired state")
            self._validate_image(temporary, descriptor)
            if destination.exists():
                try:
                    self._validate_image(destination, descriptor)
                except (OSError, SyntaxError, ValueError):
                    # A damaged cache entry must not prevent a verified download
                    # from replacing it.
                    os.replace(temporary, destination)
                    self._fsync_directory(destination.parent)
            else:
                os.replace(temporary, destination)
                self._fsync_directory(destination.parent)
            return destination
        finally:
            temporary.unlink(missing_ok=True)

    @staticmethod
    def _validate_image(path: Path, descriptor: ArtifactDescriptor) -> None:
        if (descriptor.width, descriptor.height) != EXPECTED_ARTIFACT_DIMENSIONS:
            raise ValueError("desired artifact does not match the fixed 800x480 display configuration")
        with Image.open(path) as image:
            if image.format != "PNG":
                raise ValueError("artifact must be a PNG image")
            expected_mode = "RGB"
            if image.mode != expected_mode:
                raise ValueError(f"artifact format {descriptor.format} requires a {expected_mode} PNG")
            if image.size != EXPECTED_ARTIFACT_DIMENSIONS:
                raise ValueError(
                    f"artifact dimensions {image.width}x{image.height} do not match the fixed 800x480 display configuration"
                )
            image.verify()

    def _atomic_write_bytes(self, destination: Path, content: bytes) -> None:
        temporary = self.tmp / f"{uuid4()}.state"
        try:
            with temporary.open("xb") as output:
                output.write(content)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, destination)
            self._fsync_directory(destination.parent)
        finally:
            temporary.unlink(missing_ok=True)

    @staticmethod
    def _fsync_directory(directory: Path) -> None:
        descriptor = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
