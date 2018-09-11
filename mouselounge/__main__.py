#!/usr/bin/env python3

import logging
import sys
from shutil import which
from .mousapi import Mousapi
from .handler import Managers, Handler
from ._version import __fulltitle__

for prog in "tcpflow", "youtube-dl", "mpv":
    if which(prog) is None:
        print("Please install {} and try again".format(prog), file=sys.stderr)
        sys.exit(1)

LOGGER = logging.getLogger("mouselounge")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d %(threadName)s %(levelname)s %(module)s: %(message)s',
    datefmt="%d-%m-%Y %H:%M:%S")
logging.getLogger("requests").setLevel(logging.WARNING)

LOGGER.info("Starting up %s", __fulltitle__)


def run():
    managers = Managers()
    handler = Handler(managers)
    try:
        with Mousapi() as nibba:
            if handler.community_managers:
                nibba.add_listener("play_vid_tribehouse", handler.community_data)
            if handler.game_managers:
                nibba.add_listener("play_vid_musicroom", handler.game_data)
            nibba.run()
    except KeyboardInterrupt:
        LOGGER.info("User exited with SIGINT")
        sys.exit(1)


if __name__ == "__main__":
    run()
