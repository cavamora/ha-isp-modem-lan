"""Observed Vivo GPT-2741GNAC-N1 web UI, isolated from Claro's protocol.

The modem uses HTTP login with MD5(password + ':' + fresh sid). Never log the
login response, credentials, cookies, session challenge, or exception URLs.
Only an explicit manual action can access the reboot control pages.
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
_RESTART_PATH = "device-management-resets.cgi"
_READ_PATHS = frozenset(
    ("login.cgi", "about-power-box2.cgi", "sophia_info.cgi", _RESTART_PATH,
     "popup-reboot.cgi", "device-management-rebootinfo.cgi")
)


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


def _page_controls(page: str) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Collect only form actions and labeled links, never raw management HTML."""

    class Controls(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.forms: list[tuple[str, str]] = []
            self.links: list[tuple[str, str]] = []
            self.active_link: list[str] | None = None
            self.href = ""

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            attr = dict(attrs)
            if tag == "form":
                self.forms.append((attr.get("method", "").upper(), attr.get("action", "")))
            elif tag == "a":
                self.href = attr.get("href", "")
                self.active_link = []

        def handle_data(self, data: str) -> None:
            if self.active_link is not None:
                self.active_link.append(data)

        def handle_endtag(self, tag: str) -> None:
            if tag == "a" and self.active_link is not None:
                self.links.append((self.href, " ".join(self.active_link).strip().casefold()))
                self.active_link = None

    controls = Controls()
    controls.feed(page)
    return controls.forms, controls.links


def _is_local_path(value: str, path: str) -> bool:
    parsed = urllib.parse.urlsplit(value)
    return not (parsed.scheme or parsed.netloc or parsed.query or parsed.fragment) and parsed.path in (
        path, f"/cgi-bin/{path}"
    )


def _confirmation_calls_parent_reboot(page: str) -> bool:
    class Scripts(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.active = False
            self.parts: list[str] = []
            self.scripts: list[str] = []

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            if tag == "script" and not dict(attrs).get("src"):
                self.active = True
                self.parts = []

        def handle_data(self, data: str) -> None:
            if self.active:
                self.parts.append(data)

        def handle_endtag(self, tag: str) -> None:
            if tag == "script" and self.active:
                self.scripts.append("".join(self.parts))
                self.active = False

    scripts = Scripts()
    scripts.feed(page)
    for script in scripts.scripts:
        # Reject text-only mentions and JavaScript comments. False negatives are safe.
        code = re.sub(r"/\*[\s\S]*?\*/|//[^\n]*", "", script)
        if re.search(
            r"\$\(\s*document\s*\)\.ready\s*\(\s*function\s*\(\s*\)\s*\{[\s\S]{0,600}?parent\.reboot\s*\(\s*\)",
            code,
        ):
            return True
    return False


def _reboot_controls_match(reset: str, popup: str, confirmation: str) -> bool:
    """The observed UI path must be intact and factory restore distinct."""

    def function_prefix(name: str) -> str:
        match = re.search(
            rf"function\s+{name}\s*\(\s*\)\s*\{{([\s\S]{{0,600}}?)\}}",
            reset,
            re.IGNORECASE,
        )
        return match.group(1) if match else ""

    forms, links = _page_controls(reset)
    _, popup_links = _page_controls(popup)
    reboot = function_prefix("reboot")
    restore = function_prefix("restore")
    return bool(
        any(method == "POST" and _is_local_path(action, _RESTART_PATH) for method, action in forms)
        and any(_is_local_path(href, "popup-reboot.cgi") for href, _ in links)
        and any(_is_local_path(href, "device-management-rebootinfo.cgi") and "reboot" in label for href, label in popup_links)
        and _confirmation_calls_parent_reboot(confirmation)
        and re.search(r"restoreFlag\s*:\s*1\b", reboot)
        and re.search(r"RestartBtn\s*:\s*[\"']restart[\"']", reboot, re.IGNORECASE)
        and re.search(r"restoreFlag\s*:\s*5\b", restore)
    )


class VivoModemClient:
    """New cookie/session per client. Polling never visits reboot pages."""

    def __init__(self, host: str, username: str, password: str, *, opener=None):
        self._base = "http://" + normalized_host(host) + "/cgi-bin/"
        self._username = username
        self._password = password
        self._restart_armed = False
        self._opener = opener or urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()),
            _NoRedirect(),
        )

    def _request(self, path: str, data: bytes | None = None) -> str:
        if path not in _READ_PATHS:
            raise VivoError("Unexpected modem path")
        if data is not None and path not in ("login.cgi", _RESTART_PATH):
            raise VivoError("Unexpected modem POST")
        if data is not None and path == _RESTART_PATH and not self._restart_armed:
            raise VivoError("Unexpected modem POST")
        try:
            headers = {"User-Agent": "Mozilla/5.0", "Referer": self._base + "login.cgi"}
            if data is not None and path == _RESTART_PATH:
                headers.update(
                    {
                        "Referer": self._base + _RESTART_PATH,
                        "X-Requested-With": "XMLHttpRequest",
                        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                        "Accept": "application/json, text/javascript, */*; q=0.01",
                        "Origin": self._base.removesuffix("/cgi-bin/"),
                    }
                )
            req = urllib.request.Request(
                self._base + path,
                data=data,
                headers=headers,
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

    def restart(self) -> dict:
        """Follow the UI's confirmation path, then send at most one POST."""
        self.status()  # validates login, model, firmware and session
        reset = self._request(_RESTART_PATH)
        popup = self._request("popup-reboot.cgi")
        confirmation = self._request("device-management-rebootinfo.cgi")
        if not _reboot_controls_match(reset, popup, confirmation):
            raise VivoError("Vivo reboot controls changed; request refused")
        payload = urllib.parse.urlencode(
            {"restoreFlag": "1", "RestartBtn": "restart"}
        ).encode()
        self._restart_armed = True
        try:
            try:
                self._request(_RESTART_PATH, payload)
            except VivoError as exc:
                raise VivoError(f"Request sent once; outcome unconfirmed ({exc}). Check modem before retrying") from None
        finally:
            self._restart_armed = False
        return {"attempted": True}


def send_vivo_reboot(host: str, username: str, password: str) -> dict:
    """Manual HA button executor entry point; never used by setup or polling."""
    return VivoModemClient(host, username, password).restart()
