import logging
import asyncio
import sys
import inspect
import signal


from os import devnull
from shutil import which
from contextlib import suppress
from re import search

from .listeners import Listeners
from .protocol import PROTO, ProtocolHandler

LOGGER = logging.getLogger(__name__)


class PacketFetcherError(Exception):
    def __init__(self, msg=""):
        super().__init__()
        self.msg = msg

    def __str__(self):
        if self.msg:
            return str(self.msg).strip()
        return PacketFetcherError.__name__


class PacketFetcherProtocol(asyncio.SubprocessProtocol):
    def __init__(self, loop):
        self.stopped = False
        self.error_data = ""
        self.status_data = ""
        self._loop = loop
        self._future = self._loop.create_future()

    def pipe_data_received(self, fd, data):
        if fd == 1:
            self._future.set_result(data)
            self._future = self._loop.create_future()
        elif fd == 2:
            for e in data.decode("utf8").splitlines():
                self.error_data += f"{e}\n"
            # tcpflow prints status stuff into stderr so we have to ignore it
            for status in (
                "tcpdump",
                "listening",
                "reportfilename",
                "link-type",
                "snapshot",
                "packets",
            ):
                if status in (data := self.error_data.lower()):
                    self.status_data += data
                    self.error_data = ""
            if self.error_data:
                LOGGER.debug("PacketFetcher error data: %s", self.error_data)

    async def yielder(self):
        """
        Yielding async generator that returns bytes objects.
        This function is operable only when tcpdump is run with
        "-Uw-" arguments or when tcpflow is run with "-0BC" arguments.
        """
        while not self.stopped:
            try:
                data = await self._future
                for packet in data.split(b"\n"):
                    if len(packet) > 7:
                        yield packet
            except asyncio.CancelledError:
                break

    def pipe_connection_lost(self, _fd, _exc):
        self.stopped = True
        self._future.cancel()

    def process_exited(self):
        LOGGER.debug("PacketFetcher game instance exited.")
        self.stopped = True
        self._future.cancel()


class Mousapi:

    taskset = set()

    def __init__(self, args):
        if sys.platform != "win32":
            self.loop = asyncio.new_event_loop()
        else:
            self.loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(self.loop)

        self.args = args
        self.game_transport = None
        self.game_protocol = None
        self.done = None
        self.pending = None
        self.interrupted = False

        self.fetcher_args = [
            "tcp and net 94.23.193.0/24 or net 51.75.130.0/24 or net 37.187.29.0/24 and inbound"
        ]

        self.event = asyncio.Event()
        self.listener = Listeners()
        self.protohandler = ProtocolHandler()

        def handler(signal):
            self.global_stop = True
            self.interrupted = True
            LOGGER.info("User exited with %s", signal)

        self.loop.add_signal_handler(signal.SIGQUIT, handler, "SIGQUIT")
        self.loop.add_signal_handler(signal.SIGINT, handler, "SIGINT")

    def add_listener(self, event, data):
        self.listener.add(event, data)

    async def _init_protocol_and_transport(self):
        args = []
        if which("tcpdump"):
            args.append("tcpdump")
            args.append("-Uw-")
        elif which("tcpflow"):
            args.append("tcpflow")
            args.append("-0CB")
            args.append(f"-X{devnull}")
        else:
            self.event.set()
            asyncio.ensure_future(self.loop.shutdown_asyncgens())
            raise RuntimeError(
                "You don't have a program that can fetch packets!\n"
                "Install tcpdump or tcpflow and try again!"
            )

        transport, protocol = await self.loop.subprocess_exec(
            lambda: PacketFetcherProtocol(self.loop),
            *args + self.fetcher_args,
            stdout=asyncio.subprocess.PIPE,
            stdin=None,
            stderr=asyncio.subprocess.PIPE,
        )
        self.game_transport = transport
        self.game_protocol = protocol
        self.event.set()

    async def _handle_game_server_data(self):
        await self.event.wait()
        async for line in self.game_protocol.yielder():
            for key in self.protohandler.keys():
                if match := search(key, line):
                    LOGGER.debug("Matched game line for key %s: %s", key, line)
                    self.listener.enqueue(
                        PROTO[key], self.protohandler(key, line, match)
                    )
                    self.listener.process()
        if self.game_protocol.error_data:
            raise PacketFetcherError(self.game_protocol.error_data)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, _exc_value, _traceback):
        if exc_type is not RuntimeError:
            self.gracefull_close()
        else:
            self.loop.close()

    @property
    def global_stop(self):
        with suppress(AttributeError):
            return self.game_protocol.stopped

    @global_stop.setter
    def global_stop(self, value):
        with suppress(AttributeError):
            self.game_protocol.stopped = value

    def _append_tasks(self):
        fnames_fobjs = inspect.getmembers(self, predicate=inspect.iscoroutinefunction)

        for fname, fobj in fnames_fobjs:
            Mousapi.taskset.add((fname, self.loop.create_task(fobj())))

    def listen(self):
        if not len(self.listener):
            raise RuntimeError("I got nothing to listen to!")

        self._append_tasks()

        LOGGER.debug("Current coroutines: %s", self.taskset)
        self.done, self.pending = self.loop.run_until_complete(
            asyncio.wait({fob for _fname, fob in Mousapi.taskset})
        )

    def gracefull_close(self):
        """Close all pending tasks and exit"""

        def print_coro(coro):
            return search(r"coro=<\s*(.+?)\s*>", str(coro)).group(1)

        self.global_stop = True

        with suppress(ProcessLookupError, AttributeError):
            self.game_transport.terminate()

        errors = []
        for task in self.pending:
            task.cancel()
            # Now we should await task to execute it's cancellation.
            # Cancelled task raises asyncio.CancelledError that we can suppress:
            with suppress(asyncio.CancelledError):
                try:
                    self.loop.run_until_complete(task)
                except PacketFetcherError:
                    if not self.interrupted:
                        errors.append((print_coro(task), task.exception()))
        self.loop.close()
        if self.done is not None:
            for task in self.done:
                if err := task.exception():
                    errors.append((print_coro(task), err))
            for coro, ex in errors:
                LOGGER.error("\n%s returned: %s", coro, ex)

        if self.args.status and self.game_protocol.status_data:
            LOGGER.info("Status from capture program:\n%s", self.game_protocol.status_data)
        LOGGER.info("See ya around")
        if self.interrupted:
            raise KeyboardInterrupt
        if errors:
            raise PacketFetcherError
