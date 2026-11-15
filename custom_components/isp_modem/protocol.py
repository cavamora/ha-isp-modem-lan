"""Only the observed TC7337 login and reboot protocol, with strict page guards.

Do not log full URLs: this firmware transmits base64(username:password) in the
login query string over plain HTTP. Only use on an explicitly trusted LAN.
"""

from __future__ import annotations

import base64
import re


def login_challenge(page: str) -> str | None:
    if not re.search(r'<input\b[^>]*\bname=["\']Login["\']', page, re.IGNORECASE):
        return None
    if not re.search(r'<input\b[^>]*\bname=["\']Password["\']', page, re.IGNORECASE):
        return None
    if "Authorization:***" not in page or "login.html?" not in page:
        return None
    match = re.search(r"&sessionKey=(\d+)!", page)
    return match.group(1) if match else None


def login_path(challenge: str, username: str, password: str) -> str:
    if not challenge.isdigit() or not username or not password:
        raise ValueError("Invalid login challenge or missing credentials")
    encoded = base64.b64encode((username + ":" + password).encode()).decode("ascii")
    return "login.html?&sessionKey=" + challenge + "!Authorization:***" + encoded


def reboot_token(page: str) -> str | None:
    if "reboot the router" not in page or "factory" in page.lower():
        return None
    if not re.search(r"['\"]rebootinfo\.cgi\?['\"]", page):
        return None
    if not re.search(r"['\"]sessionKey=['\"]\s*\+\s*sessionKey", page):
        return None
    match = re.search(r"var\s+sessionKey\s*=\s*['\"](\d+)['\"]", page)
    return match.group(1) if match else None


def reboot_path(token: str) -> str:
    if not token.isdigit():
        raise ValueError("Invalid reboot token")
    return "rebootinfo.cgi?sessionKey=" + token


def reboot_confirmed(before: int | None, after: int | None) -> bool:
    return (
        before is not None
        and after is not None
        and before >= 600
        and after < before - 120
    )
