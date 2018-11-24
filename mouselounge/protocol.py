"""
Known mouse protocol values goes here
"""
import logging
from struct import unpack

LOGGER = logging.getLogger(__name__)

PROTO = {
    # Community values
    "1a0c01": "play_vid_tribehouse",
    # Game values
    # "015c0548": "play_vid_musicroom",
    "01410548": "play_vid_musicroom",
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
    def dechex(line, start=None, stop=None):
        # None means "from start to x" or "from x to end"
        if start is None and stop is None:
            return bytearray.fromhex(line).decode("utf8")
        return bytearray.fromhex(line[slice(start, stop)]).decode("utf8")

    def play_vid_tribehouse(self, line):
        # query_length = unpack(">h", bytearray.fromhex(line_data[8:12]))[0]
        link = (self.dechex(line, 18, None),)
        LOGGER.debug("Data in tribeplayer: %s", link)
        return link

    def play_vid_musicroom(self, line):
        link_length = unpack(">H", bytearray.fromhex(line[8:12]))[0] * 2 + 12
        link = self.dechex(line, 12, link_length)

        video_name_length = (link_length + 4) + unpack(
            ">H", bytearray.fromhex(line[link_length : link_length + 4])
        )[0] * 2
        video_name = self.dechex(line, link_length + 4, video_name_length)
        # nick length is integer, not a short?
        nick_length = (video_name_length + 8) + unpack(
            ">I", bytearray.fromhex(line[video_name_length : video_name_length + 8])
        )[0] * 2
        nick = self.dechex(line, video_name_length + 8, nick_length)
        LOGGER.debug("Data in musicroom: \n%s \n%s \n%s", link, video_name, nick)
        return link, video_name, nick


if __name__ == "__main__":
    t = ProtocolHandler()
    t("1a0c01", "535353535353535353535353535353535353535353")
    if "1a0c01" in t:
        print(t)
