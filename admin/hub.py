# SPDX-License-Identifier: GPL-3.0-or-later

from dataclasses import dataclass
from typing import Dict, cast

from github3 import GitHub
from github3.orgs import Organization
from github3.repos.branch import ShortBranch
from github3.repos.repo import _Repository

import admin


@dataclass
class _Repo(admin.Repo):
    r: _Repository
    branches: Dict[str, ShortBranch]


class Client:
    _gh = GitHub()
    _org: Organization

    def __init__(self, gh: GitHub, organization: str) -> None:
        self._gh = gh
        self._org = gh.organization(organization)

    def fetch_repos(self) -> Dict[str, admin.Repo]:
        itr = self._org.repositories()
        # This is necessary to return the topics directly without another request
        itr.headers.update(_Repository.PREVIEW_HEADERS)

        repos = {}

        for r in itr:
            print(f"Fetching GitHub repository {r.name}")
            assert r.name not in repos, 'Duplicate project name: ' + r.name

            branches = {b.name: b for b in r.branches()}
            protected_branches = {b.name for b in branches.values() if b.protected}

            default_branch = r.default_branch
            if default_branch not in branches:
                # No need to pretend to have a default branch when it does not exist
                default_branch = None

            repos[r.name] = _Repo(r.homepage, r.description, r.as_dict()['topics'],
                                  default_branch, protected_branches,
                                  r, branches)

        return repos

    @staticmethod
    def convert_tags(repo: admin.Repo):
        # GitHub does not allow upper case / spaces / underscores in topics
        return [t.lower().replace(' ', '-').replace('_', '-') for t in repo.tags]

    def create_repo(self, name: str, other: admin.Repo):
        print(f"Creating GitHub repository {name} for {other.url}")
        r = self._org.create_repository(name, description=other.description, homepage=other.url,
                                        has_issues=False, has_wiki=False)
        if other.tags:
            r.replace_topics(self.convert_tags(other))

    def update_repository(self, repo: admin.Repo, other: admin.Repo):
        ghr = cast(_Repo, repo)
        r = ghr.r

        # Make sure this does not fail if the branch does not (yet) exist on GitHub
        other_default_branch = other.default_branch
        if repo.default_branch != other_default_branch \
                and other_default_branch not in ghr.branches:
            print(f"ERROR: Default branch {other_default_branch} for {r.full_name} "
                  "does not exist on GitHub (yet)")
            other_default_branch = None

        if repo.url != other.url or repo.description != other.description \
                or repo.default_branch != other_default_branch \
                or r.has_issues or r.has_wiki:
            print(f"Updating GitHub repository settings for {r.full_name}")

            r.edit(r.name, description=other.description, homepage=other.url,
                   default_branch=other_default_branch,
                   has_issues=False, has_wiki=False)

        # GitHub does not allow upper case / spaces in topics
        other_topics = self.convert_tags(other)
        if repo.tags != other_topics:
            print(f"Updating GitHub repository topics for {r.full_name}")
            r.replace_topics(other_topics)

        if repo.protected_branches != other.protected_branches:
            print(f"Updating GitHub protected branches for {r.full_name}")

            removed = repo.protected_branches - other.protected_branches
            if removed:
                print(f"WARNING: Refusing to remove protected branches: {removed}")

            for branch_name in other.protected_branches - repo.protected_branches:
                branch = ghr.branches.get(branch_name)
                if not branch:
                    print(f"ERROR: Protected branch {branch_name} does not exist on GitHub (yet)")
                    continue

                print(f"Protecting branch: {branch_name}")

                # Branch protection is broken in gitlab3.py :/
                # https://github.com/sigmavirus24/github3.py/issues/892
                resp = branch._put(branch._build_url('protection', base_url=branch._api),
                                   json={
                                       'required_status_checks': None,
                                       'enforce_admins': None,
                                       'required_pull_request_reviews': None,
                                       'restrictions': None,
                                   })
                branch._json(resp, 200)


def create_app_client(key: bytes, app_id: int, organization: str) -> Client:
    gh = GitHub()
    gh.login_as_app(key, app_id, expire_in=30)
    installation = gh.app_installation_for_organization(organization)
    print(f"Using GitHub organization installation: {installation.id}")

    gh.login_as_app_installation(key, app_id, installation.id)
    return Client(gh, organization)
