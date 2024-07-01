from mininet.net import Mininet
from mininet.node import Controller
from mininet.cli import CLI
from mininet.log import setLogLevel, info

def topology():
    "Create a network."
    net = Mininet(controller=Controller)

    info("*** Creating nodes\n")
    a1 = net.addHost('a1', ip='10.0.1.1/24')
    a2 = net.addHost('a2', ip='10.0.2.1/24')
    a3 = net.addHost('a3', ip='10.0.3.1/24')
    a4 = net.addHost('a4', ip='10.0.4.1/24')  # New host

    info("*** Creating links\n")
    net.addLink(a1, a2)
    net.addLink(a2, a3)
    net.addLink(a3, a4)  # New link

    info("*** Starting network\n")
    net.start()

    info("*** Configuring a2, a3\n")
    a1.cmd('ifconfig a1-eth1 10.0.1.1/24')

    a2.cmd('ifconfig a2-eth0 10.0.1.2/24')
    a2.cmd('ifconfig a2-eth1 10.0.2.1/24')
    a2.cmd('sysctl -w net.ipv4.ip_forward=1')

    a3.cmd('ifconfig a3-eth0 10.0.2.2/24')
    a3.cmd('ifconfig a3-eth1 10.0.4.2/24')
    a3.cmd('sysctl -w net.ipv4.ip_forward=1')

    info("*** Setting up routes\n")
    a1.cmd('route add -net 10.0.2.0 netmask 255.255.255.0 gw 10.0.1.2')
    a1.cmd('route add -net 10.0.4.0 netmask 255.255.255.0 gw 10.0.1.2')

    a2.cmd('route add -net 10.0.4.0 netmask 255.255.255.0 gw 10.0.2.2')

    a3.cmd('route add -net 10.0.1.0 netmask 255.255.255.0 gw 10.0.2.1')

    a4.cmd('route add -net 10.0.2.0 netmask 255.255.255.0 gw 10.0.4.2')
    a4.cmd('route add -net 10.0.1.0 netmask 255.255.255.0 gw 10.0.4.2')

    info("*** Running CLI\n")
    CLI(net)

    info("*** Stopping network")
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    topology()