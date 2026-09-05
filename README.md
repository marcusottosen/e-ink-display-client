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

The project repository is
`ssh://git@ssh.github.com:443/marcusottosen/e-ink-display-client.git`.
It is private, so add the new Pi's SSH public key to the GitHub account first.

```bash
sudo apt update && sudo apt install -y git
git clone ssh://git@ssh.github.com:443/marcusottosen/e-ink-display-client.git ~/e-ink-display-client
cd ~/e-ink-display-client
sudo ./pi-agent/scripts/install-pi-agent.sh "$PWD"
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
cd ~/e-ink-display-client
git pull --ff-only
sudo ./pi-agent/scripts/install-pi-agent.sh "$PWD"
sudo systemctl restart inky-agent
```

The retained driver code is subject to the MIT licence in [LICENSE](LICENSE).
