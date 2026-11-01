"""Mirror selection keeps source authentication, suites and non-Ubuntu sources."""

import tempfile
import unittest
from pathlib import Path

from scripts import browser_dependencies as deps


class BrowserDependencyTests(unittest.TestCase):
    def test_exact_azure_uri_in_mirrorlist_legacy_and_deb822_sources(self):
        for text in (
            "http://azure.archive.ubuntu.com/ubuntu\tpriority:1\nhttps://archive.ubuntu.com/ubuntu\tpriority:2\n",
            "deb [arch=amd64 signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] "
            "http://azure.archive.ubuntu.com/ubuntu noble-updates main universe\n",
            "Types: deb\nURIs: https://azure.archive.ubuntu.com/ubuntu/\n"
            "Suites: noble noble-security\nComponents: main restricted\n"
            "Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg\n",
        ):
            with self.subTest(text=text):
                expected = text.replace(
                    "http://azure.archive.ubuntu.com/ubuntu", "https://archive.ubuntu.com/ubuntu"
                ).replace(
                    "https://azure.archive.ubuntu.com/ubuntu/", "https://archive.ubuntu.com/ubuntu"
                )
                self.assertEqual(deps.official_mirror(text), expected)

    def test_other_security_custom_and_lookalike_uris_are_byte_preserved(self):
        for uri in (
            "https://security.ubuntu.com/ubuntu",
            "https://packages.microsoft.com/ubuntu/24.04/prod",
            "https://private.example/ubuntu",
            "http://azure.archive.ubuntu.com/ubuntu-extra",
            "http://azure.archive.ubuntu.com.evil.example/ubuntu",
            "http://azure.archive.ubuntu.com/ubuntu?token=CONTROL",
            "# http://azure.archive.ubuntu.com/ubuntu",
        ):
            text = uri + "\n"
            self.assertEqual(deps.official_mirror(text), text)

    def test_configuration_retains_modes_and_refuses_existing_policy_and_links(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            mirrors, config = root / "mirrors", root / "network"
            mirrors.write_text("http://azure.archive.ubuntu.com/ubuntu\n")
            mirrors.chmod(0o640)
            deps.configure(mirrors, config)
            self.assertEqual(mirrors.stat().st_mode & 0o777, 0o640)
            self.assertEqual(config.read_text(), deps.APT_NETWORK)
            before = mirrors.read_bytes()
            with self.assertRaises(FileExistsError):
                deps.configure(mirrors, config)
            self.assertEqual(mirrors.read_bytes(), before)
            link = root / "linked"
            link.symlink_to(mirrors)
            with self.assertRaises(ValueError):
                deps.configure(link, root / "other")
            self.assertFalse((root / "other").exists())

    def test_network_policy_does_not_relax_signatures_or_retry_package_install(self):
        self.assertEqual(
            deps.APT_NETWORK,
            'Acquire::http::Timeout "30";\nAcquire::https::Timeout "30";\n'
            'Acquire::Retries "1";\nAPT::Update::Error-Mode "any";\n',
        )


if __name__ == "__main__":
    unittest.main()
