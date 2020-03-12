# lab2hub
lab2hub uses the GitLab API to find all repositories on a GitLab group,
and mirrors them automatically to a GitHub organization. It synchronizes:

  - All branches/tags/notes
  - Repository description and tags/topics
  - Protected branches

There are two separate parts:

  - **admin:** Creates new repositories and updates repository settings
  - **sync:** Clones repositories and pushes them to the mirror

In most cases it should be enough to have a cron job for **sync**,
and run the **admin** part manually when necessary.

## Installation
lab2hub requires Python 3.7. It is possible to use it with Python 3.6
when installing the backported `dataclasses` package from pip.

```shell
$ pip install -r requirements.txt
```

## Setup
No setup is necessary on the GitLab side. It uses the GitLab API read-only
without authentication.

On GitHub you need to setup two GitHub Apps: admin and sync. Those are used for
authentication with GitHub. The following permissions are needed:

  - **admin:** Administration: Read & write
  - **sync:** Contents: Read & write

Install both GitHub Apps on the organization where the mirror repositories
should be created. Create and download private keys for the GitHub Apps.

## Usage
- **admin:** Use `./lab2hub.py <gitlab_group> <github_organization>
  --app-id <app_id> --key path/to/admin.pem`
- **sync:** Use `./sync.py <installation_id>
  --app-id <app_id> --key path/to/sync.pem`

Add a cron job (e.g. one hour) to synchronize changes from GitLab to GitHub.
