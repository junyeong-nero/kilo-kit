#!/usr/bin/env python3
"""Build the Windows x64 offline ZIP on an internet-connected Windows runner (GitHub Actions only).

Downloads are pinned by version and hash in config/offline-artifacts.lock.json, config/redis/requirements.lock
and config/word/requirements.lock.
The target PC never downloads, installs or builds anything.
  python .github/tools/build.py   # prepare bin/ and runtime/, then dist/kilo-kit-win-x64.zip
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import ssl
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]
NAME = "kilo-kit"
CACHE = ROOT / ".cache/offline"


def digest(path, algorithm="sha256"):
    value = hashlib.new(algorithm)
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def fetch(name, artifact):
    target = CACHE / f"{name}-{artifact['version']}.zip"
    if not target.exists():
        print(f"Downloading {name} {artifact['version']} ...", flush=True)
        request = urllib.request.Request(artifact["url"], headers={"User-Agent": "kilo-kit-offline-builder"})
        partial = target.with_suffix(".partial")
        try:
            with urllib.request.urlopen(request, context=ssl.create_default_context(), timeout=300) as source, partial.open("wb") as out:
                shutil.copyfileobj(source, out)
            if digest(partial) != artifact["sha256"]:
                raise ValueError(f"Checksum mismatch: {artifact['url']}")
            partial.replace(target)
        finally:
            partial.unlink(missing_ok=True)
    if digest(target) != artifact["sha256"]:
        raise ValueError(f"Checksum mismatch: {target}")
    return target


def extract(archive, destination, prefix=""):
    """Reject unsafe ZIP entries and keep the distribution's relative layout."""
    with zipfile.ZipFile(archive) as source:
        for entry in source.infolist():
            filename = entry.filename.replace("\\", "/")
            if not filename.startswith(prefix) or filename.endswith("/"):
                continue
            relative = filename[len(prefix):]
            path = PurePosixPath(relative)
            if not relative or path.is_absolute() or ".." in path.parts or ":" in relative:
                raise ValueError(f"Unsafe ZIP member: {entry.filename}")
            target = destination.joinpath(*path.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with source.open(entry) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)


def require_pe(path):
    with Path(path).open("rb") as source:
        if source.read(2) != b"MZ":
            raise ValueError(f"Not a Windows executable: {path}")


def prepare_artifacts(lock):
    for name, artifact in lock["artifacts"].items():
        archive = fetch(name, artifact)
        destination = ROOT / artifact["destination"]
        with tempfile.TemporaryDirectory(prefix=f"{name}-", dir=CACHE) as tmp:
            staging = Path(tmp) / "files"
            extract(archive, staging, artifact["prefix"])
            if "file" in artifact:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(staging / artifact["file"], destination)
                require_pe(destination)
            else:
                if destination.exists():
                    shutil.rmtree(destination)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(staging), destination)
        print(f"Prepared {artifact['destination']} ({artifact['version']})", flush=True)
    for relative in ("bin/kilo/kilo.exe", "runtime/python/python.exe", "bin/rg.exe", "bin/fd.exe"):
        require_pe(ROOT / relative)


def install_wheels(lock, packages):
    wheels = CACHE / "python-wheels"
    wheels.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, "-m", "pip", "download", "--require-hashes", "--only-binary=:all:",
                    "--platform", "win_amd64", "--python-version", "3.13", "--dest", str(wheels), "-r", str(lock)], check=True)
    if packages.exists():
        shutil.rmtree(packages)
    subprocess.run([sys.executable, "-m", "pip", "install", "--require-hashes", "--no-index", "--find-links", str(wheels),
                    "--only-binary=:all:", "--no-compile", "--no-warn-script-location",
                    "--platform", "win_amd64", "--python-version", "3.13",
                    "--target", str(packages), "-r", str(lock)], check=True)


def prepare_python():
    """Install hash-locked Windows wheels for the embedded Python here, never on the offline target."""
    runtime = ROOT / "runtime/python"
    packages = runtime / "Lib/site-packages"
    lock = ROOT / "config/redis/requirements.lock"
    install_wheels(lock, packages)
    # word-mcp-live needs mcp 2 and the build center mcp 1: separate folder, selected by mcp/word/word_mcp.py.
    word_packages = ROOT / "runtime/word-mcp"
    word_lock = ROOT / "config/word/requirements.lock"
    install_wheels(word_lock, word_packages)
    # Embedded Python ignores PYTHONPATH; the server modules and packages are listed explicitly.
    (runtime / "python313._pth").write_text("python313.zip\n.\nLib/site-packages\n../../mcp/build-center\n../../mcp/word\nimport site\n",
                                            encoding="utf-8")
    notices = ROOT / "third_party/python"
    shutil.copy2(runtime / "LICENSE.txt", notices / "PYTHON-LICENSE.txt")
    shutil.copy2(lock, notices / "requirements.lock")
    shutil.copy2(word_lock, notices / "word-requirements.lock")
    (notices / "PACKAGES.json").write_text(json.dumps([
        {"metadata": str(p.relative_to(ROOT / "runtime")).replace(os.sep, "/"), "sha256": digest(p)}
        for p in sorted(packages.glob("*.dist-info/METADATA")) + sorted(word_packages.glob("*.dist-info/METADATA"))
    ], indent=2) + "\n", encoding="utf-8")
    subprocess.run([str(runtime / "python.exe"), "-I", "-X", "utf8", "-B", "-c",
                    "import redis, mcp, pydantic_core; from main import create_server; from zoneinfo import ZoneInfo; ZoneInfo('Asia/Seoul')"],
                   check=True, cwd=tempfile.gettempdir())
    # The Word server must see mcp 2 and a working pywin32; importing main registers its tools without starting.
    subprocess.run([str(runtime / "python.exe"), "-I", "-X", "utf8", "-B", "-c",
                    "import word_mcp; word_mcp.use_word_packages(); import mcp, importlib.metadata as m; "
                    "assert m.version('mcp').startswith('2.'), m.version('mcp'); "
                    "import pythoncom, win32com.client, docx, fastmcp, word_document_server.main"],
                   check=True, cwd=tempfile.gettempdir())


def package(lock, output):
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    # Never ship a real models.json, internal mappings, backups, caches or bytecode.
    never = {"models.json", "server_IP_mappings.json", "owners.json", "cache", "__pycache__"}

    def ignore(directory, names):
        return [n for n in names if n in never or n.endswith((".pyc", ".bak", ".log"))]

    with tempfile.TemporaryDirectory(prefix="package-", dir=CACHE) as tmp:
        stage = Path(tmp) / NAME
        stage.mkdir()
        for relative in ("bin", "runtime/python", "runtime/word-mcp", "mcp", "config", "scripts", "docs", "third_party"):
            shutil.copytree(ROOT / relative, stage / relative, ignore=ignore)
        for relative in ("setup.ps1", "README.md"):
            shutil.copy2(ROOT / relative, stage / relative)
        manifest = {
            "version": os.environ.get("RELEASE_VERSION", "dev"),
            "platform": lock["platform"], "artifacts": lock["artifacts"],
            "files": {str(p.relative_to(stage)).replace(os.sep, "/"): digest(p) for p in sorted(stage.rglob("*")) if p.is_file()},
        }
        (stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        partial = output.with_suffix(".zip.partial")
        try:
            with zipfile.ZipFile(partial, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as target:
                for path in sorted(stage.rglob("*")):
                    if path.is_file():
                        target.write(path, path.relative_to(stage.parent))
            partial.replace(output)
        finally:
            partial.unlink(missing_ok=True)
        shutil.copy2(stage / "manifest.json", output.parent / "manifest-win-x64.json")
    checksum = digest(output)
    output.with_suffix(output.suffix + ".sha256").write_text(f"{checksum}  {output.name}\n")
    print(f"Built {output} ({output.stat().st_size / 1024 / 1024:.1f} MiB)\nSHA256 {checksum}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", default=str(ROOT / f"dist/{NAME}-win-x64.zip"))
    args = parser.parse_args()
    if sys.platform != "win32":
        raise SystemExit("Run on Windows: the embedded Python is verified by executing it.")
    CACHE.mkdir(parents=True, exist_ok=True)
    lock = json.loads((ROOT / "config/offline-artifacts.lock.json").read_text(encoding="utf-8"))
    prepare_artifacts(lock)
    prepare_python()
    package(lock, args.output)


if __name__ == "__main__":
    main()
