"""Synthetic fixtures: never put live modem HTML or credentials in this repository."""

import unittest

from custom_components.isp_modem.client import normalized_host
from custom_components.isp_modem.parser import parse_rf, parse_software


class HostTests(unittest.TestCase):
    def test_accepts_only_ipv4_without_scheme_or_path(self):
        self.assertEqual(normalized_host(" 192.0.2.1 "), "192.0.2.1")
        for host in (
            "http://192.0.2.1",
            "192.0.2.1/rebootinfo.cgi",
            "127.0.0.1",
            "example.org",
            "0.0.0.0",
        ):
            with self.subTest(host=host), self.assertRaises(ValueError):
                normalized_host(host)


class SoftwareTests(unittest.TestCase):
    def test_parse_status_without_personal_network_data(self):
        page = """<h2>Informações</h2><ul class="list">
        <li><strong>Versão do hardware</strong><br> V3.00</li>
        <li><strong>Versão do software</strong><br> 08.89.17.27.26</li>
        <li><strong>Endereço MAC</strong><br> 00:11:22:33:44:55</li></ul>
        <h2>Status</h2><ul class="list">
        <li><strong>Tempo de Disponibilidade do Sistema</strong><br>1 days 00h:40m:18s.00</li>
        <li><strong>Acesso à Rede</strong><br> Allowed</li></ul>"""
        self.assertEqual(
            parse_software(page),
            {
                "hardware_version": "V3.00",
                "software_version": "08.89.17.27.26",
                "uptime_seconds": 88818,
                "network_access": "Allowed",
            },
        )

    def test_missing_or_invalid_measurement_is_not_zero(self):
        self.assertEqual(
            parse_software(
                "<li><strong>Tempo de Disponibilidade do Sistema</strong><br>--</li>"
            ),
            {},
        )


class RFTests(unittest.TestCase):
    def test_parse_downstream_and_upstream_separately(self):
        page = """<h2>Portadoras de Downstream adquiridas</h2><ul>
          <li><strong>Canal: 1</strong><br>Frequência: 381000000 Hz<br>Potência: 9.0 dBmV<br>SNR: 41.0 dBmV<br>Corrigido: 47<br>Sem correção: 0</li>
          <li><strong>Canal: 2</strong><br>Potência: 8.0 dBmV<br>SNR: 39.0 dBmV<br>Corrigido: 3<br>Sem correção: 1</li></ul>
          <ul><li><strong>Total corrigido</strong><br>50</li><li><strong>Total sem correção</strong><br>1</li></ul>
          <h2>Portadora de Upstream adquirida</h2><ul>
          <li><strong>Canal: 1</strong><br>Potência: 44.0 dBmV</li>
          <li><strong>Canal: 2</strong><br>Potência: 45.0 dBmV</li></ul>"""
        self.assertEqual(
            parse_rf(page),
            {
                "downstream_channels": 2,
                "downstream_power_dbmv": 8.5,
                "downstream_snr_db": 40.0,
                "corrected_total": 50,
                "uncorrectable_total": 1,
                "upstream_channels": 2,
                "upstream_power_dbmv": 44.5,
            },
        )

    def test_total_counters_allow_blank_lines_after_br(self):
        page = "<h2>Portadoras de Downstream adquiridas</h2><li><strong>Total corrigido</strong><br>\n 77</li><li><strong>Total sem correção</strong><br>\n0</li>"
        self.assertEqual(
            parse_rf(page), {"corrected_total": 77, "uncorrectable_total": 0}
        )

    def test_empty_rf_page_is_not_reported_as_healthy(self):
        self.assertEqual(parse_rf("<h2>Conexão RF</h2>"), {})


if __name__ == "__main__":
    unittest.main()
