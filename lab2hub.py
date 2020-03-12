#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

import argparse

import admin.hub
import admin.lab

parser = argparse.ArgumentParser(description="Mirror GitLab repositories to GitHub organization")
parser.add_argument('gitlab_group', help="GitLab group (source)")
parser.add_argument('github_organization', help="GitHub organization (destination)")
parser.add_argument('--key', type=argparse.FileType('rb'), required=True,
                    help="Path to GitHub app private key (used for repository administration)")
parser.add_argument('--app-id', type=int, required=True, help="GitHub App ID")
parser.add_argument('--prefix-description', default="(mirror) ",
                    help="Add prefix to repository description")
parser.add_argument('--delete', action='store_true',
                    help="Delete all (current) repository mirrors")
args = parser.parse_args()

ghc = admin.hub.create_app_client(args.key.read(), args.app_id, args.github_organization)

gitlab_repos = admin.lab.fetch_repos(args.gitlab_group)
github_repos = ghc.fetch_repos()

if args.delete:
    for name, src in gitlab_repos.items():
        dest = github_repos.get(name)
        if dest:
            ghc.delete_repo(dest)
    exit(0)

created = False

for name, src in gitlab_repos.items():
    # Add specified prefix to repository description
    src.description = args.prefix_description + src.description

    dest = github_repos.get(name)
    if dest:
        ghc.update_repository(dest, src)
    else:
        ghc.create_repo(name, src)
        created = True

if created:
    print("New projects created, please sync and run again!")
