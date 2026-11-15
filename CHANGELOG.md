# Changelog

## 0.2.1

- Add a clearly labeled **Restart (experimental)** button to Vivo entries with credentials, at the owner's request for testing inside Home Assistant. It is not yet confirmed to reboot the modem.
- Check the observed model/firmware and UI confirmation chain before sending one reboot-only request. Factory restore is a separate action and is never called; no automatic retry after a dropped connection.
- Keep Vivo setup/polling read-only and preserve the existing Claro restart behavior. See README for safety and verification limits.

## 0.2.0

- Add a separate, read-only Vivo GPT-2741GNAC-N1 client for the observed `BR_g8.10_1.11` firmware family, with authenticated model, firmware, hardware and optical-power sensors.
- Add an explicit modem-family selector; entries created before this version remain Claro entries without migration.
- Preserve Claro status and the manual Restart button. Vivo has **no restart button or uptime sensor**: live reboot attempts did not produce a confirmable reboot, so the operation is not shipped.
- Add synthetic flow, coordinator, sensor, parser and safety regression tests. No real modem traffic occurs in CI.

## 0.1.1

- Fix authenticated Claro status setup when the modem presents a login challenge.

## 0.1.0

- Initial experimental Claro firmware-family support.
