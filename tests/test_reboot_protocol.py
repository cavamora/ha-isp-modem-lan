"""Synthetic protocol tests: never send a live reboot from the test suite."""

import unittest

from custom_components.isp_modem.protocol import (
    login_challenge,
    login_path,
    reboot_confirmed,
    reboot_path,
    reboot_token,
)


class ProtocolTests(unittest.TestCase):
    def test_login_challenge_requires_expected_form(self):
        page = """<h2>Por favor, informe o login e a senha</h2>
        <form><input name="Login"/><input name="Password"/></form>
        <script>function apply() { loc = "login.html?";
        loc += "&sessionKey=123456!"; loc += "Authorization:Basic"; }</script>"""
        self.assertEqual(login_challenge(page), "123456")
        self.assertIsNone(login_challenge("<h2>Status</h2>"))

    def test_login_path_is_only_the_observed_firmware_protocol(self):
        path = login_path("123456", "example", "secret")
        self.assertTrue(
            path.startswith("login.html?&sessionKey=123456!Authorization:Basic")
        )
        self.assertNotIn("secret", path)

    def test_reboot_token_never_accepts_factory_reset_page(self):
        page = """<script>var sessionKey='789'; function btnReset() {
          var loc = 'rebootinfo.cgi?'; loc += 'sessionKey=' + sessionKey;
        }</script><strong>Click the button below to reboot the router.</strong>"""
        self.assertEqual(reboot_token(page), "789")
        self.assertEqual(reboot_path("789"), "rebootinfo.cgi?sessionKey=789")
        self.assertIsNone(
            reboot_token(page.replace("rebootinfo.cgi?", "factoryreset.cgi?"))
        )
        self.assertIsNone(
            reboot_token(page.replace("reboot the router", "restore factory settings"))
        )

    def test_uptime_drop_proves_reboot_but_increment_does_not(self):
        self.assertTrue(reboot_confirmed(90000, 80))
        self.assertFalse(reboot_confirmed(90000, 90100))
        self.assertFalse(reboot_confirmed(100, 80))
        self.assertFalse(reboot_confirmed(None, 80))


if __name__ == "__main__":
    unittest.main()
