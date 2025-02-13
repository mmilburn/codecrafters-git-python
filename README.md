# About the Project
This is a finished Python implementation for the 
["Build Your Own Git" Challenge](https://codecrafters.io/challenges/git).
This code implements functionality for all stages (and extensions) of the
challenge as of 2025-02-13. 

## What `git` Commands Are Implemented?
- [x] `init` 
- [x] `cat-file`
- [x] `hash-object` 
- [x] `ls-tree` 
- [x] `write-tree`
- [x] `commit-tree` (`author` and `committer` are hardcoded, `message` is not)
- [x] `clone`

# Running Locally

The `your_git.sh` script is expected to operate on the `.git` folder inside the
current working directory. If you're running this inside the root of this
repository, you might end up accidentally damaging the repository's `.git`
folder.

It is recommended to execute `your_git.sh` in a different folder when running locally.
For example:

```sh
mkdir -p /tmp/testing && cd /tmp/testing
/path/to/your/repo/your_git.sh init
```

To make this easier to type out, you could add a
[shell alias](https://shapeshed.com/unix-alias/):

```sh
alias mygit=/path/to/your/repo/your_git.sh

mkdir -p /tmp/testing && cd /tmp/testing
mygit init
```
# Test Run Video
Here's a video of the code being run in the codecrafters test environment:

https://github.com/user-attachments/assets/31761ebf-4cc8-40fb-bc3b-a3427e6b98dd