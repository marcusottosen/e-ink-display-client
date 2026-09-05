# Inky Pi Agent

This package runs on the Raspberry Pi and communicates outbound to the Docker-hosted Inky server. It targets the fixed Pimoroni Inky Impression 7.3-inch E673 display at 800 x 480 pixels.

The agent:

- Polls for a newer desired revision.
- Downloads and verifies the host-rendered `rgb-png` artifact.
- Updates the display through the local Inky driver.
- Persists state and pending acknowledgements under `/var/lib/inky-agent`.
- Retries network failures without opening a listening port on the Pi.

## Development mode

From the repository root:

```bash
python3 -m venv pi-agent/.venv
pi-agent/.venv/bin/python -m pip install -e .
pi-agent/.venv/bin/python -m pip install -e pi-agent
INKY_AGENT_HARDWARE_ENABLED=false \
INKY_AGENT_DATA_DIR=/tmp/inky-agent \
INKY_AGENT_SERVER_URL=http://127.0.0.1:8000 \
pi-agent/.venv/bin/inky-agent
```

The disabled-hardware mode still exercises configuration, networking, artifact handling, and job acknowledgements without accessing GPIO/SPI/I²C.

## Raspberry Pi installation

The deployment target is `/opt/inky` by default:

```bash
sudo /opt/inky/pi-agent/scripts/install-pi-agent.sh /opt/inky
sudoedit /etc/inky-agent/config.env
sudo systemctl restart inky-agent
sudo systemctl status inky-agent
```

The installer enables SPI and I²C when `raspi-config` is available, installs the root Inky package and agent package into a virtual environment, creates the restricted service account, and installs the systemd unit.

The Docker host URL in `config.env` is the application URL, never a Docker daemon socket or Docker TCP API URL.

The agent uses the shared `inky_contract.DesiredState` model. The host response
must contain `api_version`, `display_id`, `revision`, `job_id`, and an artifact
descriptor with `sha256`, relative `url`, `format: rgb-png`, `media_type:
image/png`, `width: 800`, `height: 480`, `palette`, and `renderer_version`.
