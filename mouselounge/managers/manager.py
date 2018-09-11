# import logging
# import warnings

import asyncio
from ..processor import Processor

__all__ = ["BaseManager", "CommunityManager", "GameManager"]


def _run_process(self, callback, arglist):
    if not hasattr(self, "processor"):
        self.processor = Processor()
    if not hasattr(self, "loop"):
        self.loop = asyncio.get_event_loop()

    self.loop.call_soon(self.processor, callback, arglist)

class BaseManager:
    def run_process(self, callback, arglist):
        _run_process(self, callback, arglist)

class CommunityManager(BaseManager):
    def handle_data(self, data):
        raise NotImplementedError()


class GameManager(BaseManager):
    def handle_data(self, data):
        raise NotImplementedError()
