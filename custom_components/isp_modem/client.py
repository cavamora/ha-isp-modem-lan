"""Read-only modem status client with challenge login when required."""

from __future__ import annotations

import asyncio
import ipaddress

from .parser import parse_rf, parse_software
from .protocol import login_challenge, login_path


class ModemResponseError(Exception):
    """A modem page was unreachable or did not contain the expected status."""


def normalized_host(host: str) -> str:
    """Accept a numeric modem host, never a URL/path or loopback target."""
    try:
        ip = ipaddress.IPv4Address(host.strip())
    except (ipaddress.AddressValueError, AttributeError) as exc:
        raise ValueError("Use an IPv4 address without scheme, port, or path") from exc
    if ip.is_loopback or ip.is_unspecified or ip.is_multicast or ip.is_link_local:
        raise ValueError("The address cannot be loopback, multicast, or link-local")
    return str(ip)


class ClaroModemClient:
    """The observed TC7337 status pages are readable without submitting credentials."""

    TIMEOUT_SECONDS = 8

    def __init__(self, session, host: str, username: str = "", password: str = ""):
        self._session = session
        self._base = "http://" + normalized_host(host)
        self._username = username
        self._password = password

    async def _page(self, path: str) -> str:
        async with asyncio.timeout(self.TIMEOUT_SECONDS):
            async with self._session.get(
                f"{self._base}/{path}",
                allow_redirects=False,
                headers={"User-Agent": "Mozilla/5.0"},
            ) as response:
                if path.startswith("login.html?") and response.status in (
                    301,
                    302,
                    303,
                ):
                    return ""
                if response.status != 200:
                    raise ModemResponseError(
                        f"Status page returned HTTP {response.status}"
                    )
                chunks = []
                total = 0
                while chunk := await response.content.read(65536):
                    total += len(chunk)
                    if total > 300000:
                        raise ModemResponseError("Status page exceeds size limit")
                    chunks.append(chunk)
                return b"".join(chunks).decode("utf-8", "replace")

    async def _authenticated_page(self, path: str) -> str:
        page = await self._page(path)
        challenge = login_challenge(page)
        if challenge is not None:
            if not self._username or not self._password:
                raise ModemResponseError("Modem login required; credentials absent")
            await self._page(login_path(challenge, self._username, self._password))
            page = await self._page(path)
            if login_challenge(page) is not None:
                raise ModemResponseError("Modem login failed")
        return page

    async def status(self) -> dict:
        software = parse_software(
            await self._authenticated_page("status-software.html")
        )
        rf = parse_rf(await self._authenticated_page("status-conexao-rf.html"))
        if not software.get("software_version") or not rf.get("downstream_channels"):
            raise ModemResponseError("Unsupported modem page or login required")
        return software | rf
