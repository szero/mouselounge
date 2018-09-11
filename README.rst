===========
mouselounge
===========

Play videos in your tribehouse while running the client outisde of the browser
(using steam client for example).

Playing videos in music rooms works, but videos that are longer than 5 minutes
won't be closed automatically.

This works only on linux atm.

Requirements
~~~~~~~~~~~~

Install those programs with your package manager or download them from the developers
directly:

Please use recent version of ``python3``.

- `mpv <https://mpv.io/installation>`_
- `youtube-dl <https://github.com/rg3/youtube-dl>`_
- `tcpflow <https://github.com/simsong/tcpflow>`_

Installation
~~~~~~~~~~~~
::

    pip3 install https://github.com/Szero/mouseloungue/archive/master.zip

Since most Linux distributions don't allow packet fetching for non-root users, you
either have to run this program with ``sudo`` or give your "tcpflow" program the rights
to capture packets by using ``setcap`` program and issuing it like this:

::

    setcap 'CAP_NET_RAW+eip CAP_NET_ADMIN+eip' /usr/bin/tcpflow

Running
~~~~~~~

Run ``mouselounge`` from your terminal!

Thats it! Now you can paste your links inside music input box like you always did and
but now mpv window with given video will open.

To quit, either press ``Ctrl + Z`` or ``Ctrl + \``
