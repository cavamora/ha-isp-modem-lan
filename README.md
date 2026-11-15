# ISP Modem LAN — experimental

This is a **local, read-only** Home Assistant custom integration prototype for the observed Claro/Technicolor status-page family (hardware V3.00, firmware 08.89.17.27.26). It has **no reboot, reset, factory-restore, or write requests**. Vivo and other modem models are not supported.

## Setup (when installed in a test Home Assistant)

Copy `custom_components/isp_modem/` into the HA instance's `config/custom_components/isp_modem/`, restart Home Assistant, then add **ISP Modem LAN (experimental)** under Settings → Devices & services. Supply the modem **IPv4 address** (not a URL), and optionally its username and password. The credentials are stored in that HA config entry for future login work but **are not sent by this release**; leave them blank if testing only sensors. The host is contacted over HTTP on port 80. **Do not install this prototype as an active HACS integration yet.**

Confirmed on one live Claro modem (management address held outside this public repository): `status-software.html` and `status-conexao-rf.html` were readable via GET without sending credentials. Supported sensor fields: hardware/firmware version, uptime, network-access state; upstream/downstream channel counts, average RF power/SNR, corrected/uncorrectable codeword totals. Refresh interval: 90 seconds. The parser deliberately excludes IP addresses, MAC addresses, SSIDs, subscriber identifiers and passwords. No credentials or captured live HTML are checked in; tests use synthetic fixtures.

**Safety finding:** in this environment a GET of the modem's unauthenticated landing page exposed a Wi-Fi password in page source. This integration does not fetch that page; restrict access to the modem management interface from untrusted LAN clients, and review modem firmware/security settings. Never publish raw HTML/HAR from this device.

## Development

Run `python3 -m unittest discover -s tests -q`. The parser has synthetic tests and was exercised on live read-only status pages. The Home Assistant config-flow and sensor wiring have **not been tested inside Home Assistant yet**. No live reboot test has been conducted. Before shipping a reboot button: identify and validate the login mechanism, verify session/key handling, add isolated fake-modem tests and explicit manual-only opt-in, and obtain owner permission for a disruptive test.

## Packaging decision

Keep this integration in its **own repository** for HACS. A Home Assistant *add-on repository* has a different discovery/install contract; putting `custom_components/` beside add-ons does not make HACS install it. Share maintainership and docs with the existing add-ons organization, but release and version this integration separately.
