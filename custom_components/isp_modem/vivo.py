"""Observed Vivo GPT-2741GNAC-N1 web UI, isolated from Claro's protocol.

The modem uses HTTP login with MD5(password + ':' + fresh sid). Never log the
login response, credentials, cookies, session challenge, or exception URLs.
Only login and status endpoints are allowlisted. Vivo reboot is not exposed.
"""

from __future__ import annotations

import hashlib
import http.cookiejar
import re
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

from .client import normalized_host

MODEL = "GPT-2741GNAC-N1"
FIRMWARE_PREFIX = "BR_g8.10_1.11"
_READ_PATHS = frozenset(("login.cgi", "about-power-box2.cgi", "sophia_info.cgi"))


class VivoError(Exception):
    """Safe-to-display failure with no URL or credential-bearing context."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class _StatusItems(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.items: list[str] = []

    def handle_data(self, data: str) -> None:
        item = " ".join(data.split())
        if item:
            self.items.append(item)


def _value_after(page: str, label: str) -> str | None:
    items = _StatusItems()
    items.feed(page)
    for i, item in enumerate(items.items[:-1]):
        if item.strip().rstrip(":").strip().casefold() == label.casefold():
            return items.items[i + 1]
    return None


def parse_vivo_status(about_page: str, info_page: str) -> dict:
    """Return an allowlist: never expose Wi-Fi, serial, IP, MAC or login data."""
    result: dict[str, str | float] = {}
    for label, key in (
        ("Modelo", "model"),
        ("Versão do Software", "software_version"),
        ("Versão do Hardware", "hardware_version"),
    ):
        value = _value_after(about_page, label)
        if value and re.fullmatch(r"[A-Za-z0-9_.()\-]{1,40}", value):
            result[key] = value
    for label, key in (("Potência Rx", "optical_rx_dbm"), ("Potência Tx", "optical_tx_dbm")):
        value = _value_after(info_page, label)
        if value:
            match = re.fullmatch(r"([+-]?\d{1,3}(?:\.\d{1,3})?)\s*dBm", value)
            if match:
                result[key] = float(match.group(1))
    return result


def _login_challenge(page: str) -> str | None:
    if not re.search(r'<input\b[^>]*\bname=["\']LoginPasswordValue["\']', page, re.IGNORECASE):
        return None
    if "hex_md5" not in page or "LoginPassword.value" not in page:
        return None
    if not re.search(r"acceptLoginIndex\.value\s*=\s*1", page):
        return None
    match = re.search(r"\bvar\s+sid\s*=\s*([\"'])([A-Za-z0-9]{8})\1", page)
    return match.group(2) if match else None


class VivoModemClient:
    """New cookie/session per client. No reboot path is available."""

    def __init__(self, host: str, username: str, password: str, *, opener=None):
        self._base = "http://" + normalized_host(host) + "/cgi-bin/"
        self._username = username
        self._password = password
        self._opener = opener or urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
            _NoRedirect(),
        )

    def _request(self, path: str, data: bytes | None = None) -> str:
        if path not in _READ_PATHS:
            raise VivoError("Unexpected modem path")
        if data is not None and path != "login.cgi":
            raise VivoError("Unexpected modem POST")
        try:
            req = urllib.request.Request(
                self._base + path,
                data=data,
                headers={"User-Agent": "ISPModemLAN/0.2", "Referer": self._base + "login.cgi"},
            )
            with self._opener.open(req, timeout=15) as response:
                if response.status != 200:
                    raise VivoError(f"Modem HTTP {response.status}")
                chunks = []
                total = 0
                while chunk := response.read(65536):
                    total += len(chunk)
                    if total > 200000:
                        raise VivoError("Modem page exceeds size limit")
                    chunks.append(chunk)
                return b"".join(chunks).decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            raise VivoError(f"Modem HTTP {exc.code}") from None
        except VivoError:
            raise
        except Exception as exc:  # noqa: BLE001 - exceptions may embed auth URLs
            raise VivoError(f"Modem request failed ({type(exc).__name__})") from None

    def _login(self) -> None:
        if not self._username or not self._password:
            raise VivoError("Modem username and password required")
        page = self._request("login.cgi")
        challenge = _login_challenge(page)
        if challenge is None:
            raise VivoError("Unsupported Vivo login page")
        digest = hashlib.md5(  # Device's login protocol, not local password storage.
            (self._password + ":" + challenge).encode()
        ).hexdigest()
        data = urllib.parse.urlencode(
            {
                "Loginuser": self._username,
                "LoginPasswordValue": digest,
                "acceptLoginIndex": "1",
            }
        ).encode()
        result = self._request("login.cgi", data)
        if "sophia_index.cgi" not in result or "LoginPasswordValue" in result:
            raise VivoError("Modem login failed")

    def status(self) -> dict:
        """Authenticate, then read only model, firmware, and optical power."""
        self._login()
        about = self._request("about-power-box2.cgi")
        info = self._request("sophia_info.cgi")
        if "LoginPasswordValue" in info:
            raise VivoError("Modem login failed")
        status = parse_vivo_status(about, info)
        if status.get("model") != MODEL or not str(status.get("software_version", "")).startswith(FIRMWARE_PREFIX):
            raise VivoError("Unsupported Vivo modem or status page")
        if "optical_rx_dbm" not in status or "optical_tx_dbm" not in status:
            raise VivoError("Vivo optical status unavailable")
        return status
