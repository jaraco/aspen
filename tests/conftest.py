from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import sys

import pytest
from aspen.testing import Harness, teardown


@pytest.yield_fixture
def sys_path_scrubber():
    before = set(sys.path)
    yield
    after = set(sys.path)
    for name in after - before:
        sys.path.remove(name)


@pytest.yield_fixture
def harness(sys_path_scrubber):
    harness = Harness()
    yield harness
    harness.teardown()


@pytest.yield_fixture
def DjangoClient():
    def _DjangoClient(*a, **kw):
        try:
            from django.test.client import Client
        except ImportError:
            raise pytest.skip.Exception
        else:
            return Client(*a, **kw)
    yield _DjangoClient


def pytest_runtest_teardown():
    teardown()
