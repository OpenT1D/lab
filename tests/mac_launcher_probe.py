"""Opt-in Cocoa Quit fault probe using an owned worker and an NSAlert recording sink.

The production delegate and termination callback run unchanged. Only NSAlert's
blocking modal presentation is replaced in this fixture; real visible startup
failure is a separate application probe. No installed/user application is used.
"""

import argparse
import json
import os
import platform
import plistlib
import shlex
import signal
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHIM = r"""
#import <Cocoa/Cocoa.h>
#import <objc/runtime.h>

static NSString *directory(void) {
    return [[[NSBundle mainBundle] bundlePath] stringByDeletingLastPathComponent];
}
static NSModalResponse recordAlert(NSAlert *alert, SEL selector) {
    NSString *message = [NSString stringWithFormat:@"%@\n%@", alert.messageText,
                         alert.informativeText];
    [message writeToFile:[directory() stringByAppendingPathComponent:@"alert.txt"]
             atomically:YES encoding:NSUTF8StringEncoding error:nil];
    return NSAlertFirstButtonReturn;
}
static void quitWhenReady(unsigned attempts) {
    if ([[NSFileManager defaultManager] fileExistsAtPath:
         [directory() stringByAppendingPathComponent:@"ready"]]) {
        // Schedule a normal run-loop action. Calling terminate inside this GCD
        // block would prevent the serial main queue draining during its modal
        // NSTerminateLater wait, unlike the actual menu action.
        [NSApp performSelector:@selector(terminate:) withObject:nil afterDelay:0];
    } else if (attempts > 500) {
        exit(4);
    } else {
        dispatch_after(dispatch_time(DISPATCH_TIME_NOW, 20 * NSEC_PER_MSEC),
                       dispatch_get_main_queue(), ^{ quitWhenReady(attempts + 1); });
    }
}
@interface OpenT1DAlertProbe : NSObject
@end
@implementation OpenT1DAlertProbe
+ (void)load {
    method_setImplementation(class_getInstanceMethod([NSAlert class], @selector(runModal)),
                             (IMP)recordAlert);
    [[NSNotificationCenter defaultCenter] addObserverForName:
        NSApplicationDidFinishLaunchingNotification
        object:nil queue:nil usingBlock:^(NSNotification *note) { quitWhenReady(0); }];
}
@end
"""


def probe(launcher, output):
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise ValueError("This explicit Cocoa probe needs Apple Silicon macOS")
    output.mkdir()  # Existing evidence/user work is never overwritten.
    sdk = subprocess.check_output(["/usr/bin/xcrun", "--show-sdk-path"], text=True).strip()
    compiler = subprocess.check_output(["/usr/bin/xcrun", "--find", "clang"], text=True).strip()
    results = []
    for name, exit_code in (("clean", 0), ("failure", 19)):
        case = output / name
        app = case / "OpenT1D.app"
        contents = app / "Contents"
        binary = contents / "MacOS/OpenT1D"
        binary.parent.mkdir(parents=True)
        payload = contents / "Resources/payload"
        (payload / "app").mkdir(parents=True)
        fake = payload / "runtime/bin/python3.12"
        fake.parent.mkdir(parents=True)
        ready = shlex.quote(str(case / "ready"))
        exited = shlex.quote(str(case / "exit-marker"))
        stop = shlex.quote(f"printf shutdown > {exited}; exit {exit_code}")
        fake.write_text(
            f"#!/bin/sh\ntrap {stop} TERM\n"
            f"printf ready > {ready}\nwhile :; do /bin/sleep 0.05; done\n"
        )
        fake.chmod(0o755)
        with (contents / "Info.plist").open("wb") as stream:
            plistlib.dump(
                {
                    "CFBundleExecutable": "OpenT1D",
                    "CFBundlePackageType": "APPL",
                    "CFBundleIdentifier": f"org.opent1d.mmtt.fault.{os.getpid()}.{name}",
                    "CFBundleName": "OpenT1D MMTT Fault Probe",
                },
                stream,
            )
        shim = case / "AlertProbe.m"
        shim.write_text(SHIM)
        subprocess.run(
            [
                compiler,
                "-isysroot",
                sdk,
                "-fobjc-arc",
                "-arch",
                "arm64",
                "-mmacosx-version-min=11.0",
                "-framework",
                "Cocoa",
                launcher,
                shim,
                "-o",
                binary,
            ],
            check=True,
            timeout=60,
            capture_output=True,
        )
        process = subprocess.Popen(
            [binary],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            # This session contains only this probe's app, fake worker and sleep.
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate(timeout=2)
            (case / "stdout.txt").write_text(stdout)
            (case / "stderr.txt").write_text(stderr)
            raise
        (case / "stdout.txt").write_text(stdout)
        (case / "stderr.txt").write_text(stderr)
        assert process.returncode == 0, process.returncode
        assert (case / "exit-marker").read_text() == "shutdown"
        alert = case / "alert.txt"
        if exit_code:
            assert alert.exists(), "A Quit-initiated worker failure was silently hidden"
            assert "startup or shutdown error" in alert.read_text()
        else:
            assert not alert.exists(), "Normal Quit incorrectly reported a failure"
        results.append({"case": name, "worker_exit": exit_code, "alert_called": alert.exists()})
    (output / "receipt.json").write_text(json.dumps(results, indent=2) + "\n")
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--launcher", type=Path, default=ROOT / "packaging/mac/Launcher.m")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(probe(args.launcher.resolve(strict=True), args.output.resolve())))


if __name__ == "__main__":
    main()
