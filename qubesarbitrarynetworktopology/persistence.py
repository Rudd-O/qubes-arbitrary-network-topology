import json
import logging
import qubesdb


from qubesarbitrarynetworktopology.conjoin import ConjoinTracker


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class ConjoinStore(object):
    # FIXME: store this in Qubes DB instead of in a file.
    PATH = "/qubes-active-network-topology"

    def load(self) -> ConjoinTracker:
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
        except BaseException:
            log.exception("Failure loading conjoin store")
            raise
        finally:
            q.close()

    def save(self, o: ConjoinTracker) -> None:
        q = qubesdb.QubesDB()
        try:
            oj = json.dumps(o)
            q.write(self.PATH, oj)
        except BaseException:
            log.exception("Failure persisting conjoin store")
            raise
        finally:
            q.close()
