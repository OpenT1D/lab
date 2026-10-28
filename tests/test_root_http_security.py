"""Known HTTP security invariants in the root tooling's patched dependency."""

import http.client
import io
import ssl
import unittest
import zlib
from types import SimpleNamespace
from unittest.mock import patch

from urllib3 import HTTPResponse
from urllib3._base_connection import ProxyConfig
from urllib3.connection import HTTPSConnection
from urllib3.exceptions import ProtocolError
from urllib3.response import DeflateDecoder


class RootHTTPSecurityTests(unittest.TestCase):
    def test_chunk_size_line_is_bounded_before_untrusted_extension_is_buffered(self):
        class ObservedStream(io.BytesIO):
            def readline(self, size=-1):
                result = super().readline(size)
                self.largest_line = max(self.largest_line, len(result))
                return result

        stream = ObservedStream(
            b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n1;" + b"a" * 1_000_000
        )
        stream.largest_line = 0
        socket = SimpleNamespace(makefile=lambda *_args: stream)
        raw = http.client.HTTPResponse(socket)
        raw.begin()
        response = HTTPResponse(body=raw, headers=raw.headers.items(), preload_content=False)
        with self.assertRaisesRegex(ProtocolError, "maximum allowed length"):
            list(response.read_chunked())
        self.assertLess(stream.largest_line, 100_000)
        self.assertTrue(response.closed)

    def test_explicit_https_proxy_policy_is_separate_from_target_policy(self):
        proxy_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        target_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        target_context.check_hostname = False
        target_context.verify_mode = ssl.CERT_NONE
        connection = HTTPSConnection(
            "target.invalid",
            ssl_context=target_context,
            cert_reqs=ssl.CERT_NONE,
            ca_certs="target-only-ca.pem",
            proxy_config=ProxyConfig(proxy_context, False, None, None),
        )
        wrapped = SimpleNamespace(socket=object(), is_verified=True)
        with patch(
            "urllib3.connection._ssl_wrap_socket_and_match_hostname", return_value=wrapped
        ) as wrap:
            connection._connect_tls_proxy("proxy.invalid", object())
        self.assertIs(wrap.call_args.kwargs["ssl_context"], proxy_context)
        self.assertEqual(wrap.call_args.kwargs["cert_reqs"], ssl.CERT_REQUIRED)
        self.assertIsNone(wrap.call_args.kwargs["ca_certs"])
        self.assertEqual(proxy_context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(proxy_context.check_hostname)

    def test_deflate_trailing_input_cannot_restart_a_finished_stream(self):
        decoder = DeflateDecoder()
        payload = b"bounded tooling HTTP response"
        self.assertEqual(decoder.decompress(zlib.compress(payload)), payload)
        self.assertEqual(decoder.decompress(b"unexpected trailing bytes"), b"")
        self.assertEqual(decoder.decompress(b"more trailing bytes"), b"")


if __name__ == "__main__":
    unittest.main()
