from __future__ import print_function

import asyncio
import contextlib
import logging
import subprocess
import sys


try:
    import qubes
    import qubes.ext
    from qubesarbitrarynetworktopology.conjoin import (
        ConjoinTracker,
        ACTION_ADD,
        ACTION_REMOVE,
    )
    from qubesarbitrarynetworktopology.persistence import ConjoinStore
except ImportError:
    qubes = None


log = logging.getLogger(__name__)


@contextlib.contextmanager
def with_qubes():
    log.info("Opening Qubes connection")
    q = qubes.Qubes()
    try:
        yield q
    finally:
        q.close()
        log.info("Closed Qubes connection")


def attach(backend, frontend):
    """Returns the network VIF ID as a string."""
    _ = subprocess.run(
        [
            "xl",
            "network-attach",
            frontend,
            "backend=%s" % backend,
            "vifname=%s" % frontend,
            "script=%s" % "vif-route-nexus",
        ],
        check=True,
    )
    p = subprocess.run(
        ["xl", "network-list", frontend],
        stdout=subprocess.PIPE,
        universal_newlines=True,
        check=True,
    )
    vifid = [x for x in p.stdout.splitlines() if x.strip()][-1].split()[0]
    return vifid


def detach(frontend, vifid):
    p = subprocess.run(["xl", "network-detach", frontend, vifid], check=True)


if qubes:

    class QubesArbitraryNetworkTopologyExtension(qubes.ext.Extension):

        config = None
        active = None

        def __init__(self):
            super().__init__()

        def _delayed_graphs_loader(self, force_feature=None, for_vm=None):
            with with_qubes() as q:
                if self.config is None or for_vm is not None:
                    vm_table = {
                        backend.name: (
                            (force_feature)
                            if for_vm is not None and for_vm == backend.name
                            else (backend.features.get("attach-network-to") or "")
                        )
                        for backend in q.domains
                    }
                    self.config = ConjoinTracker.from_vm_table(vm_table)
                    print("Loaded configuration: %s" % self.config, file=sys.stderr)
            if self.active is None:
                self.active = ConjoinStore().load()
            print("Active configuration: %s" % self.active, file=sys.stderr)

        def conjoin_vm_with_peers(self, vm):
            with with_qubes() as q:
                domains = q.domains
                for action, backend, frontend, config in self.config.diff(
                    self.active, limit_to_vm=vm
                ):
                    if backend not in domains or frontend not in domains:
                        continue
                    if not all(
                        [
                            domains[backend].is_running(),
                            not domains[backend].is_paused(),
                            domains[frontend].is_running(),
                            not domains[frontend].is_paused(),
                        ]
                    ):
                        continue
                    if action == ACTION_ADD:
                        try:
                            attached_vifid = attach(backend, frontend)
                            self.active.conjoin(
                                backend,
                                frontend,
                                config=config,
                                frontend_network_id=attached_vifid,
                            )
                            log.info(
                                "Attached backend %s to frontend %s with frontend VIF %s",
                                backend,
                                frontend,
                                attached_vifid,
                            )
                        except subprocess.CalledProcessError as e:
                            log.exception(
                                "Could not attach backend %s to frontend %s",
                                backend,
                                frontend,
                            )
                    elif action == ACTION_REMOVE:
                        vifid_to_detach = self.active.frontend_network_id(
                            backend, frontend
                        )
                        try:
                            detach(frontend, vifid_to_detach)
                            log.info(
                                "Detached backend %s from frontend %s VIF %s",
                                backend,
                                frontend,
                                vifid_to_detach,
                            )
                        except subprocess.CalledProcessError as e:
                            log.exception(
                                "Could not detach backend %s from frontend",
                                backend,
                                frontend,
                            )
                        self.active.disjoin(backend, frontend)
                ConjoinStore().save(self.active)

        def disjoin_vm_from_peers(self, vm):
            with with_qubes() as q:
                domains = q.domains
                combos = self.active.connections(vm)
                for backend, frontend in combos:
                    if backend not in domains or frontend not in domains:
                        continue
                    vifid_to_detach = self.active.frontend_network_id(backend, frontend)
                    if vm == frontend:
                        # This VM was a frontend; the VIF is cleaned up by Xen
                        # from tke backend automatically so we cannot detach it
                        # even if we wanted to; hence we only deregister.
                        log.info(
                            "Unlinked already-detached backend %s from frontend %s VIF %s",
                            backend,
                            frontend,
                            vifid_to_detach,
                        )
                        self.active.disjoin(backend, frontend)
                        continue
                    try:
                        detach(frontend, vifid_to_detach)
                        log.info(
                            "Detached backend %s from frontend %s VIF %s",
                            backend,
                            frontend,
                            vifid_to_detach,
                        )
                    except subprocess.CalledProcessError as e:
                        log.exception(
                            "Could not detach backend %s from frontend %s VIF %s",
                            backend,
                            frontend,
                            vifid_to_detach,
                        )
                    self.active.disjoin(backend, frontend)
                ConjoinStore().save(self.active)

        @qubes.ext.handler(
            "domain-feature-set:attach-network-to",
            "domain-feature-delete:attach-network-to",
        )
        def on_attach_network_to_changed(self, vm, unused_event, **kwargs):
            self._delayed_graphs_loader(kwargs.get("value", None), vm.name)
            self.conjoin_vm_with_peers(vm.name)

        @qubes.ext.handler("domain-start")
        def on_domain_started(self, vm, unused_event, **unused_kwargs):
            self._delayed_graphs_loader()
            self.conjoin_vm_with_peers(vm.name)

        @qubes.ext.handler("domain-unpaused")
        def on_domain_unpaused(self, vm, unused_event, **unused_kwargs):
            self._delayed_graphs_loader()
            self.conjoin_vm_with_peers(vm.name)

        @qubes.ext.handler("domain-shutdown")
        def on_domain_shutdown(self, vm, unused_event, **kwargs):
            self._delayed_graphs_loader()
            self.disjoin_vm_from_peers(vm.name)
