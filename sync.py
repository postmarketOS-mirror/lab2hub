#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

import argparse

import sync.git
import sync.hub

parser = argparse.ArgumentParser(description="Sync mirror repositories on GitHub organization")
parser.add_argument('installation_id', help="GitHub installation ID")
parser.add_argument('--key', type=argparse.FileType('rb'), required=True,
                    help="Path to GitHub app private key (used for synchronization)")
parser.add_argument('--app-id', type=int, required=True, help="GitHub App ID")
parser.add_argument('--repo-dir', default='repos',
                    help="Directory to store cloned repositories in")
parser.add_argument('--no-push', dest='push', default=True, action='store_false',
                    help="Only fetch changes, do not push to mirror")
parser.add_argument('--no-optimize', dest='optimize', default=True, action='store_false',
                    help="Do not run 'git gc' after fetching changes")
args = parser.parse_args()

s = sync.hub.prepare_sync(args.key.read(), args.app_id, args.installation_id)

sync.git.fetch(args.repo_dir, s)
if args.push:
    sync.git.push(args.repo_dir, s)
if args.optimize:
    sync.git.optimize(args.repo_dir, s)
