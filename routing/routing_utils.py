import argparse
import re
import time
import os
import numpy as np
import datetime

import threading
import queue
from copy import copy, deepcopy

import networkx as nx
import matplotlib.pyplot as plt
import bellmanford as bf
import itertools
from multiprocessing import Process, Manager, Pool


def generate_ips_for_constellation(ip_subnet):
    ip_octs = ip_subnet.split(".")
    available_ips = []
    for i in range (int(ip_octs[1]), 250):
        for j in range (int(ip_octs[2]), 250):
            for k in range (0, 240, 16):
                ip = str(str(ip_octs[0])+".")+str(i)+"."+str(j)+"."+str(k)
                available_ips.append((1, ip))

    return available_ips

def generate_ips_for_physical_nodes(num_of_ips):
    available_ips = []
    for i in range(1, num_of_ips):
        ip = str("192.168.101.")+str(i)
        available_ips.append((1, ip))

    return available_ips

def get_free_network_address(pool):
    free_ip = -1
    for i in pool:
        if i[0] == 1:
            free_ip = i[1]
            pool.remove(i)
            break;

    return free_ip

def get_network_address(str_ip_address):
    # Assuming /28 subnet mask
    ip_oct1, ip_oct2, ip_oct3, ip_oct4 = str_ip_address.split(".")
    net_add1= int(ip_oct1) & 255
    net_add2= int(ip_oct2) & 255
    net_add3= int(ip_oct3) & 255
    net_add4= int(ip_oct4) & 240

    return str(net_add1)+"."+str(net_add2)+"."+str(net_add3)+"."+str(net_add4)

def assign_ips_for_constellation(links, addresses_pool):
    list_of_Intf_IPs = []
    #link = satx-ethy:satz-ethw
    for link in links:
        linkIntf1, linkIntf2 = link.split(":")
        network_address = get_free_network_address(addresses_pool)
        if network_address != -1:
           oct1, oct2, oct3, oct4 = network_address.split('.');
           list_of_Intf_IPs.append({"Interface": linkIntf1, "IP": oct1+"."+oct2+"."+oct3+"."+str(int(oct4)+1)+"/28"})
           list_of_Intf_IPs.append({"Interface": linkIntf2, "IP": oct1+"."+oct2+"."+oct3+"."+str(int(oct4)+2)+"/28"})
        else:
           print("[Create Sat Network -- GSL] No Available IPs to assign")
    return list_of_Intf_IPs

def get_link_intfs_ips(node1, node2, links, list_of_Intf_IPs):
    link_intfs_ips = []
    n1n2Link = ""
    for link in links:
        if node1 in link and node2 in link:
            n1n2Link = link
            break

    print(n1n2Link)
    linkIntf1, linkIntf2 = n1n2Link.split(":")
    # print linkIntf1, linkIntf2
    for intf_IP in list_of_Intf_IPs:
        if intf_IP["Interface"] == linkIntf1:
            link_intfs_ips.append(intf_IP)
        if intf_IP["Interface"] == linkIntf2:
            link_intfs_ips.append(intf_IP)

    return link_intfs_ips

def get_node_intf_ip(interface, list_of_Intf_IPs):
    for intf_IP in list_of_Intf_IPs:
        if intf_IP["Interface"] == interface:
            return intf_IP["IP"]
