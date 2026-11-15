"""Parse observed Technicolor/Claro status pages; never return identifiers or secrets."""
from __future__ import annotations

from html.parser import HTMLParser
import re
from statistics import mean


class _Items(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.section = ""
        self._heading = False
        self._heading_text: list[str] = []
        self._item_depth = 0
        self._item_text: list[str] = []
        self.items: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "h2":
            self._heading = True
            self._heading_text = []
        elif tag == "li":
            if self._item_depth == 0:
                self._item_text = []
            self._item_depth += 1
        elif tag == "br" and self._item_depth:
            self._item_text.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag == "h2" and self._heading:
            self.section = " ".join("".join(self._heading_text).split())
            self._heading = False
        elif tag == "li" and self._item_depth:
            self._item_depth -= 1
            if self._item_depth == 0:
                text = "\n".join(" ".join(line.split()) for line in "".join(self._item_text).splitlines())
                self.items.append((self.section, text.strip()))

    def handle_data(self, data: str) -> None:
        if self._heading:
            self._heading_text.append(data)
        if self._item_depth:
            self._item_text.append(data)


def _items(page: str) -> list[tuple[str, str]]:
    parser = _Items()
    parser.feed(page)
    return parser.items


def parse_software(page: str) -> dict[str, str | int]:
    """Return only public operational fields, never MAC/IP/serial/password."""
    result: dict[str, str | int] = {}
    labels = {
        "Versão do hardware": "hardware_version",
        "Versão do software": "software_version",
        "Acesso à Rede": "network_access",
    }
    for _, item in _items(page):
        label, _, value = item.partition("\n")
        value = value.strip()
        if label in labels and value and value != "--":
            result[labels[label]] = value
        elif label == "Tempo de Disponibilidade do Sistema":
            match = re.fullmatch(r"(\d+)\s+days?\s+(\d+)h:(\d+)m:(\d+)s(?:\.\d+)?", value)
            if match:
                d, h, m, s = (int(x) for x in match.groups())
                result["uptime_seconds"] = d * 86400 + h * 3600 + m * 60 + s
    return result


def parse_rf(page: str) -> dict[str, int | float]:
    """Parse RF aggregate measurements, excluding subscriber and channel IDs."""
    downstream_power: list[float] = []
    downstream_snr: list[float] = []
    upstream_power: list[float] = []
    downstream_count = upstream_count = 0
    result: dict[str, int | float] = {}
    for section, item in _items(page):
        in_downstream = section == "Portadoras de Downstream adquiridas"
        in_upstream = section == "Portadora de Upstream adquirida"
        if in_downstream and item.startswith("Total corrigido\n"):
            value = item.partition("\n")[2].strip()
            if value.isdigit():
                result["corrected_total"] = int(value)
        if in_downstream and item.startswith("Total sem correção\n"):
            value = item.partition("\n")[2].strip()
            if value.isdigit():
                result["uncorrectable_total"] = int(value)
        if not (in_downstream or in_upstream) or not re.match(r"Canal:\s*\d+", item):
            continue
        if in_downstream:
            downstream_count += 1
        else:
            upstream_count += 1
        power = re.search(r"Potência:\s*(-?\d+(?:\.\d+)?)\s*dBmV", item)
        snr = re.search(r"SNR:\s*(-?\d+(?:\.\d+)?)\s*dB(?:mV)?", item)
        if power:
            (downstream_power if in_downstream else upstream_power).append(float(power[1]))
        if snr and in_downstream:
            downstream_snr.append(float(snr[1]))
    if downstream_count:
        result["downstream_channels"] = downstream_count
    if upstream_count:
        result["upstream_channels"] = upstream_count
    for key, values in (("downstream_power_dbmv", downstream_power),
                        ("downstream_snr_db", downstream_snr),
                        ("upstream_power_dbmv", upstream_power)):
        if values:
            result[key] = round(mean(values), 2)
    return result
