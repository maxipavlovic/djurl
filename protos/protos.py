from __future__ import print_function

from bs4 import BeautifulSoup
from twisted.internet.protocol import Protocol, Factory
from twisted.internet.defer import Deferred
from twisted.web.client import Agent
from django.utils import timezone

ws_factory, deployer = None, None


class WebSocketsProto(Protocol):

    def __init__(self, factory):
        self.factory = factory

    def connectionMade(self):
        self.factory.protos.append(self)
        from main import models
        for result in models.get_results():
            if result.title or result.encoding or result.h1:
                self.sendMessage(
                    "2$PAYLOAD$"
                    "{0} - "
                    "\nTitle: {1}"
                    "\nEncoding: {2}"
                    "\nh1: {3}"
                    .format(result.url.url, result.title, result.encoding, result.h1)
                )
            else:
                self.sendMessage(
                    "2$PAYLOAD${}".format(result.url.url)
                )
            suffix = 'OK' if result.iscorrect else 'ERROR'
            self.sendMessage(
                "1$PAYLOAD${0:%d.%m.%Y %H:%M:%S}:{1} {2} ".format(result.datetime, result.url.url, suffix)
            )

    def sendMessage(self, msg):
        self.transport.write(msg)

    def connectionLost(self, reason):
        self.factory.protos.remove(self)


class WebSocketsFactory(Factory):
    protocol = WebSocketsProto

    def __init__(self):
        self.protos = []

    def buildProtocol(self, addr):
        return self.protocol(self)


class Body(Protocol):

    def __init__(self, finished, run_after, url):
        self.finished = finished
        self.remaining = 1024 * 10
        self.body = ""
        self.run_after = run_after
        self.url = url

    def dataReceived(self, bytes):
        if self.remaining:
            display = bytes[:self.remaining]
            self.remaining -= len(display)
            self.body += display

    def connectionLost(self, reason):
        print('Finished receiving body:', reason.getErrorMessage())
        self._soup()

    def _soup(self):
        print("Beautiful soup")
        soup = BeautifulSoup(self.body, 'html.parser')
        current_time = timezone.now()
        self.run_after(soup, self.url, current_time)
        if ws_factory.protos:
            for proto in ws_factory.protos:
                if soup.title or soup.encoding or soup.h1:
                    proto.sendMessage(
                        "2$PAYLOAD$"
                        "{0} - "
                        "\nTitle: {1}"
                        "\nEncoding: {2}"
                        "\nh1: {3}"
                        .format(self.url.url, soup.title, soup.encoding, soup.h1)
                    )
                else:
                    proto.sendMessage(
                        "2$PAYLOAD${}".format(self.url.url)
                    )
                proto.sendMessage(
                    "1$PAYLOAD${0:%d.%m.%Y %H:%M:%S}:{1} OK".format(current_time, self.url.url)
                )


def cbResponse(response, run_after, url):
    print("OK")
    finished = Deferred()
    response.deliverBody(Body(finished, run_after, url))


def cbError(_, run_after, url):
    print("Error")
    current_time = timezone.now()
    run_after(None, url, current_time)
    if ws_factory.protos:
        for proto in ws_factory.protos:
            proto.sendMessage(
                "2$PAYLOAD${}".format(url.url)
            )
            proto.sendMessage(
                "1$PAYLOAD${0:%d.%m.%Y %H:%M:%S}:{1} ERROR".format(current_time, url.url)
            )


def call_from_sender(url, run_after, url_instance):
    agent = Agent(deployer.reactor)
    d = agent.request(
        'GET',
        url
    )
    d.addCallback(cbResponse, run_after, url_instance)
    d.addErrback(cbError, run_after, url_instance)


def sender(url, run_after, url_instance, timeshift):
    if timeshift != 0:
        global deployer
        deployer.reactor.callLater(timeshift, call_from_sender, url, run_after, url_instance)
    else:
        call_from_sender(url, run_after, url_instance)


def get_factory(_deployer):
    global deployer, ws_factory
    deployer = _deployer
    ws_factory = WebSocketsFactory()
    return ws_factory