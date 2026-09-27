# E-ink display client

Raspberry Pi client for the Pimoroni Inky Impression E673 / Spectra 6 7.3-inch
display.

## Set up a Pi

```bash
sudo apt update && sudo apt install -y git
git clone https://github.com/marcusottosen/e-ink-display-client.git
cd ~/e-ink-display-client
sudo ./pi-agent/scripts/install-pi-agent.sh "$PWD"

sudoedit /etc/inky-agent/config.env
// set server url
sudoedit /boot/firmware/config.txt
// comment out dtparam=spi=on 

reboot...

sudo systemctl enable --now inky-agent
systemctl status inky-agent
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
