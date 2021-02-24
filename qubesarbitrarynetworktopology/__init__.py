from __future__ import print_function

import asyncio
import logging
import qubes
import qubes.ext
import sys


log = logging.getLogger(__name__)


class ConjoinTracker(dict):
    def conjoin(self, backend, frontend, frontend_network_id):
        self["%s %s" % (backend, frontend)] = frontend_network_id

    def disjoin(self, backend, frontend):
        del self["%s %s" % (backend, frontend)]

    def frontend_network_id(self, backend, frontend):
        try:
            return self["%s %s" % (backend, frontend)]
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


class QubesArbitraryNetworkTopologyExtension(qubes.ext.Extension):

    # def shutdown_routing_for_vm(self, netvm, appvm):
    # self.reload_routing_for_vm(netvm, appvm, True)

    # def reload_routing_for_vm(self, netvm, appvm, shutdown=False):
    #'''Reload the routing method for the VM.'''
    # if not netvm.is_running():
    # return
    # for addr_family in (4, 6):
    # ip = appvm.ip6 if addr_family == 6 else appvm.ip
    # if ip is None:
    # continue
    ## report routing method
    # self.setup_forwarding_for_vm(netvm, appvm, ip, remove=shutdown)

    # def setup_forwarding_for_vm(self, netvm, appvm, ip, remove=False):
    #'''
    # Record in Qubes DB that the passed VM may be meant to have traffic
    # forwarded to and from it, rather than masqueraded from it and blocked
    # to it.

    # The relevant incantation on the command line to assign the forwarding
    # behavior is `qvm-features <VM> routing-method forward`.  If the feature
    # is set on the TemplateVM upon which the VM is based, then that counts
    # as the forwarding method for the VM as well.

    # The counterpart code in qubes-firewall handles setting up the NetVM
    # with the proper networking configuration to permit forwarding without
    # masquerading behavior.

    # If `remove` is True, then we remove the respective routing method from
    # the Qubes DB instead.
    #'''
    # if ip is None:
    # return
    # routing_method = appvm.features.check_with_template(
    #'routing-method', 'masquerade'
    # )
    # base_file = '/qubes-routing-method/{}'.format(ip)
    # if remove:
    # netvm.untrusted_qdb.rm(base_file)
    # elif routing_method == 'forward':
    # netvm.untrusted_qdb.write(base_file, 'forward')
    # else:
    # netvm.untrusted_qdb.write(base_file, 'masquerade')

    config = None
    active = None
    _qubes = None

    def __init__(self):
        super().__init__()

    def _delayed_graphs_loader(self, force_vm_feature=None):
        if self._qubes is None:
            log.info("Connecting to qubesd")
            self._qubes = qubes.Qubes()
        if self.config is None or force_vm_feature is not None:
            log.info("Reloading config")
            config = ConjoinTracker()
            if force_vm_feature is not None:
                force_vm, force_feature = force_vm_feature
                force_vm = force_vm.name
            else:
                force_vm, force_feature = None, None
            for backend in self._qubes.domains:
                if force_vm == backend.name:
                    feature = force_feature
                    if force_feature is None:
                        continue
                else:
                    feature = backend.features.get("attach-network-to") or ""
                frontends = [f for f in feature.splitlines() if f.strip()]
                if not frontends:
                    continue
                for frontend in frontends:
                    config.conjoin(backend.name, frontend, True)
            self.config = config
        if self.active is None:
            log.info("Setting up active connection tracker")
            self.active = ConjoinTracker()

    def with_graphs_loaded(f):
        def g(*a, **kw):
            a[0]._delayed_graphs_loader()
            return f(*a, **kw)

        g.__name__ = f.__name__
        g.__doc__ = f.__doc__
        return g

    @with_graphs_loaded
    def conjoin_vm_with_peers(self, vm):
        domains = self._qubes.domains
        combos = [(x, vm) for x in self.config.backends(vm)] + [
            (vm, x) for x in self.config.frontends(vm)
        ]
        for backend, frontend in combos:
            if backend not in domains:
                continue
            if self.active.frontend_network_id(backend, frontend) is None:
                if all(
                    [
                        domains[backend].is_running(),
                        not domains[backend].is_paused(),
                        domains[frontend].is_running(),
                        not domains[frontend].is_paused(),
                    ]
                ):
                    log.info("Attaching backend %s to frontend %s", backend, frontend)
                    self.active.conjoin(backend, frontend, 1)
                else:
                    log.info(
                        "Won't attach backend %s to frontend %s — either not running",
                        backend,
                        frontend,
                    )
            else:
                log.info(
                    "Won't attach backend %s to frontend %s — already attached",
                    backend,
                    frontend,
                )

    @with_graphs_loaded
    def disjoin_vm_from_peers(self, vm):
        domains = self._qubes.domains
        combos = [(x, vm) for x in self.active.backends(vm)] + [
            (vm, x) for x in self.active.frontends(vm)
        ]
        for backend, frontend in combos:
            if backend not in domains:
                continue
            if self.active.frontend_network_id(backend, frontend) is None:
                log.info(
                    "Won't detach backend %s from frontend %s — already detached",
                    backend,
                    frontend,
                )
            else:
                log.info(
                    "Detaching backend %s from frontend %s",
                    backend,
                    frontend,
                )
                self.active.disjoin(backend, frontend)

    # TODO: handle case of VMs being removed from the property, or properties being deleted, or changed.
    # the basic case should be relatively simple:
    # any VMs currently attached that are no longer configured to be attached, must be detached
    # any VMs currently not attached that are now configured to be attached, must be attached if they are running
    # and then we use a reduced version of the primitives above to effect those changes.
    # (e.g. in the case of detaching, we can't detach a VM from all its peers, we need to detach it
    #  only from the VM that it is no longer supposed to be attached to, and vice versa in the case of attaching.)
    # but anyway, the cornerstone is always to compute the delta between what is currently active
    # and what was just recently configured, and effect those changes now.
    # TODO: maybe rename the property to `network-backend-for`
    @qubes.ext.handler(
        "domain-feature-set:attach-network-to",
        "domain-feature-delete:attach-network-to",
    )
    def on_attach_network_to_changed(self, vm, event, **kwargs):
        # pylint: disable=no-self-use,unused-argument
        if "value" in kwargs:
            force_vm_feature = (vm, kwargs["value"])
        else:
            force_vm_feature = (vm, None)
        self._delayed_graphs_loader(force_vm_feature)

    @qubes.ext.handler("domain-unpaused")
    @qubes.ext.handler("domain-start")
    def on_domain_started_or_unpaused(self, vm, event, **kwargs):
        self.conjoin_vm_with_peers(vm.name)

    @qubes.ext.handler("domain-shutdown")
    def on_domain_shutdown(self, vm, event, **kwargs):
        self.disjoin_vm_from_peers(vm.name)
