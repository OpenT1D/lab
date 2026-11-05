"""Run complete unittest discovery, optionally partitioned on module boundaries."""

import argparse
import hashlib
import json
import subprocess
import sys
import unittest
from collections import Counter
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def cases(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from cases(item)
        else:
            yield item


def partition(suite, index, total, weights):
    if not 1 <= index <= total <= 16:
        raise ValueError("Require 1 <= shard index <= total <= 16")
    modules = {}
    for case in cases(suite):
        modules.setdefault(case.__class__.__module__, []).append(case)
    loads = [0.0] * total
    assignments = {}
    for name in sorted(modules, key=lambda name: (-weights.get(name, len(modules[name])), name)):
        target = min(range(total), key=lambda number: (loads[number], number))
        assignments[name] = target
        loads[target] += weights.get(name, len(modules[name]))
    selected = [
        case for case in cases(suite) if assignments[case.__class__.__module__] == index - 1
    ]
    if not selected:
        raise ValueError("Empty root-test shard")
    return unittest.TestSuite(selected)


def discover(root=ROOT):
    loader = unittest.TestLoader()
    suite = loader.discover(str(root / "tests"))
    if loader.errors:
        raise ValueError(
            "Test discovery failed before shard selection:\n" + "\n".join(loader.errors)
        )
    return suite


def identities(suite):
    return [case.id() for case in cases(suite)]


def digest(names):
    return hashlib.sha256(("\n".join(names) + "\n").encode()).hexdigest()


class AccountingResult(unittest.TextTestResult):
    """Explain fixture skips without treating unexplained unrun cases as passes."""

    def __init__(self, *args, selected, **kwargs):
        super().__init__(*args, **kwargs)
        self.started_ids = []
        self.fixture_skipped = []
        self.fixture_cases = {}
        for case in selected:
            kind = case.__class__
            for fixture in (
                f"setUpClass ({kind.__module__}.{kind.__qualname__})",
                f"setUpModule ({kind.__module__})",
            ):
                self.fixture_cases.setdefault(fixture, []).append(case.id())

    def startTest(self, test):
        self.started_ids.append(test.id())
        super().startTest(test)

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        remaining = Counter(self.fixture_cases.get(test.id(), []))
        remaining.subtract(self.started_ids)
        remaining.subtract(row["test"] for row in self.fixture_skipped)
        for name, count in remaining.items():
            self.fixture_skipped.extend(
                {"test": name, "reason": reason, "fixture": test.id()} for _ in range(max(0, count))
            )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shard", default="1/1", help="one-based INDEX/TOTAL; whole modules")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--list", action="store_true", help="write discovery/selection without running"
    )
    args = parser.parse_args(argv)
    receipt = {
        "schema": "opent1d.root-tests/1",
        "shard": args.shard,
        "completed": False,
        "passed": False,
        "phase": "discovery",
    }

    def write_receipt():
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")

    # Replace previous evidence before discovery can fail or be interrupted.
    write_receipt()
    started = perf_counter()
    try:
        receipt["source_sha"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
        receipt["source_dirty"] = bool(
            subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
        )
        index, total = map(int, args.shard.split("/"))
        weights = json.loads((ROOT / "tests/root-test-timings.json").read_text())["module_seconds"]
        suite = discover()
        all_ids = identities(suite)
        selected = partition(suite, index, total, weights)
        receipt.update(
            discovered=len(all_ids),
            discovery_sha256=digest(all_ids),
            selected=identities(selected),
            selection_sha256=digest(identities(selected)),
            phase="selected",
        )
        write_receipt()
    except (ValueError, KeyError) as error:
        receipt["error"] = str(error)
        write_receipt()
        print(str(error), file=sys.stderr)
        return 2
    selected_ids = identities(selected)
    print(
        f"Root shard {args.shard}: {len(selected_ids)} / {len(all_ids)} discovered cases",
        flush=True,
    )
    print(f"Discovery SHA256: {receipt['discovery_sha256']}", flush=True)
    try:
        if args.list:
            print(json.dumps(receipt, indent=2))
            return 0
        receipt["phase"] = "tests"
        write_receipt()
        selected_cases = list(cases(selected))
        result = unittest.TextTestRunner(
            verbosity=2,
            durations=25,
            resultclass=lambda *args, **kwargs: AccountingResult(
                *args, selected=selected_cases, **kwargs
            ),
        ).run(selected)
        accounted = Counter(result.started_ids) + Counter(
            row["test"] for row in result.fixture_skipped
        )
        complete = accounted == Counter(selected_ids)
        passed = complete and result.wasSuccessful()
        receipt.update(
            completed=complete,
            phase="finished",
            passed=passed,
            tests_run=result.testsRun,
            skipped=[{"test": case.id(), "reason": reason} for case, reason in result.skipped],
            fixture_skipped=result.fixture_skipped,
            failures=[case.id() for case, _ in result.failures],
            errors=[case.id() for case, _ in result.errors],
            expected_failures=[case.id() for case, _ in result.expectedFailures],
            unexpected_successes=[case.id() for case in result.unexpectedSuccesses],
            durations=result.collectedDurations,
        )
        return 0 if passed else 1
    finally:
        receipt["elapsed_seconds"] = perf_counter() - started
        write_receipt()


if __name__ == "__main__":
    raise SystemExit(main())
