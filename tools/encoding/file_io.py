"""Strict file I/O for OpenCode custom tools. JSON stdin/stdout; Python stdlib only.

prepare never writes. commit checks the approved original hash and atomically replaces
one regular file. This is not a sandbox or a lock against external editors.
"""
import base64
import codecs
import difflib
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile

MAX_BYTES = 8 * 1024 * 1024
RULE_FILE = "encoding-rules.json"
ENCODINGS = {"utf-8", "cp949", "euc_kr", "utf-16-le", "utf-16-be"}
BOMS = ((codecs.BOM_UTF8, "utf-8"), (codecs.BOM_UTF16_LE, "utf-16-le"),
        (codecs.BOM_UTF16_BE, "utf-16-be"))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical_encoding(name):
    encoding = codecs.lookup(name).name
    if encoding not in ENCODINGS:
        raise ValueError(f"Unsupported encoding: {name}. Use UTF-8, CP949, EUC-KR, UTF-16LE or UTF-16BE.")
    return encoding


def glob_match(pattern, relative):
    # '*' never crosses a directory; '**/' matches zero or more directories.
    if not isinstance(pattern, str) or not pattern or pattern.startswith("/") or "\\" in pattern:
        raise ValueError("Encoding patterns must be relative paths using '/'.")
    parts = pattern.split("/")
    if ".." in parts:
        raise ValueError("Encoding patterns must not contain '..'.")

    def match(p, r):
        if not p:
            return not r
        if p[0] == "**":
            return match(p[1:], r) or bool(r) and match(p, r[1:])
        return bool(r) and fnmatch.fnmatchcase(r[0], p[0]) and match(p[1:], r[1:])

    return match(parts, relative.split("/"))


def rule_encoding(root, path):
    rules_path = root / RULE_FILE
    if not rules_path.exists():
        return None
    data = json.loads(rules_path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or set(data) != {"rules"} or not isinstance(data["rules"], list):
        raise ValueError(f"Invalid {RULE_FILE}: expected {{\"rules\": [...]}}.")
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError:
        relative = None  # Never apply project rules to an external file.
    chosen = None
    for rule in data["rules"]:
        if not isinstance(rule, dict) or set(rule) != {"pattern", "encoding"}:
            raise ValueError("Each encoding rule needs exactly pattern and encoding.")
        encoding = canonical_encoding(rule["encoding"])
        matches = glob_match(rule["pattern"], relative or "")
        if relative is not None and matches:
            chosen = encoding
    return chosen


def load_bytes(path):
    if not path.exists():
        return None
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError("Only regular, single-link files are supported.")
    if info.st_size > MAX_BYTES:
        raise ValueError(f"File exceeds the {MAX_BYTES} byte safety limit.")
    with path.open("rb") as source:
        data = source.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("File grew beyond the safety limit.")
    return data


def decode(raw, explicit):
    if raw is None:
        return "", explicit or "utf-8", b""
    if raw.startswith((codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE)):
        raise ValueError("UTF-32 is not supported; file was not modified.")
    bom, bom_encoding = next(((b, e) for b, e in BOMS if raw.startswith(b)), (b"", None))
    if explicit and bom_encoding and explicit != bom_encoding:
        raise ValueError(f"Encoding rule {explicit} conflicts with BOM {bom_encoding}.")
    encoding = explicit or bom_encoding or "utf-8"
    body = raw[len(bom):]
    try:
        text = body.decode(encoding, errors="strict")
    except UnicodeError as error:
        raise ValueError(f"Cannot decode as {encoding}. Set an explicit rule in {RULE_FILE}; no guessing.") from error
    if "\x00" in text:
        raise ValueError("NUL in text: binary data or missing UTF-16 encoding rule.")
    if text.encode(encoding, errors="strict") != body:
        raise ValueError("Original bytes do not round-trip in the selected encoding.")
    return text, encoding, bom


def encode(text, encoding, bom):
    if "\x00" in text or text.startswith("\ufeff"):
        raise ValueError("Do not put NUL or a BOM character in tool content; BOM is preserved separately.")
    try:
        body = text.encode(encoding, errors="strict")
    except UnicodeError as error:
        raise ValueError(f"Content contains characters not representable in {encoding}; file was not modified.") from error
    if body.decode(encoding, errors="strict") != text:
        raise ValueError("Output would lose characters in an encoding round-trip.")
    data = bom + body
    if len(data) > MAX_BYTES:
        raise ValueError("Output exceeds the file size safety limit.")
    return data


def align_newlines(text, original):
    endings = set(re.findall(r"\r\n|\r|\n", original))
    if len(endings) > 1 and re.search(r"\r|\n", text):
        raise ValueError("Mixed line endings: multiline edits/full rewrites need manual normalization first.")
    if endings:
        text = re.sub(r"\r\n|\r|\n", lambda _: next(iter(endings)), text)
    return text


def prepare(request):
    root = Path(request["root"]).resolve()
    path = Path(request["filePath"])
    if not path.is_absolute():
        raise ValueError("filePath must be absolute.")
    if path.is_symlink():
        raise ValueError("Symlink files are not supported.")
    path = path.resolve()
    if str(path) != request["filePath"]:
        raise ValueError("Path changed since permission check; retry with the canonical path.")
    operation = request["operation"]
    if operation == "read" and path.is_dir():
        names = sorted(p.name + ("/" if p.is_dir() else "") for p in path.iterdir())
        return {"output": "\n".join(names[:2000]), "path": str(path), "directory": True}
    explicit = rule_encoding(root, path)
    raw = load_bytes(path)
    if raw is None and operation != "write":
        raise ValueError(f"File does not exist: {path}")
    text, encoding, bom = decode(raw, explicit)
    if operation == "read":
        offset = request.get("offset", 1)
        limit = request.get("limit", 2000)
        if type(offset) is not int or type(limit) is not int or offset < 1 or not 1 <= limit <= 2000:
            raise ValueError("offset must be positive; limit must be between 1 and 2000.")
        lines = text.splitlines()
        end = min(len(lines), offset - 1 + limit)
        output = "\n".join(f"{i + 1}: {lines[i][:2000]}" for i in range(offset - 1, end))
        return {"path": str(path), "encoding": encoding,
                "output": f"{encoding}; lines {offset}-{end} of {len(lines)}\n{output}"}
    if operation == "edit":
        old = request["oldString"]
        new = request["newString"]
        if not old or old == new:
            raise ValueError("oldString must be nonempty and differ from newString.")
        old, new = align_newlines(old, text), align_newlines(new, text)
        count = text.count(old)
        if count == 0 or count > 1 and not request.get("replaceAll", False):
            raise ValueError(f"oldString matched {count} times. Require one exact match or explicit replaceAll.")
        updated = text.replace(old, new, -1 if request.get("replaceAll", False) else 1)
    elif operation == "write":
        updated = align_newlines(request["content"], text)
    else:
        raise ValueError(f"Unknown operation: {operation}")
    data = encode(updated, encoding, bom)
    if raw == data:
        raise ValueError("No byte changes to apply.")
    # Normalize only the preview, not the file bytes; make missing final newlines visible.
    preview_old = text.replace("\r\n", "\n").replace("\r", "\n").splitlines(keepends=True)
    preview_new = updated.replace("\r\n", "\n").replace("\r", "\n").splitlines(keepends=True)
    diff = "".join(line if line.endswith("\n") else line + "\n\\ No newline at end of file\n"
                   for line in difflib.unified_diff(preview_old, preview_new, fromfile=str(path), tofile=str(path)))
    return {"path": str(path), "expected": None if raw is None else digest(raw),
            "data": base64.b64encode(data).decode("ascii"), "encoding": encoding, "diff": diff,
            "added": sum(1 for s in diff.splitlines() if s.startswith("+") and not s.startswith("+++")),
            "removed": sum(1 for s in diff.splitlines() if s.startswith("-") and not s.startswith("---"))}


def commit(plan):
    path = Path(plan["path"])
    if not path.is_absolute() or path.is_symlink() or path.resolve() != path:
        raise ValueError("Path changed since approval; retry.")
    data = base64.b64decode(plan["data"], validate=True)
    if len(data) > MAX_BYTES:
        raise ValueError("Output exceeds the safety limit.")
    # A sidecar serializes kit writers. A stale lock after a crash must be inspected, not removed blindly.
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_name(path.name + ".opencode-kit.lock")
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    temporary = None
    try:
        os.close(fd)
        current = load_bytes(path)
        if (None if current is None else digest(current)) != plan["expected"]:
            raise ValueError("File changed after preview/approval. Read again; no changes were written.")
        mode = path.stat().st_mode if current is not None else None
        if mode is not None and not mode & stat.S_IWUSR:
            raise ValueError("File is read-only; no changes were written.")
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".opencode-kit-", delete=False) as output:
            temporary = Path(output.name)
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        if mode is not None:
            os.chmod(temporary, stat.S_IMODE(mode))
        # Catch external changes during staging too. External editors do not honor our lock;
        # callers must not concurrently edit the same file with an IDE.
        latest = load_bytes(path)
        if latest != current or path.is_symlink() or path.resolve() != path:
            raise ValueError("File changed while staging; no changes were written.")
        os.replace(temporary, path)
        temporary = None
        return {"output": f"Saved {path} ({plan['encoding']}); original encoding/BOM preserved."}
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        lock.unlink(missing_ok=True)


def main():
    try:
        request = json.loads(sys.stdin.read())
        result = commit(request["plan"]) if request["action"] == "commit" else prepare(request)
        print(json.dumps(result, ensure_ascii=True))
    except Exception as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=True))
        sys.exit(1)


if __name__ == "__main__":
    main()
