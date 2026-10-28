"""Bounded, patched-runtime intake for trusted G2P2C tensor checkpoints.

This is a format and identity boundary, not a sandbox for adversarial files.
No pickle fallback or caller-supplied allowlist is supported.
"""

import hashlib
import io
import re
import zipfile
from collections import OrderedDict
from pathlib import Path, PurePosixPath

TORCH_VERSION = "2.13.0"
MAX_BYTES = 64 * 1024 * 1024
MAX_ENTRIES = 1024


def require_runtime():
    import torch

    if torch.__version__.split("+")[0] != TORCH_VERSION:
        raise ValueError(f"Checkpoint intake requires patched torch=={TORCH_VERSION}")
    # This exact release registers defaults during import and lazy actor/RNN
    # inference. Compare identity with pinned implementations, never names or
    # a captured caller-controlled registry. Resulting subclasses still fail
    # the plain tensor boundary below.
    from torch._dynamo.decorators import _DimRange
    from torch.distributed._mesh_layout import _FlatLayout, _MeshLayout
    from torch.distributed.device_mesh import DeviceMesh
    from torch.distributed.tensor import DTensor
    from torch.distributed.tensor._dtensor_spec import DTensorSpec, ShardOrderEntry, TensorMeta
    from torch.distributed.tensor.placement_types import Partial, Replicate, Shard, _StridedShard
    from torch.nested._internal.nested_tensor import NestedTensor, _rebuild_njt

    defaults = {
        NestedTensor,
        _rebuild_njt,
        _FlatLayout,
        _MeshLayout,
        DTensorSpec,
        DeviceMesh,
        ShardOrderEntry,
        TensorMeta,
        Partial,
        Replicate,
        Shard,
        DTensor,
        _StridedShard,
        _DimRange,
    }
    if set(torch.serialization.get_safe_globals()) - defaults:
        raise ValueError("Checkpoint intake refuses caller-added safe globals")


def _container(data):
    """Reject legacy and executable archives before torch.load sees the bytes."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            names = [entry.filename for entry in entries]
            if (
                not 1 <= len(entries) <= MAX_ENTRIES
                or len(set(names)) != len(names)
                or sum(entry.file_size for entry in entries) > MAX_BYTES
                or any(
                    entry.compress_type != zipfile.ZIP_STORED or entry.flag_bits & 1
                    for entry in entries
                )
            ):
                raise ValueError("Checkpoint ZIP exceeds the bounded stored format")
            paths = [PurePosixPath(name) for name in names]
            if (
                any(
                    path.is_absolute() or len(path.parts) < 2 or ".." in path.parts or "\\" in name
                    for path, name in zip(paths, names)
                )
                or len({path.parts[0] for path in paths}) != 1
            ):
                raise ValueError("Checkpoint ZIP paths are invalid")
            relative = {str(PurePosixPath(*path.parts[1:])) for path in paths}
            if (
                not {"data.pkl", "version"} <= relative
                or "constants.pkl" in relative
                or any(name.startswith("code/") for name in relative)
            ):
                raise ValueError("Expected a state_dict ZIP, not a TorchScript archive")
    except zipfile.BadZipFile as error:
        raise ValueError("Legacy pickle/TAR checkpoints are refused") from error


def validate_tensors(weights, expected):
    import torch

    if type(weights) not in (dict, OrderedDict) or not weights:
        raise ValueError("Expected a plain nonempty actor state_dict")
    if any(type(key) is not str for key in weights) or set(weights) != set(expected):
        raise ValueError("Actor checkpoint tensor keys differ")
    for name, value in weights.items():
        reference = expected[name]
        if (
            type(value) is not torch.Tensor
            or value.layout != torch.strided
            or value.device.type != "cpu"
            or value.is_quantized
        ):
            raise ValueError(f"Expected a plain dense CPU tensor: {name}")
        if value.shape != reference.shape:
            raise ValueError(f"Actor checkpoint tensor shape differs: {name}")
        if value.dtype != reference.dtype or value.dtype != torch.float32:
            raise ValueError(f"Actor checkpoint tensor dtype differs: {name}")
        if not bool(torch.isfinite(value).all()):
            raise ValueError(f"Actor checkpoint tensor is nonfinite: {name}")
    return weights


def load_actor_weights(checkpoint, *, sha256, expected):
    """Load exact declared bytes once, with the fixed patched weights-only loader."""
    import torch

    require_runtime()
    if type(sha256) is not str or re.fullmatch(r"[0-9a-f]{64}", sha256) is None:
        raise ValueError("Expected lowercase SHA-256 for checkpoint")
    # One bounded read prevents a changed file or decompression from bypassing
    # the pre-deserialization byte ceiling. The hash binds these same bytes.
    with Path(checkpoint).open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("Checkpoint exceeds the byte limit")
    if hashlib.sha256(data).hexdigest() != sha256:
        raise ValueError("Checkpoint SHA-256 mismatch")
    _container(data)
    weights = torch.load(io.BytesIO(data), map_location="cpu", weights_only=True)
    return validate_tensors(weights, expected)
