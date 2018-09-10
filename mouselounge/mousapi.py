import asyncio
import sys
import inspect
import signal
import binascii
from contextlib import suppress
from re import search
import logging

from .listeners import Listeners
from .protocol import PROTO
from .protocol import ProtocolHandler

# logging.basicConfig(level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)

class TCPFlowError(Exception):

    def __init__(self, boi):
        super().__init__()
        self.boi = boi
    def __repr__(self):
        return self.boi.strip()
    def __str__(self):
        return self.boi.strip()


class TCPFlowProtocol(asyncio.SubprocessProtocol):

    def __init__(self):
        self.data = None
        self.error_data = str()
        self.stopped = False

    def pipe_data_received(self, fd, data):
        self.data = data
        if fd == 2:
            for e in data.decode("utf8").splitlines():
                self.error_data += e + "\n"
            # silly proggo prints info data to stderr
            if "listening" in self.error_data or len(self.error_data) < 2:
                self.error_data = str()


    async def yielder(self):
        """
        Yielding async generator that turns tcpflow output into a single string
        of hex encoded bytes. This function is operable only when tcpflow is run
        with and only -B and -D arguments.
        """
        while not self.stopped:
            if self.data is not None:
                try:
                    for l in self.data.split(b"\n"):
                        packet = binascii.hexlify(l).decode("ascii")
                        if packet != b'':
                            yield packet
                except IndexError:
                    pass
                finally:
                    self.data = None
            await asyncio.sleep(0.05)

    def pipe_connection_lost(self, fd, exc):
        self.stopped = True

    def process_exited(self):
        LOGGER.debug("Process exited.")
        self.stopped = True


class Mousapi:

    tasklist = list()

    def __init__(self):
        if sys.platform != "win32":
            self.loop = asyncio.new_event_loop()
        else:
            self.loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(self.loop)
        self.testloop = asyncio.get_event_loop()

        self.game_transport = None
        self.game_protocol = None
        self.community_transport = None
        self.community_protocol = None
        self.retcodes = None
        self.community = ["tcp and src 164.132.202.12 and greater 69"]
        # game ports so far 44440, 44444, 6112, 3724, 5555
        self.game = ["tcp and port 6112 or port 44440 or port 44444 or port 3724"
                " or port 5555 and greater 69 and inbound"]
        self.event = asyncio.Event()
        self.listener = Listeners()
        self.protohandler = ProtocolHandler()
        # self.run()
        # self.run()
        # self.barrier = threading.Barrier(2)
        # self.mpevent = mp.Event()
        # self.barrier = mp.Barrier(2)
        # self.thread = mp.Process(daemon=True, target=self._loop())
        # self.thread.start()
        # self instance variable needed to be passed to to tasklist method
        # to create coroutine list
        # self.barrier.wait()
        # self.thread.join()
        # self.run()

    # def _loop(self):
        # """Actual thread"""

        # if sys.platform != "win32":
            # self.loop = asyncio.new_event_loop()
            # asyncio.set_event_loop(self.loop)
        # else:
            # self.loop = asyncio.ProactorEventLoop()
            # asyncio.set_event_loop(self.loop)
        # # self.barrier.wait()
        # try:
            # self.run()
        # except Exception:
            # # import sys
            # sys.exit(1)
    def add_listener(self, event, data):
        self.listener.add(event, data)


    async def _init_protocol_and_transport(self):
        args = list()
        args.append("tcpflow")
        args.append("-BC")
        args.append("-X/dev/null")

        # Create the subprocess controlled by the protocol DateProtocol,
        # redirect the standard output into a pipe

        for i in "community", "game":
            transport, protocol = await self.loop.subprocess_exec(TCPFlowProtocol,
                    *args + getattr(self, i), stdout=asyncio.subprocess.PIPE,
                    stdin=None, stderr=asyncio.subprocess.PIPE)
            setattr(self, i + "_transport", transport)
            setattr(self, i + "_protocol", protocol)

        self.event.set()

    async def _handle_community_server_data(self):
        await self.event.wait()
        async for line in self.community_protocol.yielder():
            if self.global_stop:
                break
            event = line[12:18]
            LOGGER.debug("What's the community event: %s", event)
            if event in self.protohandler:
                self.listener.enqueue(PROTO[event], self.protohandler(event, line))
                self.listener.process()
        self.community_transport.close()
        if self.community_protocol.error_data:
            self.community_protocol.stopped = True
            with suppress(ProcessLookupError):
                # self.community_transport.terminate()
                self.game_transport.terminate()
            error = self.community_protocol.error_data
            self.community_protocol.error_data = str()
            raise TCPFlowError(error)

    async def _handle_game_server_data(self):
        await self.event.wait()
        async for line in self.game_protocol.yielder():
            if self.global_stop:
                break
            event = line[4:8]
            LOGGER.debug("What's the game event: %s", event)
            if event in self.protohandler:
                self.listener.enqueue(PROTO[event], self.protohandler(event, line))
                self.listener.process()
        self.game_transport.close()
        if self.game_protocol.error_data:
            self.global_stop = True
            with suppress(ProcessLookupError):
                # self.game_transport.terminate()
                self.community_transport.terminate()
            error = self.game_protocol.error_data
            self.game_protocol.error_data = str()
            raise TCPFlowError(error)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.gracefull_close()

    @property
    def global_stop(self):
        return self.community_protocol.stopped or self.game_protocol.stopped

    @global_stop.setter
    def global_stop(self, value):
        self.community_protocol.stopped = self.game_protocol.stopped = value

    @staticmethod
    def sort_coroutines(iterable):
        return sorted(iterable, key=lambda k: k[2])

    def append_tasks(self):
        fnames_fobjs = inspect.getmembers(self,
                predicate=inspect.iscoroutinefunction)

        for fname, fobj in fnames_fobjs:
            Mousapi.tasklist.append((fname, fobj))

    def call_later(self, cb, args):
        self.loop.call_later(1, cb, args)

    def run(self):
        self.append_tasks()
        LOGGER.debug("Current coroutines: %s", self.tasklist)
        def handler(_signum, _frame):
            LOGGER.info("User exited with SIGQUIT")
            with suppress(ProcessLookupError):
                self.game_transport.terminate()
            with suppress(ProcessLookupError):
                self.community_transport.terminate()
        signal.signal(signal.SIGQUIT, handler)
        self.retcodes, _pending = self.loop.run_until_complete(
                asyncio.wait([fobj() for _fname, fobj in Mousapi.tasklist],
                    return_when=asyncio.FIRST_EXCEPTION))

    def gracefull_close(self):
        """Close all pending tasks and exit"""
        def print_coro(coro):
            return search(r"coro=<\s*(.+?)\s*>", str(coro)).group(1)

        pending = asyncio.Task.all_tasks()
        errors = list()
        for task in pending:
            task.cancel()
            # # Now we should await task to execute it's cancellation.
            # # Cancelled task raises asyncio.CancelledError that we can suppress:
            with suppress(asyncio.CancelledError):
                try:
                    self.loop.run_until_complete(task)
                except TCPFlowError:
                    errors.append((print_coro(task), task.exception()))

        self.loop.close()
        if self.retcodes is not None:
            for coro, ex in errors:
                LOGGER.error("\n%s returned: %s", coro, ex)

        LOGGER.info("See ya araound")
        if errors:
            return 1
        return 0
