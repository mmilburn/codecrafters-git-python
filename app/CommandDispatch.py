import inspect
import struct
import time
import urllib.request
from typing import cast

from app.util import *


class CommandDispatch:

    def __init__(self):
        self.dispatch_dict = {}
        self._build_dispatch_table()

    def _build_dispatch_table(self):
        for name, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if name.startswith("cmd_"):
                cmd_name = name.replace("cmd_", "")  # Remove prefix
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
        # print(f"args: {args}", file=sys.stderr)
        parent = Path(args[-1][-1]) if args and args[-1] else Path(".")
        # print(f"parent: {parent}", file=sys.stderr)
        (parent / ".git" / "objects").mkdir(parents=True)
        (parent / ".git" / "refs" / "heads").mkdir(parents=True)
        (parent / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
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
        return write_object("blob", Path("."), Path(args[-1][-1]).read_bytes()).hexdigest() + "\n"

    # Courtesy ggzor -- https://app.codecrafters.io/users/ggzor
    def cmd_ls_tree(self, *args, **kwargs):
        tree_sha = args[-1][-1]
        name_only = args[-1][-2]
        entries = []
        _, contents = read_object(Path("."), tree_sha)
        while contents:
            mode, contents = contents.split(b" ", 1)
            name, contents = contents.split(b"\0", 1)
            sha = contents[:20]
            contents = contents[20:]
            entries.append((mode.decode(), name.decode(), sha.hex()))
        if name_only == "--name-only":
            return "\n".join([entry[1] for entry in entries]) + "\n"
        return "\n".join([f"{entry[0]} {entry[1]} {entry[2]}" for entry in entries]) + "\n"

    def cmd_write_tree(self, *args, **kwargs):
        return write_object("tree", Path("."), create_tree(os.getcwd())).hexdigest() + "\n"

    def cmd_commit_tree(self, *args, **kwargs):
        tree_sha = args[-1][0]
        arg_list = args[-1]
        commit_sha, message = "", ""
        for index in range(len(arg_list)):
            if arg_list[index] == "-p":
                commit_sha = arg_list[index + 1]
            elif arg_list[index] == "-m":
                message = arg_list[index + 1].replace("\"", "").replace("'", "")
        print(f"tree_sha: {tree_sha} commit_sha: {commit_sha} message: {message}", file=sys.stderr)
        # Courtesy Ben Hoyt https://benhoyt.com/writings/pygit/#committing
        timestamp = int(time.mktime(time.localtime()))
        utc_offset = -time.timezone
        author_time = "{} {}{:02}{:02}".format(
            timestamp,
            '+' if utc_offset > 0 else '-',
            abs(utc_offset) // 3600,
            (abs(utc_offset) // 60) % 60)
        content = ["tree " + tree_sha]
        # parent commit
        if commit_sha:
            content.append("parent " + commit_sha)
        content.append(f"author Mark <mark@example.com> {author_time}")
        content.append(f"committer Mark <mark@example.com> {author_time}")
        content.append("")
        content.append(message)
        content.append("")
        return write_object("commit", Path("."), "\n".join(content).encode()).hexdigest() + "\n"

    # Courtesy ggzor -- https://app.codecrafters.io/users/ggzor
    def cmd_clone(self, *args, **kwargs):
        """ The fetch command underlies two other commonly used commands. clone is used to set up a
        new repository that’s a copy of an existing one, and this can be accomplished using the init,
        remote, fetch and reset commands. --Building Git
        `init` is already implemented.
        I don't think we need `remote add` since our clone operation is a one-shot deal.
        Likewise, I don't think a reset is necessary.
        """
        clone_url = args[-1][-2]
        parent = Path(args[-1][-1])
        print(f"clone_url: {clone_url} clone_dir: {parent}", file=sys.stderr)
        self.cmd_init(*args)
        req = urllib.request.Request(f"{clone_url}/info/refs?service=git-upload-pack")
        with urllib.request.urlopen(req) as f:
            refs = {
                chunk[1].decode(): chunk[0].decode()
                for chunk0 in cast(bytes, f.read()).split(b"\n")
                if (chunk1 := chunk0[4:])
                   and not chunk1.startswith(b"#")
                   and (chunk2 := chunk1.split(b"\0")[0])
                   and (chunk := (chunk2[4:] if chunk2.endswith(b"HEAD") else chunk2).split(b" "))
            }
        # create ref entries
        for name, sha in refs.items():
            Path(parent / ".git" / name).write_text(f"{sha}\n")

        body = (b"0011command=fetch0001000fno-progress"
                + b"".join(b"0032want " + ref.encode() + b"\n" for ref in refs.values())
                + b"0009done\n0000")
        req = urllib.request.Request(f"{clone_url}/git-upload-pack", data=body, headers={"Git-Protocol": "version=2"})
        with urllib.request.urlopen(req) as f:
            pack_bytes = cast(bytes, f.read())
        pack_lines = []
        while pack_bytes:
            line_len = int(pack_bytes[:4], 16)
            if line_len == 0:
                break
            pack_lines.append(pack_bytes[4:line_len])
            pack_bytes = pack_bytes[line_len:]
        pack_file = b"".join(l[1:] for l in pack_lines[1:])
        pack_file = pack_file[8:]  # strip header, version
        n_objs, *_ = struct.unpack("!I", pack_file[:4])
        pack_file = pack_file[4:]
        for _ in range(n_objs):
            kind, _, pack_file = next_size_type(pack_file)
            match kind:
                case "commit" | "tree" | "blob" | "tag":
                    dec = zlib.decompressobj()
                    content = dec.decompress(pack_file)
                    pack_file = dec.unused_data
                    write_object(kind, parent, content)
                case "ref_delta":
                    obj = pack_file[:20].hex()
                    pack_file = pack_file[20:]
                    dec = zlib.decompressobj()
                    content = dec.decompress(pack_file)
                    pack_file = dec.unused_data
                    target_content = b""
                    base_kind, base_content = read_object(parent, obj)
                    _, content = next_size(content)
                    _, content = next_size(content)
                    while content:
                        is_copy = content[0] & 0b_1000_0000
                        if is_copy:
                            data_ptr = 1
                            offset = 0
                            size = 0
                            for i in range(0, 4):
                                if content[0] & (1 << i):
                                    offset |= content[data_ptr] << (i * 8)
                                    data_ptr += 1
                            for i in range(0, 3):
                                if content[0] & (1 << (4 + i)):
                                    size |= content[data_ptr] << (i * 8)
                                    data_ptr += 1
                            content = content[data_ptr:]
                            target_content += base_content[offset: offset + size]
                        else:
                            size = content[0]
                            addition = content[1: size + 1]
                            content = content[size + 1:]
                            target_content += addition
                    write_object(base_kind, parent, target_content)
                case _:
                    raise RuntimeError("Not implemented")
        _, commit = read_object(parent, refs["HEAD"])
        tree_sha = commit[5: 40 + 5].decode()
        render_tree(parent, parent, tree_sha)
