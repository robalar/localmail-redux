# coding: utf-8

import time
import imaplib
import smtplib
from io import BytesIO
from email.charset import Charset, BASE64, QP
from email.message import Message
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header

import pytest

from .base import BaseLocalmailTest

try:
    from email.generator import BytesGenerator as Generator
except ImportError:
    from email.generator import Generator
try:
    import unittest2 as unittest
except ImportError:
    import unittest  # NOQA

from .helpers import (
    IMAPClient
)


class TestAuth(BaseLocalmailTest):
    def test_smtp_any_auth_allowed(self, server):
        smtp = smtplib.SMTP(self.HOST, server.smtp_port)
        smtp.login("a", "b")
        smtp.sendmail("a@b.com", ["c@d.com"], "Subject: test\n\ntest")
        smtp.quit()
        smtp = smtplib.SMTP(self.HOST, server.smtp_port)
        smtp.login("c", "d")
        smtp.sendmail("a@b.com", ["c@d.com"], "Subject: test\n\ntest")
        smtp.quit()

    def test_smtp_anonymous_allowed(self, server):
        smtp = smtplib.SMTP(self.HOST, server.smtp_port)
        smtp.sendmail("a@b.com", ["c@d.com"], "Subject: test\n\ntest")
        smtp.quit()

    def test_imap_any_auth_allowed(self, server):
        imap = imaplib.IMAP4(self.HOST, server.imap_port)
        imap.login("any", "thing")
        imap.select()
        assert imap.search("ALL") == ("OK", [None])
        imap.close()
        imap.logout()

        imap = imaplib.IMAP4(self.HOST, server.imap_port)
        imap.login("other", "something")
        imap.select()
        assert imap.search("ALL") == ("OK", [None])
        imap.close()
        imap.logout()

    def test_imap_anonymous_not_allowed(self, server):
        imap = imaplib.IMAP4(self.HOST, server.imap_port)
        with pytest.raises(imaplib.IMAP4.error):
            imap.select()
            assert imap.search("ALL") == ("OK", [None])


class TestSequentialID(BaseLocalmailTest):
    def _testmsg(self, n):
        msg = MIMEText("test %s" % n)
        msg["Subject"] = "test %s" % n
        msg["From"] = "from%s@example.com" % n
        msg["To"] = "to%s@example.com" % n
        return msg

    def assert_message(self, msg, n):
        expected = self._testmsg(n)
        assert msg["From"] == expected["From"]
        assert msg["To"] == expected["To"]
        assert msg["Subject"] == expected["Subject"]
        assert msg.is_multipart() == expected.is_multipart()
        if msg.is_multipart():
            for part, expected_part in zip(msg.walk(), expected.walk()):
                assert part.get_content_maintype() == expected_part.get_content_maintype()

                if part.get_content_maintype() != "multipart":
                    assert (
                        part.get_payload().strip() == expected_part.get_payload().strip()
                    )
        else:
            assert msg.get_payload().strip() == expected.get_payload().strip()

    def test_simple_message(self, smtp_client, imap_client):
        smtp_client.send(self._testmsg(1))
        msg = imap_client.fetch(1)
        self.assert_message(msg, 1)

    def test_multiple_messages(self, smtp_client, imap_client):
        smtp_client.send(self._testmsg(1))
        smtp_client.send(self._testmsg(2))
        msg1 = imap_client.fetch(1)
        msg2 = imap_client.fetch(2)
        self.assert_message(msg1, 1)
        self.assert_message(msg2, 2)

    def test_delete_single_message(self, smtp_client, imap_client):
        smtp_client.send(self._testmsg(1))
        imap_client.store(1, r"(\Deleted)")
        imap_client.client.expunge()
        assert imap_client.search("ALL") == []

    def test_delete_with_multiple(self, smtp_client, imap_client):
        smtp_client.send(self._testmsg(1))
        smtp_client.send(self._testmsg(2))
        imap_client.store(1, r"(\Deleted)")
        imap_client.client.expunge()
        assert imap_client.search("ALL") == [imap_client.msgid(1)]

    def test_search_deleted(self, smtp_client, imap_client):
        smtp_client.send(self._testmsg(1))
        smtp_client.send(self._testmsg(2))
        imap_client.store(1, r"(\Deleted)")
        assert imap_client.search("(DELETED)") == [imap_client.msgid(1)]
        assert imap_client.search("(NOT DELETED)") == [imap_client.msgid(2)]


class TestUid(TestSequentialID):
    @pytest.fixture(scope="class")
    def imap_client(self, server):
        imap = IMAPClient(self.HOST, server.imap_port, uid=True)
        imap.start()
        yield imap
        imap.stop()


class MultipartTestCase(TestSequentialID):
    def _testmsg(self, n):
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "test %s" % n
        msg["From"] = "from%s@example.com" % n
        msg["To"] = "to%s@example.com" % n
        html = MIMEText("<b>test %s</b>" % n, "html")
        text = MIMEText("test %s" % n, "plain")
        msg.attach(html)
        msg.attach(text)
        return msg


class TestEncoding(BaseLocalmailTest):

    # These characters are one byte in latin-1 but two in utf-8
    difficult_chars = "£ë"
    # These characters are two bytes in either encoding
    difficult_chars += "筷子"
    # Unicode snowman for good measure
    difficult_chars += "☃"
    # These characters might trip up Base64 encoding...
    difficult_chars += "=+/"
    # ... and these characters might trip up quoted printable
    difficult_chars += "=3D"  # QP encoded

    difficult_chars_latin1_compatible = difficult_chars.encode(
        "latin-1", "ignore"
    ).decode("latin-1")

    def _encode_message(self, msg):
        with BytesIO() as fp:
            generator = Generator(fp)
            generator.flatten(msg)
            return fp.getvalue()

    def _make_message(self, text, charset, cte):
        msg = Message()
        ctes = {"8bit": None, "base64": BASE64, "quoted-printable": QP}
        cs = Charset(charset)
        cs.body_encoding = ctes[cte]
        msg.set_payload(text, charset=cs)

        # Should always be encoded correctly.
        msg["Subject"] = self.difficult_chars
        msg["From"] = "from@example.com"
        msg["To"] = "to@example.com"
        assert msg["Content-Transfer-Encoding"] == cte
        return msg

    def _fetch_and_delete_sole_message(self, imap_client):
        for _ in range(5):
            try:
                (message_number,) = imap_client.search("ALL")
                break
            except ValueError:
                time.sleep(0.5)
        else:
            raise AssertionError("Single Message not found")
        msg = imap_client.fetch(message_number)
        imap_client.store(message_number, r"(\Deleted)")
        imap_client.client.expunge()
        return msg

    @pytest.mark.parametrize("payload, charset, cte", [
        pytest.param(difficult_chars_latin1_compatible, "iso-8859-1", "8bit"),
        pytest.param(difficult_chars, "utf-8", "8bit"),
        pytest.param(difficult_chars, "utf-8", "quoted-printable"),
        pytest.param(difficult_chars, "utf-8", "base64"),
    ])
    def test_encoding(self, payload, charset, cte, smtp_client, imap_client):
        # Arrange
        msg = self._make_message(payload, charset, cte)
        encoded = self._encode_message(msg)

        # Act
        smtp_client.client.sendmail(msg["From"], msg["To"], encoded)
        received = self._fetch_and_delete_sole_message(imap_client)

        # Assert
        payload_bytes = received.get_payload(decode=True)
        payload_text = payload_bytes.decode(received.get_content_charset())
        assert received["Content-Transfer-Encoding"] == cte
        assert received.get_content_charset() == charset.lower()
        ((subject_bytes, subject_encoding),) = decode_header(received["Subject"])
        assert subject_bytes.decode(subject_encoding) == self.difficult_chars
        assert payload_text.strip() == payload
