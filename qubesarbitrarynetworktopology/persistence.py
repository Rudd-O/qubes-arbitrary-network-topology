import json
import logging
import qubesdb
import typing


from qubesarbitrarynetworktopology.conjoin import ConjoinTracker


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class OldConfig(typing.TypedDict):
    config: bool
    frontend_network_id: str | None


class ConjoinStore(object):
    PATH = "/qubes-active-network-topology"

    def load(self) -> ConjoinTracker:
        q = qubesdb.QubesDB()
        try:
            d = q.read(self.PATH) or "{}"
            try:
                if isinstance(d, bytes):
                    d = d.decode("utf-8")
                loadedd: dict[str, tuple[str, str | None] | OldConfig] = json.loads(d)
            except (FileNotFoundError, json.decoder.JSONDecodeError):
                loadedd = {}
            final: dict[str, tuple[str, str | None]] = {}
            for k, v in loadedd.items():
                if isinstance(v, tuple) or isinstance(v, list):
                    cfg = (v[0], v[1])
                else:
                    cfg = ("", v.get("frontend_network_id"))
                final[k] = cfg
            return ConjoinTracker.from_deserializable(final)
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
