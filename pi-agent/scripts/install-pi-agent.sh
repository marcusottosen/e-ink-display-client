#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
    echo "Run this installer with sudo." >&2
    exit 1
fi

PROJECT_ROOT="${1:-/opt/inky}"
PROJECT_ROOT="$(realpath "$PROJECT_ROOT")"
AGENT_ROOT="$PROJECT_ROOT/pi-agent"
VENV="$AGENT_ROOT/.venv"

if [[ ! -f "$PROJECT_ROOT/pyproject.toml" || ! -f "$AGENT_ROOT/pyproject.toml" ]]; then
    echo "Expected an Inky project with pi-agent/ at $PROJECT_ROOT" >&2
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 is required" >&2
    exit 1
fi

apt-get update
apt-get install -y python3-venv python3-pip

if command -v raspi-config >/dev/null 2>&1; then
    raspi-config nonint do_spi 0
    raspi-config nonint do_i2c 0
fi

CONFIG_FILE="/boot/firmware/config.txt"
if [[ -f "$CONFIG_FILE" ]] && ! grep -qxF 'dtoverlay=spi0-0cs' "$CONFIG_FILE"; then
    printf '\n%s\n' 'dtoverlay=spi0-0cs' >> "$CONFIG_FILE"
    echo "Added dtoverlay=spi0-0cs; reboot the Pi before starting the agent."
fi

if ! getent group inky-agent >/dev/null 2>&1; then
    groupadd --system inky-agent
fi
if ! id inky-agent >/dev/null 2>&1; then
    useradd --system --gid inky-agent --home-dir /var/lib/inky-agent --create-home --shell /usr/sbin/nologin inky-agent
fi

for group in gpio spi i2c; do
    if getent group "$group" >/dev/null 2>&1; then
        usermod --append --groups "$group" inky-agent
    fi
done

mkdir -p /var/lib/inky-agent /etc/inky-agent
chown -R inky-agent:inky-agent /var/lib/inky-agent

python3 -m venv --system-site-packages "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install "$PROJECT_ROOT"
"$VENV/bin/python" -m pip install "$AGENT_ROOT"

if [[ ! -f /etc/inky-agent/config.env ]]; then
    install -o root -g inky-agent -m 0640 \
        "$AGENT_ROOT/deploy/systemd/inky-agent.env.example" \
        /etc/inky-agent/config.env
    echo "Edit /etc/inky-agent/config.env before starting the agent."
fi

SERVICE_TEMPLATE="$AGENT_ROOT/deploy/systemd/inky-agent.service"
if [[ "$PROJECT_ROOT" == "/opt/inky" ]]; then
    sed '/^BindReadOnlyPaths=@PROJECT_ROOT@:/d' "$SERVICE_TEMPLATE" \
        > /etc/systemd/system/inky-agent.service
else
    install -d -m 0755 /opt/inky
    sed "s|@PROJECT_ROOT@|$PROJECT_ROOT|g" "$SERVICE_TEMPLATE" \
        > /etc/systemd/system/inky-agent.service
fi
chown root:root /etc/systemd/system/inky-agent.service
chmod 0644 /etc/systemd/system/inky-agent.service

systemctl daemon-reload
systemctl enable inky-agent
echo "Pi agent installed. Configure /etc/inky-agent/config.env, then run: systemctl restart inky-agent"
