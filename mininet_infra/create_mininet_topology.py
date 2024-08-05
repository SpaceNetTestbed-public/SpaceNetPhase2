from mininet.net import Mininet
from mininet.node import Node, OVSKernelSwitch, Controller, RemoteController
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.link import *
from mininet.topo import Topo
from mininet.log import setLogLevel, info
from mininet.node import OVSController
import socket
import time
import subprocess
import threading
import queue
import os
import math
from multiprocessing import Process, Manager, Pool
import sys

sys.path.append("../routing")
from routing.constellation_routing import *

net_queue = queue.Queue()
cnt_queue = queue.Queue()

def apply_updates_thread(net, updates):
    for update in updates:
        update_routes = update.split(",")       #sat1539,ip route del 10.2.2.112 via 10.2.6.130/28 dev sat1539-eth4
        sat_node = net.getNodeByName(update_routes[0])
        sat_node.cmd(update_routes[1].strip()+" &")

def static_routes_batch_worker(args):
    (
        routes_chunk,
        links,
        list_of_Intf_IPs,
        satellites_by_index
    ) = args


    commands = ""
    commands_list = []
    for route in routes_chunk:
        parameters = get_static_route_parameter_optimised(route, links, list_of_Intf_IPs, satellites_by_index)
        if len(parameters) > 0:
            commands = str(parameters[0])+" ip route add "+str(parameters[1])+" via "+str(parameters[2].split("/")[0])+" dev "+str(parameters[3])+" & \n"+str(parameters[4])+" ip route add "+str(parameters[5])+" via "+str(parameters[6].split("/")[0])+" dev "+str(parameters[7])+" & \n"
            commands_list.append(commands)

    return commands_list

class LinuxRouter( Node ):	# from the Mininet library
    "A Node with IP forwarding enabled."

    def config( self, **params ):
        super( LinuxRouter, self).config( **params )
        # Enable forwarding on the router
        info ('enabling forwarding on ', self)
        self.cmd( 'sysctl net.ipv4.ip_forward=1' )

    def terminate( self ):
        self.cmd( 'sysctl net.ipv4.ip_forward=0' )
        super( LinuxRouter, self ).terminate()


class sat_network(Topo):
    def __init__(self, **kwargs):
        super(sat_network, self).__init__(**kwargs)

    def rp_disable(self, host):
    	ifaces = host.cmd('ls /proc/sys/net/ipv4/conf')
    	ifacelist = ifaces.split()    # default is to split on whitespace
    	for iface in ifacelist:
            if iface != 'lo':
                host.cmd('sysctl net.ipv4.conf.' + iface + '.rp_filter=0')

    def set_default_gw_gs(self, net, gs_list):
        for gs in gs_list:
            ground_station = net.getNodeByName(gs)
            print(ground_station.IP())


    def create_sat_network(self, satellites, ground_stations, connectivity_matrix, link_throughput, link_latency, Tmode, physical_gs_index, physical_sats_index, border_gateway):
        sat_list = []
        gs_list  = []
        links    = []
        mgnt_intf = []
        cnt_ip = 0

        #self.addController('c1')
        sat_intf_count = [0 for i in range(len(satellites))] #that should be 1s if we are adding management interface, 0s otherwise
        gs_intf_count = [0 for i in range(len(ground_stations))] #that should be 1s if we are adding management interface, 0s otherwise
        s1 = self.addSwitch('s1')


        # create satellites node and management interfaces to Mininet Switch
        for i in range(0, len(satellites)):
            ip_control_intf_oct3 = (i+5)/254
            ip_control_intf_oct4 = (i+5)%254
            if i in physical_sats_index:
                print("configure the physical satellite ", str(i), " with the following ip addresses ", "172.16.", str(ip_control_intf_oct3),".",str(ip_control_intf_oct4),"/16")
                sat_name = "sat"+str(i)
                sat_list.append(sat_name)

            if i not in physical_sats_index:
                sat_name = self.addHost('sat'+str(i), cls=LinuxRouter)
                # sat_name = self.addHost('sat'+str(i), cls=LinuxRouter, ip="172.16."+str(ip_control_intf_oct3)+"."+str(ip_control_intf_oct4)+"/16")
                # self.addLink(sat_name, s1, cls=TCLink)
                # mgnt_intf.append({"node":'sat'+str(i), "mgnt_ip": "172.16."+str(ip_control_intf_oct3)+"."+str(ip_control_intf_oct4)})
                sat_list.append(sat_name)

            cnt_ip = i

        # create ground-stations node
        for i in range(0, len(ground_stations)):
            ip_control_intf_oct3 = (i+5+len(satellites))/254
            ip_control_intf_oct4 = (i+5+len(satellites))%254

            if i in physical_gs_index:
                print("configure the physical ground station ", str(i), " with the following ip addresses ", "172.16.", str(ip_control_intf_oct3),".",str(ip_control_intf_oct4),"/16")
                gs_name = "gs"+str(i)
                gs_list.append(gs_name)

            if i not in physical_gs_index:
                gs_name = self.addHost('gs'+str(i))
                if 'gs'+str(i) == border_gateway:
                    gs_name = self.addHost('gs'+str(i))
                    self.addLink(gs_name, s1, cls=TCLink)
                    # gs_name.cmd('dhclient '+gs_name.defaultIntf().name)
                    gs_intf_count[i] += 1
                # mgnt_intf.append({"node":'gs'+str(i), "mgnt_ip": "172.16."+str(ip_control_intf_oct3)+"."+str(ip_control_intf_oct4)})
                gs_list.append(gs_name)

            # gs_name = self.addHost('gs'+str(i))
            # gs_list.append(gs_name)

        # connectivity_matrix_temp = connectivity_matrix[:]
        connectivity_matrix_temp = [row[:] for row in connectivity_matrix]
        for i in range(0,len(connectivity_matrix_temp)):
            for j in range(0, len(connectivity_matrix_temp[i])):

                # Add the ISL links
                if i < len(satellites) and j < len(satellites) and connectivity_matrix_temp[i][j] == 1:
                    if i not in physical_sats_index and j not in physical_sats_index:
                        lt = link_latency[i][j]
                        # print lt#delay=str(lt)+'ms'
                        self.addLink(sat_list[i], sat_list[j], intfname1 = 'sat'+str(i)+'-eth'+str(sat_intf_count[i]), inftname2 = 'sat'+str(j)+'-eth'+str(sat_intf_count[j]), cls=TCLink, delay=str(0.005)+'ms', bw=link_throughput[i][j])
                        links.append('sat'+str(i)+'-eth'+str(sat_intf_count[i])+":"+'sat'+str(j)+'-eth'+str(sat_intf_count[j]))
                        # print 'sat'+str(i)+'-eth'+str(sat_intf_count[i])+":"+'sat'+str(j)+'-eth'+str(sat_intf_count[j])

                    if i in physical_sats_index and j not in physical_sats_index:
                        self.addLink(sat_list[j], s1, cls=TCLink, delay=str(link_latency[i][j])+'ms', bw=link_throughput[i][j])
                        print("... Configure the switch to allow the bidirectional traffic between physical satellite "+str(i)+" and the virtual satellite "+str(j))

                    if i not in physical_sats_index and j in physical_sats_index:
                        self.addLink(sat_list[i], s1, cls=TCLink, delay=str(link_latency[i][j])+'ms', bw=link_throughput[i][j])
                        print("... Configure the switch to allow the bidirectional traffic between physical satellite "+str(j)+" and the virtual satellite "+str(i))

                    connectivity_matrix_temp[i][j] = 0
                    connectivity_matrix_temp[j][i] = 0

                    sat_intf_count[i] = sat_intf_count[i] + 1
                    sat_intf_count[j] = sat_intf_count[j] + 1


                # Add the GSL links
                if i < len(satellites) and j >= len(satellites) and connectivity_matrix_temp[i][j] == 1:
                    gid = j - len(satellites)

                    if i not in physical_sats_index and gid not in physical_gs_index:
                        lt = link_latency[i][j]/8.0
                        # print lt #delay=str(lt)+'ms',
                        self.addLink(sat_list[i], gs_list[gid], intfname1 = 'sat'+str(i)+'-eth'+str(sat_intf_count[i]), inftname2 = 'gs'+str(gid)+'-eth'+str(gs_intf_count[gid]), cls=TCLink, delay=str(lt)+'ms', bw=link_throughput[i][j])
                        links.append('sat'+str(i)+'-eth'+str(sat_intf_count[i])+":"+ 'gs'+str(gid)+'-eth'+str(gs_intf_count[gid]))

                        connectivity_matrix_temp[i][j] = 0
                        connectivity_matrix_temp[j][i] = 0
                        sat_intf_count[i] = sat_intf_count[i] + 1
                        gs_intf_count[gid] = gs_intf_count[gid] + 1

                    if i not in physical_sats_index and gid in physical_gs_index:
                        self.addLink(sat_list[i], s1, cls=TCLink, delay=str(link_latency[i][j])+'ms', bw=link_throughput[i][j])
                        print("... Configure the switch to allow the bidirectional traffic between virtual satellite "+str(i)+" and the physical ground station "+str(j)+" or .. ", str(gid))

                        connectivity_matrix_temp[i][j] = 0
                        connectivity_matrix_temp[j][i] = 0
                        sat_intf_count[i] = sat_intf_count[i] + 1

                    if i in physical_sats_index and gid in physical_gs_index:
                        print("... Configure the switch to allow the bidirectional traffic between physcial satellite "+str(i)+" and the physical ground station "+str(j)+" or .. ", str(gid))

        return {
        	"sat_list": sat_list,  #This list has only the virtual satellites not the physical
        	"gs_list": gs_list,    #This list has only the virtual ground stations not the physical
            "isl_gls_links": links,
            "intf_count_sats": sat_intf_count,
            "management_interface": mgnt_intf
    	}

    def get_network_address(self, str_ip_address):
        # Assuming /28 subnet mask
        ip_oct1, ip_oct2, ip_oct3, ip_oct4 = str_ip_address.split(".")
        net_add1= int(ip_oct1) & 255
        net_add2= int(ip_oct2) & 255
        net_add3= int(ip_oct3) & 255
        net_add4= int(ip_oct4) & 240

        return str(net_add1)+"."+str(net_add2)+"."+str(net_add3)+"."+str(net_add4)

    def configure_initial_static_route(self, net, route, num_of_satellites, num_of_ground_stations, cmds_list):
        if len(route) > 2:
            src_node, next_hop_node, dest_node, last_hop_node = route[0], route[1], route[len(route)-1], route[len(route)-2]

            src_node_prefix  = "gs" if src_node >= num_of_satellites else "sat"
            dest_node_prefix = "gs" if dest_node >= num_of_satellites else "sat"

            src_node_m      = net.getNodeByName(src_node_prefix+str(src_node%num_of_satellites))
            next_hop_node_m = net.getNodeByName("sat"+str(next_hop_node%num_of_satellites))
            first_hop_link  = net.linksBetween(src_node_m, next_hop_node_m)[0]

            dest_node_m     = net.getNodeByName(dest_node_prefix+str(dest_node%num_of_satellites))
            last_hop_node_m = net.getNodeByName("sat"+str(last_hop_node%num_of_satellites))
            last_hop_link   = net.linksBetween(last_hop_node_m, dest_node_m)[0]

            src_dev, src_via = (str(first_hop_link.intf1), str(first_hop_link.intf2.IP())) if str(src_node_m.name) in str(first_hop_link.intf1) else (str(first_hop_link.intf2), str(first_hop_link.intf1.IP()))
            dest_dev, dest_via = (str(last_hop_link.intf2), str(last_hop_link.intf1.IP())) if str(dest_node_m.name) in str(last_hop_link.intf2) else (str(last_hop_link.intf1), str(last_hop_link.intf2.IP()))

            cmd_on_src_node     = "ip route add "+ self.get_network_address(last_hop_link.intf1.IP())+"/28 via "+src_via+" dev "+src_dev+" & "
            cmd_on_dest_node    = "ip route add "+ self.get_network_address(first_hop_link.intf1.IP())+"/28 via "+dest_via+" dev "+dest_dev+" & "

            src_node_m.cmd(cmd_on_src_node)
            dest_node_m.cmd(cmd_on_dest_node)
            # print cmd_on_src_node
            # print cmd_on_dest_node

            # cmds_list[src_node].append(cmd_on_src_node)
            # cmds_list[dest_node].append(cmd_on_dest_node)

        else:
            print("No need to configure static route")

        # return cmds_list

    def get_topology_links(self, net):
        links = []
        nodes = net.hosts
        for node in nodes:
            for intf in node.intfList():
                current_link = intf.link
                if current_link:
                    intf1, intf2        = current_link.intf1, current_link.intf2
                    intf1_ip, intf2_ip  = current_link.intf1.IP(), current_link.intf2.IP()

                    print("Interface 1: ", str(intf1), "( "+str(intf1_ip)+" )")
                    print("Interface 2: ", str(intf2), "( "+str(intf2_ip)+" )")

                    link_name = str(intf1)+":"+str(intf2)
                    links.append(link_name)
        return links

    def run_static_update_commands(self, net, cmds_list, num_of_satellites):
        for i in range(len(cmds_list)):
            node_prefix  = "gs" if i >= num_of_satellites else "sat"
            node_m      = net.getNodeByName(node_prefix+str(i%num_of_satellites))
            all_cmds_per_node = ""
            for cmd in cmds_list[i]:
                all_cmds_per_node += cmd + " && "

            node_m.cmd(all_cmds_per_node)

    def initial_ipv4_assignment_for_interfaces(self, data_path, net, addresses_pool, addresses_pool_physical):
        list_of_Intf_IPs = []
        nodes = net.hosts
        for node in nodes:
            for intf in node.intfList():
                # if "eth0" not in intf.name:
                if intf.link:
                    intf1, intf2 = intf.link.intf1, intf.link.intf2
                    if "s1" != str(intf1).split("-")[0] and "s1" != str(intf2).split("-")[0]:
                        network_address = self.get_free_IP(addresses_pool)
                        if network_address != -1:
                            oct1, oct2, oct3, oct4 = network_address.split('.');
                            intf1.setIP(oct1+"."+oct2+"."+oct3+"."+str(int(oct4)+1)+"/28")
                            intf2.setIP(oct1+"."+oct2+"."+oct3+"."+str(int(oct4)+2)+"/28")
                            #print "-- Set IP address for "+str(intf1)+" : "+str(oct1)+"."+str(oct2)+"."+str(oct3)+"."+str(int(oct4)+1)+"/28"
                            #print "-- Set IP address for "+str(intf2)+" : "+str(oct1)+"."+str(oct2)+"."+str(oct3)+"."+str(int(oct4)+2)+"/28"
                            # Assign the default gw to the ground stations
                            if "gs" in node.name:
                                debug("route add default gw "+str(intf1.IP())+" dev "+node.name+"-eth0", intf2.IP())
                                # print "route add default gw "+str(intf.link.intf1.IP())+" dev "+node.name+"-eth1", intf.link.intf2.IP()
                                node.cmd("route add default gw "+str(intf1.IP())+" dev "+node.name+"-eth0");
                        else:
                            print("[Create Sat Network -- GSL] No Available IPs to assign")
                            exit()
                    if "s1" == str(intf1).split("-")[0] or "s1" == str(intf2).split("-")[0]:
                        ip_address = self.get_free_IP(addresses_pool_physical)
                        if ip_address != -1:
                            if "s1" != str(intf1).split("-")[0]:
                                oct1, oct2, oct3, oct4 = ip_address.split('.');
                                intf1.setIP(oct1+"."+oct2+"."+oct3+"."+oct4+"/24")
                                print("-- Set IP address for "+str(intf1)+" : "+str(oct1)+"."+str(oct2)+"."+str(oct3)+"."+str(oct4)+"/24")
                            elif "s1" != str(intf2).split("-")[0]:
                                oct1, oct2, oct3, oct4 = ip_address.split('.');
                                intf2.setIP(oct1+"."+oct2+"."+oct3+"."+oct4+"/24")
                                print("-- Set IP address for "+str(intf2)+" : "+str(oct1)+"."+str(oct2)+"."+str(oct3)+"."+str(oct4)+"/24")

                        else:
                            print("[Create Sat Network -- GSL] No Available IPs to assign")
                            exit()

            self.rp_disable(node)

        with open(data_path+'/constellation_ip_assignment.txt', 'w') as f:
            for node in nodes:
                for intf in node.intfList():
                    if intf.link:
                        intf1, intf2 = intf.link.intf1, intf.link.intf2
                        write_toFile = str(intf1)+"\t"+str(intf1.IP())+"\n"+str(intf2)+"\t"+str(intf2.IP())+"\n"
                        f.write(write_toFile)
                        list_of_Intf_IPs.append({"Interface": str(intf1), "IP": str(intf1.IP())+"/28"})
                        list_of_Intf_IPs.append({"Interface": str(intf2), "IP": str(intf2.IP())+"/28"})

                        if "gs" in str(intf1) and "eth0" in str(intf1):
                            print("route add default gw "+str(intf2.IP())+" dev "+str(intf1)+"---"+str(intf1).split("-")[0])
                            gsNode = net.getNodeByName(str(intf1).split("-")[0])
                            gsNode.cmd("route add default gw "+str(intf2.IP())+" dev "+str(intf1));

                        if "gs" in str(intf2) and "eth0" in str(intf2):
                            print("route add default gw "+str(intf1.IP())+" dev "+str(intf2)+"----"+str(intf2).split("-")[0])
                            gsNode = net.getNodeByName(str(intf2).split("-")[0])
                            gsNode.cmd("route add default gw "+str(intf1.IP())+" dev "+str(intf2));

        return list_of_Intf_IPs

    def initial_ipv4_assignment_for_interfaces_optimised(self, data_path, net, addresses_pool, addresses_pool_physical, border_gateway):
        list_of_Intf_IPs = {}
        nodes = net.hosts
        for node in nodes:
            for intf in node.intfList():
                # if "eth0" not in intf.name:
                if intf.link:
                    intf1, intf2 = intf.link.intf1, intf.link.intf2
                    if "s1" != str(intf1).split("-")[0] and "s1" != str(intf2).split("-")[0]:
                        network_address = self.get_free_IP(addresses_pool)
                        if network_address != -1:
                            oct1, oct2, oct3, oct4 = network_address.split('.');
                            intf1.setIP(oct1+"."+oct2+"."+oct3+"."+str(int(oct4)+1)+"/28")
                            intf2.setIP(oct1+"."+oct2+"."+oct3+"."+str(int(oct4)+2)+"/28")
                            #print "-- Set IP address for "+str(intf1)+" : "+str(oct1)+"."+str(oct2)+"."+str(oct3)+"."+str(int(oct4)+1)+"/28"
                            #print "-- Set IP address for "+str(intf2)+" : "+str(oct1)+"."+str(oct2)+"."+str(oct3)+"."+str(int(oct4)+2)+"/28"
                            # Assign the default gw to the ground stations
                            if "gs" in node.name:
                                if node.name != border_gateway:
                                    debug("route add default gw "+str(intf1.IP())+" dev "+node.name+"-eth0", intf2.IP())
                                    # print "route add default gw "+str(intf.link.intf1.IP())+" dev "+node.name+"-eth1", intf.link.intf2.IP()
                                    node.cmd("route add default gw "+str(intf1.IP())+" dev "+node.name+"-eth0");
                                else:
                                    debug("route add default gw "+str(intf1.IP())+" dev "+node.name+"-eth1", intf2.IP())
                                    node.cmd("dhclient "+node.defaultIntf().name)
                                    node.cmd("route add default gw "+str(intf1.IP())+" dev "+node.name+"-eth1");
                        else:
                            print("[Create Sat Network -- GSL] No Available IPs to assign")
                            exit()
                    # if "s1" == str(intf1).split("-")[0] or "s1" == str(intf2).split("-")[0]:
                    #     ip_address = self.get_free_IP(addresses_pool_physical)
                    #     if ip_address != -1:
                    #         if "s1" != str(intf1).split("-")[0]:
                    #             oct1, oct2, oct3, oct4 = ip_address.split('.');
                    #             intf1.setIP(oct1+"."+oct2+"."+oct3+"."+oct4+"/24")
                    #             print "-- Set IP address for "+str(intf1)+" : "+str(oct1)+"."+str(oct2)+"."+str(oct3)+"."+str(oct4)+"/24"
                    #         elif "s1" != str(intf2).split("-")[0]:
                    #             oct1, oct2, oct3, oct4 = ip_address.split('.');
                    #             intf2.setIP(oct1+"."+oct2+"."+oct3+"."+oct4+"/24")
                    #             print "-- Set IP address for "+str(intf2)+" : "+str(oct1)+"."+str(oct2)+"."+str(oct3)+"."+str(oct4)+"/24"
                    #
                    #     else:
                    #         print "[Create Sat Network -- GSL] No Available IPs to assign"
                    #         exit()

            self.rp_disable(node)

        with open(data_path+'/constellation_ip_assignment.txt', 'w') as f:
            for node in nodes:
                for intf in node.intfList():
                    if intf.link:
                        intf1, intf2 = intf.link.intf1, intf.link.intf2
                        write_toFile = str(intf1)+"\t"+str(intf1.IP())+"\n"+str(intf2)+"\t"+str(intf2.IP())+"\n"
                        f.write(write_toFile)
                        list_of_Intf_IPs[str(intf1)] = []
                        list_of_Intf_IPs[str(intf1)].append(str(intf1.IP())+"/28")
                        list_of_Intf_IPs[str(intf2)] = []
                        list_of_Intf_IPs[str(intf2)].append(str(intf2.IP())+"/28")

                        if "gs" in str(intf1) and "eth0" in str(intf1):
                            #print "route add default gw "+str(intf2.IP())+" dev "+str(intf1)+"---"+str(intf1).split("-")[0]
                            gsNode = net.getNodeByName(str(intf1).split("-")[0])
                            gsNode.cmd("route add default gw "+str(intf2.IP())+" dev "+str(intf1));

                        if "gs" in str(intf2) and "eth0" in str(intf2):
                            #print "route add default gw "+str(intf1.IP())+" dev "+str(intf2)+"----"+str(intf2).split("-")[0]
                            gsNode = net.getNodeByName(str(intf2).split("-")[0])
                            gsNode.cmd("route add default gw "+str(intf1.IP())+" dev "+str(intf2));


        return list_of_Intf_IPs

    def get_free_IP(self, pool):
        free_ip = -1
        for i in pool:
            if i[0] == 1:
                free_ip = i[1]
                pool.remove(i)
                break;
        return free_ip

    def get_management_ip(self, all_mgnt_ips, node):
        for interface in all_mgnt_ips:
            if interface["node"] == node:
                return interface["mgnt_ip"]

    def run_topology_commands(self, net, command, node1, node2):
        net_node1 = net.getNodeByName(node1)
        net_node2 = net.getNodeByName(node2)

        if command == "deleteLink":
            if net.linksBetween(net_node1, net_node2):
                net.delLinkBetween(net_node1, net_node2)

        if command == "addLink":
            net_node1.cmd("ifconfig")
            net_node2.cmd("ifconfig")
            net.addLink(net_node1, net_node2, cls=TCLink)

    def handle_topology_updates_commands(self, net):
        UDPSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        UDPSocket.bind(("", 20001))
        print("Mininet main listener is created ... ")
        while(True):
            bytesAddressPair = UDPSocket.recvfrom(1024)
            recv_msg = updateTopologyMsg.c_m_update_topology()
            recv_msg.ParseFromString(bytesAddressPair[0])
            self.run_topology_commands(net, recv_msg.command, recv_msg.node1_name, recv_msg.node2_name)
            # t = threading.Thread(target=self.run_topology_commands, args=(net, recv_msg.command, recv_msg.node1_name, recv_msg.node2_name))
            # t.start()

    def startListener(self, net, satellites, ground_stations, intfs):
        for i in range(len(satellites)):
            sat_node = net.getNodeByName("sat"+str(i))
            node_m_ip = self.get_management_ip(intfs, "sat"+str(i)).strip()
            print(("added .....,"+node_m_ip))
            sat_node.cmd("python ../comm_protocol/satellite_agent.py "+node_m_ip+ " &")

        for i in range(len(ground_stations)):
            gs_node = net.getNodeByName("gs"+str(i))
            node_m_ip = self.get_management_ip(intfs, "gs"+str(i)).strip()
            gs_node.cmd("python ../comm_protocol/satellite_agent.py "+node_m_ip+ " &")

        mininet_topology_listner = threading.Thread(target=self.handle_topology_updates_commands, args=(net,))
        mininet_topology_listner.start()

    def startworker(self, net, satellites, ground_stations, intfs):
        for i in range(len(satellites)):
            sat_node = net.getNodeByName("sat"+str(i))
            node_m_ip = self.get_management_ip(intfs, "sat"+str(i)).strip()
            print(("added .....,"+"sat"+str(i)+" -- "+node_m_ip))
            sat_node.cmd("python ../comm_protocol/satellite_worker.py "+node_m_ip+ " &")

    def create_static_routes_batch_parallel(self, routes, links, list_of_Intf_IPs, satellites_by_index, number_of_cores):
        step = len(routes)//number_of_cores
        routes_chunks = [routes[x:x+step] for x in range(0, len(routes), step)]

        static_routing_batch_args = []

        for chunk in routes_chunks:
            static_routing_batch_args.append((chunk, links, list_of_Intf_IPs, satellites_by_index))

        pool = Pool(number_of_cores)
        static_routes_b_chunks = pool.map(static_routes_batch_worker, static_routing_batch_args)
        pool.close()
        pool.join()

        return static_routes_b_chunks

    def create_static_routes_batch(self, routes, links, list_of_Intf_IPs, satellites_by_index):
        commands = ""
        for route in routes:
            # print route
            start = round(time.time()*1000)
            parameters = get_static_route_parameter(route, links, list_of_Intf_IPs, satellites_by_index)
            # print parameters
            if len(parameters) > 0:
                commands += str(parameters[0])+" ip route add "+str(parameters[1])+" via "+str(parameters[2])+" dev "+str(parameters[3])+" & \n"+str(parameters[4])+" ip route add "+str(parameters[5])+" via "+str(parameters[6])+" dev "+str(parameters[7])+" & \n"

            end = round(time.time()*1000)
            print("------ gen ", end-start, "ms ")

        logg = open('linit-9wi.txt', 'a')
        logg.write(commands)
        logg.close()

    def startRoutingConfig(self, net, satellites, ground_stations, intfs):
        patch_size = 10.0
        intervals = int(math.ceil(len(satellites)/float(patch_size)))
        print(intervals)
        remaining_sats = len(satellites)
        for v in range(intervals):
            start = int(v*patch_size)
            end = int((v+1)*patch_size) if remaining_sats>=patch_size else len(satellites)
            remaining_sats -= patch_size
            print("Run satellites from sat", start, " to sat", end, " The remaining sats = ", remaining_sats)
            for i in range(start, end, 1):
                sat_node = net.getNodeByName("sat"+str(i))
                # print("Start routing config for .....,"+"sat"+str(i))
                sat_node.cmd("python ../comm_protocol/config_initial_routes.py "+"sat"+str(i)+" &")
                # sat_node.cmd("python ../comm_protocol/config_gs_sat_table.py "+"sat"+str(i)+" &")

            time.sleep(30)
            for i in range(start, end, 1):
                sat_node.cmd("pkill -f 'python ../comm_protocol/config_initial_routes.py sat"+str(i)+"'")

    def updateRoutingTables_timer(self, updateTime, data_path, net, updates_files_name, num_of_satellites, stepCnt):
        while True:
            print(time.ctime(), stepCnt)
            updateThr = threading.Thread(target=self.updateRoutingTables, args=(data_path, net, updates_files_name, stepCnt, num_of_satellites))
            updateThr.start()
            time.sleep(updateTime)
            updateThr.join()
            net_new = net_queue.get()
            new_cnt = cnt_queue.get()
            net = net_new
            stepCnt = new_cnt

    def updateRoutingTables(self, data_path, net, updates_files_name, stepCnt, num_of_satellites):
        filename = data_path+"/allchanges_log_"+str(updates_files_name[stepCnt])
        updatefile = open(filename, 'r')
        updates = updatefile.readlines()

        if len(updates) < 1:
            return

        for update in updates:
            update_links = update.split(",")       #330,1575,0,1
            # print update_links
            node1 = "sat"+str(update_links[0]) if int(update_links[0]) < num_of_satellites else "gs"+str(int(update_links[0])%num_of_satellites)
            node2 = "sat"+str(update_links[1]) if int(update_links[1]) < num_of_satellites else "gs"+str(int(update_links[1])%num_of_satellites)
            # print node1, node2
            net_node1 = net.getNodeByName(node1)
            net_node2 = net.getNodeByName(node2)

            if update_links[2] == 1 and update_links[3].strip() == 0:
                if net.linksBetween(net_node1, net_node2):
                    net.delLinkBetween(net_node1, net_node2)

        for update in updates:
            update_links = update.split(",")       #330,1575,0,1
            node1 = "sat"+str(update_links[0]) if int(update_links[0]) < num_of_satellites else "gs"+str(int(update_links[0])%num_of_satellites)
            node2 = "sat"+str(update_links[1]) if int(update_links[1]) < num_of_satellites else "gs"+str(int(update_links[1])%num_of_satellites)
            net_node1 = net.getNodeByName(node1)
            net_node2 = net.getNodeByName(node2)
            # print node1, node2
            if update_links[2] == 0 and update_links[3].strip() == 1:
                net.addLink(net_node1, net_node2, cls=TCLink)


        start = round(time.time()*1000)
        filename = data_path+"/routing_updates_"+str(updates_files_name[stepCnt])
        updatefile = open(filename, 'r')
        routes_updates = updatefile.readlines()
        end = round(time.time()*1000)
        print(" Deploy the IP Route commands for whole constellation took -----", end-start, "ms ")

        # thread_list = []
        # start = round(time.time()*1000)
        # num_thread = 100;
        # sublist_len = len(routes_updates)/num_thread
        # for i in range(0, len(routes_updates), sublist_len):
        #     subroutes = routes_updates[i:i+sublist_len]
        #     thread = threading.Thread(target=apply_updates_thread, args=(net, subroutes))
        #     thread_list.append(thread)
        #
        # for thread in thread_list:
        #     thread.start()
        # for thread in thread_list:
        #     thread.join()
        #
        # end = round(time.time()*1000)
        # print " Deploy the IP Route commands for whole constellation took ->>>----", end-start, "ms "

        start = round(time.time()*1000)
        # for update in routes_updates:
            # update_routes = update.split(",")       #sat1539,ip route del 10.2.2.112 via 10.2.6.130/28 dev sat1539-eth4
            # print update_routes
        for i in range(0, num_of_satellites):
            start = round(time.time()*1000)
            sat_node = net.getNodeByName("sat"+str(i))
            sat_node.cmd("./"+data_path+"/temFiles_u/sat"+str(i)+"_routes.sh &")
            # sat_node.cmd(update_routes[1].strip()+" &")

            end = round(time.time()*1000)
            print(" Deploy the IP Route commands for whole constellation took ->>>----", end-start, "ms ")

        stepCnt+=1
        net_queue.put(net)
        cnt_queue.put(stepCnt)

    def startRoutingConfigV2(self, data_path, net, satellites, ground_stations, intfs):
        counter = 1
        patch_counter = 10
        for i in range(0, len(satellites)):
            sat_node = net.getNodeByName("sat"+str(i))
            sat_node.cmd("chmod +x "+data_path+"/cmd_files/sat"+str(i)+"_routes.sh && ./"+data_path+"/cmd_files/sat"+str(i)+"_routes.sh &")
            patch_counter -= 1
            if patch_counter == 0:
                time.sleep(8)
                patch_counter = 10
            if i%100 == 0:
                print(".......... Configure the routing tables of satellites", i, "-", (counter*100))
                counter+=1

        time.sleep(60)
        print(".......... Delete all bash processes now")
        for i in range(0, len(satellites)):
            sat_node = net.getNodeByName("sat"+str(i))
            pkill_command = "pkill -f "+"*_routes.sh"
            sat_node.cmd(pkill_command)

            # sat_node.cmd("python ../comm_protocol/config_gs_sat_table.py "+"sat"+str(i)+" &")

    def find_orbits(self, satname):
        absolute_path = "/home/mininet/simulator/SimLEO_MConstellations/results/starlink/"
        orbits_sats = open(absolute_path+'orbits_satellites.txt', 'r')
        Lines_orbits_sats = orbits_sats.readlines()

        for line in Lines_orbits_sats:
            satinfo = line.split("\t")
            if "sat"+str(satinfo[1].strip()) == satname:
                return satinfo[0]

        return -1

    def get_gw_sat_ip(self, satname, gw):
        absolute_path = "/home/mininet/simulator/SimLEO_MConstellations/results/starlink/"
        ip_files = open(absolute_path+'constellation_ip_assignment.txt', 'r')
        Lines = ip_files.readlines()

        links_file = open(absolute_path+'links.txt', 'r')
        Lines_links = links_file.readlines()

        interface_gw  = ""
        for line in Lines_links:
            two_endpoints = line.split(":")
            # print two_endpoints
            if (satname+str("-") in two_endpoints[0].strip() and gw+str("-") in two_endpoints[1].strip()):
                interface_gw = two_endpoints[1].strip()
            elif (satname+str("-") in two_endpoints[1].strip() and gw+str("-") in two_endpoints[0].strip()):
                interface_gw = two_endpoints[0].strip()

        for line in Lines:
            sat_interface = line.split("\t")
            if interface_gw == str(sat_interface[0]):
                interface_ip = sat_interface[1].strip()
                return interface_ip


    def startRoutingOSPF(self, data_path, net, satellites):
        for i in range(0, len(satellites)):
            sat_node = net.getNodeByName("sat"+str(i))
            sat_node.cmd("/usr/sbin/zebra -f /home/mininet/simulator/SimLEO_MConstellations/results/starlink/ospf_config/zebra-%s.conf -d -i /tmp/zebra-%s.pid > /home/mininet/simulator/SimLEO_MConstellations/results/starlink/logs/%s-zebra-stdout 2>&1" % (sat_node.name, sat_node.name, sat_node.name))
            sat_node.waitOutput()
            sat_node.cmd("/usr/sbin/ospfd -f /home/mininet/simulator/SimLEO_MConstellations/results/starlink/ospf_config/ospf-%s.conf -d -i /tmp/ospfd-%s.pid > /home/mininet/simulator/SimLEO_MConstellations/results/starlink/logs/%s-ospfd-stdout 2>&1" % (sat_node.name, sat_node.name, sat_node.name), shell=True)
            sat_node.waitOutput()
            print(sat_node.name)

        # areas_0 = [0, 27, 52, 65, 101, 120, 129, 164, 167, 195, 210, 225, 247, 274, 301, 307, 335, 352, 395, 410, 421, 452, 469, 483, 511, 537, 554, 563, 584, 616, 632, 651, 665, 697, 716, 719, 746, 772, 799, 800, 821, 857, 862, 888, 900, 930, 942, 970, 980, 1000, 1026, 1040, 1060, 1081, 1103, 1123, 1159, 1173, 1205, 1227, 1241, 1268, 1276, 1301, 1315, 1353, 1360, 1386, 1415, 1439, 1454, 1481]
        # for i in range(0, len(satellites)):
        #     sat_gw = ""
        #     sat_node = net.getNodeByName("sat"+str(i))
        #     current_orbit = self.find_orbits(sat_node.name)
        #     for val in range(len(areas_0)):
        #         # print "sat"+str(areas_0[val])
        #         orid = self.find_orbits("sat"+str(areas_0[val]))
        #         if current_orbit == orid:
        #             sat_gw = "sat"+str(areas_0[val])
        #             print sat_gw, sat_node.name, orid
        #
        #             break
        #
        #     interface_gw_ip = self.get_gw_sat_ip(sat_node.name, sat_gw)
        #     print interface_gw_ip, sat_node.name, sat_gw
            # log("Starting zebra and ospfd on %s" % sat_node.name)
