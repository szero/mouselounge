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
    def __init__(self, loop, name):
        self.stopped = False
        self.error_data = str()
        self._loop = loop
        self._name = name
        self._future = self._loop.create_future()

    def pipe_data_received(self, fd, data):
        if fd == 1:
            self._future.set_result(data)
            self._future = self._loop.create_future()
        elif fd == 2:
            for e in data.decode("utf8").splitlines():
                self.error_data += f"{e}\n"
            # tcpflow prints status stuff into stderr so we have to ignore it
            for status in "listening", "reportfilename":
                if status in self.error_data.lower() or len(self.error_data) <= 2:
                    self.error_data = str()
                    break

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
        LOGGER.debug("PacketFetcher %s instance exited.", self._name.capitalize())
        self.stopped = True
        self._future.cancel()


class Mousapi:

    tasklist = []

    def __init__(self):
        if sys.platform != "win32":
            self.loop = asyncio.new_event_loop()
        else:
            self.loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(self.loop)

        self.game_transport = None
        self.game_protocol = None
        self.community_transport = None
        self.community_protocol = None
        self.retcodes = None
        self.interrupted = False
        self.community = ["tcp and src 94.23.193.229 or src 51.75.130.180"]
        self.game = [
            "tcp and net 94.23.249.0/24 or net 188.165.194.0/24 "
            "or net 188.165.220.0/24 or net 198.27.83.0/24 "
            "or net 46.105.100.0/24 and inbound"
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

        for i in "community", "game":
            transport, protocol = await self.loop.subprocess_exec(
                lambda x=i: PacketFetcherProtocol(self.loop, x),
                *args + getattr(self, i),
                stdout=asyncio.subprocess.PIPE,
                stdin=None,
                stderr=asyncio.subprocess.PIPE,
            )
            setattr(self, f"{i}_transport", transport)
            setattr(self, f"{i}_protocol", protocol)
        self.event.set()

    async def _handle_community_server_data(self):
        await self.event.wait()
        async for line in self.community_protocol.yielder():
            for key in self.protohandler.keys():
                match = search(key, line)
                if match:
                    LOGGER.debug("Matched community line for key %s: %s", key, line)
                    self.listener.enqueue(
                        PROTO[key], self.protohandler(key, line, match)
                    )
                    self.listener.process()
        if self.community_protocol.error_data:
            self.game_transport.close()
            raise PacketFetcherError(self.community_protocol.error_data)

    async def _handle_game_server_data(self):
        await self.event.wait()
        async for line in self.game_protocol.yielder():
            for key in self.protohandler.keys():
                match = search(key, line)
                if match:
                    LOGGER.debug("Matched game line for key %s: %s", key, line)
                    self.listener.enqueue(
                        PROTO[key], self.protohandler(key, line, match)
                    )
                    self.listener.process()
        if self.game_protocol.error_data:
            self.community_transport.close()
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
            return self.community_protocol.stopped or self.game_protocol.stopped

    @global_stop.setter
    def global_stop(self, value):
        with suppress(AttributeError):
            self.community_protocol.stopped = self.game_protocol.stopped = value

    def _append_tasks(self):
        fnames_fobjs = inspect.getmembers(self, predicate=inspect.iscoroutinefunction)

        for fname, fobj in fnames_fobjs:
            Mousapi.tasklist.append((fname, fobj))

    def listen(self):
        if not len(self.listener):
            raise RuntimeError("I got nothing to listen to!")

        self._append_tasks()

        LOGGER.debug("Current coroutines: %s", self.tasklist)
        self.retcodes, _pending = self.loop.run_until_complete(
            asyncio.wait([fobj() for _fname, fobj in Mousapi.tasklist])
        )

    def gracefull_close(self):
        """Close all pending tasks and exit"""

        def print_coro(coro):
            return search(r"coro=<\s*(.+?)\s*>", str(coro)).group(1)

        self.global_stop = True

        with suppress(ProcessLookupError, AttributeError):
            self.community_transport.terminate()
            self.game_transport.terminate()

        pending = asyncio.Task.all_tasks()
        errors = []
        for task in pending:
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
        if self.retcodes is not None:
            for coro, ex in errors:
                LOGGER.error("\n%s returned: %s", coro, ex)

        LOGGER.info("See ya around")
        if self.interrupted:
            raise KeyboardInterrupt
        if errors:
            raise PacketFetcherError
