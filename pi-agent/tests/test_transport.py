import hashlib
from io import BytesIO

import httpx
from PIL import Image

from inky_pi_agent.config import AgentSettings
from inky_contract import ArtifactDescriptor, JobEvent
from inky_pi_agent.spool import AgentSpool
from inky_pi_agent.transport import HostClient


def rgb_png():
    image = Image.new("RGB", (800, 480), (255, 0, 0))
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_host_client_uses_documented_pull_endpoints(tmp_path):
    payload = rgb_png()
    digest = hashlib.sha256(payload).hexdigest()
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path == "/api/v1/displays/inky-main/desired":
            return httpx.Response(
                200,
                json={
                    "api_version": "v1",
                    "display_id": "inky-main",
                    "job_id": "job-1",
                    "revision": 1,
                    "artifact": {
                        "url": f"/api/v1/artifacts/{digest}",
                        "sha256": digest,
                        "width": 800,
                        "height": 480,
                        "format": "rgb-png",
                        "media_type": "image/png",
                        "palette": ["black", "white", "red", "yellow", "blue", "green", "orange"],
                        "renderer_version": "1.1.0",
                    },
                    "not_before": None,
                    "expires_at": None,
                },
            )
        if request.url.path == f"/api/v1/artifacts/{digest}":
            return httpx.Response(200, content=payload)
        return httpx.Response(204)

    settings = AgentSettings(
        server_url="http://inky-host",
        display_id="inky-main",
        device_token="secret",
        data_dir=tmp_path / "state",
        poll_interval_seconds=5,
        heartbeat_interval_seconds=5,
    )
    client = HostClient(settings, httpx.Client(transport=httpx.MockTransport(handler)))
    spool = AgentSpool(settings.data_dir)

    desired = client.desired_state(0)
    path = client.download_artifact(desired.artifact, spool)
    client.heartbeat(0, None)
    client.acknowledge("job-1", JobEvent.COMPLETED, revision=1)
    client.close()

    assert path.is_file()
    assert requests[0].url.params["current_revision"] == "0"
    assert all(request.headers["Authorization"] == "Bearer secret" for request in requests)
    assert [request.url.path for request in requests] == [
        "/api/v1/displays/inky-main/desired",
        f"/api/v1/artifacts/{digest}",
        "/api/v1/displays/inky-main/heartbeat",
        "/api/v1/displays/inky-main/jobs/job-1/completed",
    ]
