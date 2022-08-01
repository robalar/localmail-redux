from email.message import Message
from mailbox import mbox
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Tuple

import pytest

from tests.helpers import IMAPClient, start_server


class TestPrePopulatedMboxFile:
    @pytest.fixture(scope="class")
    def mbox_path(self):
        with TemporaryDirectory() as temp_dir:
            yield Path(temp_dir) / "temp.mbox"

    @pytest.fixture(scope="class")
    def mbox(self, mbox_path) -> mbox:
        yield mbox(mbox_path)

    @pytest.fixture(scope="class")
    def populated_mbox(self, mbox):
        msg = Message()
        msg["Subject"] = "Test"
        msg["From"] = "from@test.org"
        msg["To"] = "to@test.org"
        mbox.add(msg)
        mbox.flush()

    @pytest.fixture(scope="class")
    def server(self, populated_mbox, mbox_path) -> Tuple[int, int, int]:
        start_server(mbox_path=mbox_path)
        yield 2025, 2143, 8880

    @pytest.fixture(scope="class")
    def imap_client(self, server) -> IMAPClient:
        imap = IMAPClient("localhost", server[1], uid=False)
        imap.start()
        yield imap
        imap.stop()

    def test_inbox_prepopulated(self, imap_client):
        msg = imap_client.fetch(1)
        assert msg["Subject"] == "Test"
        assert msg["To"] == "to@test.org"
        assert msg["From"] == "from@test.org"
