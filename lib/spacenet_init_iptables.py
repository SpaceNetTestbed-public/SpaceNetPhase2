#spacenet_init_iptables.py
import os
import netifaces


nfqueueList = []

def initialize_ip_tables_and_nfqueue(use_loopback_as_source = False, use_netfilter = False, nfqueue_base_port_num = 55555, nfqueue_admin_queue_num = 1, nfqueue_unknown_queue_num = 99, admin_traffic_callback = None, unknown_traffic_callback = None, verbose = False):
    if use_loopback_as_source:
        ip_tables_loopback_as_source(verbose)
    if use_netfilter:
        import netfilterqueue # don't import this at the top of the file because it may not be installed on all systems
        if admin_traffic_callback:
            ip_tables_netfilter(nfqueue_base_port_num + nfqueue_admin_queue_num, nfqueue_admin_queue_num, verbose)
            init_netfilterqueue(nfqueue_admin_queue_num, admin_traffic_callback, verbose)
        if unknown_traffic_callback:
            ip_tables_netfilter(nfqueue_base_port_num + nfqueue_unknown_queue_num, nfqueue_unknown_queue_num, verbose)
            init_netfilterqueue(nfqueue_unknown_queue_num, unknown_traffic_callback, verbose)

# All IP traffic from interfaces is designated to loopback IP
def ip_tables_loopback_as_source(verbose = False):
    if verbose:
        print("(spacenet_init_iptables.ip_tables_loopback_as_source) Setting up IP tables to use loopback IP as source")
    intf_ip_addresses = {}
    for interface in netifaces.interfaces():
        if 's1_' in interface:
            continue # Skip any management network interfaces
        try:
            intf_ip = netifaces.ifaddresses(interface)[netifaces.AF_INET][0]['addr']
        except:
            continue
        intf_ip_addresses[interface] = intf_ip
    loopback_ip = intf_ip_addresses['lo'].split('/')[0]
    del intf_ip_addresses['lo']
    if verbose:
        print("(spacenet_init_iptables.ip_tables_loopback_as_source) Designating all ip traffic source from interfaces to loopback IP")
    for intf_ip in intf_ip_addresses.values():
        cmdString = f"iptables -t nat -A POSTROUTING -s {intf_ip.split('/')[0]} -j SNAT --to-source {loopback_ip}"
        if verbose:
            print(f"  (spacenet_init_iptables.ip_tables_loopback_as_source) Running command: {cmdString}")
        os.system(cmdString)
    if verbose:
        print("(spacenet_init_iptables.ip_tables_loopback_as_source) Done setting up IP tables")

def ip_tables_netfilter(nfqueue_port_num, nfqueue_num, verbose = False):
    if verbose:
        print(f"(spacenet_init_iptables.ip_tables_netfilter) Setting up netfilter queue for traffic received on port {nfqueue_port_num}")
    netfilter_queue_command = f"iptables -I INPUT -p tcp --dport {nfqueue_port_num} -j NFQUEUE --queue-num {nfqueue_num}"
    if verbose:
        print(f"  (spacenet_init_iptables.ip_tables_netfilter) Running command: {netfilter_queue_command}")
    os.system(netfilter_queue_command)
    if verbose:
        print("(spacenet_init_iptables.ip_tables_netfilter) Done setting up netfilter queue")

def init_netfilterqueue(nfqueue_num, callback_function, verbose = False): # only called if using netfilter queues
    global nfqueueList
    if verbose:
        print(f"(spacenet_init_iptables.init_netfilterqueue) Setting up netfilter queue for traffic received on port {nfqueue_num}")
    nfqueue = netfilterqueue.NetfilterQueue()
    nfqueue.bind(queue_num = nfqueue_num, callback = callback_function, mode = netfilterqueue.COPY_PACKET)
    nfqueue.run(block = False)
    nfqueueList.append(nfqueue)
    if verbose:
        print("(spacenet_init_iptables.init_netfilterqueue) Done setting up netfilter queue")

def stop_netfilterqueues(verbose = False):
    global nfqueueList
    if verbose:
        print("(spacenet_init_iptables.stop_netfilterqueues) Shutting down netfilter queues")
    for nfqueue in nfqueueList:
        nfqueue.unbind()
    nfqueueList = []
    if verbose:
        print("(spacenet_init_iptables.stop_netfilterqueues) Done shutting down netfilter queues")

