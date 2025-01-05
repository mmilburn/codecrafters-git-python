import hashlib
import os
import sys
import zlib
from pathlib import Path

GIT_DIR = ".git"
GIT_OBJECTS_PATH = os.path.join(GIT_DIR, "objects")


def object_path(sha: str) -> str:
    hash_dir = sha[:2]
    object_file = sha[2:]
    return os.path.join(GIT_OBJECTS_PATH, hash_dir, object_file)


def extract_content(object_string: bytes):
    # Find the position of the first null character '\0'
    null_index = object_string.find(b'\0')

    if null_index == -1:
        raise ValueError("Invalid blob or tree format: missing null character")
    # Extract <size> and <content>
    size_str = object_string[5:null_index]  # Start after "blob " or "tree " and end before '\0'
    if object_string.startswith(b"blob") or object_string.startswith(b"tree"):
        content_start_index = null_index + 1
        content_length = int(size_str)
        content = object_string[content_start_index:content_start_index + content_length]
        return content


def read_object(parent, sha):
    directory = sha[:2]
    obj = sha[2:]
    p = (parent / ".git" / "objects" / directory / obj)
    byte_stream = p.read_bytes()
    header, content = zlib.decompress(byte_stream).split(b"\0", 1)
    kind, _ = header.split(b" ")
    return kind.decode(), content


def write_object(obj_type: str, parent: Path, content: bytes):
    content = f"{obj_type} {len(content)}\0".encode() + content
    raw_digest = hashlib.sha1(content)
    digest = raw_digest.hexdigest()
    hash_dir = digest[:2]
    object_file = digest[2:]
    p = (parent / ".git" / "objects" / hash_dir / object_file)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(zlib.compress(content))
    return raw_digest


def render_tree(parent: Path, dir: Path, sha: str):
    dir.mkdir(parents=True, exist_ok=True)
    _, tree = read_object(parent, sha)
    while tree:
        mode, tree = tree.split(b" ", 1)
        name, tree = tree.split(b"\0", 1)
        sha = tree[:20].hex()
        tree = tree[20:]
        match mode:
            case b"40000":
                render_tree(parent, dir / name.decode(), sha)
            case b"100644":
                _, content = read_object(parent, sha)
                Path(dir / name.decode()).write_bytes(content)
            case _:
                raise RuntimeError("Not implemented")


def read_file(file_path):
    content = None
    if os.path.isfile(file_path):
        try:
            with open(file_path, 'r') as file:
                content = file.read()
        except Exception as e:
            print(f"Exception occurred: {type(e).__name__}: {e}", file=sys.stderr)
    else:
        print(f"File not found: {file_path}", file=sys.stderr)
    return content


def is_symlink(file_path):
    return os.path.islink(file_path)


def is_executable(file_path):
    return os.path.isfile(file_path) and os.access(file_path, os.X_OK)


def get_mode(file_path):
    if os.path.isdir(file_path):
        # Official implementation doesn't have a leading zero!
        return "40000"
    else:
        if is_symlink(file_path):
            return "120000"
        elif is_executable(file_path):
            return "100755"
        else:
            return "100644"


def create_tree(path):
    entries = {}
    listings = filter(lambda x: x != GIT_DIR, os.listdir(path))
    # print(f"{listings}", file=sys.stderr)
    for entry in listings:
        entry_path = os.path.join(path, entry)
        if os.path.isfile(entry_path):
            entries[entry] = f"{get_mode(entry_path)} {entry}\0".encode("utf-8") + write_object("blob", Path("."), Path(
                str(entry_path)).read_bytes()).digest()
        else:
            entries[entry] = f"{get_mode(entry_path)} {entry}\0".encode("utf-8") + write_object("tree", Path("."),
                                                                                                create_tree(
                                                                                                    entry_path)).digest()
    return b"".join([entries[key] for key in sorted(entries)])

# All code below courtesy ggzor -- https://app.codecrafters.io/users/ggzor
def next_size_type(byte_stream):
    kind = (byte_stream[0] & 0b_0111_0000) >> 4
    match kind:
        case 1:
            kind = "commit"
        case 2:
            kind = "tree"
        case 3:
            kind = "blob"
        case 4:
            kind = "tag"
        case 6:
            kind = "ofs_delta"
        case 7:
            kind = "ref_delta"
        case _:
            kind = "unknown"
    size = byte_stream[0] & 0b_0000_1111
    i = 1
    off = 4
    while byte_stream[i - 1] & 0b_1000_0000:
        size += (byte_stream[i] & 0b_0111_1111) << off
        i += 1
        off += 7
    return kind, size, byte_stream[i:]


def next_size(byte_stream):
    size = byte_stream[0] & 0b0111_1111
    i, off = 1, 7
    while byte_stream[i - 1] & 0b_1000_0000:
        size += (byte_stream[i] & 0b_0111_1111) << off
        off += 7
        i += 1
    return size, byte_stream[i:]
