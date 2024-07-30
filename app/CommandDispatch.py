import inspect
import os
import sys
import zlib
import hashlib
from typing import Optional
from app.util import *

class CommandDispatch:

    def __init__(self):
        self.dispatch_dict = {}
        self._build_dispatch_table()

    def _build_dispatch_table(self):
        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if name.startswith('cmd_'):
                cmd_name = name[4:]  # Remove prefix
                cmd_name = cmd_name.replace("_", "-")
                self.dispatch_dict[cmd_name] = method

    def dispatch(self, cmd, *args, **kwargs):
        if cmd in self.dispatch_dict:
            return self.dispatch_dict[cmd](*args, **kwargs)
        else:
            return f"Error: Unknown command #{cmd}\n"

    def available_commands(self):
        return self.dispatch_dict.keys()

    def cmd_init(self, *args, **kwargs):
        os.mkdir(GIT_DIR)
        os.mkdir(GIT_OBJECTS_PATH)
        os.mkdir(GIT_REFS_PATH)
        with open(".git/HEAD", "w") as f:
            f.write("ref: refs/heads/main\n")
        return "Initialized git directory\n"

    def cmd_cat_file(self, *args, **kwargs):
        sha = args[-1][-1]
        o_path = object_path(sha)
        if os.path.isfile(o_path):
            try:
                with open(o_path, "rb") as f:
                    return extract_content(zlib.decompress(f.read())).decode("utf-8")
            except Exception as e:
                print(f"Exception occurred: {type(e).__name__}: {e}", file=sys.stderr)

    def cmd_hash_object(self, *args, **kwargs):
        return write_blob(read_file(args[-1][-1])).hexdigest() + "\n"

    def cmd_ls_tree(self, *args, **kwargs):
        sha = args[-1][-1]
        name_only = args[-1][-2]
        o_path = object_path(sha)
        if os.path.isfile(o_path):
            try:
                with open(o_path, "rb") as f:
                    content = extract_content(zlib.decompress(f.read()))
                    #print("converting content to stream")
                    null_index = content.find(b"\0")
                    prev = 0
                    result = ""
                    while null_index != -1:
                        mode, name = content[prev:null_index].decode("utf-8").split(" ")
                        digest = content[null_index + 1: null_index + 21]
                        prev = null_index + 21
                        if name_only == "--name-only":
                            result += name + "\n"
                        else:
                            result += f"{mode} {name} {digest.hex()}\n"
                        null_index = content.find(b"\0", null_index + 1)
                    return result
            except Exception as e:
                print(f"Exception occurred: {type(e).__name__}: {e}", file=sys.stderr)

    def cmd_write_tree(self, *args, **kwargs):
        return write_tree(create_tree(os.getcwd())).hexdigest() + "\n"
