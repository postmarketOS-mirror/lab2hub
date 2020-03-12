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


def _optimize_repo(name: str, repo_dir: str, force: bool = False):
    # Try to GC/repack a bit earlier than Git itself would
    # These are mostly (stupid) heuristics I came up with randomly
    p = subprocess.run(['git', 'count-objects', '-v'],
                       stdout=subprocess.PIPE, universal_newlines=True, # text
                       cwd=repo_dir, check=True)
    stats = dict(line.split(': ', 1) for line in p.stdout.splitlines())

    need_repack = int(stats.get('count', 0)) >= 256
    packs = int(stats.get('packs', 0)) + int(need_repack)

    # Too many packs: GC and combine them
    if force or packs > 16:
        # Running 'git gc' on large repositories takes a lot of time,
        # so we only do it here if it is likely going to be quick.
        # Otherwise we hope that git manages somehow with git gc --auto
        # (or need to do it with a separate cron job or so...)
        if int(stats.get('in-pack', 0)) < 4_000_000:
            print(f"Running 'git gc' for {name}: {stats}")
            subprocess.run(['git', 'gc'], cwd=repo_dir, check=True)
            return

        print(f'WARNING: Skipping optimization of {name} because it is too large: {stats}')

    # Many (unpacked) objects: pack them
    if need_repack:
        print(f"Packing objects for {name}: {stats}")
        subprocess.run(['git', 'repack', '-d'], cwd=repo_dir, check=True)

    # Pack refs at least
    if force:
        subprocess.run(['git', 'pack-refs', '--all'], cwd=repo_dir, check=True)
    else:
        subprocess.run(['git', 'pack-refs'], cwd=repo_dir, check=True)


def fetch(repos_dir: str, s: Sync):
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
            _optimize_repo(name, repo_dir, force=True)


def push(repos_dir: str, s: Sync):
    git_dir = os.path.join(repos_dir, _GIT_DIR)

    # Push updates to mirror
    for name, r in s.repos.items():
        print(f"Pushing {name}")

        repo_dir = os.path.join(git_dir, _hash_url(r.src.url))
        subprocess.run(['git', 'push', '--mirror', r.dest.url],
                       cwd=repo_dir, check=True)


def optimize(repos_dir: str, s: Sync):
    print(f"Optimizing repositories")
    git_dir = os.path.join(repos_dir, _GIT_DIR)

    # Pack repository to save some space
    for name, r in s.repos.items():
        _optimize_repo(name, os.path.join(git_dir, _hash_url(r.src.url)))
