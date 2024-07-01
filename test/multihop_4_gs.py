from mininet.net import Mininet
from mininet.node import Node
from mininet.node import OVSController
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink
from mininet.topo import Topo


class LinuxRouter(Node):
    "A Node with IP forwarding enabled."

    # pylint: disable=arguments-differ
    def config( self, **params ):
        super(LinuxRouter, self).config(**params)
        # Enable forwarding on the router
        self.cmd( 'sysctl net.ipv4.ip_forward=1')

    def terminate(self):
        self.cmd('sysctl net.ipv4.ip_forward=0')
        super(LinuxRouter, self).terminate()


def topology():


    # =================================================================

    net = Mininet(link=TCLink, autoSetMacs = True, controller=OVSController, waitConnected=True)
    net.addController('c0')

    # =================================================================

    info("*** Creating nodes\n")
    a1 = net.addHost('a1',      cls=LinuxRouter,    ip='10.0.1.100/24') # Source
    a2 = net.addHost('a2',      cls=LinuxRouter,    ip='10.0.2.100/24')
    a3 = net.addHost('a3',      cls=LinuxRouter,    ip='10.0.3.100/24')
    a4 = net.addHost('a4',      cls=LinuxRouter,    ip='10.0.4.100/24')
    a5 = net.addHost('a5',      cls=LinuxRouter,    ip='10.0.5.100/24') # Destination
    gs1 = net.addHost('gs1',    cls=LinuxRouter,    ip='11.0.1.100/24') # GS

    # =================================================================

    info("*** Creating links\n")
    
    # Satellite network (direct)
    net.addLink(a1, a2,     cls=TCLink,     delay='10ms')
    net.addLink(S2, a3,     cls=TCLink,     delay='10ms')
    net.addLink(a3, a4,     cls=TCLink,     delay='10ms')
    net.addLink(a4, a5,     cls=TCLink,     delay='10ms')

    # Ground station -> a2 (direct)
    net.addLink(gs1, a2,    cls=TCLink,     delay='100ms')

    info("*** Starting network\n")
    net.start()

    # =================================================================

    info("*** Configuring host ports\n")

    # Enable IP forwarding (a2, a3, a4)
    a2.cmd('sysctl -w net.ipv4.ip_forward=1')
    a3.cmd('sysctl -w net.ipv4.ip_forward=1')
    a4.cmd('sysctl -w net.ipv4.ip_forward=1') 

    # Host 'a1' (source)
    a1.cmd('ifconfig a1-eth0 10.0.1.1/24')      # Port 1

    # Host 'a2'
    a2.cmd('ifconfig a2-eth0 10.0.1.2/24')      # Port 1
    a2.cmd('ifconfig a2-eth1 10.0.2.1/24')      # Port 2
    a2.cmd('ifconfig a2-eth2 11.0.1.2/24')      # Port 3 (to GS)

    # Host 'a3'
    a3.cmd('ifconfig a3-eth0 10.0.2.2/24')      # Port 1
    a3.cmd('ifconfig a3-eth1 10.0.3.1/24')      # Port 2

    # Host 'a4'
    a4.cmd('ifconfig a4-eth0 10.0.3.2/24')      # Port 1
    a4.cmd('ifconfig a4-eth1 10.0.5.1/24')      # Port 2

    # Host 'a5' (destination)
    a5.cmd('ifconfig a5-eth0 10.0.5.2/24')      # Port 1

    # Host 'gs1' (ground station)
    gs1.cmd('ifconfig gs1-eth0 11.0.1.1/24')    # Port 1 (to a2)

    # =================================================================

    info("*** Setting up routes\n")

    # LEFT-TO-RIGHT (FORWARD HOP)
    # =================================================================

    # a1 to a2 via a2-eth0
    a1.cmd('route add -net 10.0.2.0 netmask 255.255.255.240 gw 10.0.1.2')

    # a1 to a3 via a2-eth0
    a1.cmd('route add -net 10.0.3.0 netmask 255.255.255.240 gw 10.0.1.2')

    # a1 to a4 via a2-eth0
    a1.cmd('route add -net 10.0.4.0 netmask 255.255.255.240 gw 10.0.1.2')

    # a1 to a5 via a2-eth0
    a1.cmd('route add -net 10.0.5.0 netmask 255.255.255.240 gw 10.0.1.2')

    # a2 to a3 via a3-eth0
    a2.cmd('route add -net 10.0.3.0 netmask 255.255.255.240 gw 10.0.2.2')

    # a2 to a4 via a3-eth0
    a2.cmd('route add -net 10.0.4.0 netmask 255.255.255.240 gw 10.0.2.2')

    # a2 to a5 via a3-eth0
    a2.cmd('route add -net 10.0.5.0 netmask 255.255.255.240 gw 10.0.2.2')

    # a3 to a4 via a4-eth0
    a3.cmd('route add -net 10.0.4.0 netmask 255.255.255.240 gw 10.0.3.2')

    # a3 to a5 via a4-eth0
    a3.cmd('route add -net 10.0.5.0 netmask 255.255.255.240 gw 10.0.3.2')

    # a4 to a5 via a5-eth0
    a4.cmd('route add -net 10.0.5.0 netmask 255.255.255.240 gw 10.0.5.2')


    # RIGHT-TO-LEFT (BACKWARD HOP)
    # =================================================================

    # a5 to a4 via a4-eth1
    a5.cmd('route add -net 10.0.4.0 netmask 255.255.255.240 gw 10.0.5.1')

    # a5 to a3 via a4-eth1
    a5.cmd('route add -net 10.0.3.0 netmask 255.255.255.240 gw 10.0.5.1')

    # a5 to a2 via a4-eth1
    a5.cmd('route add -net 10.0.2.0 netmask 255.255.255.240 gw 10.0.5.1')

    # a5 to a1 via a4-eth1
    a5.cmd('route add -net 10.0.1.0 netmask 255.255.255.240 gw 10.0.5.1')

    # a4 to a3 via a3-eth1
    a4.cmd('route add -net 10.0.3.0 netmask 255.255.255.240 gw 10.0.3.1')

    # a4 to a2 via a3-eth1
    a4.cmd('route add -net 10.0.2.0 netmask 255.255.255.240 gw 10.0.3.1')

    # a4 to a1 via a3-eth1
    a4.cmd('route add -net 10.0.1.0 netmask 255.255.255.240 gw 10.0.3.1')

    # a3 to a2 via a2-eth1
    a3.cmd('route add -net 10.0.2.0 netmask 255.255.255.240 gw 10.0.2.1')

    # a3 to a1 via a2-eth1
    a3.cmd('route add -net 10.0.1.0 netmask 255.255.255.240 gw 10.0.2.1')

    # a2 to a1 via a1-eth1
    a2.cmd('route add -net 10.0.1.0 netmask 255.255.255.240 gw 10.0.1.1')


    # GROUND STATION
    # =================================================================

    # a1 <-> gs1
    a1.cmd('route add -net 11.0.1.0 netmask 255.255.255.240 gw 10.0.1.2')
    gs1.cmd('route add -net 10.0.1.0 netmask 255.255.255.240 gw 11.0.1.2')

    # a2 <-> gs1
    a2.cmd('route add -net 11.0.1.0 netmask 255.255.255.240 gw 11.0.1.1')
    gs1.cmd('route add -net 10.0.2.0 netmask 255.255.255.240 gw 11.0.1.2')

    # a3 <-> gs1
    a3.cmd('route add -net 11.0.1.0 netmask 255.255.255.240 gw 10.0.2.1')
    gs1.cmd('route add -net 10.0.3.0 netmask 255.255.255.240 gw 11.0.1.2')

    # a4 <-> gs1
    a4.cmd('route add -net 11.0.1.0 netmask 255.255.255.240 gw 10.0.3.1')
    gs1.cmd('route add -net 10.0.4.0 netmask 255.255.255.240 gw 11.0.1.2')

    # a4 <-> gs1
    a5.cmd('route add -net 11.0.1.0 netmask 255.255.255.240 gw 10.0.5.1')
    gs1.cmd('route add -net 10.0.5.0 netmask 255.255.255.240 gw 11.0.1.2')






    
    info("*** Running CLI\n")
    CLI(net)

    info("*** Stopping network")
    net.stop()









if __name__ == '__main__':
    setLogLevel('info')
    topology()