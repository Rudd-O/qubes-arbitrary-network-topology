import collections
import re
import typing


ACTION_ADD = "+"
ACTION_REMOVE = "-"


class MacAddress(str):
    @classmethod
    def from_string(klass, s: str) -> "MacAddress":
        if not re.match(
            "^[0-9a-f][0-9a-f]:[0-9a-f][0-9a-f]:[0-9a-f][0-9a-f]:[0-9a-f][0-9a-f]:[0-9a-f][0-9a-f]:[0-9a-f][0-9a-f]$",
            s,
        ):
            raise ValueError(s)
        return MacAddress(s)


class Parameters(object):
    def __init__(self) -> None:
        self.frontend_mac: MacAddress | None = None

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return repr(self) == repr(other)

    @classmethod
    def from_string(klass, s: str) -> "Parameters":
        obj = klass()
        keypairs = s.split(" ")
        if not keypairs:
            return obj
        if len(keypairs) == 1 and keypairs[0] == "":
            return obj

        for k in keypairs:
            k, sep, v = k.partition("=")
            if sep != "=":
                raise ValueError("key without value in %r" % s)
            if k == "frontend_mac":
                if v != "None":
                    obj.frontend_mac = MacAddress.from_string(v)

        return obj

    def __str__(self) -> str:
        setparms = []
        if self.frontend_mac:
            setparms.append(f"frontend_mac={self.frontend_mac}")
        return " ".join(setparms)

    def __repr__(self) -> str:
        return self.__str__()


class VifAttachment:
    config: Parameters
    frontend_network_id: str | None

    def __init__(self, config: Parameters, frontend_network_id: str | None):
        self.config = config
        self.frontend_network_id = frontend_network_id

    def __str__(self) -> str:
        return (
            f"<VifAttachment ID {self.frontend_network_id} with config {self.config}>"
        )

    def __repr__(self) -> str:
        return self.__str__()


class ConjoinTracker(dict[str, VifAttachment]):
    def conjoin(
        self,
        backend: str,
        frontend: str,
        config: Parameters,
        frontend_network_id: str | None,
    ) -> None:
        self["%s %s" % (backend, frontend)] = VifAttachment(
            config=config,
            frontend_network_id=frontend_network_id,
        )

    def disjoin(self, backend: str, frontend: str) -> None:
        del self["%s %s" % (backend, frontend)]

    def frontend_network_id(
        self, backend: str, frontend: str
    ) -> typing.Union[str, None]:
        try:
            return self["%s %s" % (backend, frontend)].frontend_network_id
        except KeyError:
            return None

    def config(self, backend: str, frontend: str) -> Parameters:
        return self["%s %s" % (backend, frontend)].config

    def _others(
        self, me: str, compare_column: int, return_column: int
    ) -> typing.List[str]:
        ret = []
        for k in self.keys():
            cols = k.split(" ", 1)
            if cols[compare_column] == me:
                ret.append(cols[return_column])
        return ret

    def frontends(self, backend: str) -> list[str]:
        return self._others(backend, 0, 1)

    def backends(self, frontend: str) -> list[str]:
        return self._others(frontend, 1, 0)

    def connections(self, vm: str) -> list[tuple[str, str]]:
        """
        connections returns a list of (backend, frontend) for
        all connections involving vm.
        """
        return [(x, vm) for x in self.backends(vm)] + [
            (vm, x) for x in self.frontends(vm)
        ]

    @classmethod
    def from_vm_table(klass, vm_table: dict[str, str | None]) -> "ConjoinTracker":
        # vm_table is a dictionary vm_name -> feature config string.
        me = klass()
        for backend, feature in vm_table.items():
            if not feature:
                continue
            frontends_and_configs = [f for f in feature.splitlines() if f.strip()]
            if not frontends_and_configs:
                continue
            for fe in frontends_and_configs:
                cfg = Parameters()
                if len(fe.split(" ")) == 1:
                    pass
                else:
                    fe, cfgstr = fe.split(" ", 1)
                    cfg = Parameters.from_string(cfgstr)
                me.conjoin(backend, fe, config=cfg, frontend_network_id=None)
        return me

    def to_serializable(self) -> dict[str, tuple[str, str | None]]:
        to_be_saved: dict[str, tuple[str, str | None]] = {}
        for k, v in self.items():
            to_be_saved[k] = str(v.config), v.frontend_network_id
        return to_be_saved

    @classmethod
    def from_deserializable(
        klass, d: dict[str, tuple[str, str | None]]
    ) -> "ConjoinTracker":
        o = klass()
        for k, (cfgstr, frontend_network_id) in d.items():
            o[k] = VifAttachment(Parameters.from_string(cfgstr), frontend_network_id)
        return o

    def diff(
        self, other: "ConjoinTracker", limit_to_vm: typing.Union[str, None] = None
    ) -> list[tuple[str, str, str, Parameters]]:
        """
        diff returns a list of actions to take in order to bring
        the second conjoiner in line with the first, encoded as
        a list of (action, backend, frontend, config).
        """
        diffs = []
        common = collections.OrderedDict()
        for item in self:
            if item not in other:
                first, second = item.split(" ", 1)
                t = (ACTION_ADD, first, second, self[item].config)
                diffs.append(t)
            else:
                common[item] = True
        for item in other:
            if item not in self:
                first, second = item.split(" ", 1)
                t = (ACTION_REMOVE, first, second, other[item].config)
                diffs.append(t)
                common[item] = True
        for item in common:
            if item not in self or item not in other:
                continue
            if str(self[item].config) != str(other[item].config):
                first, second = item.split(" ", 1)
                t = (ACTION_REMOVE, first, second, other[item].config)
                diffs.append(t)
                t = (ACTION_ADD, first, second, self[item].config)
                diffs.append(t)
        if limit_to_vm is not None:
            diffs = [d for d in diffs if d[1] == limit_to_vm or d[2] == limit_to_vm]
        return diffs
