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

import logging
import html
import re
from time import time
from time import strftime
from time import localtime

from colorama import init, Fore  #, Back, Style
from cachetools import LRUCache
import isodate

from ..utils import get_text, u8str
from .manager import CommunityManager, GameManager, BaseManager

init(autoreset=True)

__all__ = ["XYoutuberCommunityManager", "XYoutuberGameManager"]

LOGGER = logging.getLogger(__name__)


class WebManager(BaseManager):
    needle = r"https?://(?:www\.)?(?:youtu\.be/\S+|youtube\.com/(?:v|watch|embed)\S+)"
    # needle = r"[A-Za-z0-9_-]{11}"

    description = re.compile(
        r'itemprop="description"\s+content="(.+?)"', re.M | re.S)
    duration = re.compile(r'itemprop="duration"\s+content="(.+?)"', re.M | re.S)
    title = re.compile(r'itemprop="name"\s+content="(.+?)"', re.M | re.S)
    # needle = re.compile("^$"), 0
    cooldown = LRUCache(maxsize=10)
    timeout = 60

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        if isinstance(self.needle, str):
            self.needle = self.needle, 0
        if self.needle and isinstance(self.needle[0], str):
            self.needle = re.compile(self.needle[0]), self.needle[1]

    @staticmethod
    def fixup(url):
        return url

    def handle_data(self, data):
        needle, group = self.needle
        now = time()
        # skip url verification if we are in the music room
        if len(data) > 1:
            url = "https://www.youtube.com/watch?v={}".format(data[0])
            rest = data[1:]
            self.onurl(url, rest)
            return True
        else:
            url = data[0]
            rest = None
        for url in needle.finditer(url):
            url = url.group(group).strip()
            if self.cooldown.get(url, 0) + self.timeout > now:
                print(Fore.YELLOW + "No video spamming!\n")
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

    def handle_rest(self, rest):
        raise NotImplementedError()

    def onurl(self, url, rest):
        self.play_vid(url)
        title, duration, desc = self.extract(
            url, self.title, self.duration, self.description)
        title = self.unescape(title.group(1))
        if not title:
            return
        if duration:
            duration = str(isodate.parse_duration(duration.group(1)))
        desc = self.unescape(desc.group(1))
        yt = Fore.RED + "Youtube: " + Fore.RESET
        self.fprint(
            strftime(
                Fore.LIGHTBLUE_EX + "Post time: " + Fore.RESET +
                "%a, %d %b %Y, %H:%M:%S", localtime()))
        self.handle_rest(rest)
        self.fprint(Fore.MAGENTA + "Link: " + Fore.RESET + "{}", url)
        if duration and desc:
            self.fprint(yt + "{} ({})\n{}\n", title, duration, desc)
        elif duration:
            self.fprint(yt + "{} ({})\n", title, duration)
        elif desc:
            self.fprint(yt + "{}\n{}\n", title, desc)
        else:
            self.fprint(yt + "{}\n", title)

    @staticmethod
    def _fail(res):
        if res[0]:
            LOGGER.error(
                "Player returnen non-zero status code, error trace:\n%s",
                u8str(res[1]))
            return False
        return True

    def play_vid(self, url):
        self.run_process(
            self._fail, [
                "mpv", url, "--ytdl-raw-options=format="
                "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/webm/mp4"
            ])

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
            string = string.replace("&lt;", "<").\
                    replace("&gt;", ">").\
                    replace("&quot;", '"').\
                    replace("&amp;", "&")
            string = re.sub(r"[\s+\n]+", " ", string.replace("\r\n", "\n"))
        return string

    @staticmethod
    def fprint(string, *args, **kw):
        print(string.format(*args), **kw)


class XYoutuberCommunityManager(WebManager, CommunityManager):
    def handle_rest(self, _rest):
        pass


class XYoutuberGameManager(WebManager, GameManager):
    def handle_rest(self, rest):
        self.fprint(Fore.CYAN + "Poster: " + Fore.RESET + "{}", rest[1])
