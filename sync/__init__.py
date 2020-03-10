# SPDX-License-Identifier: GPL-3.0-or-later

from dataclasses import dataclass
from typing import Dict

from urllib3.util import Url


@dataclass
class Repo:
    src: Url
    dest: Url


@dataclass
class Sync:
    repos: Dict[str, Repo]
