"""
Known mouse protocol values goes here
"""
import logging

from struct import unpack
from struct import error as StructError

LOGGER = logging.getLogger(__name__)

PROTO = {
    # Community values
    b"\x1a\x0c\x01": "play_vid_tribehouse",
    # 0x01320101: "play_vid_tribehouse",
    # 0x01430101: "play_vid_tribehouse",
    # Game values
    # 0x0548000B: "play_vid_musicroom",
    # 0x050A0001: "play_vid_on_musicroom_enter",
    # 0x07010001: "play_vid_on_musicroom_enter",
    # 0x071e0b01: "play_vid_on_musicroom_enter",
    b"\x05\x48": "play_vid_musicroom",
}


class ProtocolHandler(dict):
    """
    Extract data from incoming packets. PROTO defines
    which packets will be processed.
    Handling functions names must be exactly the same
    as values of PROTO dictionary and return tuples.
    """

    def __init__(self):
        super().__init__()
        method_names = dir(self)
        for key, val in PROTO.items():
            for method_name in method_names:
                if val == method_name:
                    self[key] = getattr(self, method_name)

    def __call__(self, event, line, match):
        return self[event](line, match)

    @staticmethod
    def play_vid_tribehouse(line, match):
        if line[match.end()] != 104:
            return ()
        link = line[match.end():].decode("ascii")
        LOGGER.debug("Link tribeplayer: %s", link)
        return (link,)

    @staticmethod
    def play_vid_musicroom(line, match):
        link_start = match.end()
        if line[link_start : link_start + 2] != b"\x00\x0b":
            return ()
        try:
            link_length = (
                link_start + 2 + unpack(">H", line[link_start : link_start + 2])[0]
            )
            link = line[link_start + 2 : link_length].decode("ascii")

            video_name_length = (link_length + 2) + unpack(
                ">H", line[link_length : link_length + 2]
            )[0]
            video_name = line[link_length + 2 : video_name_length].decode("utf8")
            # nick lenght is integer instead of short??
            # there are two shorts next to eachother, that look like integer
            nick_length = (video_name_length + 4) + unpack(
                ">H", line[video_name_length + 2 : video_name_length + 4]
            )[0]
            nick = line[video_name_length + 4 : nick_length].decode("ascii")

            LOGGER.debug("Data in musicroom: \n%s \n%s \n%s", link, video_name, nick)
            return link, video_name, nick
        except (UnicodeDecodeError, StructError) as ex:
            LOGGER.exception("%s line failed with:\n%s", line, ex)
            return ()

    def __repr__(self):
        nice_print = str()
        for k, v in self.items():
            nice_print += f"0x{k.hex()}, {v}\n"
        return nice_print


if __name__ == "__main__":
    t = ProtocolHandler()
    print(repr(t))
