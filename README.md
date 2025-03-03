# Qubes arbitrary network topology

This software lets you turn your [Qubes OS 4.2](https://www.qubes-os.org/) machine into
an arbitrary network topology host.  It is ideal to create networks of interconnected VMs with arbitrary pathways between them, and minimal effort compared to manually setting everything up using `xl attach` in your `dom0` as `root`.

**Note**: this software only supports release 4.2 and later of Qubes OS.  For support of release 4.1, see branch `r4.1`.  For support of release 4.0, see branch `r4.0`.

## How to use

Suppose you have two VMs, which you want to be interconnected via (virtualized) Ethernet.  VM `F` (for *frontend*) will be attached to VM `B` (for *backend*).

With this software, all you have to do is attach a feature `attach-network-to` onto `B`, like so:

```sh
# Run me on dom0 as your regular Qubes login user.
qvm-features B attach-network-to F
# You can add multiple VMs to attach to, by separating them with newlines like so:
#     [user@dom0]$ qvm-features B attach-network-to 'F
#     G
#     H'
```

And that's it.  As soon as both `B` and `F` are running, network interfaces will appear on each one; if you set the feature while the VMs were running, the interfaces will appear instantly.

Here's the lowdown on network interface naming:

* The network interface in `F` will generally be named `eth0` (or `eth1` or other name sequentially increasing in value).
* The network interface in `B` will be named after `F`.  This name is set by the script
  `vif-route-nexus` deployed to your VMs in the `qubes-arbitrary-network-topology` package.

You can force a particular MAC address onto the interface attached to `F` by specifying
it as the value of the `attach-network-to` feature:

```sh
# Note the quoted string
qvm-features B attach-network-to 'F frontend_mac=12:34:56:78:90:ab'
```

IP networking on none of the network interfaces will be autoconfigured.  Network
addressing and routing are *on you*.  Fortunately, this should be doable (as explained
below) since the frontend VM's network interface can have a static MAC address controlled
by you, and the backend VM's network interface is named after the frontend.

From this point on, all you have to do is configure the network interfaces — e.g. using NetworkManager — on those two VMs, then [adjust the firewall rules](https://www.qubes-os.org/doc/firewall/) on both VMs to permit input from one VM to the other, or even forwarding through them.  You could build a bridge, or set IP configuration to your liking.

Here is a sample IP configuration file for NetworkManager (to follow our example, stored in `B` under `/rw/config/NM-system-connections/F.nmconnection`):

```
[connection]
id=F
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

## How to stop attaching network interfaces

To stop attaching network interfaces to a VM `V` which already has a feature property `attach-network-to`, simply issue this command:

```
qvm-features --unset V attach-network-to
```

## Troubleshooting

### The network interface attached to the backend VM does not have the name of the frontend VM

You are missing the RPM named `qubes-arbitrary-network-topology` in the template of the backend VM (or, if standalone, on the VM itself).

Install the RPM as per the instructions below, and power off the VM (and its template, if any), then power the VM back on.

## How it works

A small Qubes extension running under `qubesd` in dom0 monitors VMs as they start and stop.  If a VM starts and it has the `attach-network-to` feature, all VMs named in the feature will get Xen Ethernet frontends attached, with the backends attached to the VM that just started.  The converse is also true — if a VM starts, and it is mentioned in the `attach-network-to` feature of another VM, the frontend is attached to the VM that just started, and the backend is attached to the VM with the feature.

It's very simple, no magic involved.

## How to install

Build the two necessary RPM packages and then install them to the respective VMs:

1. The `qubes-arbitrary-network-topology` RPM: use the command `make rpm` on a VM with the same Fedora version as your TemplateVM.  Then install the RPM in the TemplateVM, and power off the Template VM, as well as any other VMs you plan to attach networking to.
2. The `qubes-core-admin-addon-arbitrary-network-topology` RPM: use the command `make rpm` on a VM or a `chroot` or `toolbox` container with the same Fedora version as your dom0 (that's Fedora 25 for Qubes 4.0, Fedora 32 for Qubes 4.1, and Fedora 37 for Qubes 4.2).  Then copy the resultant admin addon `noarch` RPM file into your `dom0`, and install the RPM there using `sudo rpm -Uvh`.

You should now be good to go.

## Licensing

This software is shared under the GNU GPL v2.  You can find the text of the GNU GPL in the `COPYING` file distributed with the source.
