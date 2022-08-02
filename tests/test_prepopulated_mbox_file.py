from email.message import Message
from mailbox import mbox
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

import localmail
from tests.base import BaseLocalmailTest


class TestPrePopulatedMboxFile(BaseLocalmailTest):
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

    @pytest.fixture(scope="class", autouse=True)
    def server(self, mbox_path, populated_mbox):
        server = localmail.run(mbox_path=mbox_path)
        yield server
        server.stop_listening_fn()

    def test_inbox_prepopulated(self, imap_client):
        msg = imap_client.fetch(1)
        assert msg["Subject"] == "Test"
        assert msg["To"] == "to@test.org"
        assert msg["From"] == "from@test.org"
