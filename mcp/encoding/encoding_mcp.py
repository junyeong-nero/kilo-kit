"""Bundled stdio MCP server: read/edit/write text files without changing their encoding, BOM or line endings.

Kilo starts it in the project folder (cwd); only files under that folder are handled. stdout is the MCP protocol.
Detection: encoding-rules.json rule > BOM > valid UTF-8 > valid CP949. Anything else is rejected, never guessed.
Writes are strict (no '?' replacement) and atomic; the file must not change between reading and replacing.
"""
import codecs
import difflib
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile

MAX_BYTES = 8 * 1024 * 1024
RULE_FILE = "encoding-rules.json"
ENCODINGS = {"utf-8", "cp949", "euc_kr", "utf-16-le", "utf-16-be"}
BOMS = ((codecs.BOM_UTF8, "utf-8"), (codecs.BOM_UTF16_LE, "utf-16-le"), (codecs.BOM_UTF16_BE, "utf-16-be"))


def canonical_encoding(name):
    encoding = codecs.lookup(name).name
    if encoding not in ENCODINGS:
        raise ValueError(f"Unsupported encoding: {name}. Use utf-8, cp949, euc-kr, utf-16-le or utf-16-be.")
    return encoding


def glob_match(pattern, relative):
    # '*' never crosses a directory; '**/' matches zero or more directories.
    if not isinstance(pattern, str) or not pattern or pattern.startswith("/") or "\\" in pattern:
        raise ValueError(f"{RULE_FILE} patterns must be relative paths using '/'.")
    parts = pattern.split("/")
    if ".." in parts:
        raise ValueError(f"{RULE_FILE} patterns must not contain '..'.")

    def match(p, r):
        if not p:
            return not r
        if p[0] == "**":
            return match(p[1:], r) or bool(r) and match(p, r[1:])
        return bool(r) and fnmatch.fnmatchcase(r[0], p[0]) and match(p[1:], r[1:])

    return match(parts, relative.split("/"))


def rule_encoding(root, path):
    rules_path = root / RULE_FILE
    if not rules_path.is_file():
        return None
    data = json.loads(rules_path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or set(data) != {"rules"} or not isinstance(data["rules"], list):
        raise ValueError(f"Invalid {RULE_FILE}: expected {{\"rules\": [...]}}.")
    relative = path.relative_to(root).as_posix()
    chosen = None
    for rule in data["rules"]:
        if not isinstance(rule, dict) or set(rule) != {"pattern", "encoding"}:
            raise ValueError(f"Each {RULE_FILE} rule needs exactly pattern and encoding.")
        encoding = canonical_encoding(rule["encoding"])
        if glob_match(rule["pattern"], relative):
            chosen = encoding  # The last matching rule wins.
    return chosen


def resolve(root, file_path):
    """Absolute path inside root; symlinks are rejected so the checked path is the written path."""
    path = Path(file_path)
    path = path if path.is_absolute() else root / path
    if path.is_symlink():
        raise ValueError("Symlink files are not supported.")
    path = path.resolve()
    if path != root and root not in path.parents:
        raise ValueError(f"Outside the project folder {root}. Use the built-in tools, which ask for approval.")
    return path


def load_bytes(path):
    if not path.exists():
        return None
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError("Only regular, single-link files are supported.")
    if info.st_size > MAX_BYTES:
        raise ValueError(f"File exceeds the {MAX_BYTES} byte limit.")
    data = path.read_bytes()
    if len(data) > MAX_BYTES:
        raise ValueError("File grew beyond the size limit.")
    return data


def decode(raw, explicit):
    """Return (text, encoding, bom). Only lossless interpretations are accepted."""
    if raw is None:
        return "", explicit or "utf-8", b""
    if raw.startswith((codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE)):
        raise ValueError("UTF-32 is not supported.")
    bom, bom_encoding = next(((b, e) for b, e in BOMS if raw.startswith(b)), (b"", None))
    if explicit and bom_encoding and explicit != bom_encoding:
        raise ValueError(f"{RULE_FILE} says {explicit} but the file has a {bom_encoding} BOM.")
    body = raw[len(bom):]
    candidates = [explicit or bom_encoding] if explicit or bom_encoding else ["utf-8", "cp949"]
    for encoding in candidates:
        try:
            text = body.decode(encoding, errors="strict")
        except UnicodeError:
            continue
        if "\x00" in text:
            raise ValueError(f"NUL in text: binary file, or UTF-16 without BOM (add a {RULE_FILE} rule).")
        if text.encode(encoding, errors="strict") != body:
            raise ValueError(f"Bytes do not round-trip as {encoding}; file left unchanged.")
        return text, encoding, bom
    raise ValueError(f"Cannot decode as {' or '.join(candidates)}. Set the encoding in {RULE_FILE}.")


def encode(text, encoding, bom):
    if "\x00" in text or text.startswith("\ufeff"):
        raise ValueError("Do not put NUL or a BOM character in content; the BOM is preserved separately.")
    try:
        body = text.encode(encoding, errors="strict")
    except UnicodeError as error:
        bad = text[error.start:error.end] if isinstance(error, UnicodeEncodeError) else ""
        raise ValueError(f"{bad!r} cannot be represented in {encoding}; file left unchanged.") from None
    data = bom + body
    if len(data) > MAX_BYTES:
        raise ValueError("Output exceeds the size limit.")
    return data


def align_newlines(text, original):
    endings = set(re.findall(r"\r\n|\r|\n", original))
    if len(endings) > 1 and re.search(r"\r|\n", text):
        raise ValueError("The file mixes line endings; multi-line edits need manual normalization first.")
    if endings:
        ending = next(iter(endings))
        text = re.sub(r"\r\n|\r|\n", lambda _: ending, text)
    return text


def read_file(root, file_path, offset=1, limit=2000):
    path = resolve(root, file_path)
    if path.is_dir():
        names = sorted(p.name + ("/" if p.is_dir() else "") for p in path.iterdir())
        return "\n".join(names[:2000])
    raw = load_bytes(path)
    if raw is None:
        raise ValueError(f"File does not exist: {path}")
    if type(offset) is not int or type(limit) is not int or offset < 1 or not 1 <= limit <= 2000:
        raise ValueError("offset must be >= 1 and limit between 1 and 2000.")
    text, encoding, bom = decode(raw, rule_encoding(root, path))
    lines = text.splitlines()
    end = min(len(lines), offset - 1 + limit)
    body = "\n".join(f"{i + 1}: {lines[i][:2000]}" for i in range(offset - 1, end))
    label = encoding + (" with BOM" if bom else "")
    return f"{path} ({label}); lines {offset}-{end} of {len(lines)}\n{body}"


def save(path, raw, data):
    """Atomically replace path with data if it still holds raw (None = must not exist)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = None if raw is None else stat.S_IMODE(path.stat().st_mode)
    if mode is not None and not mode & stat.S_IWUSR:
        raise ValueError("File is read-only; nothing written.")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".kilo-kit-", delete=False) as output:
            temporary = Path(output.name)
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        if mode is not None:
            os.chmod(temporary, mode)
        if load_bytes(path) != raw or path.is_symlink():
            raise ValueError("File changed while saving; nothing written. Read it again.")
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def change(root, file_path, update):
    path = resolve(root, file_path)
    if path.is_dir():
        raise ValueError(f"Is a directory: {path}")
    raw = load_bytes(path)
    text, encoding, bom = decode(raw, rule_encoding(root, path))
    updated = update(text, raw is None)
    data = encode(updated, encoding, bom)
    if raw == data:
        raise ValueError("No changes to apply.")
    save(path, raw, data)
    old = text.replace("\r\n", "\n").replace("\r", "\n").splitlines()
    new = updated.replace("\r\n", "\n").replace("\r", "\n").splitlines()
    diff = list(difflib.unified_diff(old, new, lineterm="", n=1))[2:]
    added = sum(1 for line in diff if line.startswith("+"))
    removed = sum(1 for line in diff if line.startswith("-"))
    preview = "\n".join(diff)
    if len(preview) > 4000:
        preview = preview[:4000] + "\n... (diff truncated)"
    label = encoding + (" with BOM" if bom else "")
    return f"Saved {path} ({label}, +{added} -{removed}); encoding, BOM and line endings preserved.\n{preview}"


def edit_file(root, file_path, old_string, new_string, replace_all=False):
    def update(text, missing):
        if missing:
            raise ValueError(f"File does not exist: {file_path}")
        if not old_string or old_string == new_string:
            raise ValueError("old_string must be non-empty and differ from new_string.")
        old, new = align_newlines(old_string, text), align_newlines(new_string, text)
        count = text.count(old)
        if count == 0 or count > 1 and not replace_all:
            raise ValueError(f"old_string matched {count} times; it must match exactly once, or set replace_all.")
        return text.replace(old, new, -1 if replace_all else 1)

    return change(root, file_path, update)


def write_file(root, file_path, content):
    return change(root, file_path, lambda text, _missing: align_newlines(content, text))


def create_server(root):
    from mcp.server.fastmcp import FastMCP  # Imported here so the file logic is testable without mcp installed.

    server = FastMCP("encoding")
    root = Path(root).resolve()
    readonly = {"readOnlyHint": True, "destructiveHint": False}

    @server.tool(annotations=readonly)
    def read(file_path: str, offset: int = 1, limit: int = 2000) -> str:
        """Read a text file in the project folder, decoded in its real encoding (UTF-8, CP949, UTF-16, BOM).

        Use this instead of the built-in read for source files: it shows Korean in CP949/UTF-16 files correctly.
        Lines are prefixed with 'N: '; never copy that prefix into old_string. Directories are listed.
        """
        return read_file(root, file_path, offset, limit)

    @server.tool()
    def edit(file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> str:
        """Replace exact text in a project file, keeping its encoding, BOM and line endings byte-for-byte.

        old_string must match exactly once unless replace_all is true. Characters the file's encoding
        cannot store (for example emoji in CP949) are rejected instead of being replaced with '?'.
        """
        return edit_file(root, file_path, old_string, new_string, replace_all)

    @server.tool()
    def write(file_path: str, content: str) -> str:
        """Write a whole project file. Existing files keep their encoding, BOM and line endings.

        New files use the matching encoding-rules.json rule, otherwise UTF-8 without BOM.
        """
        return write_file(root, file_path, content)

    return server


if __name__ == "__main__":
    create_server(Path.cwd()).run(transport="stdio")
