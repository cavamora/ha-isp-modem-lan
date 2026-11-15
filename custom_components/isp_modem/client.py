"""Read-only modem client. Credentials reserved for a verified login protocol."""
from __future__ import annotations

import asyncio
import ipaddress

from .parser import parse_rf, parse_software


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

    def __init__(self, session, host: str):
        self._session = session
        self._base = "http://" + normalized_host(host)

    async def _page(self, path: str) -> str:
        async with asyncio.timeout(self.TIMEOUT_SECONDS):
            async with self._session.get(f"{self._base}/{path}") as response:
                if response.status != 200:
                    raise ModemResponseError(f"Status page returned HTTP {response.status}")
                data = await response.content.read(300001)
                if len(data) > 300000:
                    raise ModemResponseError("Status page exceeds size limit")
                return data.decode("utf-8", "replace")

    async def status(self) -> dict:
        software = parse_software(await self._page("status-software.html"))
        rf = parse_rf(await self._page("status-conexao-rf.html"))
        if not software.get("software_version") or not rf.get("downstream_channels"):
            raise ModemResponseError("Unsupported modem page or login required")
        return software | rf
