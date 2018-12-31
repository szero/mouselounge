"""
The MIT License (MIT)
Copyright © 2015 RealDolos
Copyright © 2018 Szero

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the “Software”), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import inspect
import logging
import os
import sys

from importlib import import_module

# pylint: disable=unused-wildcard-import,wildcard-import
from .managers import *

# pylint: enable=unused-wildcard-import,wildcard-import

# Stuff cwd into python path
sys.path.insert(0, os.getcwd())

__all__ = ["Managers", "Handler"]

LOGGER = logging.getLogger(__name__)


class Managers(list):
    def __init__(self, additional=None):
        super().__init__()
        if additional is not None:
            for cmd in additional:
                try:
                    mod = import_module(cmd)
                    for cand in mod.__dict__.values():
                        if not self.valid(cand):
                            continue
                        self += (cand,)
                except ImportError:
                    LOGGER.exception("Failed to import custom command")
        for cand in globals().values():
            if not self.valid(cand):
                continue
            self += (cand,)
        LOGGER.debug("Managers: %s", ", ".join(c.__name__ for c in self))

    @staticmethod
    def valid(cand):
        if not inspect.isclass(cand) or not issubclass(cand, BaseManager):
            return False
        if cand is BaseManager or cand is CommunityManager or cand is GameManager:
            return False
        return True


class Handler:
    def __init__(self, manager_candidates):
        community_managers = list()
        game_managers = list()
        for cand in manager_candidates:
            try:
                inst = cand()
                if issubclass(cand, CommunityManager):
                    community_managers += (inst,)
                if issubclass(cand, GameManager):
                    game_managers += (inst,)
            except Exception:
                LOGGER.exception("Failed to initialize managers %s", str(cand))

        def sort(self):
            return self.__class__.__name__

        self.community_managers = sorted(community_managers, key=sort)
        self.game_managers = sorted(game_managers, key=sort)
        LOGGER.debug(
            "Initialized community managers %s",
            ", ".join(repr(h) for h in self.community_managers),
        )
        LOGGER.debug(
            "Initialized game managers %s",
            ", ".join(repr(h) for h in self.game_managers),
        )

    def add_asyncio_calls(self, *calls):
        """
        Every asyncio function will be added to both managers with its
        original name.
        """
        for manager in self.community_managers + self.game_managers:
            try:
                for c in calls:
                    setattr(manager, c.__name__, c)
            except Exception:
                LOGGER.exception("Failed to add asyncio call: %s", c.__name__)

    def community_data(self, data):
        for manager in self.community_managers:
            try:
                manager.handle_data(data)
            except Exception:
                LOGGER.exception(
                    "Failed to process manager %s with data %s", manager, data
                )
                return False
        return True

    def game_data(self, data):
        for manager in self.game_managers:
            try:
                manager.handle_data(data)
            except Exception:
                LOGGER.exception(
                    "Failed to process manager %s with data %s", manager, data
                )
                return False
        return True

    @staticmethod
    def call(item):
        callback, args, kwargs = item
        try:
            callback(*args, **kwargs)
        except Exception:
            LOGGER.exception(
                "Failed to process callback with %r (%r, **%r)", callback, args, kwargs
            )
