import logging

from collections import namedtuple, defaultdict
from copy import copy

LOGGER = logging.getLogger(__name__)


class Listeners(namedtuple("Listeners", ("callbacks", "queue"))):
    """
    Collection of Listeners
    `callbacks` are function objects.
    `queue` holds data that will be send to each function object
    in `callbacks` variable.
    Each issue of `process` method will run given callback
    against items in `queue` when their types match. After that
    `queue` is cleared and amount of `callbacks` is returned.
    """

    def __new__(cls):
        return super().__new__(cls, defaultdict(list), defaultdict(list))

    def process(self):
        """Process queue for these listeners"""
        # with self.lock:

        callbacks = copy(self.callbacks)

        rm_cb = False
        for ki, vi in self.queue.items():
            if ki in self.callbacks:
                for item in vi:
                    for cb in self.callbacks[ki]:
                        if cb(item) is False:
                            callbacks[ki].remove(cb)
                            if not callbacks[ki]:
                                del callbacks[ki]
                            rm_cb = True

        self.queue.clear()
        if rm_cb:
            self.callbacks.clear()
            for k, v in callbacks.items():
                self.callbacks[k].extend(v)

        return len(self.callbacks)

    def add(self, callback_type, callback):
        """Add a new listener"""

        # with self.lock:
        self.callbacks[callback_type].append(callback)

    def enqueue(self, item_type, item):
        """Queue a new data item, make item iterable"""

        if not isinstance(item, tuple):
            raise ValueError("I can only process tuples!")
        # with self.lock:
        self.queue[item_type].append(item)

    def __len__(self):
        """Return number of listeners in collection"""

        # with self.lock:
        return len(self.callbacks)


if __name__ == "__main__":
    listeners = defaultdict(Listeners)
    t1 = listeners[0]
    t2 = listeners[1]

    def boi(val):
        print("boi {}".format(val))

    def wut(val):
        print("wut {}".format(val))
        return False

    t1.add("t1", boi)
    t2.add("t2", wut)

    t1.enqueue("t1", "whats")
    t2.enqueue("t2", "good")
    t1.enqueue("t1", "mah")
    t2.enqueue("t2", "boi")

    for listener in listeners.values():
        print(listener)
        listener.process()
