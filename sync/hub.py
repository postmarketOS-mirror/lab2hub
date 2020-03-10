# SPDX-License-Identifier: GPL-3.0-or-later

from github3 import GitHub, decorators, apps
from github3.repos import ShortRepository
from urllib3.util import parse_url

from sync import Repo, Sync


# /installation/repositories is missing in github3 for some reason,
# I should upstream it eventually
@decorators.requires_app_installation_auth
def _app_installation_repositories(self: GitHub, number=-1, etag=None):
    url = self._build_url("installation", "repositories")
    return self._iter(int(number), url, ShortRepository, None, etag,
                      apps.APP_PREVIEW_HEADERS, "repositories")


def prepare_sync(key: bytes, app_id: int, installation_id: int) -> Sync:
    gh = GitHub()
    gh.login_as_app_installation(key, app_id, installation_id)
    auth = "x-access-token:" + gh.session.auth.token

    repos = {}

    print(f"Checking GitHub repositories for installation {installation_id}")
    for r in _app_installation_repositories(gh):
        if not r.homepage:
            print(f"NOTE: Skipping repository {r.full_name} (no homepage)")
            continue

        assert r.name not in repos, 'Duplicate repository name: ' + r.name

        # FIXME: Should we always append .git?
        src = parse_url(r.homepage + ".git")
        dest = parse_url(r.clone_url)._replace(auth=auth)

        repos[r.name] = Repo(src, dest)

    return Sync(repos)
