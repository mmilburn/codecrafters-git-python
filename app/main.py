import os
import sys
import zlib

GIT_ROOT_PATH = ".git"
GIT_OBJECTS_PATH = os.path.join(GIT_ROOT_PATH, "objects")
GIT_REFS_PATH = os.path.join(GIT_ROOT_PATH, "refs")


def extract_content(blob_string):
    # Find the position of the null character '\0'
    null_index = blob_string.find('\0')

    if null_index == -1:
        raise ValueError("Invalid blob format: missing null character")

    # Extract <size> and <content>
    size_str = blob_string[5:null_index]  # Start after "blob " and end before '\0'
    content_start_index = null_index + 1
    content_length = int(size_str)
    content = blob_string[content_start_index:content_start_index + content_length]

    return content


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
        hash_dir = sha[:2]
        object_file = sha[2:]
        object_path = os.path.join(GIT_OBJECTS_PATH, hash_dir, object_file)
        if os.path.isfile(object_path):
            try:
                with open(object_path, "rb") as f:
                    content = extract_content(zlib.decompress(f.read()).decode("utf-8"))
                    print(content, end="")
            except Exception as e:
                print(f"Exception occurred: {type(e).__name__}: {e}", file=sys.stderr)
    else:
        raise RuntimeError(f"Unknown command #{command}")


if __name__ == "__main__":
    main()
