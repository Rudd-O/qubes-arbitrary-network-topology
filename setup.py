import os
import setuptools

if __name__ == '__main__':
    version = open(os.path.join(os.path.dirname(__file__), 'qubes-arbitrary-network-topology.spec')).read().strip()
    version = [v for v in version.splitlines() if v.startswith("Version:")][0]
    version = version.split()[-1]
    setuptools.setup(
        name='qubesarbitrarynetworktopology',
        version=version,
        author='Manuel Amador (Rudd-O)',
        author_email='rudd-o@rudd-o.com',
        description='Qubes arbitrary network topology dom0 component',
        license='GPL2+',
        url='https://github.com/Rudd-O/qubes-arbitrary-network-topology',

        packages=('qubesarbitrarynetworktopology',),

        entry_points={
            'qubes.ext': [
                'qubesarbitrarynetworktopology = qubesarbitrarynetworktopology:QubesArbitraryNetworkTopologyExtension',
            ],
        }
    )
