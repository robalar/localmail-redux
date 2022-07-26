Forked from the original repo `here <https://launchpad.net/localmail>`_.

Localmail Redux
=========

For local people.

Localmail is an SMTP and IMAP server that stores all messages into a single
in-memory mailbox. It is designed to be used to speed up running test suites on
systems that send email, such as new account sign up emails with confirmation
codes. It can also be used to test SMTP/IMAP client code.

Features:

  * Fast and robust IMAP/SMTP implementations, including multipart
    messages and unicode support.

  * Includes simple HTTP interface for reading messages, which is useful for
    checking html emails.

  * Compatible with python's stdlib client, plus clients like mutt and
    thunderbird.

  * Authentication is supported but completely ignored, all message go in
    single mailbox.

  * Messages not persisted by default, and will be lost on shutdown.
    Optionally, you can log messages to disk in mbox format.

Missing features/TODO:

  * SSL support

WARNING: not a real SMTP/IMAP server - not for production usage.


Running localmail
-----------------

.. code-block:: bash

    twistd localmail

This will run localmail in the background, SMTP on port 2025 and IMAP on 2143,
It will log to a file ./twistd.log. Use the -n option if you want to run in
the foreground, like so.

.. code-block:: bash

    twistd -n localmail


You can pass in arguments to control parameters.

.. code-block:: bash

   twistd localmail --imap <port> --smtp <port> --http <port> --file localmail.mbox


You can have localmail use random ports if you like. The port numbers will be logged.
TODO: enable writing random port numbers to a file.

.. code-block:: bash

   twisted -n localmail --random


Embedding
---------

If you want to embed localmail in another non-twisted program, such as test
runner, do the following.

.. code-block:: python

    import localmail

    server = localmail.run()
    ...
    server.stop_listening_fn()

This will run the twisted reactor using `crochet <https://crochet.readthedocs.io/en/stable/>`_ in a seperate thread,
and attach the servers to the ports. ``stop_listening_fn`` **must** be called if you wish to call `localmail.run`
again.

Publishing New Version
----------------------

Handled by ``.github/workflows/publish.yml``.

1. Update the version in ``pyproject.toml``
2. Get that update merged into main
3. Tag a commit with the same version with ``v`` prefixed (``0.1.1 in`` pyproject.toml, ``v0.1.1`` git tag)
4. Wait for the action to build
