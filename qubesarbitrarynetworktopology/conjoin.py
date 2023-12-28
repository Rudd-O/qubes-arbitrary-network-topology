import collections
import typing


ACTION_ADD = "+"
ACTION_REMOVE = "-"


class Cfg(typing.TypedDict):
    config: bool | str
    frontend_network_id: str | None


class ConjoinTracker(dict[str, Cfg]):
    def conjoin(
        self,
        backend: str,
        frontend: str,
        config: bool | str,
        frontend_network_id: str | None,
    ) -> None:
        self["%s %s" % (backend, frontend)] = {
            "config": config,
            "frontend_network_id": frontend_network_id,
        }

    def disjoin(self, backend: str, frontend: str) -> None:
        del self["%s %s" % (backend, frontend)]

    def frontend_network_id(
        self, backend: str, frontend: str
    ) -> typing.Union[str, None]:
        try:
            return self["%s %s" % (backend, frontend)]["frontend_network_id"]
        except KeyError:
            return None

    def config(self, backend: str, frontend: str) -> typing.Union[bool, str, None]:
        try:
            return self["%s %s" % (backend, frontend)]["config"]
        except KeyError:
            return None

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
                cfg: bool | str = True
                if len(fe.split(" ")) == 1:
                    pass
                else:
                    fe, cfg = fe.split(" ", 1)
                me.conjoin(backend, fe, config=cfg, frontend_network_id=None)
        return me

    @classmethod
    def from_dict(klass, d: dict[str, Cfg]) -> "ConjoinTracker":
        o = klass()
        for k, v in d.items():
            o[k] = v
        return o

    def diff(
        self, other: "ConjoinTracker", limit_to_vm: typing.Union[str, None] = None
    ) -> list[tuple[str, str, str, bool | str]]:
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
                t = (ACTION_ADD, first, second, self[item]["config"])
                diffs.append(t)
            else:
                common[item] = True
        for item in other:
            if item not in self:
                first, second = item.split(" ", 1)
                t = (ACTION_REMOVE, first, second, other[item]["config"])
                diffs.append(t)
                common[item] = True
        for item in common:
            if item not in self or item not in other:
                continue
            if self[item]["config"] != other[item]["config"]:
                first, second = item.split(" ", 1)
                t = (ACTION_REMOVE, first, second, self[item]["config"])
                diffs.append(t)
                t = (ACTION_ADD, first, second, other[item]["config"])
                diffs.append(t)
        if limit_to_vm is not None:
            diffs = [d for d in diffs if d[1] == limit_to_vm or d[2] == limit_to_vm]
        return diffs
