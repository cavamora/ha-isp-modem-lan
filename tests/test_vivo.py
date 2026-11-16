"""Synthetic Vivo modem tests; no live network or reboot calls."""

import hashlib
import unittest
import urllib.error
import urllib.parse

from custom_components.isp_modem.vivo import (
    VivoError,
    VivoModemClient,
    parse_vivo_status,
)

ABOUT = """<div>Modelo :</div><span>GPT-2741GNAC-N1</span>
<div>Versão do Software:</div><span>BR_g8.10_1.11(WVK.0)b46</span>
<div>Versão do Hardware:</div><span>tmp_hardware1.0</span>"""
INFO = """<span>Potência Rx:</span><span>-21.31 dBm</span>
<span>Potência Tx:</span><span>2.25 dBm</span>
<span>Senha:</span><span>do-not-expose</span>"""
LOGIN = """<form name="passWarning" action="login.cgi" method="post">
<input name="Loginuser"><input name="LoginPasswordValue"></form>
<script>function clicklogin(){var sid='Ab12Cd34';
var passwd=hex_md5(document.passWarning.LoginPassword.value+":"+sid);
document.passWarning.acceptLoginIndex.value=1;
document.passWarning.LoginPasswordValue.value=passwd;}</script>"""
RESETS = """<form method="POST" action="device-management-resets.cgi"></form>
<a href="popup-reboot.cgi">Reboot</a><a href="popup-resets.cgi">Restore</a>
<script>function reboot(){var data={restoreFlag:1,RestartBtn:"RESTART"};$.post(document.forms[0].action,data);}
function restore(){var data={restoreFlag:5,RestartBtn:"RESTART"};$.post(document.forms[0].action,data);}</script>"""
POPUP = '<a href="device-management-rebootinfo.cgi">Reboot</a><a href="#">Cancel</a>'
CONFIRM = '<script>$(document).ready(function(){parent.reboot();});</script>'


class _Response:
    status = 200

    def __init__(self, body):
        self.body = body.encode()
        self.offset = 0

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, n):
        chunk = self.body[self.offset : self.offset + min(n, 31)]
        self.offset += len(chunk)
        return chunk


class _Opener:
    def __init__(self, *, about=ABOUT, info=INFO, resets=RESETS, popup=POPUP, confirm=CONFIRM):
        self.about, self.info = about, info
        self.resets, self.popup, self.confirm = resets, popup, confirm
        self.requests = []
        self.logged_in = False

    def open(self, request, timeout):
        path = urllib.parse.urlsplit(request.full_url).path
        payload = request.data
        self.requests.append((path, payload))
        if path.endswith("/login.cgi") and payload is None:
            return _Response(LOGIN)
        if path.endswith("/login.cgi") and payload is not None:
            posted = urllib.parse.parse_qs(payload.decode())
            assert posted == {
                "Loginuser": ["user"],
                "LoginPasswordValue": [hashlib.md5(b"pass:Ab12Cd34").hexdigest()],
                "acceptLoginIndex": ["1"],
            }
            self.logged_in = True
            return _Response("sophia_index.cgi")
        if not self.logged_in:
            return _Response(LOGIN)
        if path.endswith("/about-power-box2.cgi"):
            return _Response(self.about)
        if path.endswith("/sophia_info.cgi"):
            return _Response(self.info)
        if path.endswith("/device-management-resets.cgi"):
            if payload is not None:
                assert payload == b"restoreFlag=1&RestartBtn=RESTART"
                assert request.get_header("X-requested-with") == "XMLHttpRequest"
                assert request.get_header("Referer").endswith("/device-management-resets.cgi")
                return _Response("accepted")
            return _Response(self.resets)
        if path.endswith("/popup-reboot.cgi"):
            return _Response(self.popup)
        if path.endswith("/device-management-rebootinfo.cgi"):
            return _Response(self.confirm)
        raise AssertionError(path)


class VivoTests(unittest.TestCase):
    def test_parser_allowlists_model_firmware_and_optical_power(self):
        result = parse_vivo_status(ABOUT, INFO)
        self.assertEqual(result["model"], "GPT-2741GNAC-N1")
        self.assertEqual(result["software_version"], "BR_g8.10_1.11(WVK.0)b46")
        self.assertEqual(result["optical_rx_dbm"], -21.31)
        self.assertEqual(result["optical_tx_dbm"], 2.25)
        self.assertNotIn("do-not-expose", str(result))
        self.assertNotIn("uptime_seconds", result)

    def test_status_authenticates_without_reboot_request(self):
        opener = _Opener()
        status = VivoModemClient("192.0.2.2", "user", "pass", opener=opener).status()
        self.assertEqual(status["model"], "GPT-2741GNAC-N1")
        self.assertEqual(
            [path.rsplit("/", 1)[-1] for path, _ in opener.requests],
            ["login.cgi", "login.cgi", "about-power-box2.cgi", "sophia_info.cgi"],
        )

    def test_only_known_firmware_is_supported(self):
        opener = _Opener(about=ABOUT.replace("BR_g8.10_1.11", "BR_unknown"))
        with self.assertRaisesRegex(VivoError, "Unsupported Vivo modem"):
            VivoModemClient("192.0.2.2", "user", "pass", opener=opener).status()

    def test_manual_restart_follows_confirmation_and_sends_one_non_factory_request(self):
        opener = _Opener()
        client = VivoModemClient("192.0.2.2", "user", "pass", opener=opener)
        self.assertEqual(client.restart(), {"attempted": True})
        self.assertEqual(
            [path.rsplit("/", 1)[-1] for path, _ in opener.requests],
            ["login.cgi", "login.cgi", "about-power-box2.cgi", "sophia_info.cgi",
             "device-management-resets.cgi", "popup-reboot.cgi",
             "device-management-rebootinfo.cgi", "device-management-resets.cgi"],
        )
        self.assertEqual(sum(1 for _, body in opener.requests if body and b"restoreFlag" in body), 1)

    def test_icon_only_entry_link_still_follows_confirmed_reboot_path(self):
        page = RESETS.replace(
            '<a href="popup-reboot.cgi">Reboot</a>',
            '<a href="popup-reboot.cgi"><img alt="Reboot"></a>',
        )
        opener = _Opener(resets=page)
        result = VivoModemClient("192.0.2.2", "user", "pass", opener=opener).restart()
        self.assertEqual(result, {"attempted": True})
        self.assertEqual(sum(1 for _, body in opener.requests if body and b"restoreFlag" in body), 1)

    def test_direct_reset_post_is_refused_without_the_manual_guard(self):
        opener = _Opener()
        client = VivoModemClient("192.0.2.2", "user", "pass", opener=opener)
        with self.assertRaisesRegex(VivoError, "Unexpected modem POST"):
            client._request("device-management-resets.cgi", b"restoreFlag=1")
        self.assertEqual(opener.requests, [])

    def test_comment_about_parent_reboot_does_not_arm_the_post(self):
        opener = _Opener(confirm='<script>// parent.reboot()\n</script>')
        with self.assertRaisesRegex(VivoError, "controls changed"):
            VivoModemClient("192.0.2.2", "user", "pass", opener=opener).restart()
        self.assertFalse(any(body and b"restoreFlag" in body for _, body in opener.requests))

    def test_factory_restore_flag_cannot_be_used_as_reboot(self):
        opener = _Opener(resets=RESETS.replace("restoreFlag:1", "restoreFlag:5"))
        with self.assertRaisesRegex(VivoError, "controls changed"):
            VivoModemClient("192.0.2.2", "user", "pass", opener=opener).restart()
        self.assertFalse(any(body and b"restoreFlag" in body for _, body in opener.requests))

    def test_unexpected_restart_button_value_refuses_post(self):
        opener = _Opener(resets=RESETS.replace('RestartBtn:"RESTART"', 'RestartBtn:"restart"', 1))
        with self.assertRaisesRegex(VivoError, "controls changed"):
            VivoModemClient("192.0.2.2", "user", "pass", opener=opener).restart()
        self.assertFalse(any(body and b"restoreFlag" in body for _, body in opener.requests))

    def test_confirmation_link_to_another_host_is_refused(self):
        opener = _Opener(popup=POPUP.replace(
            'href="device-management-rebootinfo.cgi"',
            'href="http://example.com/device-management-rebootinfo.cgi"',
        ))
        with self.assertRaisesRegex(VivoError, "controls changed"):
            VivoModemClient("192.0.2.2", "user", "pass", opener=opener).restart()
        self.assertFalse(any(body and b"restoreFlag" in body for _, body in opener.requests))

    def test_disconnected_response_does_not_retry_or_leak_credentials(self):
        class DroppedPost(_Opener):
            def open(self, request, timeout):
                if request.data and request.full_url.endswith("device-management-resets.cgi"):
                    self.requests.append((urllib.parse.urlsplit(request.full_url).path, request.data))
                    raise urllib.error.URLError("pass:secret@192.0.2.2")
                return super().open(request, timeout)

        opener = DroppedPost()
        with self.assertRaisesRegex(VivoError, "outcome unconfirmed") as caught:
            VivoModemClient("192.0.2.2", "user", "pass", opener=opener).restart()
        self.assertNotIn("secret", str(caught.exception))
        self.assertNotIn("192.0.2.2", str(caught.exception))
        self.assertEqual(sum(1 for _, body in opener.requests if body and b"restoreFlag" in body), 1)

    def test_missing_credentials_rejected_without_network_request(self):
        opener = _Opener()
        with self.assertRaises(VivoError):
            VivoModemClient("192.0.2.2", "", "", opener=opener).status()
        self.assertEqual(opener.requests, [])

    def test_transport_error_does_not_disclose_url_or_password(self):
        class FailedOpener:
            def open(self, request, timeout):
                raise urllib.error.URLError("pass:secret@192.0.2.2")

        client = VivoModemClient("192.0.2.2", "user", "secret", opener=FailedOpener())
        with self.assertRaises(VivoError) as caught:
            client.status()
        self.assertNotIn("secret", str(caught.exception))
        self.assertNotIn("192.0.2.2", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
