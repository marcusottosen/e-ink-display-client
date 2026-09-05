from datetime import UTC, datetime

from PIL import Image

from inky_pi_agent.agent import InkyAgent
from inky_pi_agent.config import AgentSettings
from inky_contract import ArtifactDescriptor, DesiredState, JobEvent
from inky_pi_agent.hardware import NoopDisplayDriver, SerializedDisplayWorker
from inky_pi_agent.spool import AgentSpool


class FakeTransport:
    def __init__(self, artifact_path):
        self.artifact_path = artifact_path
        self.heartbeats = []
        self.acknowledgements = []
        self.desired = DesiredState(
            api_version="v1",
            display_id="inky-main",
            job_id="job-1",
            revision=1,
            artifact=ArtifactDescriptor(
                url="/artifact",
                sha256="a" * 64,
                width=800,
                height=480,
                format="rgb-png",
                media_type="image/png",
                palette=("black", "white", "red", "yellow", "blue", "green"),
                renderer_version="1.1.0",
            ),
            not_before=None,
            expires_at=None,
        )

    def desired_state(self, current_revision):
        return self.desired if current_revision < self.desired.revision else None

    def download_artifact(self, descriptor, spool):
        return self.artifact_path

    def heartbeat(self, current_revision, artifact_sha256):
        self.heartbeats.append((current_revision, artifact_sha256))

    def acknowledge(self, job_id, event, **kwargs):
        self.acknowledgements.append((job_id, event, kwargs))


def test_agent_polls_refreshes_and_persists_completion(tmp_path):
    artifact = tmp_path / "artifact.png"
    image = Image.new("RGB", (800, 480), 0)
    image.save(artifact, format="PNG")

    spool = AgentSpool(tmp_path / "state")
    transport = FakeTransport(artifact)
    settings = AgentSettings(
        data_dir=tmp_path / "state",
        hardware_enabled=False,
        poll_interval_seconds=5,
        heartbeat_interval_seconds=5,
    )
    agent = InkyAgent(settings, transport, spool, SerializedDisplayWorker(NoopDisplayDriver()))

    assert agent.run_once(datetime(2026, 8, 30, tzinfo=UTC)) is True

    assert transport.heartbeats == [(0, None)]
    assert [event[1] for event in transport.acknowledgements] == [JobEvent.STARTED, JobEvent.COMPLETED]
    assert agent.state.current_revision == 1
    assert agent.state.last_successful_artifact_sha256 == "a" * 64
    assert agent.state.pending_acknowledgement is None
