from genericpath import isdir
import os
from posix import listdir
import sys
import hashlib
import zlib

GIT_DIR = ".git"
GIT_OBJECTS_PATH = os.path.join(GIT_DIR, "objects")
GIT_REFS_PATH = os.path.join(GIT_DIR, "refs")

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
    return b""

def _create_entry(type, content):
    if isinstance(content, str):
        content = content.encode("utf-8")
    size = len(content)
    return f"{type} {size}\0".encode("utf-8") + content

def _write_object(object):
    raw_digest = hashlib.sha1(object)
    digest = raw_digest.hexdigest()
    hash_dir = digest[:2]
    object_file = digest[2:]
    object_dir = os.path.join(GIT_OBJECTS_PATH, hash_dir)
    if not os.path.exists(object_dir):
        os.mkdir(object_dir)
    o_path = os.path.join(object_dir, object_file)
    try:
        with open(o_path, "wb") as f:
            f.write(zlib.compress(object))
    except Exception as e:
        print(f"Exception occurred: {type(e).__name__}: {e}", file=sys.stderr)
    return raw_digest

def write_blob(content):
    return _write_object(_create_entry("blob", content))

def write_tree(content):
    return _write_object(_create_entry("tree", content))

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
            entries[entry] = f"{get_mode(entry_path)} {entry}\0".encode("utf-8") + write_blob(read_file(entry_path)).digest()
        else:
            entries[entry] = f"{get_mode(entry_path)} {entry}\0".encode("utf-8") + write_tree(create_tree(entry_path)).digest()
    return b"".join([entries[key] for key in sorted(entries)])
