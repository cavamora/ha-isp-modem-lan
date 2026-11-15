"""Explicit, one-shot TC7337 reboot workflow; no factory-reset endpoints.

The observed firmware embeds credentials in an HTTP query string during login.
Never log request URLs or exception text from this module.
"""

from __future__ import annotations

import http.cookiejar
import urllib.error
import urllib.request

from .client import normalized_host
from .parser import parse_software
from .protocol import login_challenge, login_path, reboot_path, reboot_token


class RebootError(Exception):
    """Safe error without credentials, tokens, or request URLs."""


def prepare_and_maybe_send(get, username: str, password: str, *, execute: bool) -> dict:
    """Verify software/uptime and exact reboot page before one disruptive GET."""

    def authenticated(path):
        page = get(path)
        challenge = login_challenge(page)
        if challenge is not None:
            if not username or not password:
                raise RebootError("Modem login required; credentials absent")
            get(login_path(challenge, username, password))
            page = get(path)
            if login_challenge(page) is not None:
                raise RebootError("Modem login failed")
        return page

    before = parse_software(authenticated("status-software.html"))
    uptime = before.get("uptime_seconds")
    if not before.get("software_version") or not isinstance(uptime, int):
        raise RebootError("Modem status not verified; refusing reboot")
    reset_page = authenticated("resetrouter.html")
    token = reboot_token(reset_page)
    if token is None:
        raise RebootError("Expected reboot page not found; refusing reboot")
    if execute:
        get(reboot_path(token))  # exactly one request; never retry a disruptive GET
    return {
        "attempted": execute,
        "before_uptime": uptime,
        "software_version": before["software_version"],
    }


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def send_reboot(host: str, username: str, password: str) -> dict:
    """Synchronous function for HA executor. Only used by explicit button press."""
    if not username or not password:
        raise RebootError("Configure modem username and password before reboot")
    base = "http://" + normalized_host(host) + "/"
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()), _NoRedirect()
    )

    def get(path):
        try:
            req = urllib.request.Request(
                base + path, headers={"User-Agent": "ISPModemLAN/0.1"}
            )
            with opener.open(req, timeout=8) as response:
                data = response.read(300001)
                if len(data) > 300000:
                    raise RebootError("Response exceeds size limit")
                return data.decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            # This firmware may redirect immediately after login or reboot.
            if exc.code in (301, 302, 303) and path.startswith(
                ("login.html?", "rebootinfo.cgi?")
            ):
                return ""
            raise RebootError(f"Modem HTTP {exc.code}") from None
        except RebootError:
            raise
        except Exception as exc:  # noqa: BLE001 - redact credential-bearing URLs
            # The underlying error can contain the URL with base64 credentials.
            raise RebootError(f"Modem request failed ({type(exc).__name__})") from None

    return prepare_and_maybe_send(get, username, password, execute=True)
