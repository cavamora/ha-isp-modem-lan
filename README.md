# ISP Modem LAN — experimental

A single Home Assistant / HACS integration with **separate clients for two observed firmware families**:

- **Claro / Technicolor DOCSIS 3.0** — hardware V3.00, firmware 08.89.17.27.26: authenticated status, RF/channel data, uptime, and guarded **manual Restart** button. The existing Claro installation has been used successfully in Home Assistant. Entries created before 0.2.0 remain Claro entries.
- **Vivo / GPT-2741GNAC-N1** — firmware `BR_g8.10_1.11…`: authenticated model, firmware/hardware versions, optical RX/TX power and an **experimental manual Restart button**. No Vivo uptime or RF/channel entities. Earlier HA button presses did not restart the modem; the browser UI's manual reboot works. Version 0.2.3 matches the browser's observed uppercase `RestartBtn=RESTART` form value, but has not yet been live-tested.

These are **not** generic integrations for every Claro or Vivo modem. Other models/firmware must be investigated independently. The Vivo reader was checked directly against one live device; its status-sensor lifecycle has not been independently validated in a live HA instance.

## Installation

In HACS: Integrations → menu → Custom repositories → add `https://github.com/cavamora/ha-isp-modem-lan` as **Integration** → download **ISP Modem LAN** → restart Home Assistant → Settings → Devices & services → Add Integration → **ISP Modem LAN**. Select the exact modem type and enter its IPv4 address **without** `http://`, port or path. **Poll modem status** is enabled by default; turn it off for button-only operation. Vivo always requires username and password; Claro requires them when polling is off so the restart button can work. To replace credentials in this beta, remove and re-add that config entry. Avoid deleting a working Claro entry just to add Vivo: both can coexist.

Credentials are saved in Home Assistant config storage and relevant backups, not in this repository or retrieved from the developer's vault. Both observed login flows use **plain HTTP** on the local network; the Claro firmware also places base64-encoded credentials in a login URL (base64 is not encryption). Use a trusted management LAN, restrict access, and avoid proxy/URL logs. The integration does not log credentials, URLs containing them, session tokens, or raw pages.

## Entities and safety

When enabled, Claro polls every 90 seconds: uptime in seconds, firmware/hardware versions, access status, channel counts, RF averages and codeword totals. Its manual Restart button appears only with credentials, sends one guarded reboot request, and never retries a dropped connection. A button press alone does not prove the reboot; compare uptime before/after. A user has confirmed successful HA button use on the observed Claro modem.

When enabled, Vivo polls every 90 seconds: model, firmware/hardware versions, optical RX/TX power in dBm. Its **Restart (experimental)** button appears only with credentials. Pressing it logs in, checks the observed model/firmware and the exact reboot UI chain (management page → reboot popup → confirmation page), then sends **one** reboot request. It never calls factory restore and never retries if the connection closes. Earlier HA button presses sent a lowercase `RestartBtn=restart` value, ended with disconnected HTTP responses and produced **no observed management outage**. Version 0.2.3 corrects the value to the browser-observed uppercase `RESTART`, but its live reboot remains **unverified**. Do not repeatedly press it. A dashboard confirmation can reduce accidental presses, but direct HA service calls can still activate a button. Do not infer boot uptime from the UI's “Tempo conectado” label.

For either modem, turning off **Poll modem status** skips network validation during initial setup, creates no coordinator, makes no initial or periodic status request, and does not load status sensors. It still loads the manual restart button with the saved credentials; the button makes its own one-shot requests only when pressed. Existing entries default to polling on. After updating to 0.2.2 or later and restarting Home Assistant, go to **Settings → Devices & services → ISP Modem LAN → Configure** on each existing modem entry to change the polling setting without removing/re-adding it. Turning polling off requires already-configured credentials. Re-enabling restores the sensors and their existing entity IDs. The Claro button remains functional independently of polling; the Vivo button remains experimental and has not yet been live-tested with the corrected payload.

Both readers allowlist output fields; IP/MAC addresses, serials, SSIDs, Wi-Fi passwords, subscriber IDs and session values are excluded. No live page captures, HAR files, credentials, cookies or session challenges belong in the repository. Tests use synthetic fixtures and never contact or restart a modem.

The development-only Claro CLI, `python3 -m scripts.manual_reboot --host <IP>`, defaults to a non-disruptive dry run. Live execution additionally requires `ALLOW_LIVE_REBOOT=1` and `--execute`; never run this in CI.

## Development

`python3 -m unittest discover -s tests -q`; `python3 -m compileall -q custom_components tests`; `uvx ruff check .`. This is an HA integration, **not** an HAOS add-on. New modem families require isolated protocols, sanitized synthetic fixtures, and confirmation against the actual firmware before enabling disruptive actions.
