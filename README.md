# ISP Modem LAN — experimental

A custom Home Assistant integration for **one observed Claro/Technicolor DOCSIS 3.0 firmware family** (hardware V3.00, firmware 08.89.17.27.26). It is not a generic Claro/Vivo integration; no Vivo support or factory-reset capability exists. Only install on a modem whose pages match this firmware. This is an early beta.

## Install via HACS (custom repository)

HACS → Integrations → menu → Custom repositories → add this repository as **Integration** → download **ISP Modem LAN** → restart Home Assistant → Settings → Devices & services → Add Integration → **ISP Modem LAN**.

Enter the modem IPv4 **without** `http://`, port or path. Username/password may be omitted only when the status pages are publicly readable; if the modem serves a login form, they are required even for setup and sensors. They are always required for the manual **Restart** button. They are entered in Home Assistant and saved in its configuration storage (including relevant HA backups), **not** read from the developer's Bitwarden vault. To change credentials in this beta, remove and re-add the config entry.

This modem's observed login JavaScript places base64-encoded `username:password` in a **plain-HTTP URL**. Base64 is not encryption. Use a trusted management LAN, prevent untrusted clients from reaching the admin interface, and avoid URL/proxy/access logs. The integration never prints credentials or full request URLs. A modem already authenticated for this source may serve status/restart pages without another login; if it shows a login form, the integration follows the observed firmware challenge. The read-only authenticated status flow has been checked on one live modem; setup inside HA still requires validation.

## Entities

- Sensor **Uptime** (seconds since modem boot): compare it before/after a restart; a drop is stronger evidence than an accepted HTTP request.
- Firmware/hardware version and network access; upstream/downstream channel counts, average RF power/SNR, corrected and uncorrectable codeword totals. Polls every 90 seconds.
- **Restart** button, present only when both username and password were configured. It sends **one** guarded reboot request; it does not retry after a dropped connection. The button being pressed does not itself prove a completed reboot. Protect its dashboard control with confirmation where appropriate; direct HA service calls can still press it.

The status parser deliberately excludes IP addresses, MAC addresses, SSIDs, subscriber identifiers, Wi-Fi passwords and login/session tokens. No captured HTML or credentials belong in this repository. Tests use synthetic fixtures.

## Safety / validation

- On one authorized Claro modem, the manual script sent exactly one `rebootinfo.cgi` request after reading the observed `resetrouter.html` token. The modem became temporarily unavailable and the software-status uptime fell from ~25 hours to under 4 minutes. No factory-reset endpoint was called.
- The status parser was exercised against live read-only firmware/RF pages, and protocol/unit tests use synthetic pages. **The Home Assistant config flow and entity lifecycle are not yet verified inside HA.** Treat this as a pre-release, not broad firmware support.
- The observed management interface served a page containing a Wi-Fi password in its source without a fresh login challenge from the test client. The integration does not fetch that page; restrict management access from untrusted LAN devices and review firmware/security settings. Never post raw captures/HAR files.
- The `scripts/manual_reboot.py` CLI is a development-only check: `python3 -m scripts.manual_reboot --host <IP>` is a non-disruptive dry run; live execution additionally requires `ALLOW_LIVE_REBOOT=1` and `--execute`. **Never run a live reboot in CI.**

## Development

`python3 -m unittest discover -s tests -q`; `python3 -m compileall -q custom_components`. The repository is a standard HACS integration, not an HAOS add-on. Corrections for other hardware/firmware must include sanitized synthetic fixtures and a separate compatibility check, not an assumption that the ISP name defines the protocol.
