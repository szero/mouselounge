#!/usr/bin/env python3

import sys
from .mousapi import Mousapi
from .handler import Managers, Handler


def run():

    managers = Managers([])
    handler = Handler(managers)

    try:
        with Mousapi() as nibba:
            if handler.mouse_managers:
                nibba.add_listener("play_vid_tribehouse", handler.mouse_data)
                nibba.add_listener("play_vid_musicroom", handler.mouse_data)
            nibba.run()
    except KeyboardInterrupt:
        print("\nUser exited with SIGINT")
        sys.exit(1)


if __name__ == "__main__":
    run()
