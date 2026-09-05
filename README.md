# Inky E673 display project

One Raspberry Pi agent for a Pimoroni Inky Impression E673 / Spectra 6
7.3-inch display (800 × 480). The Pi polls the Docker host every 10 seconds,
downloads a newer RGB PNG, and refreshes the display.

- `inky/` — retained E673 hardware driver and EEPROM helper
- `pi-agent/` — polling agent, systemd unit, installer, and tests
- `docs/` — Pi and Docker-host protocol notes

## Deploy on a fresh Pi

Use Raspberry Pi OS with the display connected and network access to
`192.168.0.101:8000`.

This repository must first be committed and pushed to **your own Git remote**.
The current `origin` points to Pimoroni's upstream project, so do not clone it
for deployment.

Publish this project once from the development Pi, replacing the placeholder
with your empty GitHub/GitLab repository URL:

```bash
git remote set-url origin <your-repository-url>
git add -A
git commit -m "Create Inky E673 display agent"
git push -u origin main
```

```bash
sudo apt update && sudo apt install -y git
sudo git clone <your-repository-url> /opt/inky
sudo /opt/inky/pi-agent/scripts/install-pi-agent.sh /opt/inky
sudoedit /etc/inky-agent/config.env
sudo systemctl enable --now inky-agent
sudo systemctl status inky-agent
```

The installed configuration should contain:

```ini
INKY_AGENT_SERVER_URL=http://192.168.0.101:8000
INKY_AGENT_DISPLAY_ID=inky-main
INKY_AGENT_DEVICE_TOKEN=
INKY_AGENT_POLL_INTERVAL_SECONDS=10
```

Leave `INKY_AGENT_DEVICE_TOKEN` empty while host authentication is disabled.
The agent starts automatically on later boots. Follow its logs with:

```bash
journalctl -u inky-agent -f
```

## Update an installed Pi

```bash
sudo git -C /opt/inky pull --ff-only
sudo /opt/inky/pi-agent/scripts/install-pi-agent.sh /opt/inky
sudo systemctl restart inky-agent
```

The retained driver code is subject to the MIT licence in [LICENSE](LICENSE).
