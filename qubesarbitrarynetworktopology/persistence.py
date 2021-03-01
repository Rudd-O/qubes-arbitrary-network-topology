import json

import qubesdb

from qubesarbitrarynetworktopology import ConjoinTracker


class ConjoinStore(object):

    # FIXME: store this in Qubes DB instead of in a file.
    PATH = "/qubes-active-network-topology"

    def __init__(self):
        pass

    def load(self):
        q = qubesdb.QubesDB()
        try:
            d = q.read(self.PATH) or "{}"
            try:
                if isinstance(d, bytes):
                    d = d.decode("utf-8")
                d = json.loads(d)
            except (FileNotFoundError, json.decoder.JSONDecodeError):
                d = {}
            return ConjoinTracker.from_dict(d)
        finally:
            q.close()

    def save(self, o):
        q = qubesdb.QubesDB()
        try:
            o = json.dumps(o)
            q.write(self.PATH, o)
        finally:
            q.close()
