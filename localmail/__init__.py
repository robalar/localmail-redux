# Copyright (C) 2012- Canonical Ltd
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
from time import sleep
from typing import NamedTuple, Callable

from crochet import setup, run_in_reactor, wait_for
from twisted.application import service
from twisted.internet import reactor
from twisted.cred import portal, checkers
from .cred import TestServerRealm, CredentialsNonChecker
from .smtp import TestServerESMTPFactory
from .imap import TestServerIMAPFactory
from .http import TestServerHTTPFactory, index

setup()


class PortReporterTCPServer(service.Service, object):
    def __init__(self, name, port, factory, reportPort):
        self.name = name
        self.port = port
        self.factory = factory
        self.reportPort = reportPort

    def privilegedStartService(self):
        self.listeningPort = reactor.listenTCP(self.port, self.factory)
        if self.reportPort is not None:
            self.reportPort(self.name, self.listeningPort.getHost().port)
        return super(PortReporterTCPServer, self).privilegedStartService()

    def stopService(self):
        self.listeningPort.stopListening()
        return super(PortReporterTCPServer, self).stopService()


def get_portal():
    localmail_portal = portal.Portal(TestServerRealm())
    localmail_portal.registerChecker(CredentialsNonChecker())
    localmail_portal.registerChecker(checkers.AllowAnonymousAccess())
    return localmail_portal


def get_factories():
    auth = get_portal()
    smtpServerFactory = TestServerESMTPFactory(auth)
    imapServerFactory = TestServerIMAPFactory()
    imapServerFactory.portal = auth
    httpServerFactory = TestServerHTTPFactory(index)
    return smtpServerFactory, imapServerFactory, httpServerFactory


def get_services(smtp_port, imap_port, http_port, callback=None):
    smtpFactory, imapFactory, httpFactory = get_factories()

    smtp = PortReporterTCPServer("smtp", smtp_port, smtpFactory, callback)
    imap = PortReporterTCPServer("imap", imap_port, imapFactory, callback)
    http = PortReporterTCPServer("http", http_port, httpFactory, callback)

    return smtp, imap, http


class ServerPorts(NamedTuple):
    smtp_port: int
    imap_port: int
    http_port: int
    stop_listening_fn: Callable


def run(smtp_port=2025, imap_port=2143, http_port=8880, mbox_path=None) -> ServerPorts:
    result = _run(smtp_port, imap_port, http_port, mbox_path)
    return ServerPorts(*result.wait(timeout=30))


@wait_for
def _wait_for_deferred(d):
    return d


@run_in_reactor
def _run(smtp_port, imap_port, http_port, mbox_path):
    from twisted.internet import reactor

    if mbox_path is not None:
        from localmail.inbox import INBOX

        INBOX.setFile(mbox_path)
    smtpFactory, imapFactory, httpFactory = get_factories()
    smtp = reactor.listenTCP(smtp_port, smtpFactory)
    imap = reactor.listenTCP(imap_port, imapFactory)
    http = reactor.listenTCP(http_port, httpFactory)

    def stop_listening():
        _wait_for_deferred(smtp.stopListening())
        _wait_for_deferred(imap.stopListening())
        _wait_for_deferred(http.stopListening())
        sleep(0.1)

    return smtp.getHost().port, imap.getHost().port, http.getHost().port, stop_listening
