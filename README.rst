===========
mouselounge
===========

Play videos in transformice while using non-browser game clients.
(using steam client for example)

Works both in tribehouses and music rooms!

This works only on linux atm.

Requirements
~~~~~~~~~~~~

Install those programs with your package manager or download them from the developers
directly:

Please use recent version of ``python3``.

- `mpv <https://mpv.io/installation>`_
- `youtube-dl <https://github.com/rg3/youtube-dl>`_
- `tcpdump <https://www.tcpdump.org/#latest-releases>`_

  OR
- `tcpflow <https://github.com/simsong/tcpflow>`_

Installation
~~~~~~~~~~~~
::

    pip3 install https://github.com/szero/mouselounge/archive/master.zip

If you're using ``tcpdump``, it should be already configured and ready to use.
As for ``tcpflow``, you would either have to run ``mouselounge``
script with ``sudo`` or give your ``tcpflow`` instance rights
to capture packets by using ``setcap`` program and issuing it like this:

::

    sudo setcap 'CAP_NET_RAW+eip CAP_NET_ADMIN+eip' /usr/bin/tcpflow

Usage
~~~~~

Run ``mouselounge`` in your terminal!

Thats it! Now you can paste your links inside music input box like you always did,
but now, mpv window with given video will open and information about posted youtube
videos will be printed.

To quit, either press ``Ctrl + C`` or ``Ctrl + \``
