import logging
from collections import namedtuple
from collections import defaultdict

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

        # print("whatz in queue:\n{}".format(self.queue))
        for ki, vi in self.queue.items():
            # print("k:{} v:{}".format(ki, vi))
            if ki in self.callbacks:
                for item in vi:
                    for cb in self.callbacks[ki]:
                        # print("cb: {}".format(cb))
                        if cb(item) is False:
                            LOGGER.warning("Removing callback %s from listeners.", cb)
                            self.callbacks[ki].remove(cb)
                            if len(self.callbacks[ki]) == 0:
                                del self.callbacks[ki]
        self.queue.clear()
        return len(self.callbacks)

    def add(self, callback_type, callback):
        """Add a new listener"""

        # with self.lock:
        self.callbacks[callback_type].append(callback)

    def enqueue(self, item_type, item):
        """Queue a new data item"""

        # with self.lock:
        self.queue[item_type].append(item)

    def __len__(self):
        """Return number of listeners in collection"""

        # with self.lock:
        return len(self.callbacks)


if __name__ == "__main__":
    test = Listeners()

    def boi(val):
        print("boi {}".format(val))

    def wut(val):
        print("wut {}".format(val))
        return False

    test.add("nibba", boi)
    test.add("gibba", wut)
    test.enqueue("nibba", "dingo")
    test.enqueue("nibba", "dingo")
    test.enqueue("gibba", "dingo")
    test.process()
    test.enqueue("nibba", "dingo")
    test.process()
