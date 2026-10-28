"""Native checks for the patched tensor-only checkpoint and causal boundary."""

import hashlib
import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from experiments.c1 import g2p2c_checkpoint as boundary

HAS_TORCH = importlib.util.find_spec("torch") is not None


class ExecutablePayload:
    def __reduce__(self):
        return eval, ("1 + 1",)


@unittest.skipUnless(HAS_TORCH, "requires the locked C1 PyTorch runtime")
class CheckpointBoundaryTests(unittest.TestCase):
    def setUp(self):
        import torch

        self.torch = torch
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "actor.pt"
        self.expected = {"weight": torch.ones((2, 3), dtype=torch.float32)}

    def load(self, value, **options):
        self.torch.save(value, self.path, **options)
        return boundary.load_actor_weights(
            self.path,
            sha256=hashlib.sha256(self.path.read_bytes()).hexdigest(),
            expected=self.expected,
        )

    def test_exact_dense_state_dict_roundtrip(self):
        result = self.load(self.expected)
        self.assertTrue(self.torch.equal(result["weight"], self.expected["weight"]))

    def test_runtime_lazy_inference_defaults_do_not_weaken_plain_tensor_boundary(self):
        from torch.distributions import Normal

        Normal(self.torch.zeros(1), self.torch.ones(1)).sample()
        result = self.load(self.expected)
        self.assertTrue(self.torch.equal(result["weight"], self.expected["weight"]))
        with self.torch.serialization.safe_globals([eval]):
            with self.assertRaisesRegex(ValueError, "caller-added"):
                self.load(self.expected)

    def test_old_runtime_refused_before_loader(self):
        with (
            patch.object(self.torch, "__version__", "2.2.0"),
            patch.object(self.torch, "load") as loader,
        ):
            with self.assertRaisesRegex(ValueError, "patched torch"):
                self.load(self.expected)
            loader.assert_not_called()

    def test_hash_refused_before_loader(self):
        self.torch.save(self.expected, self.path)
        with patch.object(self.torch, "load") as loader:
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                boundary.load_actor_weights(self.path, sha256="0" * 64, expected=self.expected)
            loader.assert_not_called()

    def test_legacy_pickle_refused_before_loader(self):
        with patch.object(self.torch, "load") as loader:
            with self.assertRaisesRegex(ValueError, "Legacy pickle/TAR"):
                self.load(self.expected, _use_new_zipfile_serialization=False)
            loader.assert_not_called()

    def test_executable_object_refused_without_unsafe_retry(self):
        import pickle

        with self.assertRaises(pickle.UnpicklingError):
            self.load({"weight": ExecutablePayload()})

    def test_user_allowlist_refused_before_loader(self):
        with (
            self.torch.serialization.safe_globals([eval]),
            patch.object(self.torch, "load") as loader,
        ):
            with self.assertRaisesRegex(ValueError, "caller-added"):
                self.load(self.expected)
            loader.assert_not_called()

    def test_missing_and_extra_keys_refused(self):
        for value in ({"other": self.expected["weight"]}, {**self.expected, "extra": 1}):
            with self.subTest(keys=list(value)), self.assertRaisesRegex(ValueError, "keys"):
                self.load(value)

    def test_shape_dtype_and_nonfinite_refused(self):
        for value, error in (
            (self.torch.zeros(6), "shape"),
            (self.torch.zeros((2, 3), dtype=self.torch.float64), "dtype"),
            (self.torch.full((2, 3), float("nan")), "nonfinite"),
            (self.torch.full((2, 3), float("inf")), "nonfinite"),
        ):
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                self.load({"weight": value})

    def test_sparse_and_tensor_subclass_refused(self):
        for value in (
            self.expected["weight"].to_sparse(),
            self.torch.nn.Parameter(self.expected["weight"]),
        ):
            with self.assertRaisesRegex(ValueError, "plain dense CPU"):
                self.load({"weight": value})

    def test_byte_limit_refused_before_loader(self):
        with patch.object(boundary, "MAX_BYTES", 128), patch.object(self.torch, "load") as loader:
            with self.assertRaisesRegex(ValueError, "byte limit"):
                self.load(self.expected)
            loader.assert_not_called()

    def test_torchscript_and_compressed_zip_refused_before_loader(self):
        for compressed in (False, True):
            with zipfile.ZipFile(
                self.path,
                "w",
                compression=(zipfile.ZIP_DEFLATED if compressed else zipfile.ZIP_STORED),
            ) as archive:
                archive.writestr("actor/data.pkl", b"not executable")
                archive.writestr("actor/version", b"3")
                archive.writestr("actor/code/model.py", b"untrusted")
            with patch.object(self.torch, "load") as loader:
                with self.assertRaises(ValueError):
                    boundary.load_actor_weights(
                        self.path,
                        sha256=hashlib.sha256(self.path.read_bytes()).hexdigest(),
                        expected=self.expected,
                    )
                loader.assert_not_called()

    def test_invalid_action_and_observation_preserve_state_and_rng(self):
        from experiments.c1.g2p2c_policy_adapter import CausalActorAdapter
        from experiments.m1.contracts import Observation

        torch = self.torch

        class InvalidActor(torch.nn.Module):
            def forward(self, *_args):
                torch.rand(5)
                return None, None, torch.tensor([float("nan")])

        before = torch.get_rng_state().clone()
        controller = CausalActorAdapter(InvalidActor(), seed=24)
        local = controller._rng_state.clone()
        with self.assertRaisesRegex(ValueError, "finite"):
            controller.command(Observation(0, 110, 0, True), 0)
        self.assertIsNone(controller.previous)
        self.assertIsNone(controller.state._time_min)
        self.assertTrue(torch.equal(local, controller._rng_state))
        self.assertTrue(torch.equal(before, torch.get_rng_state()))
        with self.assertRaises(ValueError):
            controller.command(Observation(3, 110, 0, False), 0)
        self.assertIsNone(controller.state._time_min)
        self.assertTrue(torch.equal(before, torch.get_rng_state()))


if __name__ == "__main__":
    unittest.main()
