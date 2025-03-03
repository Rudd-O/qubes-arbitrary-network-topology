import contextlib
import logging
import subprocess
import qubes
import qubes.ext
import typing


from qubesarbitrarynetworktopology.conjoin import (
    ConjoinTracker,
    ACTION_ADD,
    ACTION_REMOVE,
    MacAddress,
)
from qubesarbitrarynetworktopology.persistence import ConjoinStore


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


@contextlib.contextmanager
def with_qubes() -> typing.Generator[qubes.Qubes, None, None]:
    log.debug("Opening Qubes connection")
    q = qubes.Qubes()
    try:
        yield q
    finally:
        q.close()
        log.debug("Closed Qubes connection")


def attach(backend: str, frontend: str, frontend_mac: MacAddress | None = None) -> str:
    """Returns the network VIF ID as a string."""
    cmd = (
        ["xl", "network-attach", frontend]
        + (["mac=%s" % frontend_mac] if frontend_mac else [])
        + [
            "backend=%s" % backend,
            "vifname=%s" % frontend,
            "script=%s" % "vif-route-nexus",
        ]
    )
    _ = subprocess.run(
        cmd,
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


def detach(frontend: str, vifid: str) -> None:
    subprocess.run(["xl", "network-detach", frontend, vifid], check=True)


class QubesArbitraryNetworkTopologyExtension(qubes.ext.Extension):  # type:ignore
    config: ConjoinTracker = None  # type: ignore
    active: ConjoinTracker = None  # type: ignore

    def __init__(self) -> None:
        super().__init__()

    def _delayed_graphs_loader(
        self,
        force_feature: str | None = None,
        for_vm: qubes.vm.BaseVM | None = None,
        apply: bool = True,
    ) -> None:
        with with_qubes() as q:
            if self.config is None or for_vm is not None:
                vm_table: dict[str, str | None] = {
                    backend.name: (
                        (force_feature)
                        if for_vm is not None and for_vm == backend.name
                        else (backend.features.get("attach-network-to") or "")
                    )
                    for backend in q.domains
                }
                config = ConjoinTracker.from_vm_table(vm_table)
                if not apply:
                    return
                self.config = config
                log.info("Loaded configuration: %s", self.config)
        if self.active is None:
            self.active = ConjoinStore().load()
        log.info("Active configuration: %s", self.active)

    def conjoin_vm_with_peers(self, vm: str) -> None:
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
                        attached_vifid = attach(
                            backend, frontend, frontend_mac=config.frontend_mac
                        )
                        self.active.conjoin(
                            backend,
                            frontend,
                            config=config,
                            frontend_network_id=attached_vifid,
                        )
                        log.info(
                            "Attached backend %s to frontend %s with frontend VIF %s config %s",
                            backend,
                            frontend,
                            attached_vifid,
                            config,
                        )
                    except subprocess.CalledProcessError:
                        log.exception(
                            "Could not attach backend %s to frontend %s",
                            backend,
                            frontend,
                        )
                elif action == ACTION_REMOVE:
                    vifid_to_detach = self.active.frontend_network_id(backend, frontend)
                    try:
                        if vifid_to_detach is not None:
                            detach(frontend, vifid_to_detach)
                            log.info(
                                "Detached backend %s from frontend %s VIF %s config %s",
                                backend,
                                frontend,
                                vifid_to_detach,
                                config,
                            )
                        else:
                            log.info(
                                "No need to detach backend %s from frontend %s since VIF is %s",
                                backend,
                                frontend,
                                vifid_to_detach,
                            )
                    except subprocess.CalledProcessError:
                        log.exception(
                            "Could not detach backend %s from frontend",
                            backend,
                            frontend,
                        )
                    self.active.disjoin(backend, frontend)
            ConjoinStore().save(self.active)

    def disjoin_vm_from_peers(self, vm: qubes.vm.BaseVM) -> None:
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
                    if vifid_to_detach is not None:
                        detach(frontend, vifid_to_detach)
                        log.info(
                            "Detached backend %s from frontend %s VIF %s",
                            backend,
                            frontend,
                            vifid_to_detach,
                        )
                    else:
                        log.info(
                            "No need to detach backend %s from frontend %s since VIF is %s",
                            backend,
                            frontend,
                            vifid_to_detach,
                        )
                except subprocess.CalledProcessError:
                    log.exception(
                        "Could not detach backend %s from frontend %s VIF %s",
                        backend,
                        frontend,
                        vifid_to_detach,
                    )
                self.active.disjoin(backend, frontend)
            ConjoinStore().save(self.active)

    @qubes.ext.handler(
        "domain-feature-pre-set:attach-network-to",  # type: ignore
    )
    def on_attach_network_to_before_change(
        self,
        subject: qubes.vm.BaseVM,
        event: typing.Any,
        feature: typing.Any,
        value: str,
        oldvalue: str | None = None,
    ) -> None:
        # Attempt to load configuration with new value, but do not apply it.
        self._delayed_graphs_loader(value, subject.name, apply=False)

    @qubes.ext.handler(
        "domain-feature-set:attach-network-to",  # type: ignore
        "domain-feature-delete:attach-network-to",
    )
    def on_attach_network_to_changed(
        self, vm: qubes.vm.BaseVM, unused_event: typing.Any, **kwargs: typing.Any
    ) -> None:
        self._delayed_graphs_loader(kwargs.get("value", None), vm.name)
        self.conjoin_vm_with_peers(vm.name)

    @qubes.ext.handler("domain-start")  # type: ignore
    def on_domain_started(
        self, vm: qubes.vm.BaseVM, unused_event: typing.Any, **unused_kwargs: typing.Any
    ) -> None:
        self._delayed_graphs_loader()
        self.conjoin_vm_with_peers(vm.name)

    @qubes.ext.handler("domain-unpaused")  # type: ignore
    def on_domain_unpaused(
        self, vm: qubes.vm.BaseVM, unused_event: typing.Any, **unused_kwargs: typing.Any
    ) -> None:
        self._delayed_graphs_loader()
        self.conjoin_vm_with_peers(vm.name)

    @qubes.ext.handler("domain-shutdown")  # type: ignore
    def on_domain_shutdown(
        self, vm: qubes.vm.BaseVM, unused_event: typing.Any, **kwargs: typing.Any
    ) -> None:
        self._delayed_graphs_loader()
        self.disjoin_vm_from_peers(vm.name)
