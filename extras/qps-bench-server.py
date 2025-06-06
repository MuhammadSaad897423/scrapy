#!/usr/bin/env python
from collections import deque
from time import time

from twisted.internet import reactor  # noqa: TID253
from twisted.web.resource import Resource
from twisted.web.server import NOT_DONE_YET, Site


class Root(Resource):
    def __init__(self):
        Resource.__init__(self)
        self.concurrent = 0
        self.tail = deque(maxlen=100)
        self._reset_stats()

    def _reset_stats(self):
        self.tail.clear()
        self.start = self.lastmark = self.lasttime = time()

    def getChild(self, request, name):
        return self

    def render(self, request):
        now = time()
        delta = now - self.lasttime

        # reset stats on high iter-request times caused by client restarts
        if delta > 3:  # seconds
            self._reset_stats()
            return ""

        self.tail.appendleft(delta)
        self.lasttime = now
        self.concurrent += 1

        if now - self.lastmark >= 3:
            self.lastmark = now
            qps = len(self.tail) / sum(self.tail)
            print(
                f"samplesize={len(self.tail)} concurrent={self.concurrent} qps={qps:0.2f}"
            )

        if "latency" in request.args:
            latency = float(request.args["latency"][0])
            reactor.callLater(latency, self._finish, request)
            return NOT_DONE_YET

        self.concurrent -= 1
        return ""

    def _finish(self, request):
        self.concurrent -= 1
        if not request.finished and not request._disconnected:
            request.finish()


root = Root()
factory = Site(root)
reactor.listenTCP(8880, factory)
reactor.run()
