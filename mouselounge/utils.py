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
import string

from stat import S_ISSOCK
from contextlib import suppress
from tempfile import gettempdir
from functools import lru_cache
from weakref import finalize
from threading import Thread
from random import choices


from requests import Session
from bs4 import BeautifulSoup

from ._version import __version__

__all__ = ["requests", "get_text", "get_json", "rand_string", "MPV_IPC_Client"]

LOGGER = logging.getLogger(__name__)

UA = (
    "Mozilla/5.0 (Linux; cli) pyrequests/0.1 "
    f"(python, like Gecko, like KHTML, like wget, like CURL) mouselounge/{__version__}"
)
requests = Session()
requests.headers.update({"User-Agent": UA})


@lru_cache(128)
def get_text(url):
    r = requests.get(url).text
    if "itemprop" in r:
        return r
    post_builder = {}
    soup = BeautifulSoup(r, "html.parser")
    for i in soup.find_all("input"):
        with suppress(KeyError):
            post_builder.update({i["name"]: i["value"]})
    return requests.post("https://consent.youtube.com/s", data=post_builder).text


@lru_cache(512)
def get_json(url):
    return requests.get(url).json()


def u8str(s):
    return str(s, encoding="utf-8", errors="ignore")


def rand_string(length):
    return "".join(choices(string.ascii_letters + string.digits, k=length))


class MPV_IPC_Client:

    recv_size = 2 ** 10

    def __init__(self):
        self.connected = False
        self.tmp_dir = os.environ.get("XDG_RUNTIME_DIR") or gettempdir()
        self.socket_file = self.create_tmp_filepath("mpvipcsocket", True)
        self._soc = socket.socket(socket.AF_UNIX)
        self._soc.settimeout(1)
        self.__fileset = set()
        self.__finalizer = finalize(self, self.clean_exit)
        self._receiving_task = Thread(daemon=True, target=self._receiver)
        self.cbset = set()

    def _receiver(self):
        while self.connected:
            try:
                received = self._soc.recv(self.recv_size).split(b"\n")
            except socket.timeout:
                continue
            for resp in [resp for resp in received if resp.strip()]:
                try:
                    resp = json.loads(resp)
                except json.decoder.JSONDecodeError:
                    LOGGER.exception("Error during decoding for line:\n%s", resp)
                    continue
                for cb in self.cbset:
                    cb(resp)
                error = resp.get("error")
                if error and error != "success":
                    raise ConnectionError(error)

    def connect(self):
        try:
            self._soc.connect(self.socket_file)
            self.connected = True
            self._receiving_task.start()
        except (OSError, RuntimeError):
            self.connected = False
            self._receiving_task.join()
            self._soc = socket.socket(socket.AF_UNIX)
            self._soc.settimeout(1)
            self._soc.connect(self.socket_file)
            self.connected = True
            self._receiving_task = Thread(daemon=True, target=self._receiver)
            self._receiving_task.start()

    def send_data(self, data):
        data = f"{json.dumps(data)}\n"
        data = data.encode("utf8")
        self._soc.send(data)

    def create_tmp_filepath(self, fname, is_socket=False):
        if not isinstance(fname, str):
            raise ValueError("Your filename must be a string")
        if self.tmp_dir:
            tmp_file = f"{self.tmp_dir}/{fname}_{rand_string(6)}"
            if not is_socket:
                self.__fileset.add(tmp_file)
            return tmp_file
        raise RuntimeError("Couldn't find any temp dirs on your system")

    def is_socket_avaliable(self):
        with suppress(FileNotFoundError):
            return S_ISSOCK(os.stat(self.socket_file).st_mode)
        return False

    def clean_exit(self):
        """
        Finalizer gets called when the instance is garbage collected,
        calling it explicitly is optional.
        """
        self.disconnect()
        for file in self.__fileset:
            with suppress(FileNotFoundError):
                os.remove(file)

    def disconnect(self):
        self.connected = False
        with suppress(RuntimeError):
            self._receiving_task.join()
        with suppress(OSError):
            self.send_data({"command": ["quit"]})
            self._soc.shutdown(socket.SHUT_RDWR)
            self._soc.close()
        with suppress(FileNotFoundError):
            os.remove(self.socket_file)
