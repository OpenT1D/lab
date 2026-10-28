"""Seven selected IV-001 faults in disposable source copies, with controls and exact patches."""

import argparse
import difflib
import importlib.metadata
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import traceback
from pathlib import Path

from experiments.m0.simglucose.recording import interruption, write_json
from experiments.m1.artifacts import digest

from .common import ROOT, identity

MUTATIONS = (
    dict(
        id="rate_factor_60",
        target="experiments/m2/analysis.py",
        before='insulin += p["delivered_u_h"] * dt / 60',
        after='insulin += p["delivered_u_h"] * dt',
        runtime="python",
        test="test_m2.M2Tests.test_amounts_variable_intervals_endpoints_and_unobserved_day",
        failure=r"210\.0 != 3\.5",
    ),
    dict(
        id="duplicate_announcement",
        target="experiments/m1/control.py",
        before="self._announced.add(time_min)",
        after="pass  # selected mutation: no delivery memory",
        runtime="simglucose",
        test="experiments.m1.test_native.NativeTests.test_condition_order_missingness_and_once_only",
        failure=r"45\.0 != 0",
    ),
    dict(
        id="wrong_event_interval",
        target="experiments/m1/control.py",
        before="dict(MEALS).get(time_min, 0)",
        after="dict(MEALS).get(time_min + STEP, 0)",
        runtime="simglucose",
        test="experiments.verification.test_faults_native.FaultInformationTests.test_announcement_interval",
        failure=r"45\.0 != 0",
        prior_test="experiments.m1.test_native.NativeTests.test_condition_order_missingness_and_once_only",
    ),
    dict(
        id="skipped_masked_sensor",
        target="experiments/m2/cambridge.mjs",
        before="const sample = this.native.update(t,y);",
        after=(
            "if (!available(this.condition,(t-START)/60000)) return {};\n"
            "    const sample = this.native.update(t,y);"
        ),
        runtime="node",
        test="masking does not skip random-stream generation, including reset",
        failure="ERR_ASSERTION",
    ),
    dict(
        id="future_information",
        target="experiments/m2/cambridge.mjs",
        before="this.native.update(new Date(t), {CGM:()=>glucose}, history);",
        after="this.native.update(new Date(t), {CGM:()=>glucose}, _nativeAnnouncements);",
        runtime="node",
        test="boundary copies inputs and delivers announcements once; reset clears memory",
        failure="ERR_ASSERTION",
    ),
    dict(
        id="false_completion",
        target="experiments/m2/analysis.py",
        before="if len(points) != 2881 or",
        after="if False or",
        runtime="python",
        test="test_verification_faults.FaultBoundaryTests.test_complete_fixture_then_missing_final_point",
        failure="ValueError not raised",
    ),
    dict(
        id="changed_input_bytes",
        target="experiments/m2/analysis.py",
        before="if hashlib.sha256(snapshot.read(name)).hexdigest() != expected:",
        after="if False and hashlib.sha256(snapshot.read(name)).hexdigest() != expected:",
        runtime="python",
        test="test_verification_faults.FaultBoundaryTests.test_changed_input_bytes_with_identical_json_value",
        failure="ValueError not raised",
    ),
)


def command(case, source):
    if case["runtime"] == "node":
        node = shutil.which("node")
        if node is None:
            raise FileNotFoundError("Node 22.22.2 required")
        return [
            node,
            "--test",
            "--test-name-pattern",
            "^" + re.escape(case["test"]) + "$",
            "experiments/m2/test-native.mjs",
        ]
    python = (
        sys.executable
        if case["runtime"] == "python"
        else str(ROOT / "experiments/m0/simglucose/.venv/bin/python")
    )
    module = case["target"].removesuffix(".py").replace("/", ".")
    code = (
        "import pathlib,sys,unittest; from importlib import import_module; "
        f"assert pathlib.Path(import_module({module!r}).__file__).resolve()=="
        f"pathlib.Path({case['target']!r}).resolve(); "
        f"suite=unittest.defaultTestLoader.loadTestsFromName({case['test']!r}); "
        "assert suite.countTestCases()==1; "
        "result=unittest.TextTestRunner(verbosity=2).run(suite); "
        "sys.exit(0 if result.wasSuccessful() else 1)"
    )
    return [python, "-B", "-c", code]


def invoke(case, source, log, revision):
    cmd = command(case, source)
    environment = dict(
        os.environ,
        PYTHONPATH=os.pathsep.join((str(source / "tests"), str(source))),
        IV_TEST_REVISION=revision,
        PYTHONDONTWRITEBYTECODE="1",
        MPLCONFIGDIR="/private/tmp/opent1d-iv-mpl"
        if sys.platform == "darwin"
        else "/tmp/opent1d-iv-mpl",
    )
    child = None
    try:
        with log.open("wb") as stream:
            child = subprocess.Popen(
                cmd,
                cwd=source,
                env=environment,
                stdout=stream,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            code = child.wait(timeout=120)
        return dict(command=cmd, returncode=code, timeout=False, log_sha256=digest(log))
    except subprocess.TimeoutExpired:
        return dict(command=cmd, returncode=None, timeout=True)
    finally:
        if child is not None and child.poll() is None:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            child.wait()


def classify(case, result, log):
    if result["timeout"]:
        return "invalid_timeout"
    text = log.read_text(errors="replace")
    if result["returncode"] == 0:
        return "survived"
    if any(word in text for word in ("SyntaxError:", "ImportError:", "ModuleNotFoundError:")):
        return "invalid_unrelated_failure"
    if case["test"].split(".")[-1] not in text or not re.search(case["failure"], text):
        return "invalid_unrelated_failure"
    return "detected"


def run(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    summary = dict(
        schema="iv001.selected-mutations/1",
        status="started",
        identity=identity(),
        scope="Seven selected faults only; not whole-program mutation coverage",
        cases=[dict(definition=case, status="not_attempted") for case in MUTATIONS],
    )
    write_json(output / "mutation-report.json", summary)
    try:
        if summary["identity"]["dirty"]:
            raise ValueError("Commit sources before the mutation campaign")
        if subprocess.check_output(["node", "--version"], text=True).strip() != "v22.22.2":
            raise ValueError("Use locked Node 22.22.2")
        summary["node"] = "v22.22.2"
        native_python = str(ROOT / "experiments/m0/simglucose/.venv/bin/python")
        probe = (
            "import json,sys,platform,importlib.metadata as m; "
            "print(json.dumps(dict(python=sys.version,platform=platform.platform(),"
            "packages={k:m.version(k) for k in "
            "['simglucose','numpy','scipy','pandas','setuptools']},"
            "source=json.loads(m.distribution('simglucose').read_text('direct_url.json')))))"
        )
        summary["native_environment"] = json.loads(
            subprocess.check_output([native_python, "-c", probe], text=True)
        )
        if (
            summary["native_environment"]["source"]["vcs_info"]["commit_id"]
            != "a6f6777586c860457a2a1e6cce6d0bd3fd33d1cc"
        ):
            raise ValueError("Unexpected native simglucose revision")
        summary["python"] = sys.version
        summary["packages"] = {
            p.metadata["Name"]: p.version for p in importlib.metadata.distributions()
        }
        paths = [
            p
            for p in subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT, text=True).split(
                "\0"
            )
            if p
        ]
        summary["copied_source_sha256"] = {p: digest(ROOT / p) for p in paths}
        with interruption(1800):
            for index, case in enumerate(MUTATIONS):
                folder = output / case["id"]
                source = folder / "source"
                source.mkdir(parents=True)
                record = summary["cases"][index]
                record["status"] = "started"
                write_json(output / "mutation-report.json", summary)
                for name in paths:
                    origin = ROOT / name
                    if origin.is_symlink() or not origin.is_file():
                        raise ValueError("Copy regular tracked files only")
                    destination = source / name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(origin, destination)
                target = source / case["target"]
                original = target.read_text()
                if original.count(case["before"]) != 1:
                    raise ValueError(f"Nonunique mutation anchor: {case['id']}")
                record["before_sha256"] = digest(target)
                control = invoke(
                    case, source, folder / "control.log", summary["identity"]["revision"]
                )
                record["control"] = control
                if control["timeout"] or control["returncode"] != 0:
                    raise ValueError(f"Control failed: {case['id']}")
                if case["runtime"] == "node" and not re.search(
                    r"(?m)^# pass 1$", (folder / "control.log").read_text()
                ):
                    raise ValueError("Node control did not execute exactly the selected test")
                mutated = original.replace(case["before"], case["after"])
                target.write_text(mutated)
                record["after_sha256"] = digest(target)
                (folder / "mutation.patch").write_text(
                    "".join(
                        difflib.unified_diff(
                            original.splitlines(keepends=True),
                            mutated.splitlines(keepends=True),
                            fromfile="a/" + case["target"],
                            tofile="b/" + case["target"],
                        )
                    )
                )
                if "prior_test" in case:
                    prior = case | {"test": case["prior_test"]}
                    record["prior_selected_test"] = invoke(
                        prior, source, folder / "prior-test.log", summary["identity"]["revision"]
                    )
                outcome = invoke(
                    case, source, folder / "mutant.log", summary["identity"]["revision"]
                )
                record["mutant"] = outcome
                record["status"] = classify(case, outcome, folder / "mutant.log")
                write_json(output / "mutation-report.json", summary)
                print(case["id"], record["status"], flush=True)
        summary["status"] = (
            "completed" if all(c["status"] == "detected" for c in summary["cases"]) else "failed"
        )
        if {p: digest(ROOT / p) for p in paths} != summary["copied_source_sha256"]:
            raise ValueError("The original checkout changed during the mutation campaign")
    except BaseException as error:
        summary.update(status="failed", error=f"{type(error).__name__}: {error}")
        (output / "failure.log").write_text(traceback.format_exc())
        raise
    finally:
        summary["files_sha256"] = {
            str(p.relative_to(output)): digest(p)
            for p in sorted(output.rglob("*"))
            if p.is_file() and p != output / "mutation-report.json"
        }
        write_json(output / "mutation-report.json", summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    result = run(parser.parse_args().output)
    sys.exit(0 if result["status"] == "completed" else 1)
