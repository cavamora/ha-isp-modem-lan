"""Read-only client test: no live modem calls and no reboot path."""

import asyncio
import unittest

from custom_components.isp_modem.client import ClaroModemClient


class _Content:
    def __init__(self, text):
        self.text = text.encode()
        self.offset = 0

    async def read(self, limit):
        chunk = self.text[self.offset : self.offset + min(limit, 20)]
        self.offset += len(chunk)
        return chunk


class _Response:
    status = 200

    def __init__(self, text):
        self.content = _Content(text)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False


class _Session:
    def __init__(self):
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if url.endswith("/status-software.html"):
            return _Response(
                "<li><strong>Versão do software</strong><br>08.89.17.27.26</li>"
            )
        return _Response(
            "<h2>Portadoras de Downstream adquiridas</h2><li><strong>Canal: 1</strong><br>Potência: 8 dBmV</li>"
        )


class ClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_status_uses_only_bounded_read_gets(self):
        session = _Session()
        status = await ClaroModemClient(session, "192.0.2.1").status()
        self.assertEqual(status["downstream_channels"], 1)
        self.assertEqual(
            [x[0].rsplit("/", 1)[-1] for x in session.calls],
            ["status-software.html", "status-conexao-rf.html"],
        )
        self.assertTrue(
            all(x[1].get("headers", {}).get("User-Agent") for x in session.calls)
        )

    async def test_status_logs_in_when_challenged(self):
        login_page = '<form><input name="Login"><input name="Password"></form><script>loc="login.html?";loc+="&sessionKey=123!";loc+="Authorization:Basic";</script>'
        software = "<li><strong>Versão do software</strong><br>08.89.17.27.26</li>"
        rf = "<h2>Portadoras de Downstream adquiridas</h2><li><strong>Canal: 1</strong><br>Potência: 8 dBmV</li>"

        class ChallengeSession(_Session):
            def get(self, url, **kwargs):
                self.calls.append((url, kwargs))
                if url.endswith("/status-software.html"):
                    return _Response(
                        software
                        if any("login.html?" in x[0] for x in self.calls)
                        else login_page
                    )
                if "login.html?" in url:
                    return _Response("login accepted")
                return _Response(rf)

        session = ChallengeSession()
        status = await ClaroModemClient(session, "192.0.2.1", "user", "pass").status()
        self.assertEqual(status["software_version"], "08.89.17.27.26")
        self.assertEqual(
            [x[0].split("/")[-1].split("?")[0] for x in session.calls],
            [
                "status-software.html",
                "login.html",
                "status-software.html",
                "status-conexao-rf.html",
            ],
        )
        self.assertIn("!Authorization:Basic", session.calls[1][0])

    async def test_slow_read_is_bounded(self):
        class SlowContent:
            async def read(self, limit):
                await asyncio.sleep(0.1)
                return b""

        class SlowSession(_Session):
            def get(self, url, **kwargs):
                response = _Response("")
                response.content = SlowContent()
                return response

        client = ClaroModemClient(SlowSession(), "192.0.2.1")
        client.TIMEOUT_SECONDS = 0.01
        with self.assertRaises(TimeoutError):
            await client._page("status-software.html")


if __name__ == "__main__":
    unittest.main()
