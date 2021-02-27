"""
The MIT License (MIT)
Copyright © 2017 RealDolos
Copyright © 2018 Szero

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the “Software”), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import logging
import signal
import multiprocessing as mp
import subprocess

LOGGER = logging.getLogger(__name__)


def _init_worker():
    try:
        # workaround for fucken pool workers being retarded
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGQUIT, signal.SIG_IGN)
    except Exception:
        pass  # wangblows might not like it

    logging.basicConfig(
        level=logging.ERROR,
        format="%(asctime)s.%(msecs)03d %(threadName)s %(levelname)s "
        "%(module)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger("requests").setLevel(logging.WARNING)
    # LOGGER.info("starting processor")


def _run_process(*args, **kwds):
    try:
        event = kwds.pop("event", False)
        if event:
            event.clear()
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        while True:
            try:
                stdout, stderr = proc.communicate(timeout=0.1)
                if event:
                    event.clear()
                return proc.returncode, stdout, stderr
            except subprocess.TimeoutExpired:
                if event and event.is_set():
                    event.clear()
                    proc.terminate()
                    stdout, stderr = proc.communicate()
                    return proc.returncode, stdout, stderr
    except (ValueError, BrokenPipeError, AttributeError):
        # Sometimes communicate throws ValueError related to file object.
        # I think its related to low timeout value and using Popen in multiple
        # processes. Happens only during process termination?
        # BrokenPipeError happens if we SIGQUIT and the Manager().Event()
        # gets closed while this process is still running.
        return 0, b"", b""
    except Exception as ex:
        LOGGER.exception("ex running")
        return -1, b"", bytes(ex, "utf8")


class Processor:
    def __init__(self):
        self.pool = mp.Pool(5, initializer=_init_worker, maxtasksperchild=5)

    def __call__(self, callback, *args, **kwargs):
        LOGGER.debug("running %r, %r", args, kwargs)
        try:
            self.pool.apply_async(
                _run_process, args, kwargs, callback, error_callback=self.error
            )
        except Exception:
            LOGGER.exception("failed to run processor")

    @staticmethod
    def error(*args, **kw):
        LOGGER.error("failed to run processor %r %r", args, kw)


PROCESSOR = Processor()
