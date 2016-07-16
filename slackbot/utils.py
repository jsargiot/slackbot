# -*- coding: utf-8 -*-

import os
import logging
import tempfile
import requests
from contextlib import contextmanager
from six.moves import _thread, range, queue
import six
from functools import wraps

logger = logging.getLogger(__name__)


def download_file(url, fpath):
    logger.debug('starting to fetch %s', url)
    r = requests.get(url, stream=True)
    with open(fpath, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024*64):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
                f.flush()
    logger.debug('fetch %s', fpath)
    return fpath


def to_utf8(s):
    """Convert a string to utf8. If the argument is an iterable
    (list/tuple/set), then each element of it would be converted instead.

    >>> to_utf8('a')
    'a'
    >>> to_utf8(u'a')
    'a'
    >>> to_utf8([u'a', u'b', u'\u4f60'])
    ['a', 'b', '\\xe4\\xbd\\xa0']
    """
    if six.PY2:
        if isinstance(s, str):
            return s
        elif isinstance(s, unicode):
            return s.encode('utf-8')
        elif isinstance(s, (list, tuple, set)):
            return [to_utf8(v) for v in s]
        else:
            return s
    else:
        return s


@contextmanager
def create_tmp_file(content=''):
    fd, name = tempfile.mkstemp()
    try:
        if content:
            os.write(fd, content)
        yield name
    finally:
        os.close(fd)
        os.remove(name)


class WorkerPool(object):
    def __init__(self, func, nworker=10):
        self.nworker = nworker
        self.func = func
        self.queue = queue.Queue()

    def start(self):
        for __ in range(self.nworker):
            _thread.start_new_thread(self.do_work, tuple())

    def add_task(self, msg):
        self.queue.put(msg)

    def do_work(self):
        while True:
            msg = self.queue.get()
            self.func(msg)


def ignore_direct_message(fn):
    """
    Decorator declaring the wrapped function to the default reply hanlder.

    May be invoked as a simple, argument-less decorator (i.e. ``@default_reply``) or
    with arguments customizing its behavior (e.g. ``@default_reply(matchstr='pattern')``).
    """
    @wraps(fn)
    def wrapper(message, *args, **kwargs):
        if not message.channel._body.get("is_im"):
            return fn(message, *args, **kwargs)
        logger.info("Ignoring direct message from %s", message._body.get("user"))
        message.reply("Sorry, can't do that from a direct message")
    return wrapper
