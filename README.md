# UFO Game Repo

**Doodad**:
An individual section that contains a set of buttons or a slider,
plus an LCD screen label.
Runs on a Pi Pico 2 with micropython (generally Python 3.9).

**Panel**:
`uv run python main.py -p --player {n}`
A whole set of doodads for a single player.
Runs on a Pi 3B+.

**Game**:
`uv run python main.py -g`
The central coordinator for the game.
Runs on a Pi 5 8gb.

## Debian headless auto-start after boot (systemd)

The app can start automatically on boot (and after power loss) using a systemd service. These steps assume a headless Debian/Ubuntu machine.

### Prerequisites

- Install packages:

```bash
sudo apt update && sudo apt install -y git curl avahi-daemon libnss-mdns
```

- Ensure `avahi-daemon` is enabled (for mDNS/zeroconf used by the game server):

```bash
sudo systemctl enable --now avahi-daemon
```

- Install `uv` (fast Python package manager by Astral):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# Make sure your shell PATH includes ~/.local/bin (reopen shell or run):
export PATH="$HOME/.local/bin:$PATH"
uv --version
```

### Clone and set up the app

Pick a location (example uses `/opt/ufogame`) and sync dependencies with `uv`.

```bash
sudo mkdir -p /opt/ufogame
sudo chown "$USER":"$USER" /opt/ufogame
git clone https://github.com/Zanderwohl/ufogame.git /opt/ufogame
cd /opt/ufogame
uv sync --frozen
```

Create a top-level `config.toml` specifying which role to run (server, client, or test). For clients, also set `player` (1-9).

```toml
role="server"
```

or

```toml
role="client"
player=1
```

or

```toml
role="test"
```

You can override these via CLI flags, but when `config.toml` exists, running without flags is supported.

### Create a systemd service

Create a dedicated user (recommended) and set directory ownership:

```bash
sudo useradd -r -m -s /usr/sbin/nologin ufogame || true
sudo chown -R ufogame:ufogame /opt/ufogame
# Install uv for the ufogame user (if not already installed for that account)
sudo -u ufogame -H sh -c 'command -v uv >/dev/null 2>&1 || (curl -LsSf https://astral.sh/uv/install.sh | sh)'
```

Create `/etc/systemd/system/ufogame.service` with the following content (update paths if different):

```ini
[Unit]
Description=UFO Game
Wants=network-online.target
After=network-online.target avahi-daemon.service

[Service]
Type=simple
User=ufogame
WorkingDirectory=/opt/ufogame
Environment=PYTHONUNBUFFERED=1
Environment=PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/home/ufogame/.local/bin
ExecStart=/home/ufogame/.local/bin/uv run --frozen /opt/ufogame/main.py
Restart=always
RestartSec=2
KillSignal=SIGINT
TimeoutStopSec=15

[Install]
WantedBy=multi-user.target
```

Then enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ufogame.service
```

### Verify and troubleshoot

- Check status:

```bash
systemctl status ufogame | cat
```

- View logs:

```bash
journalctl -u ufogame -f | cat
```

- Update the app (re-deploy):

```bash
cd /opt/ufogame
git pull
uv sync --frozen
sudo systemctl restart ufogame
```

### Notes

- The service is configured to wait for the network (`network-online.target`) so the server/client can discover peers via mDNS.
- You can still run locally without systemd for testing:

```bash
cd /opt/ufogame
uv run /opt/ufogame/main.py
```

