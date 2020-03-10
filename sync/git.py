# SPDX-License-Identifier: GPL-3.0-or-later

import hashlib
import os.path
import subprocess

from sync import Sync

_GIT_DIR = '.git'

# The name of the (source) remote
_REMOTE_NAME = 'origin'

# By default, git clone --mirror clones all refs, including "hidden refs" from
# GitHub/GitLab like refs/pull/<id>/{head,merge}. Pushing these to a remote will
# fail horrible. Therefore we mirror only the relevant refs, as listed below.
_REFS = {'heads', 'tags', 'notes'}


def _lnsf(source: str, link: str):
    try:
        if os.readlink(link) == source:
            return
        os.unlink(link)
    except FileNotFoundError:
        pass

    os.symlink(source, link)


def _hash_url(url: str) -> str:
    # Store the repository in a directory based on the (source) remote URL
    # URLs are weird so hash it and use the hex output.
    # Could use something simpler, but why not SHA3? :D
    return hashlib.sha3_224(url.encode()).hexdigest()


def sync(repos_dir: str, s: Sync):
    git_dir = os.path.join(repos_dir, _GIT_DIR)
    os.makedirs(git_dir, exist_ok=True)

    # Fetch changes from source repositories
    for name, r in s.repos.items():
        # Some safety checks for the repository name
        assert '/' not in name
        assert name != '.' and name != '..'

        print(f"Fetching {name} from {r.src}")

        # Create a symlink for debugging purposes
        src_hash = _hash_url(r.src.url)
        _lnsf(os.path.join(_GIT_DIR, src_hash), os.path.join(repos_dir, name))

        repo_dir = os.path.join(git_dir, src_hash)
        new_repo = False
        if not os.path.isdir(repo_dir):
            new_repo = True

            # Note: git clone --mirror would be nice, but it fetches _too much_
            # e.g. also merge/pull requests that cause an error when pushing
            subprocess.run(['git', 'init', '--bare', src_hash],
                           cwd=git_dir, check=True)
            subprocess.run(['git', 'remote', 'add', '--mirror=fetch',
                            _REMOTE_NAME, r.src.url],
                           cwd=repo_dir, check=True)

            # Setup fetch refspecs, first replace the default, then add additionally
            opt = "--replace-all"
            for ref in _REFS:
                subprocess.run(['git', 'config', opt,
                                f'remote.{_REMOTE_NAME}.fetch',
                                f'+refs/{ref}/*:refs/{ref}/*'],
                               cwd=repo_dir, check=True)
                opt = "--add"

        # Fetch updates from the (source) server
        # https://stackoverflow.com/questions/6150188/how-to-update-a-git-clone-mirror
        subprocess.run(['git', 'remote', 'update', '--prune'],
                       cwd=repo_dir, check=True)

        # For some reason 'git clone --mirror' is much more efficient than 'git fetch'
        # (it does not unpack all the refs/objects). But there does not seem to be a way
        # to tell that to 'git fetch'. gc early to avoid keeping many files around.
        if new_repo:
            subprocess.run(['git', 'gc'], cwd=repo_dir, check=True)

    # Push updates to mirror
    for name, r in s.repos.items():
        print(f"Pushing {name}")

        repo_dir = os.path.join(git_dir, _hash_url(r.src.url))
        subprocess.run(['git', 'push', '--mirror', r.dest.url],
                       cwd=repo_dir, check=True)

    print(f"Optimizing repositories")

    # Pack repository to save some space
    for name, r in s.repos.items():
        repo_dir = os.path.join(git_dir, _hash_url(r.src.url))
        subprocess.run(['git', 'gc'], cwd=repo_dir, check=True)