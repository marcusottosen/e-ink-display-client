import pytest

from inky_contract import ArtifactDescriptor, ContractError, DesiredState


def descriptor_data(**overrides):
    data = {
        "url": "/api/v1/artifacts/" + "a" * 64,
        "sha256": "a" * 64,
        "width": 800,
        "height": 480,
        "format": "rgb-png",
        "media_type": "image/png",
        "palette": ["black", "white", "red", "yellow", "blue", "green", "orange"],
        "renderer_version": "1.1.0",
    }
    data.update(overrides)
    return data


def test_desired_state_parses_versioned_job():
    desired = DesiredState.from_mapping(
        {
            "api_version": "v1",
            "display_id": "inky-main",
            "job_id": "job-1",
            "revision": 4,
            "artifact": descriptor_data(),
            "not_before": "2026-08-30T12:00:00Z",
        }
    )

    assert desired.job_id == "job-1"
    assert desired.revision == 4
    assert desired.artifact.format == "rgb-png"
    assert desired.artifact.renderer_version == "1.1.0"
    assert desired.artifact.palette[-1] == "orange"
    assert desired.not_before is not None


@pytest.mark.parametrize(
    "overrides",
    [
        {"width": 600},
        {"height": 400},
        {"format": "png-paletted"},
        {"sha256": "bad"},
    ],
)
def test_artifact_descriptor_rejects_unsupported_artifacts(overrides):
    with pytest.raises(ContractError):
        ArtifactDescriptor.from_mapping(descriptor_data(**overrides))
