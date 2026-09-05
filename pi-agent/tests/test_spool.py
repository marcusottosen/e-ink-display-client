import hashlib
from io import BytesIO

import pytest
from PIL import Image

from inky_contract import ArtifactDescriptor
from inky_pi_agent.spool import AgentSpool


def png_bytes(mode="RGB"):
    image = Image.new(mode, (800, 480), 0)
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def descriptor_for(payload):
    return ArtifactDescriptor(
        url="/artifact",
        sha256=hashlib.sha256(payload).hexdigest(),
        width=800,
        height=480,
        format="rgb-png",
        media_type="image/png",
        palette=("black", "white", "red", "yellow", "blue", "green"),
        renderer_version="1.1.0",
    )


def test_spool_verifies_and_atomically_installs_rgb_png(tmp_path):
    payload = png_bytes()
    spool = AgentSpool(tmp_path / "state")
    descriptor = descriptor_for(payload)

    path = spool.install_download(descriptor, [payload[:17], payload[17:]])

    assert path == spool.artifact_path(descriptor.sha256)
    assert path.is_file()
    assert not list(spool.tmp.iterdir())


def test_spool_rejects_checksum_mismatch(tmp_path):
    payload = png_bytes()
    spool = AgentSpool(tmp_path / "state")
    descriptor = descriptor_for(payload + b"different")

    with pytest.raises(ValueError, match="checksum"):
        spool.install_download(descriptor, [payload])

    assert not list(spool.artifacts.rglob("*.png"))


def test_spool_rejects_paletted_artifact(tmp_path):
    payload = png_bytes("P")
    spool = AgentSpool(tmp_path / "state")
    descriptor = descriptor_for(payload)

    with pytest.raises(ValueError, match="requires a RGB"):
        spool.install_download(descriptor, [payload])


def test_spool_replaces_corrupt_cached_artifact(tmp_path):
    payload = png_bytes()
    spool = AgentSpool(tmp_path / "state")
    descriptor = descriptor_for(payload)
    destination = spool.artifact_path(descriptor.sha256)
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"corrupt cache")

    path = spool.install_download(descriptor, [payload])

    assert path.read_bytes() == payload
