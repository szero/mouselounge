"""
The MIT License (MIT)
Copyright © 2015 RealDolos
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
# pylint: disable=invalid-name
import logging
import socket
import json
import os

from stat import S_ISSOCK
from contextlib import suppress
from tempfile import gettempdir
from functools import lru_cache
from weakref import finalize


from requests import Session

from ._version import __version__

__all__ = ["requests", "get_text", "get_json", "MPV_IPC_Client"]

LOGGER = logging.getLogger(__name__)

UA = (
    "Mozilla/5.0 (Linux; cli) pyrequests/0.1 "
    f"(python, like Gecko, like KHTML, like wget, like CURL) mouselounge/{__version__}"
)
requests = Session()
requests.headers.update({"User-Agent": UA})


@lru_cache(128)
def get_text(url):
    return requests.get(url).text


@lru_cache(512)
def get_json(url):
    return requests.get(url).json()


def u8str(s):
    return str(s, encoding="utf-8", errors="ignore")


class MPV_IPC_Client:

    recv_size = 2 ** 12

    def __init__(self):
        self.__fileset = set()
        self.socket_file = self.create_tmp_filepath("mpvipcsocket", True)
        self.soc = socket.socket(socket.AF_UNIX)
        self.soc.settimeout(5)
        self.__finalizer = finalize(self, self.clean_exit)

    def connect(self):
        try:
            self.soc.connect(self.socket_file)
        except OSError:
            self.soc = socket.socket(socket.AF_UNIX)
            self.soc.settimeout(5)
            self.soc.connect(self.socket_file)

    def send_data(self, data):
        data = f"{json.dumps(data)}\n"
        data = data.encode("utf8")
        self.soc.send(data)
        received = self.soc.recv(self.recv_size).split(b"\n")
        for resp in [resp for resp in received if resp.strip()]:
            try:
                resp = json.loads(resp, encoding="utf8")
            except json.decoder.JSONDecodeError:
                LOGGER.exception(resp)
                continue
            error = resp.get("error")
            if error and error != "success":
                raise ConnectionError(error)

    def create_tmp_filepath(self, fname, is_socket=False):
        if not isinstance(fname, str):
            raise ValueError("Your filename must be a string")
        tmp_dir = os.environ.get("XDG_RUNTIME_DIR")
        if tmp_dir:
            tmp_file = f"{tmp_dir}/{fname}"
            if not is_socket:
                self.__fileset.add(tmp_file)
            return tmp_file
        tmp_file = f"{gettempdir()}/{fname}"
        if not is_socket:
            self.__fileset.add(tmp_file)
        return tmp_file

    def is_socket_avaliable(self):
        with suppress(FileNotFoundError):
            return S_ISSOCK(os.stat(self.socket_file).st_mode)
        return False

    def clean_exit(self):
        """
        Finalizer gets called when the instance is garbage collected,
        calling it explicitly is optional.
        """
        self.close_socket()
        for file in self.__fileset:
            with suppress(FileNotFoundError):
                os.remove(file)

    def close_socket(self):
        with suppress(OSError):
            self.send_data({"command": ["quit"]})
            self.soc.shutdown(socket.SHUT_RDWR)
            self.soc.close()
        with suppress(FileNotFoundError):
            os.remove(self.socket_file)
