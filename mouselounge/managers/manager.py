# import logging
# import warnings

import asyncio
from ..processor import Processor

__all__ = ["Manager"]


def run_process(self, callback, arglist):
    if not hasattr(self, "processor"):
        self.processor = Processor()
    if not hasattr(self, "loop"):
        self.loop = asyncio.get_event_loop()

    self.loop.call_soon(self.processor, callback, arglist)


class Manager():
    def handle_data(self, data):
        raise NotImplementedError()

    def process(self, cb, arglist):
        """
        Run an external program
        """
        run_process(self, cb, arglist)
