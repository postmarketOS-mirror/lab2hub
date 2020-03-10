# SPDX-License-Identifier: GPL-3.0-or-later

from dataclasses import dataclass
from typing import List, Set, Optional


@dataclass
class Repo:
    url: str
    description: str
    tags: List[str]
    default_branch: Optional[str]
    protected_branches: Set[str]
