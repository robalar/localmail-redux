import pytest

import localmail
from tests.helpers import clean_inbox, SMTPClient, IMAPClient


class BaseLocalmailTest:
    HOST = "localhost"

    @pytest.fixture(scope="class", autouse=True)
    def server(self):
        server = localmail.run()
        yield server
        server.stop_listening_fn()

    @pytest.fixture(autouse=True)
    def clean_inbox(self, server):
        yield
        clean_inbox(self.HOST, server.imap_port)

    @pytest.fixture(scope="class")
    def smtp_client(self, server):
        smtp = SMTPClient(self.HOST, server.smtp_port)
        smtp.start()
        yield smtp
        smtp.stop()

    @pytest.fixture(scope="class")
    def imap_client(self, server):
        imap = IMAPClient(self.HOST, server.imap_port, uid=False)
        imap.start()
        yield imap
        imap.stop()
