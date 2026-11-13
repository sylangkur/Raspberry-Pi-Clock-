# Pi Dashboard

A full-screen clock/dashboard for a **Raspberry Pi with an 800×480 (5") HDMI display**, plus a small **web portal** to control it from your phone or laptop.

## Features

- Big clock (12/24 h), English date and **Bangla (Bengali) calendar date**
- **Daily routine** banner – shows the current time block (same every day, or per weekday)
- Countdown to an exam date
- Smart "next reminder" line – birthdays, anniversaries and public holidays (see `reminders.example.json`)
- Hourly / half-hourly **chime**, special **birthday chime**, mute, quiet hours and snooze
- Custom background image, per-element **font / size / colour / opacity / alignment**, drag-to-reorder layout
- Everything is edited live from the web portal – no restart needed (the clock reloads every ~30 s)

## Requirements

- Raspberry Pi (tested idea: Pi 4/5, 8 GB) with an X11 session, Python 3.9+
- `python3-pyqt5` (display), `Flask` (portal)
- `paplay` (from `pulseaudio-utils`) for chimes – works with PipeWire-pulse

## Install (on the Pi)

```bash
sudo apt update
sudo apt install -y git python3-pyqt5 python3-flask pulseaudio-utils
git clone https://github.com/<your-username>/pi-dashboard.git ~/dashboard
cd ~/dashboard
cp reminders.example.json reminders.json
cp routine.example.json routine.json
```

## Run

Clock (needs the Pi's desktop/display):

```bash
DISPLAY=:0 python3 ~/dashboard/dashboard.py
```

Web portal:

```bash
python3 ~/dashboard/portal.py
```

Open `http://<pi-ip>:5000` from any device on your network.
Find the Pi's IP with `hostname -I`.

Keys on the clock: `Esc`/`Q` quit, `F5` reload.

## Start on boot (systemd user services)

```bash
mkdir -p ~/.config/systemd/user
cp ~/dashboard/systemd/*.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now pi-dashboard.service pi-dashboard-portal.service
sudo loginctl enable-linger $USER
```

View logs:

```bash
journalctl --user -u pi-dashboard -f
```

> If the clock doesn't appear, the service may need your session's `DISPLAY` / `XAUTHORITY`; alternatively launch `dashboard.py` from your desktop autostart instead.

## Configuration

| Environment variable | Default | Meaning |
|---|---|---|
| `DASHBOARD_DIR` | `~/dashboard` | Where settings, reminders, fonts, background and chimes live |
| `PORTAL_HOST` | `0.0.0.0` | Interface the portal listens on |
| `PORTAL_PORT` | `5000` | Portal port |

Files created at runtime (all git-ignored): `settings.json`, `reminders.json`, `routine.json`, `background.*`, `chime.*`, `birthday_chime.*`, `fonts/`.

### Reminder types

`reminders.json` entries use `"note"` to choose behaviour:

| `note` | Shown on the clock |
|---|---|
| `Birthday` | 3 days ahead; chime changes on the day |
| `Anniversary` | 3 days ahead |
| `Public Holiday` | the day before and on the day |
| anything else | next upcoming event |

## Try it on a PC

The display script is fixed at 800×480 but runs on any desktop with PyQt5:

```bash
pip install PyQt5 Flask
mkdir -p ./data && cp reminders.example.json data/reminders.json && cp routine.example.json data/routine.json
export DASHBOARD_DIR="$PWD/data"
python3 portal.py &
python3 dashboard.py
```

## ⚠️ Security

The portal has **no login** and listens on all interfaces. Run it only on a trusted home network, never expose port 5000 to the internet. To restrict it to the Pi itself (e.g. behind an SSH tunnel), set `PORTAL_HOST=127.0.0.1`.

## License

MIT – see [LICENSE](LICENSE).
