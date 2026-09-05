# E-ink display client

Raspberry Pi client for the Pimoroni Inky Impression E673 / Spectra 6 7.3-inch
display.

## Set up a Pi

```bash
sudo apt update && sudo apt install -y git
git clone ssh://git@ssh.github.com:443/marcusottosen/e-ink-display-client.git ~/e-ink-display-client
cd ~/e-ink-display-client
sudo ./pi-agent/scripts/install-pi-agent.sh "$PWD"
sudoedit /etc/inky-agent/config.env
sudo systemctl enable --now inky-agent
sudo systemctl status inky-agent
```

## Edit the agent configuration

```bash
sudoedit /etc/inky-agent/config.env
```

## Update an installed Pi

```bash
cd ~/e-ink-display-client
git pull --ff-only
sudo ./pi-agent/scripts/install-pi-agent.sh "$PWD"
sudo systemctl restart inky-agent
```
