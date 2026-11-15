"""Explicit TLS policy through invented contexts/sockets; no TLS or network I/O."""

import ssl
import unittest
from unittest.mock import Mock, patch

from experiments.simglucose_audit import intake_collector, pbs_intake, verifier_preparation

ADAPTERS = (
    (intake_collector, intake_collector._open_https, (), intake_collector.HOST, 30),
    (
        pbs_intake,
        pbs_intake._connect,
        ("https://invented.invalid/archive",),
        "invented.invalid",
        60,
    ),
    (
        verifier_preparation,
        verifier_preparation._connect,
        ("https://invented.invalid/source",),
        "invented.invalid",
        30,
    ),
)


def context():
    # Deliberately weaker fake default distinguishes an explicit floor from reliance
    # on a library default. It makes no claim about this host's real TLS defaults.
    return Mock(
        minimum_version=ssl.TLSVersion.TLSv1,
        check_hostname=True,
        verify_mode=ssl.CERT_REQUIRED,
    )


class TLSContextTests(unittest.TestCase):
    def test_explicit_tls12_floor_and_verification_precede_socket_delegation(self):
        for module, connect, args, host, timeout in ADAPTERS:
            with self.subTest(module=module.__name__):
                selected, plain, tls = context(), Mock(), Mock()
                selected.wrap_socket.return_value = tls

                def create_socket(address, *, timeout):
                    self.assertIs(selected.minimum_version, ssl.TLSVersion.TLSv1_2)
                    self.assertIs(selected.check_hostname, True)
                    self.assertEqual(selected.verify_mode, ssl.CERT_REQUIRED)
                    self.assertIsNone(selected.keylog_filename)
                    return plain

                with (
                    patch.object(module.ssl, "create_default_context", return_value=selected),
                    patch.object(
                        module.socket, "create_connection", side_effect=create_socket
                    ) as opened,
                ):
                    self.assertIs(connect(*args), tls)
                opened.assert_called_once_with((host, 443), timeout=timeout)
                selected.wrap_socket.assert_called_once_with(plain, server_hostname=host)
                plain.close.assert_not_called()

    def test_unverified_certificate_or_hostname_refuses_before_socket(self):
        for module, connect, args, _host, _timeout in ADAPTERS:
            for changed in ({"check_hostname": False}, {"verify_mode": ssl.CERT_NONE}):
                with self.subTest(module=module.__name__, changed=changed):
                    selected = context()
                    for name, value in changed.items():
                        setattr(selected, name, value)
                    with (
                        patch.object(module.ssl, "create_default_context", return_value=selected),
                        patch.object(module.socket, "create_connection") as opened,
                        self.assertRaises(ValueError),
                    ):
                        connect(*args)
                    opened.assert_not_called()
                    selected.wrap_socket.assert_not_called()

    def test_unsupported_minimum_refuses_before_socket_without_fallback(self):
        class UnsupportedContext:
            @property
            def minimum_version(self):
                return ssl.TLSVersion.TLSv1

            @minimum_version.setter
            def minimum_version(self, _value):
                raise ValueError("invented unsupported TLS minimum")

        for module, connect, args, _host, _timeout in ADAPTERS:
            with self.subTest(module=module.__name__):
                with (
                    patch.object(
                        module.ssl, "create_default_context", return_value=UnsupportedContext()
                    ),
                    patch.object(module.socket, "create_connection") as opened,
                    self.assertRaisesRegex(ValueError, "invented unsupported TLS minimum"),
                ):
                    connect(*args)
                opened.assert_not_called()

    def test_wrap_failure_closes_only_returned_plain_socket(self):
        for module, connect, args, _host, _timeout in ADAPTERS:
            with self.subTest(module=module.__name__):
                selected, plain = context(), Mock()
                selected.wrap_socket.side_effect = OSError("invented TLS wrap failure")
                with (
                    patch.object(module.ssl, "create_default_context", return_value=selected),
                    patch.object(module.socket, "create_connection", return_value=plain) as opened,
                    self.assertRaisesRegex(OSError, "invented TLS wrap failure"),
                ):
                    connect(*args)
                opened.assert_called_once()
                plain.close.assert_called_once_with()
                self.assertIs(selected.minimum_version, ssl.TLSVersion.TLSv1_2)


if __name__ == "__main__":
    unittest.main()
