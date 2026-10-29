"""Bounded Mac staging rejects unsafe runtime/source inputs before publication."""

import io
import json
import struct
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import build_mac_app as builder


class MacArchiveTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.archive = self.base / "runtime.tar.gz"

    def archive_with(self, records, aliases=None):
        with tarfile.open(self.archive, "w:gz") as bundle:
            for name, kind, content in records:
                member = tarfile.TarInfo(name)
                if kind == "file":
                    member.mode = 0o755
                    member.size = len(content)
                    bundle.addfile(member, io.BytesIO(content))
                else:
                    member.type = tarfile.SYMTYPE if kind == "link" else tarfile.LNKTYPE
                    member.linkname = content
                    bundle.addfile(member)
        return {"sha256": builder.sha256(self.archive), "omitted_alias_links": aliases or {}}

    def test_exact_aliases_are_omitted_and_only_stdlib_regular_files_remain(self):
        lock = self.archive_with(
            [
                ("python/bin/python3.12", "file", b"private python"),
                ("python/bin/python3", "link", "python3.12"),
                ("python/lib/python3.12/json/__init__.py", "file", b"stdlib"),
                ("python/lib/python3.12/site-packages/tool.py", "file", b"no tools"),
                ("python/lib/python3.12/ensurepip/__init__.py", "file", b"no pip"),
                ("python/lib/python3.12/__pycache__/x.pyc", "file", b"no bytecode"),
            ],
            {"bin/python3": "python3.12"},
        )
        destination = self.base / "staged"
        builder.extract_runtime(self.archive, destination, lock)
        self.assertEqual(
            {p.relative_to(destination).as_posix() for p in destination.rglob("*") if p.is_file()},
            {"bin/python3.12", "lib/python3.12/json/__init__.py"},
        )
        self.assertFalse(any(p.is_symlink() for p in destination.rglob("*")))
        with self.assertRaisesRegex(ValueError, "fresh"):
            builder.extract_runtime(self.archive, destination, lock)

    def test_traversal_hardlinks_duplicates_and_unexpected_aliases_are_rejected(self):
        cases = [
            ([("python/../../outside", "file", b"x")], {}),
            ([("/python/file", "file", b"x")], {}),
            ([("python/bin/python3", "hardlink", "python/bin/python3.12")], {}),
            ([("python/x", "file", b"x"), ("python/x", "file", b"y")], {}),
            ([("python/bin/python3", "link", "python3.12")], {}),
            ([("python/bin/python3", "link", "../../outside")], {"bin/python3": "../../outside"}),
            (
                [("python/lib/alias", "link", "regular"), ("python/lib/alias/x", "file", b"x")],
                {"lib/alias": "regular"},
            ),
        ]
        for records, aliases in cases:
            with self.subTest(records=records):
                lock = self.archive_with(records, aliases)
                with self.assertRaises(ValueError):
                    builder.extract_runtime(self.archive, self.base / "rejected", lock)
                self.assertFalse((self.base / "rejected").exists())

    def test_hash_and_linked_staging_are_refused_before_any_write(self):
        lock = self.archive_with([("python/x", "file", b"x")])
        lock["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "hash"):
            builder.extract_runtime(self.archive, self.base / "rejected", lock)
        lock["sha256"] = builder.sha256(self.archive)
        target = self.base / "target"
        target.mkdir()
        linked = self.base / "linked"
        linked.symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "fresh"):
            builder.extract_runtime(self.archive, linked / "runtime", lock)
        self.assertEqual(list(target.iterdir()), [])


class MacMachOTests(unittest.TestCase):
    def test_upward_and_lazy_loads_are_checked_but_dylib_identity_is_not_a_dependency(self):
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary).resolve()
            binary = runtime / "library.dylib"
            binary.write_bytes(b"\xcf\xfa\xed\xfe" + b"load-command parser fixture")
            identity = (
                "\n minos 11.0\nLoad command 0\n cmd LC_ID_DYLIB\n"
                " name /opt/provider/library.dylib (offset 24)\n"
            )
            for command in ("LC_LOAD_UPWARD_DYLIB", "LC_LAZY_LOAD_DYLIB"):
                for dependency in ("/opt/foreign/libexternal.dylib", "/usr/lib/libSystem.B.dylib"):
                    with self.subTest(command=command, dependency=dependency):
                        commands = identity + (
                            f"Load command 1\n cmd {command}\n name {dependency} (offset 24)\n"
                        )
                        with patch.object(
                            builder.subprocess, "check_output", side_effect=["arm64\n", commands]
                        ):
                            if dependency.startswith("/opt/"):
                                with self.assertRaisesRegex(ValueError, "external library"):
                                    builder.macho_inventory(runtime, "11.0", require_python=False)
                            else:
                                observed = builder.macho_inventory(
                                    runtime, "11.0", require_python=False
                                )
                                self.assertEqual(
                                    observed[binary.name]["dependencies"], [dependency]
                                )
            with patch.object(
                builder.subprocess, "check_output", side_effect=["arm64\n", identity]
            ):
                observed = builder.macho_inventory(runtime, "11.0", require_python=False)
                self.assertEqual(observed[binary.name]["dependencies"], [])

    def test_fat64_x86_slice_cannot_hide_next_to_an_approved_arm64_interpreter(self):
        # Apple's fat_header/fat_arch_64 layout, with one aligned x86_64 Mach-O
        # object slice. This is a full wrapper, not an isolated magic prefix.
        # The swapped header is rejected too, independent of tool support for it.
        slice_bytes = struct.pack("<IiiIIIII", 0xFEEDFACF, 0x01000007, 3, 1, 0, 0, 0, 0)
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary).resolve()
            python = runtime / "bin/python3.12"
            python.parent.mkdir()
            python.write_bytes(b"\xcf\xfa\xed\xfe" + b"approved interpreter control")
            image = runtime / "extra-image"
            for order in (">", "<"):
                with self.subTest(byte_order=order):
                    header = struct.pack(order + "II", 0xCAFEBABF, 1)
                    arch = struct.pack(
                        order + "iiQQII", 0x01000007, 3, 4096, len(slice_bytes), 12, 0
                    )
                    image.write_bytes((header + arch).ljust(4096, b"\0") + slice_bytes)
                    with patch.object(
                        builder.subprocess,
                        "check_output",
                        side_effect=["arm64\n", "\n minos 11.0\n"],
                    ) as inspect:
                        with self.assertRaisesRegex(ValueError, "Only thin ARM64"):
                            builder.macho_inventory(runtime, "11.0")
                    # The permitted thin interpreter was inspected normally;
                    # rejecting the unrelated fat image is the required failure.
                    self.assertEqual(inspect.call_count, 2)

    def test_external_missing_and_escaping_dylibs_and_newer_os_are_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            runtime = Path(temporary).resolve()
            binary = runtime / "bin/python3.12"
            binary.parent.mkdir()
            binary.write_bytes(b"\xcf\xfa\xed\xfe" + b"synthetic load commands")
            for dependency, minimum in [
                ("/opt/homebrew/lib/x.dylib", "11.0"),
                ("@rpath/missing.dylib", "11.0"),
                ("@loader_path/../../../outside", "11.0"),
                ("/usr/lib/libSystem.B.dylib", "12.0"),
            ]:
                commands = (
                    f"\n minos {minimum}\nLoad command 0\n cmd LC_LOAD_DYLIB\n"
                    f" name {dependency} (offset 24)\n"
                )
                with (
                    self.subTest(dependency=dependency, minimum=minimum),
                    patch.object(
                        builder.subprocess, "check_output", side_effect=["arm64\n", commands]
                    ),
                    self.assertRaises(ValueError),
                ):
                    builder.macho_inventory(runtime, "11.0")
            commands = (
                "\n minos 11.0.0\nLoad command 0\n cmd LC_LOAD_DYLIB\n"
                " name /usr/lib/libSystem.B.dylib (offset 24)\n"
            )
            with patch.object(
                builder.subprocess, "check_output", side_effect=["arm64\n", commands]
            ):
                self.assertEqual(set(builder.macho_inventory(runtime, "11.0")), {"bin/python3.12"})


class MacBuildBoundaryTests(unittest.TestCase):
    def test_dirty_source_refuses_before_download_and_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary).resolve()
            output = base / "output"
            output.mkdir()
            marker = output / "user-file"
            marker.write_bytes(b"preserve")
            with (
                patch.object(builder.platform, "system", return_value="Darwin"),
                patch.object(builder.platform, "machine", return_value="arm64"),
                patch.object(builder, "download_runtime") as download,
            ):
                with patch.object(
                    builder, "source_inventory", side_effect=ValueError("dirty source")
                ):
                    with self.assertRaisesRegex(ValueError, "dirty source"):
                        builder.build(base, base / "new-output", base / "cache")
                with patch.object(builder, "source_inventory", return_value={}):
                    with self.assertRaisesRegex(ValueError, "fresh output"):
                        builder.build(base, output, base / "cache")
                download.assert_not_called()
            self.assertEqual(marker.read_bytes(), b"preserve")

    def test_payload_selector_keeps_mmtt_ancestry_and_excludes_native_runtime_locks(self):
        names = [
            "experiments/observation_analysis/analysis.py",
            "experiments/desktop/runtime.py",
            "experiments/m4/beta_cell/runtime/uv.lock",
            "tests/private.json",
            "packaging/mac/runtime-lock.json",
            "docs/decisions/0069-mmtt-sampling-reuse.md",
        ]
        selected = builder.selected_source({"files": dict.fromkeys(names, {})})
        self.assertNotIn(names[2], selected)
        self.assertNotIn(names[3], selected)
        self.assertEqual(set(selected), {names[i] for i in (0, 1, 4, 5)})
        lock = json.loads((builder.ROOT / names[4]).read_text())
        self.assertEqual(lock["architecture"], "arm64")
        self.assertEqual(len(lock["sha256"]), 64)

    def test_actual_payload_excludes_historical_environments_outputs_and_root_tooling(self):
        from scripts.build_windows_installer import source_inventory

        selected = builder.selected_source(source_inventory(builder.ROOT, allow_dirty=True))
        for name in selected:
            self.assertNotEqual(Path(name).name, "uv.lock")
            self.assertNotEqual(Path(name).name, "pyproject.toml")
            self.assertNotIn("runtime", Path(name).parts)
            self.assertFalse(name.endswith(("execution.json", "report.json", "verification.json")))
        for required in (
            "experiments/m3/researcher/intake.py",
            "experiments/m0/simglucose/recording.py",
            "experiments/m4/c_peptide/model.py",
            "experiments/observation_analysis/analysis.py",
            "experiments/mmtt_sampling/plan.py",
            "packaging/mac/Launcher.m",
        ):
            self.assertIn(required, selected)


if __name__ == "__main__":
    unittest.main()
