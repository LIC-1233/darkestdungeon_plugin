from __future__ import annotations

import os
import site

site.addsitedir(os.path.join(os.path.dirname(__file__), "lib"))

from .DarkestDungeonModCopy import DarkestDungeonModCopy  # noqa: E402


def createPlugin() -> DarkestDungeonModCopy:
    return DarkestDungeonModCopy()
