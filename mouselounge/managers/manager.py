from functools import partial
from ..processor import PROCESSOR

__all__ = ["HelperManager", "BaseManager", "CommunityManager", "GameManager"]


class HelperManager:
    def __init__(self, **kw):
        self.feedmode = kw.get("args").feedmode
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
class BaseManager:
    def __init__(self, **kw):
        self.args = kw.get("args")


class CommunityManager(BaseManager):

    def handle_data(self, data):
        raise NotImplementedError


class GameManager(BaseManager):

    def handle_data(self, data):
        raise NotImplementedError
