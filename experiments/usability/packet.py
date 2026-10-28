"""Bounded, version-bound preparation using the existing authoritative M4 reader."""

import hashlib
import html
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import tempfile
import uuid
from pathlib import Path

from experiments.catalogue.storage import decode, digest, dump, encoded, require

from .tasks import goals, participant_goals, session_goals

ROOT = Path(__file__).resolve().parents[2]
ASSETS = Path(__file__).with_name("assets")
SCHEMA = "opent1d.usability-packet/1"
MAX_FILES = 10000
MAX_BYTES = 1024 * 1024 * 1024
MAX_BUNDLE_BYTES = 64 * 1024 * 1024


def inventory(directory):
    """Include empty directories and reject linked, special or oversized payloads."""
    directory = Path(directory).absolute()
    for parent in (directory, *directory.parents):
        require(not parent.is_symlink(), "Packet/archive paths cannot contain symlinks")
    require(directory.is_dir(), "Choose an existing regular directory")
    files, directories, total = {}, [], 0
    for folder, children, names in os.walk(directory, followlinks=False):
        folder = Path(folder)
        for name in children:
            child = folder / name
            require(stat.S_ISDIR(child.lstat().st_mode), "Linked or special directory refused")
            directories.append(child.relative_to(directory).as_posix())
            require(len(directories) + len(files) <= MAX_FILES, "Too many packet entries")
        for name in names:
            path = folder / name
            before = path.lstat()
            require(
                stat.S_ISREG(before.st_mode) and before.st_nlink == 1,
                "Linked or special file refused",
            )
            total += before.st_size
            require(
                total <= MAX_BYTES and len(files) < MAX_FILES, "Packet exceeds size/count limits"
            )
            checksum = hashlib.sha256()
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1048576), b""):
                    checksum.update(block)
            after = path.lstat()
            require(
                (before.st_ino, before.st_size, before.st_mtime_ns)
                == (after.st_ino, after.st_size, after.st_mtime_ns),
                "File changed while read",
            )
            files[path.relative_to(directory).as_posix()] = {
                "sha256": checksum.hexdigest(),
                "bytes": after.st_size,
            }
    return {"files": files, "directories": sorted(directories)}


def git(*args, root=ROOT):
    return subprocess.check_output(["git", *args], cwd=root, text=True, timeout=60).strip()


def clean_revision(root=ROOT):
    require(
        not git("status", "--porcelain", "--untracked-files=all", root=root),
        "Commit the selected implementation before making a packet",
    )
    revision = git("rev-parse", "HEAD", root=root)
    require(re.fullmatch(r"[0-9a-f]{40}", revision), "Invalid checkout revision")
    return revision


def verify(directory):
    directory = Path(directory).absolute()
    actual = inventory(directory)
    require("manifest.json" in actual["files"], "Missing packet manifest")
    require(actual["files"]["manifest.json"]["bytes"] <= 4 * 1024 * 1024, "Manifest is too large")
    record = decode((directory / "manifest.json").read_bytes())
    require(
        isinstance(record, dict)
        and set(record)
        == {
            "schema",
            "id",
            "commit",
            "language",
            "target",
            "participant_results",
            "prepared_platform",
            "rights_scope",
            "references",
            "goals",
            "bundle_sha256",
            "inventory",
        }
        and record.get("schema") == SCHEMA,
        "Unsupported packet schema",
    )
    require(
        isinstance(record["id"], str) and re.fullmatch(r"packet-[0-9a-f]{32}", record["id"]),
        "Invalid packet identity",
    )
    require(
        isinstance(record["commit"], str) and re.fullmatch(r"[0-9a-f]{40}", record["commit"]),
        "Invalid packet revision",
    )
    require(
        isinstance(record["language"], str) and record["language"] in {"en", "nl"},
        "Invalid packet language",
    )
    require(
        isinstance(record["target"], str) and record["target"] in {"posix", "windows-wsl"},
        "Invalid packet target",
    )
    require(
        record.get("goals") in [session_goals(record["language"], name) for name in ("m4", "mmtt")],
        "Packet task goals changed",
    )
    require(
        record.get("participant_results") == "not_recorded", "Packet must not invent observations"
    )
    require(
        isinstance(record["references"], dict)
        and set(record["references"]) == {"complete", "interrupted"},
        "Both native references are required",
    )
    actual["files"].pop("manifest.json")
    require(actual == record.get("inventory"), "Packet files or directories differ from manifest")
    require(
        "source.bundle" in actual["files"]
        and actual["files"]["source.bundle"]["bytes"] <= MAX_BUNDLE_BYTES,
        "Missing or oversized source bundle",
    )
    require(
        record["bundle_sha256"] == actual["files"]["source.bundle"]["sha256"],
        "Source bundle identity differs",
    )
    for kind, reference in record["references"].items():
        require(
            isinstance(reference, dict)
            and isinstance(reference.get("report_sha256"), dict)
            and reference.get("path") == "references/" + kind
            and reference.get("status") == ("completed" if kind == "complete" else "interrupted")
            and reference.get("passed") is (kind == "complete"),
            "Reference role/status differs",
        )
        for artifact in ("report.json", "report.md", "figure.svg"):
            require(
                reference.get("report_sha256", {}).get(artifact)
                == actual["files"].get("references/" + kind + "/" + artifact, {}).get("sha256")
                and reference.get("report_sha256", {}).get(artifact) is not None,
                "Reference artifact binding differs",
            )
        require(
            digest(encoded(inventory(directory / "references" / kind)))
            == reference.get("original_inventory_sha256"),
            "Reference inventory identity differs",
        )
    return record


def prepare(output, complete, interrupted, language="en", target="posix", root=ROOT, session="m4"):
    require(
        language in {"en", "nl"}
        and target in {"posix", "windows-wsl"}
        and session in {"m4", "mmtt"},
        "Unsupported language or target",
    )
    revision = clean_revision(root)
    output = Path(output).absolute()
    references = {
        "complete": Path(complete).absolute(),
        "interrupted": Path(interrupted).absolute(),
    }
    for path in references.values():
        require(
            output != path and output not in path.parents and path not in output.parents,
            "Packet output overlaps reference input",
        )
    require(not output.exists() and not output.is_symlink(), "Choose a fresh packet output")
    output.parent.mkdir(parents=True, exist_ok=True)
    for parent in (output.parent, *output.parent.parents):
        require(not parent.is_symlink(), "Output cannot contain symlinks")
    source_inventories = {name: inventory(path) for name, path in references.items()}
    with tempfile.TemporaryDirectory(prefix="opent1d-packet-") as temporary:
        stage = Path(temporary).resolve() / "packet"
        stage.mkdir()
        (stage / "references").mkdir()
        shutil.copytree(ASSETS, stage / "assets")
        record = {
            "schema": SCHEMA,
            "id": "packet-" + uuid.uuid4().hex,
            "commit": revision,
            "language": language,
            "target": target,
            "participant_results": "not_recorded",
            "prepared_platform": platform.platform(),
            "rights_scope": (
                "Technical preparation; actual handoff review and dependency rights remain separate"
            ),
            "references": {},
            "goals": session_goals(language, session),
        }
        for name, source in references.items():
            destination = stage / "references" / name
            shutil.copytree(source, destination)
            require(inventory(destination) == source_inventories[name], "Reference copy differs")
            reader_output = Path(temporary) / ("reader-" + name)
            subprocess.run(
                [
                    str(Path(os.sys.executable).absolute()),
                    "-B",
                    "-E",
                    "-s",
                    "-S",
                    "-m",
                    "experiments.m4.secure_study",
                    "reconstruct",
                    "--archive",
                    str(destination),
                    "--output",
                    str(reader_output),
                    *([] if name == "complete" else ["--allow-failed"]),
                ],
                cwd=root,
                capture_output=True,
                check=True,
                timeout=120,
            )
            report = decode((reader_output / "report.json").read_bytes())
            require(
                report["passed"]
                if name == "complete"
                else report["status"] == "interrupted" and not report["passed"],
                "Reference is not the declared complete/interrupted native case",
            )
            hashes = {}
            for artifact in ("report.json", "report.md", "figure.svg"):
                raw = (destination / artifact).read_bytes()
                require(
                    raw == (reader_output / artifact).read_bytes(),
                    "Reconstructed artifact bytes differ",
                )
                hashes[artifact] = digest(raw)
            record["references"][name] = {
                "path": "references/" + name,
                "status": report["status"],
                "passed": report["passed"],
                "report_sha256": hashes,
                "original_inventory_sha256": digest(encoded(source_inventories[name])),
            }
        require(clean_revision(root) == revision, "Selected checkout changed during preparation")
        subprocess.run(
            ["git", "bundle", "create", str(stage / "source.bundle"), "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            timeout=60,
        )
        require(
            (stage / "source.bundle").stat().st_size <= MAX_BUNDLE_BYTES,
            "Source bundle is too large",
        )
        record["bundle_sha256"] = digest((stage / "source.bundle").read_bytes())
        write_guides(stage, root)
        for name, action in (("Install", "install"), ("Start", "start"), ("Check", "check")):
            (stage / (name + ".cmd")).write_bytes(
                (
                    "@echo off\r\nsetlocal\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass "
                    f'-File "%~dp0assets\\windows.ps1" -Action {action}\r\n'
                    'set "OPENT1D_EXIT=%ERRORLEVEL%"\r\npause\r\nexit /b %OPENT1D_EXIT%\r\n'
                ).encode()
            )
        starter = (
            (ASSETS / "posix.sh")
            .read_text()
            .replace("__COMMIT__", revision)
            .replace("__BUNDLE_SHA__", record["bundle_sha256"])
            .replace("__PACKET_ID__", record["id"])
        )
        (stage / "Install.command").write_text(starter)
        (stage / "Install.command").chmod(0o700)
        (stage / "Start.command").write_text(
            '#!/usr/bin/env bash\nexec "$(dirname "$0")/Install.command" start\n'
        )
        (stage / "Start.command").chmod(0o700)
        (stage / "Check.command").write_text(
            '#!/usr/bin/env bash\nexec "$(dirname "$0")/Install.command" check\n'
        )
        (stage / "Check.command").chmod(0o700)
        if session == "mmtt":
            moderator = (ASSETS / "moderator.html").read_text()
            expected = (ASSETS / ("mmtt-moderator-" + language + ".html")).read_text()
            (stage / "assets/moderator.html").write_text(
                moderator.replace("</main>", expected + "</main>")
            )
        write_first_steps(stage, record)
        record["inventory"] = inventory(stage)
        dump(stage / "manifest.json", record)
        verify(stage)
        require(
            all(inventory(path) == source_inventories[name] for name, path in references.items()),
            "Original reference changed during preparation",
        )
        shutil.copytree(stage, output)
    verify(output)
    return record


def write_first_steps(directory, record):
    """The private entry card is usable before any local server is installed."""
    dutch = record["language"] == "nl"
    title = "Begin hier — OpenT1D-test" if dutch else "Start here — OpenT1D test"
    text = (
        "Gebruik deze map voor één test met verzonnen voorbeelden. Er zijn nog geen "
        "testresultaten ingevuld. Spreek vooraf af of installeren wordt getest."
        if dutch
        else "Use this folder for one synthetic software exercise. No observations have "
        "been filled in. Agree beforehand whether installation is being assessed."
    )
    wsl = (
        "Dit is geen gewone Windows-installatie: OpenT1D draait in Ubuntu via WSL 2, "
        "een Linux-omgeving binnen Windows. Nodig: Windows 11 of Windows 10 vanaf "
        "versie 2004 (build 19041), internet bij installatie en zo nodig "
        "administratorrechten voor WSL. Pak eerst de hele ZIP uit in één map. "
        "Als Ubuntu nog ontbreekt: open PowerShell "
        "als administrator, voer onderstaande opdracht uit, herstart Windows en "
        "open Ubuntu om een gebruikersnaam en wachtwoord aan te maken."
        if dutch
        else "This is not native Windows installation: OpenT1D runs in Ubuntu through WSL 2. "
        "Use Windows 11 or Windows 10 version 2004 (build 19041) or later, internet "
        "for installation and administrator rights if WSL needs enabling. Extract "
        "the whole ZIP into one folder first. If Ubuntu is missing, open PowerShell as "
        "administrator, run the command below, restart Windows and open Ubuntu "
        "to create your user name and password."
    )
    prerequisites = (
        "Open Ubuntu en installeer, indien nodig, Git en curl met onderstaande "
        "opdracht. De startbestanden melden duidelijk wanneer deze ontbreken."
        if dutch
        else "Open Ubuntu and install Git and curl with the command below if missing. "
        "The launch files report missing prerequisites."
    )
    actions = (
        "Daarna: dubbelklik Install.cmd om de locked softwareomgevingen te "
        "installeren. Check.cmd controleert de installatie zonder een model te "
        "starten. Start.cmd opent de sessie in je Windows-browser. Houd het "
        "startvenster open; annuleer via de interface en stop daarna met Ctrl+C."
        if dutch
        else "Then double-click Install.cmd to explicitly install the locked "
        "environments. Check.cmd checks setup without running a model. Start.cmd "
        "opens the session in your Windows browser. Keep its window open; cancel "
        "in the interface and then stop with Ctrl+C."
    )
    pending = (
        "De Windows/WSL-route is voorbereid; een echte controle op een schone "
        "Windows-computer en menselijke gebruikstest staan nog open. Bewaar "
        "foutmeldingen als onderdeel van de test."
        if dutch
        else "The Windows/WSL route is prepared. A clean Windows host check and "
        "human usability session remain open. Retain errors as test observations."
    )
    posix = (
        "Op macOS/Linux: zorg dat Git en curl beschikbaar zijn. Gebruik daarna "
        "Install.command, Check.command en Start.command (op Linux via bash). "
        "Bij twijfel: raadpleeg docs/gui-test-session.md in de meegeleverde broncode."
        if dutch
        else "On macOS/Linux provide Git and curl, then use Install.command, "
        "Check.command and Start.command (with bash on Linux). See "
        "docs/gui-test-session.md in the supplied source checkout for recovery."
    )
    goals_html = "".join(
        "<li>" + html.escape(goal["goal"]) + "</li>" for goal in participant_goals(record["goals"])
    )
    form_label = (
        "Observatieformulier — ook zonder installatie"
        if dutch
        else "Observation form — available before installation"
    )
    content = (
        f'<!doctype html><html lang="{record["language"]}"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>{html.escape(title)}</title><link rel="stylesheet" href="assets/style.css">'
        f"<main><h1>{html.escape(title)}</h1><p>{html.escape(text)}</p>"
        f'<p><a href="Observations.html">{html.escape(form_label)}</a></p>'
        '<p><a href="guides/local-gui.html">GUI guide (English)</a> · '
        '<a href="guides/gui-test-session.html">Setup and recovery (English)</a></p>'
        f'<p class="small">{record["id"]} · {record["commit"]}</p>'
        f"<h2>Windows</h2><p>{html.escape(wsl)}</p>"
        "<pre><code>wsl --install -d Ubuntu</code></pre>"
        f"<p>{html.escape(prerequisites)}</p><pre><code>sudo apt-get update &amp;&amp; "
        "sudo apt-get install git curl ca-certificates</code></pre>"
        f"<p>{html.escape(actions)}</p><aside>{html.escape(pending)}</aside>"
        '<p><a href="https://learn.microsoft.com/en-us/windows/wsl/install">'
        "Microsoft WSL installation</a></p>"
        f"<h2>{'Opdrachten' if dutch else 'Session tasks'}</h2><ol>{goals_html}</ol>"
        '<p><a href="Participant.html">Deelnemerskaart / Participant card</a> · '
        '<a href="Moderator.html">Alleen begeleider / Moderator only</a></p>'
        "<details><summary>M4 — extra sessie / additional session</summary>"
        '<p><a href="M4-Participant.html">M4 taken / tasks</a> · '
        '<a href="M4-Observations.html">M4 formulier / worksheet</a> · '
        '<a href="M4-Moderator.html">M4 begeleider / moderator</a></p></details>'
        f"<details><summary>macOS / Linux</summary><p>{html.escape(posix)}</p>"
        "</details></main></html>"
    )
    (directory / "FirstSteps.html").write_text(content, encoding="utf-8")
    projection = {
        key: record[key]
        for key in ("schema", "id", "commit", "language", "target", "goals", "references")
    }
    for prefix, selected_goals in (("", record["goals"]), ("M4-", goals(record["language"]))):
        projection["goals"] = selected_goals
        for name, asset in (
            ("Observations", "observations"),
            ("Participant", "participant"),
            ("Moderator", "moderator"),
        ):
            source = directory / "assets" / (asset + ".html")
            # M4 retains its original moderator; only the selected MMTT page has answers.
            if prefix or not source.exists():
                source = ASSETS / (asset + ".html")
            page = (
                source.read_text()
                .replace("/test/style.css", "assets/style.css")
                .replace("/test/worksheet.js", "assets/worksheet.js")
            )
            page = page.replace('href="/test/"', 'href="FirstSteps.html"')
            page = page.replace(
                'href="/test/observations"', 'href="' + prefix + 'Observations.html"'
            )
            page = page.replace(
                'href="/" data-text="open"', 'href="FirstSteps.html" data-text="first"'
            )
            data = json.dumps(projection, ensure_ascii=True, allow_nan=False).replace(
                "<", "\\u003c"
            )
            page = page.replace(
                "<main>",
                '<script id="packet-data" type="application/json">' + data + "</script><main>",
            )
            (directory / (prefix + name + ".html")).write_text(page, encoding="utf-8")


def write_guides(directory, root):
    """Render exact canonical guide sources for offline receiving-side access."""
    from markdown_it import MarkdownIt

    target = directory / "guides"
    target.mkdir()
    names = (
        "local-gui",
        "gui-test-session",
        "gui-researcher-exercise",
        "observation-analysis",
        "mmtt-sampling",
    )
    revision = clean_revision(root)
    repository = (
        "OpenT1D/lab" if (root / "publication-snapshot.json").is_file() else "OpenT1D/OpenT1D"
    )
    renderer = MarkdownIt("commonmark", {"html": False})
    for name in names:
        source = (root / "docs" / (name + ".md")).read_bytes()
        (target / (name + ".md")).write_bytes(source)
        body = renderer.render(source.decode("utf-8"))
        for other in names:
            body = body.replace('href="' + other + '.md"', 'href="' + other + '.html"')
        body = re.sub(
            r'href="(?!https?://|#)([^"]+\.md(?:#[^"]*)?)"',
            lambda match: (
                'href="https://github.com/'
                + repository
                + "/blob/"
                + revision
                + "/docs/"
                + match.group(1)
                + '"'
            ),
            body,
        )
        page = (
            '<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<link rel="stylesheet" href="../assets/style.css"><main>'
            '<nav><a href="../FirstSteps.html">Session start</a></nav>'
            '<p class="small">Canonical English guide, copied from the packet revision. '
            "Research links beyond these bundled guides may require repository access.</p>"
            + body
            + "</main></html>"
        )
        (target / (name + ".html")).write_text(page, encoding="utf-8")


def receive(source, output):
    record = verify(source)
    output = Path(output).absolute()
    require(not output.exists() and not output.is_symlink(), "Choose a fresh received packet")
    for parent in (output.parent, *output.parent.parents):
        require(not parent.is_symlink(), "Output cannot contain symlinks")
    require(
        output.resolve() != Path(source).resolve()
        and Path(source).resolve() not in output.resolve().parents,
        "Receive output overlaps packet",
    )
    shutil.copytree(source, output)
    require(verify(output) == record, "Received packet differs")
    return record
