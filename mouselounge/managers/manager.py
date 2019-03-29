from functools import partial
from ..processor import Processor

__all__ = ["BaseManager", "CommunityManager", "GameManager"]

PROCESSOR = Processor()

class BaseManager:

    def run_process(self, callback, *args, **kwargs):
        self.call_soon(partial(PROCESSOR, callback, *args, **kwargs))

    def call_soon(self, callback, *args):
        """
        This method will be added during runtime
        """

    def call_later(self, delay, callback, *args):
        """
        This method will be added during runtime
        """


class CommunityManager(BaseManager):
    def handle_data(self, data):
        raise NotImplementedError


class GameManager(BaseManager):
    def handle_data(self, data):
        raise NotImplementedError
