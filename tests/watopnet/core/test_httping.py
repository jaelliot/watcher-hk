# -*- encoding: utf-8 -*-

from types import SimpleNamespace

import falcon
import pytest

from watopnet.core import basing
from watopnet.core import httping as wat_httping


def test_throttle_process_request_unwraps_tuple_remote_addr():
    """Under the Ioflo WSGI server ``remote_addr`` is a ``(host, port)`` tuple.

    Regression test: a tuple ``remote_addr`` previously crashed with
    ``TypeError: sequence item 0: expected str instance, tuple found``
    inside the Komer key serialization, producing an HTTP 500 on every
    public request to the watcher. The tuple must be unwrapped to the
    host string before it is used as a database key.
    """
    db = basing.Baser(name="keri-v2-throttle-tuple", temp=True)
    try:
        throttle = wat_httping.Throttle(db=db)
        req = SimpleNamespace(remote_addr=("1.2.3.4", 7632), access_route=[])
        resp = SimpleNamespace(complete=False, status=None)

        throttle.process_request(req, resp)

        assert resp.complete is False
        assert resp.status is None
        reqs = db.ips.get(keys=("1.2.3.4",))
        assert reqs is not None
        assert reqs.count == 1
    finally:
        db.close(clear=True)


def test_throttle_process_request_falls_back_to_access_route():
    """When ``remote_addr`` is absent the request is keyed by ``access_route``."""
    db = basing.Baser(name="keri-v2-throttle-fallback", temp=True)
    try:
        throttle = wat_httping.Throttle(db=db)
        req = SimpleNamespace(remote_addr=None, access_route=["5.6.7.8"])
        resp = SimpleNamespace(complete=False, status=None)

        throttle.process_request(req, resp)

        assert resp.complete is False
        assert resp.status is None
        reqs = db.ips.get(keys=("5.6.7.8",))
        assert reqs is not None
        assert reqs.count == 1
    finally:
        db.close(clear=True)


def test_throttle_process_request_rejects_when_over_limit(mockHelpingNowUTC):
    """Requests beyond ``MaximumRequests`` within a window receive HTTP 429."""
    db = basing.Baser(name="keri-v2-throttle-limit", temp=True)
    try:
        throttle = wat_httping.Throttle(db=db)
        req = SimpleNamespace(remote_addr="9.9.9.9", access_route=[])
        resp = SimpleNamespace(complete=False, status=None)

        for _ in range(throttle.MaximumRequests + 1):
            throttle.process_request(req, resp)

        assert resp.complete is True
        assert resp.status == falcon.HTTP_TOO_MANY_REQUESTS
    finally:
        db.close(clear=True)
