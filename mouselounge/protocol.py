"""
Known mouse protocol values goes here
"""
import logging
from struct import unpack

LOGGER = logging.getLogger(__name__)

PROTO = {
    # Community values
    # "1a0c01": "play_vid_tribehouse",
    0x01320101: "play_vid_tribehouse",
    0x01430101: "play_vid_tribehouse",
    # Game values
    0x0548000B: "play_vid_musicroom",
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

    def __call__(self, event, line):
        return self[event](line)

    @staticmethod
    def play_vid_tribehouse(line):
        link = line[9:].decode("ascii")
        LOGGER.debug("Data in tribeplayer: %s", link)
        return (link,)

    @staticmethod
    def play_vid_musicroom(line):
        link_length = 6 + unpack(">H", line[4:6])[0]
        link = line[6:link_length].decode("ascii")

        video_name_length = (link_length + 2) + unpack(
            ">H", line[link_length : link_length + 2]
        )[0]
        video_name = line[link_length + 2 : video_name_length].decode("utf8")
        # nick lenght is integer instead of short??
        nick_length = (video_name_length + 4) + unpack(
            ">I", line[video_name_length : video_name_length + 4]
        )[0]
        nick = line[video_name_length + 4 : nick_length].decode("ascii")

        LOGGER.debug("Data in musicroom: \n%s \n%s \n%s", link, video_name, nick)
        return link, video_name, nick

    def __repr__(self):
        nice_print = str()
        for k, v in self.items():
            nice_print += f"0x{k:X}, {v}\n"
        return nice_print


if __name__ == "__main__":
    t = ProtocolHandler()
    print(t(0x01320101, b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x42\x4F\x49"))
    if 0x01320101 in t:
        print(repr(t))
