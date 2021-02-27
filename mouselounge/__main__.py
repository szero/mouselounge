#!/usr/bin/env python3

import logging
import sys
import os
import datetime as dt
import signal
import argparse

from shutil import which
from time import sleep


from .mousapi import Mousapi, PacketFetcherError
from .handler import Managers, Handler
from ._version import __fulltitle__

LOGGER = logging.getLogger("mouselounge")


class MyFormatter(logging.Formatter):
    converter = dt.datetime.fromtimestamp

    def formatTime(self, record, datefmt=None):
        ct = self.converter(record.created)
        if datefmt:
            s = ct.strftime(datefmt)
        else:
            t = ct.strftime("%H:%M:%SxD%Y-%m-%d")
            s = t.replace("xD", ".%03d " % record.msecs)
        return s


def debug_handler(_, frame):
    """
    Credit for this function goes to RealDolos, MIT license.
    If pressing enter in the interactive console returns ^M
    (carrige return), add this to your shell config: `stty icrnl`
    It will turn carrige return characters into new lines.
    """
    # pylint: disable=import-outside-toplevel
    import code
    import traceback

    def printall():
        print("\n*** STACKTRACE - START ***\n", file=sys.stderr)
        code = []
        # pylint: disable=protected-access
        for threadid, stack in sys._current_frames().items():
            # pylint: enable=protected-access
            code.append("\n# ThreadID: %s" % threadid)
            for filename, lineno, name, line in traceback.extract_stack(stack):
                code.append('File: "%s", line %d, in %s' % (filename, lineno, name))
                if line:
                    code.append("  %s" % (line.strip()))

        for line in code:
            print(line, file=sys.stderr)
        print("\n*** STACKTRACE - END ***\n", file=sys.stderr)

    def _exit(num=1):
        sys.exit(num)

    env = {"_frame": frame, "printall": printall, "exit": _exit}
    env.update(frame.f_globals)
    env.update(frame.f_locals)

    shell = code.InteractiveConsole(env)
    message = "Signal received : entering python shell.\nTraceback:\n"
    message += "".join(traceback.format_stack(frame))
    shell.interact(message)


def parse_args():
    parser = argparse.ArgumentParser(description=__fulltitle__)
    parser.add_argument(
        "-f",
        "--feedmode",
        action="store_true",
        default=False,
        help="Feed mode. Played videos will appear in the terminal but they "
        "won't be opened through mpv",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        default=False,
        help="Debug your stuff with more verbose outputs",
    )
    args = parser.parse_args()
    return args


def sigchld_handler(_signum, _frame):
    """
    This function makes sure to reap all of the children
    processes.
    """
    while True:
        try:
            ret = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            return
        else:
            if ret[1] >= 0:
                return
        sleep(0.1)



def main():
    for prog in "youtube-dl", "mpv":
        if which(prog) is None:
            print(f"Please install {prog} and try again.", file=sys.stderr)
            sys.exit(1)

    args = parse_args()
    LOGGER.setLevel(logging.DEBUG if args.debug else logging.INFO)

    console = logging.StreamHandler()

    formatter = MyFormatter(
        fmt="%(asctime)s %(threadName)s %(levelname)s " "%(module)s: %(message)s"
    )
    console.setFormatter(formatter)
    globalog = logging.getLogger()
    globalog.setLevel(logging.ERROR)
    globalog.addHandler(console)
    logging.getLogger("requests").setLevel(logging.WARNING)

    LOGGER.info("Starting up %s", __fulltitle__)

    signal.signal(signal.SIGCHLD, sigchld_handler)
    signal.signal(signal.SIGUSR2, debug_handler)

    managers = Managers()
    handler = Handler(managers, args)

    with Mousapi(args) as api:
        handler.add_asyncio_calls(api.loop.call_soon, api.loop.call_later)
        if handler.community_managers:
            api.add_listener("play_vid_tribehouse", handler.community_data)
        api.listen()


def run():
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(1)
    except PacketFetcherError:
        sys.exit(2)


if __name__ == "__main__":
    run()
