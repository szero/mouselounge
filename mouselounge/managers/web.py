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

from time import time
from time import strftime
from time import localtime
from threading import Timer

import logging
import html
import re
import os


from colorama import init, Fore  # , Back, Style
from cachetools import LRUCache

import isodate


from ..utils import get_text, u8str, MPV_IPC_Client
from .manager import HelperManager, CommunityManager

init(autoreset=True)

__all__ = ["XYoutuberCommunityManager"]

LOGGER = logging.getLogger(__name__)


class WebManager(HelperManager):
    # class WebManager(BaseManager, MPV_IPC_Client):
    needle = r"https?://(?:www\.)?(?:youtu\.be/\S+|youtube\.com/(?:v|watch|embed)\S+)"
    description = re.compile(r'itemprop="description"\s+content="(.+?)"', re.M | re.S)
    duration = re.compile(r'itemprop="duration"\s+content="(.+?)"', re.M | re.S)
    title = re.compile(r'itemprop="name"\s+content="(.+?)"', re.M | re.S)
    # needle = re.compile("^$"), 0
    cooldown = LRUCache(maxsize=10)
    timeout = 60
    mpv_idle_timeout = 30.0 * 60.0

    def __init__(self, **kw):
        super().__init__(**kw)
        self.mpvc = MPV_IPC_Client()
        for fname in filter(lambda f: f.find("receiver_callback") + 1, dir(self)):
            self.mpvc.cbset.add(getattr(self, fname))

        if isinstance(self.needle, str):
            self.needle = self.needle, 0
        if self.needle and isinstance(self.needle[0], str):
            self.needle = re.compile(self.needle[0]), self.needle[1]
        self.mpvcfg = self.mpvc.create_tmp_filepath("mpvcfg")
        # kill mpv process after 30 mins of idling
        self.mpvtimeout = None
        # making this config allows stopping the video without
        # killing the mpv process
        with open(self.mpvcfg, "w") as cfg:
            cfg.write("Q quit\n")
            cfg.write("q stop\n")
        self.mpv_started = False

    @staticmethod
    def fixup(url):
        return url

    def handle_data(self, data):
        if not data:
            return True
        needle, group = self.needle
        now = time()
        if len(data) == 1:
            url = data[0]
            rest = []
        else:
            # skip url verification if we are in the music room
            url = f"https://www.youtube.com/watch?v={data[0]}"
            rest = data[1:]
            self.onurl(url, rest)
            return True
        for url in needle.finditer(url):
            url = url.group(group).strip()
            cd = self.cooldown.get(url, 0)
            if cd + self.timeout > now:
                print(
                    f"{Fore.YELLOW}You can post {url} again "
                    f"after {self.timeout-(now-cd):.2f} seconds.\n"
                )
                continue
            self.cooldown[url] = now
            try:
                url = self.fixup(url)
                if not url:
                    continue
                if self.onurl(url, rest) is False:
                    break
            except Exception:
                LOGGER.exception("failed to process")
        return True

    def process_callback(self, response):
        self.mpv_started = False
        self.mpvc.disconnect()
        retcode, stdout, stderr = response
        if retcode and int(retcode) != 4:
            LOGGER.error(
                "Player returned non-zero status code of %s, error trace:\n%s",
                retcode,
                u8str(stdout + b'\n' + stderr),
            )
            return False
        return True

    def start_mpv(self):
        if self.mpv_started:
            return
        if os.access(self.mpvc.socket_file, os.F_OK):
            os.remove(self.mpvc.socket_file)
        self.run_process(
            self.process_callback,
            "mpv",
            "--idle=yes",
            "--loop-playlist=no",
            "--loop-file=no",
            "--cache-on-disk=yes",
            f"--cache-dir={self.mpvc.tmp_dir}",
            "--ontop",
            # "--autofit-larger=320x240",
            # "--autofit=320x240",
            "--geometry=480x280",
            "--force-window=yes",
            # "--no-keepaspect",
            # "--no-keepaspect-window",
            # "--force-window-position",
            f"--input-conf={self.mpvcfg}",
            # "--no-video",
            f"--input-ipc-server={self.mpvc.socket_file}",
            "--ytdl-raw-options=format="
            "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/webm/mp4/best",
        )
        self.mpv_started = True
        self.connect_to_mpv()

    def connect_to_mpv(self):
        if not self.mpvc.is_socket_avaliable():
            self.call_later(0.2, self.connect_to_mpv)
            return
        self.mpvc.connect()

    def send_data_to_mpv(self, data):
        if not self.mpvc.connected:
            self.call_later(0.2, self.send_data_to_mpv, data)
            return
        self.mpvc.send_data(data)

    def process_videos_with_mpv(self, url, duration_secs):
        if self.mpvtimeout:
            self.mpvtimeout.cancel()
        self.start_mpv()
        timeout = (
            self.mpv_idle_timeout
            if duration_secs < self.mpv_idle_timeout
            else duration_secs + 30.0
        )
        self.mpvtimeout = Timer(
            timeout, lambda: self.send_data_to_mpv({"command": ["quit"]})
        )
        self.mpvtimeout.setDaemon(True)
        self.mpvtimeout.start()
        self.send_data_to_mpv({"command": ["loadfile", url]})

    def onurl(self, url, rest):
        title, duration, desc = self.extract(
            url, self.title, self.duration, self.description
        )
        if title is None:
            return True
        title = self.unescape(title.group(1))
        if not title:
            return True
        desc = self.unescape(desc.group(1))
        duration_secs = 0.0
        if duration:
            duration_secs = isodate.parse_duration(duration.group(1))
            duration = str(duration_secs)
            duration_secs = duration_secs.total_seconds()
        if not self.feedmode:
            self.process_videos_with_mpv(url, duration_secs)
        print(
            strftime(
                f"{Fore.LIGHTBLUE_EX}Post time: {Fore.RESET}%a, %d %b %Y, %H:%M:%S",
                localtime(),
            )
        )
        if len(rest) > 1:
            print(f"{Fore.CYAN}Poster: {Fore.RESET}{rest[1]}")
        yt = f"{Fore.RED}Youtube: {Fore.RESET}"
        print(f"{Fore.MAGENTA}Link: {Fore.RESET}{url}")
        if duration and desc:
            print(f"{yt}{title} ({duration})\n{desc}\n")
        elif duration:
            print(f"{yt}{title} ({duration})\n")
        elif desc:
            print(f"{yt}{title}\n{desc}\n")
        else:
            print(f"{yt}{title}\n")
        return True

    @staticmethod
    def extract(url, *args):
        args = [re.compile(a) if isinstance(a, str) else a for a in args]
        text = get_text(url)
        return [a.search(text) for a in args]

    @staticmethod
    def unescape(string):
        if string:
            string = html.unescape(string.strip())
            # shit is double escaped quite often
            string = (
                string.replace("&lt;", "<")
                .replace("&gt;", ">")
                .replace("&quot;", '"')
                .replace("&amp;", "&")
            )
            string = re.sub(r"[\s+\n]+", " ", string.replace("\r\n", "\n"))
        return string


class XYoutuberCommunityManager(WebManager, CommunityManager):

    last_event = None

    def receiver_callback(self, response):
        LOGGER.debug("from community: %s", response)
        etype = response.get("event")
        if self.last_event == "end-file" and etype == "start-file":
            print(f"{Fore.YELLOW}We got a skipper!\n")
        self.last_event = etype
