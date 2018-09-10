#!/usr/bin/env python3

import sys
import logging
from .mousapi import Mousapi
from .handler import Managers, Handler
from ._version import __fulltitle__

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
            if handler.mouse_managers:
                nibba.add_listener("play_vid_tribehouse", handler.mouse_data)
                nibba.add_listener("play_vid_musicroom", handler.mouse_data)
            nibba.run()
    except KeyboardInterrupt:
        LOGGER.info("User exited with SIGINT")
        sys.exit(1)


if __name__ == "__main__":
    run()
