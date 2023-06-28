import socket
import time
import subprocess
import threading
import os
import sys
# 
# import c_m_update_topology_pb2 as updateTopologyMsg
# sys.path.append("../")
# from mininet_infra.create_mininet_topology import *
#
# def run_topology_commands(net, command, node1, node2):
#     net_node1 = net.getNodeByName(node1)
#     net_node2 = net.getNodeByName(node2)
#
#     if command == "deleteLink":
#         if net.linksBetween(net_node1, net_node2):
#             net.delLinkBetween(net_node1, net_node2)
#
#     if command == "addLink":
#         net.addLink(net_node1, net_node2, cls=TCLink)
#
# def handle_topology_updates_commands(net):
#     UDPSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
#     UDPSocket.bind(("172.16.0.4", 20001))
#     print "listener on 0.4 is created"
#     while(True):
#         bytesAddressPair = UDPSocket.recvfrom(1024)
#         print bytesAddressPair
#         recv_msg = updateTopologyMsg.c_m_update_topology()
#         recv_msg.ParseFromString(bytesAddressPair[0])
#         t = threading.Thread(target=handle_commands, args=(net, recv_msg.command, recv_msg.node1_name, recv_msg.node2_name))
#         t.start()
