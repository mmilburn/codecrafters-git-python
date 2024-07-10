import hashlib
import io
import os
import sys
import zlib
from typing import Optional

GIT_ROOT_PATH = ".git"
GIT_OBJECTS_PATH = os.path.join(GIT_ROOT_PATH, "objects")
GIT_REFS_PATH = os.path.join(GIT_ROOT_PATH, "refs")


def read_file(directory, filename) -> Optional[bytes]:
    content = None
    file_path = os.path.join(directory, filename)
    if os.path.isfile(file_path):
        try:
            with open(file_path, 'r') as file:
                content = file.read()
        except Exception as e:
            print(f"Exception occurred: {type(e).__name__}: {e}", file=sys.stderr)
    else:
        print(f"File not found: {file_path}", file=sys.stderr)
    return content


def create_blob_string(content):
    size = len(content)
    return f"blob {size}\0{content}".encode("utf-8")


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
    return None


def object_path(sha: str) -> str:
    hash_dir = sha[:2]
    object_file = sha[2:]
    return os.path.join(GIT_OBJECTS_PATH, hash_dir, object_file)


def main():
    command = sys.argv[1]
    if command == "init":
        os.mkdir(GIT_ROOT_PATH)
        os.mkdir(GIT_OBJECTS_PATH)
        os.mkdir(GIT_REFS_PATH)
        with open(".git/HEAD", "w") as f:
            f.write("ref: refs/heads/main\n")
        print("Initialized git directory")
    elif command == "cat-file":
        sha = sys.argv[-1]
        o_path = object_path(sha)
        if os.path.isfile(o_path):
            try:
                with open(o_path, "rb") as f:
                    content = extract_content(zlib.decompress(f.read())).decode("utf-8")
                    print(content, end="")
            except Exception as e:
                print(f"Exception occurred: {type(e).__name__}: {e}", file=sys.stderr)
    elif command == "hash-object":
        file = sys.argv[-1]
        blob = create_blob_string(read_file("", file))
        digest = hashlib.sha1(blob).hexdigest()
        hash_dir = digest[:2]
        object_file = digest[2:]
        object_dir = os.path.join(GIT_OBJECTS_PATH, hash_dir)
        if not os.path.exists(object_dir):
            os.mkdir(object_dir)
        o_path = os.path.join(object_dir, object_file)
        try:
            with open(o_path, "wb") as f:
                f.write(zlib.compress(blob))
        except Exception as e:
            print(f"Exception occurred: {type(e).__name__}: {e}", file=sys.stderr)
        print(digest)
    elif command == "ls-tree":
        sha = sys.argv[-1]
        name_only = sys.argv[-2]
        o_path = object_path(sha)
        if os.path.isfile(o_path):
            try:
                with open(o_path, "rb") as f:
                    content = extract_content(zlib.decompress(f.read()))
                    #print("converting content to stream")
                    null_index = content.find(b"\0")
                    prev = 0
                    while null_index != -1:
                        mode, name = content[prev:null_index].split(b" ")
                        mode = mode.decode("utf-8")
                        name = name.decode("utf-8")
                        digest = content[null_index + 1: null_index + 21]
                        prev = null_index + 21
                        if name_only == "--name-only":
                            print(name)
                        else:
                            print(f"{mode} {name} {digest.hex()}")
                        null_index = content.find(b"\0", null_index + 1)
            except Exception as e:
                print(f"Exception occurred: {type(e).__name__}: {e}", file=sys.stderr)
    else:
        raise RuntimeError(f"Unknown command #{command}")


if __name__ == "__main__":
    main()
