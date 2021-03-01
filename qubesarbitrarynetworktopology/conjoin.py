import collections


ACTION_ADD = "+"
ACTION_REMOVE = "-"


class ConjoinTracker(dict):
    def conjoin(self, backend, frontend, config, frontend_network_id):
        self["%s %s" % (backend, frontend)] = {
            "config": config,
            "frontend_network_id": frontend_network_id,
        }

    def disjoin(self, backend, frontend):
        del self["%s %s" % (backend, frontend)]

    def frontend_network_id(self, backend, frontend):
        try:
            return self["%s %s" % (backend, frontend)]["frontend_network_id"]
        except KeyError:
            pass

    def config(self, backend, frontend):
        try:
            return self["%s %s" % (backend, frontend)]["config"]
        except KeyError:
            pass

    def _others(self, me, compare_column, return_column):
        ret = []
        for k in self.keys():
            cols = k.split(" ", 1)
            if cols[compare_column] == me:
                ret.append(cols[return_column])
        return ret

    def frontends(self, backend):
        return self._others(backend, 0, 1)

    def backends(self, frontend):
        return self._others(frontend, 1, 0)

    def connections(self, vm):
        """
        connections returns a list of (backend, frontend) for
        all connections involving vm.
        """
        return [(x, vm) for x in self.backends(vm)] + [
            (vm, x) for x in self.frontends(vm)
        ]

    @classmethod
    def from_vm_table(klass, vm_table):
        # vm_table is a dictionary vm_name -> feature config string.
        config = klass()
        for backend, feature in vm_table.items():
            if not feature:
                continue
            frontends = [f for f in feature.splitlines() if f.strip()]
            if not frontends:
                continue
            for fe in frontends:
                if len(fe.split(" ")) == 1:
                    fe, cfg = fe, True
                else:
                    fe, cfg = fe.split(" ", 1)
                config.conjoin(backend, fe, config=cfg, frontend_network_id=None)
        return config

    @classmethod
    def from_dict(klass, d):
        o = klass()
        for k, v in d.items():
            o[k] = v
        return o

    def diff(self, other, limit_to_vm=None):
        """
        diff returns a list of actions to take in order to bring
        the second conjoiner in line with the first, encoded as
        a list of (action, backend, frontend, config).
        """
        diffs = []
        common = collections.OrderedDict()
        for item in self:
            if not item in other:
                diffs.append([ACTION_ADD] + item.split(" ", 1) + [self[item]["config"]])
            else:
                common[item] = True
        for item in other:
            if not item in self:
                diffs.append(
                    [ACTION_REMOVE] + item.split(" ", 1) + [other[item]["config"]]
                )
                common[item] = True
        for item in common:
            if item not in self or item not in other:
                continue
            if self[item]["config"] != other[item]["config"]:
                diffs.append(
                    [ACTION_REMOVE] + item.split(" ", 1) + [self[item]["config"]]
                )
                diffs.append(
                    [ACTION_ADD] + item.split(" ", 1) + [other[item]["config"]]
                )
        if limit_to_vm is not None:
            diffs = [d for d in diffs if d[1] == limit_to_vm or d[2] == limit_to_vm]
        return diffs
