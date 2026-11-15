# ISP Modem LAN — experimental

A single Home Assistant / HACS integration with **separate clients for two observed firmware families**:

- **Claro / Technicolor DOCSIS 3.0** — hardware V3.00, firmware 08.89.17.27.26: authenticated status, RF/channel data, uptime, and guarded **manual Restart** button. The existing Claro installation has been used successfully in Home Assistant. Entries created before 0.2.0 remain Claro entries.
- **Vivo / GPT-2741GNAC-N1** — firmware `BR_g8.10_1.11…`: authenticated **read-only** model, firmware/hardware versions, and optical RX/TX power. No Vivo uptime, RF/channel entities, or restart button. The reboot operation was not validated on the live modem and is intentionally not shipped.

These are **not** generic integrations for every Claro or Vivo modem. Other models/firmware must be investigated independently. The Vivo reader was checked directly against one live device, but its HA config entry and entity lifecycle still need confirmation in a real HA instance.

## Installation

In HACS: Integrations → menu → Custom repositories → add `https://github.com/cavamora/ha-isp-modem-lan` as **Integration** → download **ISP Modem LAN** → restart Home Assistant → Settings → Devices & services → Add Integration → **ISP Modem LAN**. Select the exact modem type and enter its IPv4 address **without** `http://`, port or path. Vivo requires both username and password; Claro may also require them for status. To replace credentials in this beta, remove and re-add that config entry. Avoid deleting a working Claro entry just to add Vivo: both can coexist.

Credentials are saved in Home Assistant config storage and relevant backups, not in this repository or retrieved from the developer's vault. Both observed login flows use **plain HTTP** on the local network; the Claro firmware also places base64-encoded credentials in a login URL (base64 is not encryption). Use a trusted management LAN, restrict access, and avoid proxy/URL logs. The integration does not log credentials, URLs containing them, session tokens, or raw pages.

## Entities and safety

Claro polls every 90 seconds: uptime in seconds, firmware/hardware versions, access status, channel counts, RF averages and codeword totals. Its manual Restart button appears only with credentials, sends one guarded reboot request, and never retries a dropped connection. A button press alone does not prove the reboot; compare uptime before/after. A user has confirmed successful HA button use on the observed Claro modem.

Vivo polls every 90 seconds: model, firmware/hardware versions, optical RX/TX power in dBm. It does **not** expose a restart button: two separately authorized, one-shot reboot requests produced disconnected HTTP responses but no observed management outage, so the actual reboot could not be confirmed. Do not infer boot uptime from the UI's “Tempo conectado” label. No factory-reset request was sent.

Both readers allowlist output fields; IP/MAC addresses, serials, SSIDs, Wi-Fi passwords, subscriber IDs and session values are excluded. No live page captures, HAR files, credentials, cookies or session challenges belong in the repository. Tests use synthetic fixtures and never contact or restart a modem.

The development-only Claro CLI, `python3 -m scripts.manual_reboot --host <IP>`, defaults to a non-disruptive dry run. Live execution additionally requires `ALLOW_LIVE_REBOOT=1` and `--execute`; never run this in CI.

## Development

`python3 -m unittest discover -s tests -q`; `python3 -m compileall -q custom_components tests`; `uvx ruff check .`. This is an HA integration, **not** an HAOS add-on. New modem families require isolated protocols, sanitized synthetic fixtures, and confirmation against the actual firmware before enabling disruptive actions.
