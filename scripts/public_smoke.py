"""Run explicit synthetic task and real-host smoke cases locally and in CI."""

import argparse
import json
import platform
import subprocess
import sys
import unittest
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
COMMON = (
    "tests.test_observation_workflow.ObservationWorkflowTests."
    "test_complete_local_cli_and_fresh_process_repeat_after_relocation",
    "tests.test_observation_workflow.ObservationWorkflowTests."
    "test_failures_reconstruct_and_all_attempts_survive",
    "tests.test_mmtt_sampling_platform.SamplingPlatformTests."
    "test_common_start_and_catalogue_verify_native_reports_without_source_changes",
    "tests.test_mmtt_sampling_workflow.SamplingWorkflowTests."
    "test_relocation_rebuilds_parent_and_native_reports",
    "tests.test_local_gui.LocalGUITests."
    "test_transport_rejects_foreign_host_origin_missing_token_and_large_body",
    "tests.public_smoke_cases.HTTPTaskSmoke.test_paired_task_http_and_reopen",
    "tests.public_smoke_cases.HTTPTaskSmoke.test_sampling_task_http_and_reopen",
    "tests.test_windows_primitives.PlatformFileTests."
    "test_atomic_json_publication_preserves_held_reader_on_long_unicode_path",
    "tests.test_windows_primitives.PlatformFileTests."
    "test_atomic_text_keeps_platform_text_bytes_and_rejects_invalid_json",
    "tests.test_windows_primitives.PlatformFileTests."
    "test_atomic_bytes_with_explicit_sibling_preserve_exact_payload",
    "tests.test_windows_primitives.PlatformFileTests."
    "test_lock_is_exclusive_and_reusable_without_replacing_file",
    "tests.test_regular_file_snapshots.RegularFileSnapshotTests."
    "test_snapshot_closes_descriptor_and_refuses_nonregular_path",
)
POSIX = tuple(
    "tests.test_catalogue_process.LocalToolProcessTests." + name
    for name in (
        "test_normal_leader_exit_retains_ownership_in_both_tools",
        "test_crashed_leader_retains_ownership_in_both_tools",
        "test_deadline_stops_descendants_and_preserves_logs",
        "test_cancellation_stops_descendants_and_preserves_logs",
    )
) + (
    "tests.test_posix_atomic_publication.PosixAtomicPublicationTests."
    "test_bytes_ignore_existing_temporary_symlinks_without_following_or_publishing_them",
    "tests.test_posix_atomic_publication.PosixAtomicPublicationTests."
    "test_text_refuses_existing_temporary_symlinks_without_following_or_publishing_them",
)
WINDOWS = tuple(
    "tests.test_windows_primitives." + name
    for name in (
        "WorkerPipeTests.test_eof_before_admission_does_not_run_the_module",
        "WorkerPipeTests.test_normal_completion_does_not_wait_for_control_pipe_or_abort_at_exit",
        "WorkerPipeTests.test_private_cancel_seals_a_reconstructible_interrupted_analysis",
        "WindowsOwnershipTests.test_job_close_removes_descendant_after_direct_child_exits",
        "WindowsOwnershipTests.test_detached_worker_cleanup_still_reaps_a_live_descendant",
        "WindowsOwnershipTests.test_real_job_launch_gates_and_reaps_example",
        "PlatformFileTests."
        "test_windows_atomic_publication_refuses_linked_targets_and_preserves_stale_pending",
        "PlatformFileTests.test_windows_atomic_publication_failure_preserves_bytes_and_closes_handles",
    )
)


def cases(system):
    if system not in {"Linux", "Darwin", "Windows"}:
        raise ValueError("Public smoke requires Linux, macOS or Windows")
    return COMMON + (WINDOWS if system == "Windows" else POSIX)


def run_cases(names, stream=sys.stderr):
    if not names or len(set(names)) != len(names):
        raise ValueError("Smoke cases must be nonempty and unique")
    suite = unittest.defaultTestLoader.loadTestsFromNames(names)
    started = perf_counter()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    return {
        "passed": (
            result.wasSuccessful()
            and not result.skipped
            and not result.expectedFailures
            and result.testsRun == len(names)
        ),
        "planned": list(names),
        "executed": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "expected_failures": [test.id() for test, _ in result.expectedFailures],
        "unexpected_successes": [test.id() for test in result.unexpectedSuccesses],
        "skips": [{"case": test.id(), "reason": reason} for test, reason in result.skipped],
        "elapsed_seconds": perf_counter() - started,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Fresh synthetic JSON receipt")
    parser.add_argument("--expected-platform", help="CI runner system-architecture assertion")
    args = parser.parse_args(argv)
    actual = platform.system().lower() + "-" + platform.machine().lower()
    if args.expected_platform and args.expected_platform != actual:
        parser.error("Runner platform differs from its declared matrix target: " + actual)
    if args.output.exists() or args.output.is_symlink():
        parser.error("Choose a fresh smoke receipt path")
    names = cases(platform.system())
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    summary = run_cases(names)
    summary.update(
        schema="opent1d.public-smoke/1",
        platform=actual,
        python=platform.python_version(),
        source_sha=subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        source_dirty=bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)),
        native_installation="not requested",
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(summary, output, indent=2, sort_keys=True)
        output.write("\n")
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
