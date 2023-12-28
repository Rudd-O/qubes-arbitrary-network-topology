%define debug_package %{nil}

%define mybuildnumber %{?build_number}%{?!build_number:1}

Name:           qubes-arbitrary-network-topology
Version:        0.1.0
Release:        %{mybuildnumber}%{?dist}
Summary:        Turn your Qubes OS into an arbitrary network topology host
BuildArch:      noarch

License:        GPLv2+
URL:            https://github.com/Rudd-O/qubes-arbitrary-network-topology
Source0:        https://github.com/Rudd-O/%{name}/archive/{%version}.tar.gz#/%{name}-%{version}.tar.gz

%global pythoninterp %{_bindir}/python3

BuildRequires:  make
BuildRequires:  coreutils
BuildRequires:  tar
BuildRequires:  findutils
BuildRequires:  python3
BuildRequires:  python3-rpm-macros

Requires:       qubes-core-agent-networking >= 4.2
Requires:       python3
Requires:       python3-qubesdb

%description
This package lets you create arbitrary network topologies in your
Qubes OS system.  Install this in the TemplateVM of your AppVMs
that will participate of the network topology.  Then install the
companion qubes-core-admin-addon-arbitrary-network-topology package
in your dom0.

Please see README.md enclosed in the package for instructions on how to use
this software.

%package -n     qubes-core-admin-addon-arbitrary-network-topology
Summary:        dom0 administrative extension for Qubes arbitrary network topology

%global pythoninterp %{_bindir}/python3

BuildRequires:  make
BuildRequires:  coreutils
BuildRequires:  tar
BuildRequires:  findutils
BuildRequires:  python3
BuildRequires:  python3-rpm-macros
BuildRequires:  python3-setuptools

BuildRequires:  systemd-rpm-macros

Requires:       python3
Requires:       qubes-core-dom0 >= 4.2

%description -n qubes-core-admin-addon-arbitrary-network-topology
This package lets you create arbitrary network topologies in your
Qubes OS system.  Install this in your dom0.  Then install the
companion qubes-arbitrary-network-topology package in the TemplateVM
of your AppVMs that will participate of the network topology.

Please see README.md enclosed in the package for instructions on how to use
this software.

%prep
%setup -q

%build
# variables must be kept in sync with install
make DESTDIR=$RPM_BUILD_ROOT SYSCONFDIR=%{_sysconfdir}

%install
rm -rf $RPM_BUILD_ROOT
# variables must be kept in sync with build
make install DESTDIR=$RPM_BUILD_ROOT SYSCONFDIR=%{_sysconfdir}
find $RPM_BUILD_ROOT

%files
%attr(0755, root, root) %{_sysconfdir}/xen/scripts/vif-route-nexus
%doc README.md

%files -n       qubes-core-admin-addon-arbitrary-network-topology
%attr(0644, root, root) %{python3_sitelib}/qubesarbitrarynetworktopology/*
%{python3_sitelib}/qubesarbitrarynetworktopology-*.egg-info

%post -n         qubes-core-admin-addon-arbitrary-network-topology
# Restart qubesd after initial install.
if [ $1 -eq 1 ] ; then
    %{_bindir}/systemctl --system restart qubesd.service
fi

%postun -n       qubes-core-admin-addon-arbitrary-network-topology
# Restart qubesd after upgrade or erasure.
%{_bindir}/systemctl --system restart qubesd.service

%changelog
* Mon Mar 02 2022 Manuel Amador (Rudd-O) <rudd-o@rudd-o.com>
- Qubes 4.1 release

* Wed Feb 17 2021 Manuel Amador (Rudd-O) <rudd-o@rudd-o.com>
- Initial release
