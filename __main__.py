#!/usr/bin/env python3

import multiprocessing as mp
# from multiprocessing import Barrier
import subprocess
import re
from struct import unpack
from functools import partial
from time import sleep
# import logging
from utils import u8str
from processor import Processor
# import sys
# logging.basicConfig(level=logging.DEBUG)

class LinkListener:
    def __init__(self):
        self.buf = mp.Queue()
        # self.barrier = Barrier(2)
        self.process = mp.Process(daemon=True, target=self.target)
        self.process.start()
        # print(globals().values())
        # self.barrier.wait()

    @staticmethod
    def tcpdump_instance():
        args = []
        # args.append("tcpdump")
        # args.append("-vvxl")
        #ports so far 44440, 44444, 6112, 3724
        args.append("tcpflow")
        args.append("-CD")
        args.append("-X/dev/null")
        args.append("tcp and src 164.132.202.12 and greater 69")
        try:
            p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, \
                shell=False, bufsize=1, universal_newlines=True)
            for stdout_line in iter(p.stdout.readline, ""):
                yield stdout_line
        except subprocess.TimeoutExpired:
            p.kill()
        except KeyboardInterrupt:
            pass

        p.stdout.flush()
        p.stdout.close()
        return_code = p.wait()

        if return_code:
            raise subprocess.CalledProcessError(return_code, " ".join(args))

    @staticmethod
    def dechex(line, start=None, stop=None):
        # None means "from start to x" or "from x to end"
        if start is None and stop is None:
            return bytearray.fromhex(line).decode("utf8")
        return bytearray.fromhex(line[slice(start, stop)]).decode("utf8")

    def target(self):
        # data_start = re.compile(r"^\s*0x0030", re.M)
        # data = re.compile(r"^\s*0x0[0-9a-fA-F][4-9a-fA-F]0", re.M)

        data_start = re.compile(r"^\s*0000", re.M)
        data = re.compile(r"^\s*[0-9a-fA-F]{2}[2-9a-fA-F]0", re.M)
        play_vid = "1a0c01"
        play_vid_confirm = False
        query_length = 0
        for line in self.tcpdump_instance():
            # line = "".join(line.strip().split())
            # line_number = line[:7]
            # line_data = line[7:]
            # if data_start.match(line_number):
                # if len(line_data) >= 26:
                    # if line_data[20:26] == play_vid and len(line_data) == 32:
                        # self.buf.put("start")
                        # self.buf.put(bytearray.fromhex(line_data[26:]).decode("utf8"))
                        # play_vid_confirm = True
                        # continue
                    # elif line_data[20:26] == play_vid and len(line_data) < 32:
                        # self.buf.put("start")
                        # self.buf.put(bytearray.fromhex(line_data[26:]).decode("utf8"))
                        # self.buf.put("stop")
                        # continue
                    # else:
                        # play_vid_confirm = False
                        # continue
                # else:
                    # continue
            # if data.match(line_number):
                # if play_vid_confirm:
                    # self.buf.put(bytearray.fromhex(line_data).decode("utf8"))
                # if len(line_data) < 32 and play_vid_confirm:
                    # self.buf.put("stop")
                    # play_vid_confirm = False

            line = "".join(line.strip().split()[:-1])
            line_number = line[:5]
            line_data = line[5:]
            if data_start.match(line_number):
                if line_data[12:18] == play_vid:
                    query_length = unpack(">h", bytearray.fromhex(line_data[8:12]))[0]
                    if len(line_data) < 64:
                        self.buf.put("start")
                        self.buf.put(self.dechex(line_data, 18, None))
                        self.buf.put("stop")
                        continue
                    if len(line_data) == 64:
                        self.buf.put("start")
                        self.buf.put(self.dechex(line_data, 18, None))
                        if query_length == 26:
                            self.buf.put("stop")
                            query_length = 0
                            continue
                        play_vid_confirm = True
            if data.match(line_number):
                if play_vid_confirm:
                    # self.buf.put(bytearray.fromhex(line_data).decode("utf8"))
                    self.buf.put(self.dechex(line_data))
                    if len(line_data) < 64:
                        self.buf.put("stop")
                        play_vid_confirm = False
                        continue
                    if ((len(line_data)/2) + query_length - 26) % 32 == 0:
                        self.buf.put("stop")
                        play_vid_confirm = False
                        query_length = 0

    def yielder(self):
        buf = []
        while True:
            try:
                if not self.buf.empty():
                    buf.append(self.buf.get_nowait())
                if len(buf) > 0:
                    if buf[0] == "start" and buf[-1] == "stop":
                    # if self.buf[0] == "start" and self.buf[-1] == "stop":
                        string = "".join(buf[1:-1])
                        if string:
                            yield string
                        del buf[:]
                sleep(0.1)
            except KeyboardInterrupt:
                break
            # except IndexError:
                # pass
        self.process.join()
        # self.barrier.wait()

if __name__ == "__main__":
    from time import localtime, strftime

    def fail(res, link):
        if res[0]:
            print("Failed to play video, reason:\n{}".format(u8str(res[1])))
            return False
        return True

    def timestamp(args):
        print(strftime("%a, %d %b %Y %H:%M:%S, ", localtime()), end="")
        print("Playing {}".format(args[1]))

    processor = Processor()
    nibba = LinkListener()
    for i in nibba.yielder():
        processor(partial(fail, link=i), ["mpv", i, \
            "--ytdl-raw-options=format=bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/webm"], \
            immidiate_callback=timestamp)

'''
4B       2B   3B
         75B
         size  code  len: 46 chars (23 bytes)
014f0101 004b 1a0c01 6173646173646173646173646173646173646173646173

len: 64 chars (32 bytes)
6461736461736461736461736461736461736461736461736461736461736461

len: 34  chars (17 bytes)
7364617364617364617364617364617364

.O...K...asdasdasdasdasdasdasdas
dasdasdasdasdasdasdasdasdasdasda
sdasdasdasdasdasd
'''
