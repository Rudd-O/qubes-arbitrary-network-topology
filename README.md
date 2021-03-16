# Qubes arbitrary network topology

This software lets you turn your [Qubes OS 4.0](https://www.qubes-os.org/) machine into
an arbitrary network topology host.  It is ideal to create networks of interconnected VMs with arbitrary pathways between them, and minimal effort compared to manually setting everything up using `xl attach` in your `dom0` as `root`.

**Note**: this software only supports release 4.0 of Qubes OS.

## How it works

Suppose you have two VMs, which you want to be interconnected via (virtualized) Ethernet.  VM `F` (for *frontend*) will be attached to VM `B` (for *backend*).

With this software, all you have to do is attach a feature `attach-network-to` onto `B`, like so:

```
# Run me on dom0 as your regular Qubes login user.
qvm-features B attach-network-to F
```

And that's it.  As soon as both `B` and `F` are running, network interfaces will appear on each one; if you set the feature while the VMs were running, the interfaces will appear instantly.  The network interface in `F` will generally be named `eth0` (or `eth1` or other name increasing in value).  The network interface in `B` will be named after `F`.  IP networking on none of the network interfaces will be configured by the system.

From this point on, all you have to do is configure the network interfaces — e.g. using NetworkManager — on those two VMs, then [adjust the firewall rules](https://www.qubes-os.org/doc/firewall/) on both VMs to permit input from one VM to the other, or even forwarding through them.  You could build a bridge, or set IP configuration to your liking.

Here is a sample IP configuration file for NetworkManager (to follow our example, stored in `B` under `/rw/config/NM-system-connections/F.nmconnection`):

```
[connection]
id=B
uuid=bb88cc30-1bcd-40bf-97f2-013626692bd1
type=ethernet
autoconnect-priority=-999
interface-name=F
permissions=

[ethernet]
mac-address-blacklist=

[ipv4]
address1=10.250.9.26/30
dns=10.250.7.2
dns-search=
method=manual
route1=10.250.0.0/20,127.0.0.1,1000
route2=10.250.8.0/24,10.250.9.25,1
route3=0.0.0.0/0,10.250.9.25,101

[ipv6]
addr-gen-mode=stable-privacy
dns-search=
method=disabled

[proxy]
```

Judicious use of the `qvm-features` command will allow you to have arbitrarily connected VMs on your system, directly testing a panoply of network topologies.

## How to install

Build the two necessary RPM packages and then install them to the respective VMs:

1. The `qubes-arbitrary-network-topology` RPM: use the command `make rpm` on a VM with the same Fedora version as your TemplateVM.  Then install the RPM in the TemplateVM, and power off the Template VM, as well as any other VMs you plan to attach networking to.
2. The `qubes-core-admin-addon-arbitrary-network-topology` RPM: use the command `make rpm` on a VM or a `chroot` with the same Fedora version as your dom0 (that's Fedora 25 for Qubes 4.0).  Then copy the RPM into your `dom0`, and install the RPM.

You should now be good to go.
