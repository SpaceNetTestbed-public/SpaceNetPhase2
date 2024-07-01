from mininet.net import Mininet
from mininet.node import Controller
from mininet.node import Host
from mininet.node import Node
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink

from mininet.topo import Topo
class LinuxRouter( Node ):
    "A Node with IP forwarding enabled."

    # pylint: disable=arguments-differ
    def config( self, **params ):
        super( LinuxRouter, self).config( **params )
        # Enable forwarding on the router
        self.cmd( 'sysctl net.ipv4.ip_forward=1' )

    def terminate( self ):
        self.cmd( 'sysctl net.ipv4.ip_forward=0' )
        super( LinuxRouter, self ).terminate()

def topology():



    # =================================================================

    net = Mininet(controller=None)

    # =================================================================

    info("*** Creating nodes\n")
    a1 = net.addHost('a1', cls=LinuxRouter, ip='10.0.1.100/24')
    a2 = net.addHost('a2', cls=LinuxRouter, ip='10.0.2.100/24')
    a3 = net.addHost('a3', cls=LinuxRouter, ip='10.0.3.100/24')
    a4 = net.addHost('a4', cls=LinuxRouter, ip='10.0.4.100/24')
    a5 = net.addHost('a5', cls=LinuxRouter, ip='10.0.5.100/24')
    gs1 = net.addHost('gs1', cls=LinuxRouter, ip='11.0.1.11/24')

    # =================================================================
    info("*** Creating links\n")
    
    # Satellite network (direct)
    net.addLink(a1, a2, intfName1='a1-eth1', intfName2='a2-eth1', params1={'ip':'10.0.0.1/30'}, params2={'ip':'10.0.0.2/30'}, cls=TCLink, delay='10ms') # NOTE: the order in which ip's are assigned to interfaces may require changes in routing commands below!
    net.addLink(a2, a3, intfName1='a2-eth2', intfName2='a3-eth1', params1={'ip':'10.0.0.5/30'}, params2={'ip':'10.0.0.6/30'}, cls=TCLink, delay='10ms')
    net.addLink(a3, a4, intfName1='a3-eth2', intfName2='a4-eth1', params1={'ip':'10.0.0.9/30'}, params2={'ip':'10.0.0.10/30'}, cls=TCLink, delay='10ms')
    net.addLink(a4, a5, intfName1='a4-eth2', intfName2='a5-eth1', params1={'ip':'10.0.0.13/30'}, params2={'ip':'10.0.0.14/30'}, cls=TCLink, delay='10ms')

    # Ground station -> a2 (direct)
    net.addLink(gs1, a2, intfName1='gs1-eth1', intfName2='a2-eth3', params1={'ip':'11.0.0.1/30'}, params2={'ip':'11.0.0.2/30'}, cls=TCLink, delay='100ms')

    

    info("*** Starting network\n")
    net.start()

    info("*** Correcting interface IP addresses\n")
    a1.cmd('ifconfig a1-eth1 10.0.0.1 netmask 255.255.255.252')
    a2.cmd('ifconfig a2-eth1 10.0.0.2 netmask 255.255.255.252')
    a3.cmd('ifconfig a3-eth1 10.0.0.6 netmask 255.255.255.252')
    a4.cmd('ifconfig a4-eth1 10.0.0.10 netmask 255.255.255.252')
    a5.cmd('ifconfig a5-eth1 10.0.0.14 netmask 255.255.255.252')
    gs1.cmd('ifconfig gs1-eth1 11.0.0.1 netmask 255.255.255.252')

    # =================================================================
    info("*** Creating loopback interfaces\n")
    a1.cmd('ifconfig lo 10.0.1.100/24')
    a2.cmd('ifconfig lo 10.0.2.100/24')
    a3.cmd('ifconfig lo 10.0.3.100/24')
    a4.cmd('ifconfig lo 10.0.4.100/24')
    a5.cmd('ifconfig lo 10.0.5.100/24')
    gs1.cmd('ifconfig lo 11.0.1.100/24')

    info("*** Setting up routes\n")

    # Using Mohamed's style
    # default routes for network endpoints
    a1.cmd('route add default gw 10.0.0.2') #a1 - everything else
    a5.cmd('route add default gw 10.0.0.13') #a5 - everything else
    gs1.cmd('route add default gw 11.0.0.2') # gs1 - everything else
    # a2
    a2.cmd('ip route add 10.0.1.0/24 via 10.0.0.1 dev a2-eth1') #a2 - a1
    a2.cmd('ip route add 11.0.1.0/24 via 11.0.0.1 dev a2-eth3') #a2 - gs1
    a2.cmd('ip route add 10.0.3.0/24 via 10.0.0.6 dev a2-eth2') #a2 - a3
    a2.cmd('ip route add 10.0.4.0/24 via 10.0.0.6 dev a2-eth2') #a2 - a4
    a2.cmd('ip route add 10.0.5.0/24 via 10.0.0.6 dev a2-eth2') #a2 - a5
    a2.cmd('ip route add 11.0.1.0/24 via 11.0.0.2 dev a2-eth3') #a2 - gs1
    # a3
    a3.cmd('ip route add 10.0.1.0/24 via 10.0.0.5 dev a3-eth1') #a3 - a1
    a3.cmd('ip route add 10.0.2.0/24 via 10.0.0.5 dev a3-eth1') #a3 - a2
    a3.cmd('ip route add 11.0.1.0/24 via 10.0.0.5 dev a3-eth1') #a3 - gs1
    a3.cmd('ip route add 10.0.4.0/24 via 10.0.0.10 dev a3-eth2') #a3 - a4
    a3.cmd('ip route add 10.0.5.0/24 via 10.0.0.10 dev a3-eth2') #a3 - a5
    # a4
    a4.cmd('ip route add 10.0.1.0/24 via 10.0.0.9 dev a4-eth1') #a4 - a1
    a4.cmd('ip route add 10.0.2.0/24 via 10.0.0.9 dev a4-eth1') #a4 - a2
    a4.cmd('ip route add 10.0.3.0/24 via 10.0.0.9 dev a4-eth1') #a4 - a3
    a4.cmd('ip route add 11.0.1.0/24 via 10.0.0.9 dev a4-eth1') #a4 - gs1
    a4.cmd('ip route add 10.0.5.0/24 via 10.0.0.14 dev a4-eth2') #a4 - a

    info("*** Configuring hosts\n")

    # Set up iptables rule to modify source ip of all packets originating from a satellite to the satellite's lo int ip
    a1.cmd('iptables -t nat -A POSTROUTING -s 10.0.0.1 -j SNAT --to-source 10.0.1.100')
    a2.cmd('iptables -t nat -A POSTROUTING -s 10.0.0.2 -j SNAT --to-source 10.0.2.100')
    a2.cmd('iptables -t nat -A POSTROUTING -s 10.0.0.5 -j SNAT --to-source 10.0.2.100')
    a2.cmd('iptables -t nat -A POSTROUTING -s 11.0.0.2 -j SNAT --to-source 10.0.2.100')
    a3.cmd('iptables -t nat -A POSTROUTING -s 10.0.0.6 -j SNAT --to-source 10.0.3.100')
    a3.cmd('iptables -t nat -A POSTROUTING -s 10.0.0.9 -j SNAT --to-source 10.0.3.100')
    a4.cmd('iptables -t nat -A POSTROUTING -s 10.0.0.10 -j SNAT --to-source 10.0.4.100')
    a4.cmd('iptables -t nat -A POSTROUTING -s 10.0.0.13 -j SNAT --to-source 10.0.4.100')
    a5.cmd('iptables -t nat -A POSTROUTING -s 10.0.0.14 -j SNAT --to-source 10.0.5.100')
    gs1.cmd('iptables -t nat -A POSTROUTING -s 11.0.0.1 -j SNAT --to-source 11.0.1.100')

    info("*** Testing connectivity\n")
    # net.pingAll()

    nodes = [a1, a2, a3, a4, a5, gs1]
    for node in nodes:
        a1.cmdPrint('ping -c1', node.IP())

    # print(a1.cmd('ping a2-eth1 -c3'))

    info("*** Running CLI\n")
    CLI(net)

    info("*** Stopping network")
    net.stop()









if __name__ == '__main__':
    setLogLevel('info')
    topology()
