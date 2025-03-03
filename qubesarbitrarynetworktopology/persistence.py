import json
import logging
import qubesdb


from qubesarbitrarynetworktopology.conjoin import ConjoinTracker


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class ConjoinStore(object):
    PATH = "/qubes-active-network-topology"

    def load(self) -> ConjoinTracker:
        q = qubesdb.QubesDB()
        try:
            d = q.read(self.PATH) or "{}"
            try:
                if isinstance(d, bytes):
                    d = d.decode("utf-8")
                loadedd: dict[str, tuple[str, str | None]] = json.loads(d)
            except (FileNotFoundError, json.decoder.JSONDecodeError):
                loadedd = {}
            return ConjoinTracker.from_deserializable(loadedd)
        except BaseException:
            log.exception("Failure loading conjoin store")
            raise
        finally:
            q.close()

    def save(self, o: ConjoinTracker) -> None:
        to_be_saved = o.to_serializable()
        q = qubesdb.QubesDB()
        try:
            oj = json.dumps(to_be_saved)
            q.write(self.PATH, oj)
        except BaseException:
            log.exception("Failure persisting conjoin store")
            raise
        finally:
            q.close()
