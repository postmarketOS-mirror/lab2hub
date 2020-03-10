# SPDX-License-Identifier: GPL-3.0-or-later

from typing import Dict

from gitlab import Gitlab

from admin import Repo


def fetch_repos(group: str) -> Dict[str, Repo]:
    repos = {}

    with Gitlab('https://gitlab.com', per_page=100) as gl:
        group = gl.groups.get(group, lazy=True)
        for gp in group.projects.list(all=True, as_list=False, include_subgroups=True):
            print(f"Fetching GitLab project {gp.path_with_namespace}")
            assert gp.path not in repos, 'Duplicate project path: ' + gp.path

            p = gl.projects.get(gp.id, lazy=True)
            protected_branches = {b.name for b in p.branches.list(as_list=False) if b.protected}
            repos[gp.path] = Repo(gp.web_url, gp.description, gp.tag_list,
                                  gp.default_branch, protected_branches)

    return repos
