import unittest

from custom_components.isp_modem.reboot import RebootError, prepare_and_maybe_send

SOFTWARE = "<li><strong>Versão do software</strong><br>08.89.17.27.26</li><li><strong>Tempo de Disponibilidade do Sistema</strong><br>1 days 00h:40m:18s.00</li>"
RESET = "<script>var sessionKey='789'; function btnReset(){var loc = 'rebootinfo.cgi?'; loc += 'sessionKey=' + sessionKey;}</script><strong>Click the button below to reboot the router.</strong>"
LOGIN = '<form><input name="Login"><input name="Password"></form><script>function apply(){loc="login.html?";loc+="&sessionKey=123456!";loc+="Authorization:***";}</script>'


class WorkflowTests(unittest.TestCase):
    def test_dry_run_does_not_send_reboot(self):
        paths = []

        def get(path):
            paths.append(path)
            return SOFTWARE if path == "status-software.html" else RESET

        result = prepare_and_maybe_send(get, "user", "password", execute=False)
        self.assertFalse(result["attempted"])
        self.assertEqual(result["before_uptime"], 88818)
        self.assertEqual(paths, ["status-software.html", "resetrouter.html"])

    def test_login_before_reboot_and_only_once(self):
        paths = []

        def get(path):
            paths.append(path)
            if path.startswith("login.html?"):
                return "<title>logged in</title>"
            if path == "status-software.html":
                return (
                    LOGIN
                    if not any(x.startswith("login.html?") for x in paths)
                    else SOFTWARE
                )
            if path == "resetrouter.html":
                return RESET
            if path == "rebootinfo.cgi?sessionKey=789":
                return "reboot started"
            raise AssertionError(path)

        result = prepare_and_maybe_send(get, "user", "password", execute=True)
        self.assertTrue(result["attempted"])
        self.assertEqual(paths[-1], "rebootinfo.cgi?sessionKey=789")
        self.assertEqual(len([p for p in paths if p.startswith("rebootinfo.cgi?")]), 1)

    def test_rejects_wrong_reset_page_without_disruptive_call(self):
        paths = []

        def get(path):
            paths.append(path)
            return (
                SOFTWARE
                if path == "status-software.html"
                else "<button>restore factory settings</button>"
            )

        with self.assertRaises(RebootError):
            prepare_and_maybe_send(get, "user", "password", execute=True)
        self.assertNotIn("rebootinfo.cgi?sessionKey=789", paths)


if __name__ == "__main__":
    unittest.main()
