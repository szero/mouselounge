# import logging
# import warnings
from ..processor import Processor

__all__ = ["BaseManager", "CommunityManager", "GameManager"]

class BaseManager:
    def __init__(self):
        self.__processor = Processor()

    def run_process(self, callback, *args):
        self.call_soon(self.__processor, callback, *args)
    # this method will be added during runtime
    def call_soon(self, callback, *args):
        pass

    # this method will be added during runtime
    def call_later(self, delay, callback, *args):
        pass

    # def run_process(self, callback, arglist, kwdict):
    # run_process(self, callback, arglist, kwdict)


class CommunityManager(BaseManager):
    def handle_data(self, data):
        raise NotImplementedError


class GameManager(BaseManager):
    def handle_data(self, data):
        raise NotImplementedError
