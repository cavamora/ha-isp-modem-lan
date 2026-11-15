"""Manual-only reboot probe. Never run in CI; explicit flag and env gate required.

This modem's login puts base64 credentials into a plain-HTTP query string. Avoid
proxy access logs, URL dumps, exception strings, screenshots, or remote access.
"""

from __future__ import annotations

import argparse
import http.cookiejar
import os
import time
import urllib.parse
import urllib.request

from custom_components.isp_modem.client import normalized_host
from custom_components.isp_modem.parser import parse_software
from custom_components.isp_modem.protocol import (
    login_challenge,
    login_path,
    reboot_confirmed,
)
from custom_components.isp_modem.reboot import prepare_and_maybe_send


def main() -> int:
    parser = argparse.ArgumentParser(description="Manual Claro modem reboot validation")
    parser.add_argument("--host", required=True, help="numeric IPv4, not a URL")
    parser.add_argument(
        "--execute", action="store_true", help="send one reboot request"
    )
    args = parser.parse_args()
    host = normalized_host(args.host)
    if args.execute and os.environ.get("ALLOW_LIVE_REBOOT") != "1":
        print("BLOCKED: set ALLOW_LIVE_REBOOT=1 as well as --execute")
        return 2
    base = "http://" + host + "/"
    cookiejar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookiejar))

    def get(path):
        try:
            with opener.open(
                urllib.request.Request(
                    base + path, headers={"User-Agent": "ISPModemLAN/experimental"}
                ),
                timeout=8,
            ) as response:
                if response.status != 200:
                    raise ValueError("unexpected HTTP status")
                data = response.read(300001)
                if len(data) > 300000:
                    raise ValueError("oversized response")
                return data.decode("utf-8", "replace")
        except Exception as exc:  # noqa: BLE001 - redact credential-bearing URLs
            # A login URL contains a password: never print str(exc), request, or URL.
            raise RuntimeError(
                "Modem request failed (" + type(exc).__name__ + ")"
            ) from None

    try:
        result = prepare_and_maybe_send(
            get,
            os.environ.get("CLARO_MODEM_USERNAME", ""),
            os.environ.get("CLARO_MODEM_PASSWORD", ""),
            execute=args.execute,
        )
    except Exception as exc:  # noqa: BLE001 - fail closed, never print URL
        print("FAILED:", type(exc).__name__)
        return 1
    print(
        "Preflight: firmware",
        result["software_version"],
        "uptime_seconds",
        result["before_uptime"],
    )
    if not args.execute:
        print("DRY RUN: reboot endpoint was not requested")
        return 0
    print("Reboot request sent once; verifying uptime (up to 5 minutes)")
    deadline = time.monotonic() + 300
    saw_unavailable = False
    while time.monotonic() < deadline:
        time.sleep(10)
        try:
            page = get("status-software.html")
            challenge = login_challenge(page)
            if challenge:
                user = os.environ.get("CLARO_MODEM_USERNAME", "")
                password = os.environ.get("CLARO_MODEM_PASSWORD", "")
                if not user or not password:
                    continue
                get(login_path(challenge, user, password))
                page = get("status-software.html")
            uptime = parse_software(page).get("uptime_seconds")
            if isinstance(uptime, int) and reboot_confirmed(
                result["before_uptime"], uptime
            ):
                print(
                    "VERIFIED: uptime reset to",
                    uptime,
                    "seconds; unavailability_observed",
                    saw_unavailable,
                )
                return 0
        except Exception:  # noqa: BLE001 - modem can disconnect during reboot
            saw_unavailable = True
    print(
        "UNVERIFIED: no observed uptime reset within timeout; do not retry automatically"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
