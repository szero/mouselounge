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
- `youtube-dl <https://github.com/ytdl-org/youtube-dl#installation>`_
- `tcpdump <https://www.tcpdump.org/#latest-releases>`_

  OR
- `tcpflow <https://github.com/simsong/tcpflow>`_

Installation
~~~~~~~~~~~~
::

    pip3 install https://github.com/szero/mouselounge/archive/master.zip

If you're using ``tcpdump``, it should be already configured and ready to use.
If it isn't the ``mouselounge`` program will error out with "[Your capture device]:
You don't have permission to capture on that device". You can assign the program
packet capturing rights by issing the command below:

::

    sudo setcap 'CAP_NET_RAW+eip CAP_NET_ADMIN+eip' "$(type tcpdump | cut -f3 -d' ')"

As for ``tcpflow``, the command looks like this this.

::

    sudo setcap 'CAP_NET_RAW+eip CAP_NET_ADMIN+eip' "$(type tcpflow | cut -f3 -d' ')"

If you don't like giving programs extended rights permanently you can skips the step above
and use the program like so:

::

    sudo mouselounge

Usage
~~~~~

Run ``mouselounge`` in your terminal!

Thats it! Now you can paste your links inside music input box like you always did,
but now, mpv window with given video will open and information about posted youtube
videos will be printed.

To quit, either press ``Ctrl + C`` or ``Ctrl + \``

FAQ
~~~

1. I installed the thing and all of its dependiencies, it was working for some time and
   videos still appear in the terminal window but no video window appears anymore.

- *This program depends on ``youtube-dl``. It always changes because youtube
  changes it's API's all the time. If you can't see vids, try updating ``youtube-dl``
  to the newest version first, from the link in Installation section preferably.*
