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

import sys
sys.path.append("./")
from routing.routing_utils import *

def gs_routing_worker (data_path, gs_sat, links_updated, num_of_satellites, satellites_by_index, list_of_Intf_IPs, constellation_routes):
    update_gsl_routing_cmd = []
    gs_number = int(gs_sat[1])%num_of_satellites
    gs_ip = get_gs_ip(list_of_Intf_IPs, "gs"+str(gs_number)+"-eth0").split("/")[0]

    gs_network_address = get_network_address(gs_ip)
    thread_list = []
    for i in range(num_of_satellites):
        route_to_sat_GW = find_route_between_src_dest(i, gs_sat[0], constellation_routes)
        if route_to_sat_GW != -1:
            parameters = get_static_route_parameter([route_to_sat_GW], links_updated, list_of_Intf_IPs, satellites_by_index);
            if len(parameters) > 0:
                update_gsl_routing_cmd.append("sat"+str(i)+",ip route add "+str(gs_network_address)+"/28 via "+str(parameters[2][:-3])+" dev "+str(parameters[3]))
            else:
                print(route_to_sat_GW)

    if len(update_gsl_routing_cmd) > 0:
        for update in update_gsl_routing_cmd:
            update_routes = update.split(",")       #sat1539,ip route del 10.2.2.112 via 10.2.6.130/28 dev sat1539-eth4
            file = open(data_path+"/cmd_files/"+update_routes[0]+"_routes.sh", 'a')
            file.writelines(update_routes[1].strip()+" & \n")
            file.close()

def update_GSL_thread(sat_id, change, constellation_routes, links_updated, list_of_Intf_IPs, satellites_by_index, gs_network_address, update_gsl_routing_cmd):
    route_to_sat_GW = find_route_between_src_dest(sat_id, change[0], constellation_routes)
    if route_to_sat_GW != -1:
        parameters = get_static_route_parameter([route_to_sat_GW], links_updated, list_of_Intf_IPs, satellites_by_index);
        if len(parameters) > 0:
            if change[2] == 0 and change[3] == 1:
                update_gsl_routing_cmd.append("ip route add "+str(gs_network_address)+" via "+str(parameters[2])+" dev "+str(parameters[3]))
            elif change[2] == 1 and change[3] == 0:
                update_gsl_routing_cmd.append("ip route del "+str(gs_network_address)+" via "+str(parameters[2])+" dev "+str(parameters[3]))
    else:
        if sat_id != int(change[0]):
            print("Error: cannot find the route between sat", sat_id, " and sat", change[0])

def static_routing_worker(args):
    (
        G,
        p,
        q
    ) = args

    new_path = []
    path_length, path_nodes, negative_cycle = bf.bellman_ford(G, source=p, target=q, weight="weight")
    new_path.append(path_nodes)

    return new_path

def initial_routing(satellites, ground_stations, connectivity_matrix):
    mega_constellation_graph = nx.Graph()
    for n in range(len(satellites)+len(ground_stations)):
        mega_constellation_graph.add_node(n)        # nodes where n > len(satellites) are ground stations

    for i in range(len(connectivity_matrix)):
        for j in range(len(connectivity_matrix[i])):
            if connectivity_matrix[i][j] == 1:
                # print i, j
                mega_constellation_graph.add_edge(i, j, weight=1)

    static_routing_list_args = []
    print(len(mega_constellation_graph.edges()))
    for p in range(len(satellites)+len(ground_stations)):#len(satellites)+len(ground_stations)
        for q in range(p, len(satellites)+len(ground_stations)):
            static_routing_list_args.append((mega_constellation_graph, p, q))

    pool = Pool(20)
    static_routes = pool.map(static_routing_worker, static_routing_list_args)
    pool.close()
    pool.join()

    return static_routes

def initial_routing_v2(satellites, ground_stations, connectivity_matrix, latency):
    mega_constellation_graph = nx.Graph()
    for n in range(len(satellites)+len(ground_stations)):
        mega_constellation_graph.add_node(n)        # nodes where n > len(satellites) are ground stations

    for i in range(len(connectivity_matrix)):
        for j in range(len(connectivity_matrix[i])):
            if connectivity_matrix[i][j] == 1:
                # print i,j
                mega_constellation_graph.add_edge(i, j, weight=1) #latency[i][j] - starlink, 1 - hopcount oneweb

    static_routing_list_args = []
    # print "number of egdes ", len(mega_constellation_graph.edges())
    for p in range(len(satellites)+len(ground_stations)):#len(satellites)+len(ground_stations)
        for q in range(p, len(satellites)):#+len(ground_stations)
            static_routing_list_args.append((mega_constellation_graph, p, q))

    # print mega_constellation_graph.edges.data()
    pool = Pool(20)
    static_routes = pool.map(static_routing_worker, static_routing_list_args)
    pool.close()
    pool.join()

    return static_routes

def update_routing_v2(satellites, ground_stations, connectivity_matrix, latency, p, q):
    mega_constellation_graph = nx.Graph()
    for n in range(len(satellites)+len(ground_stations)):
        mega_constellation_graph.add_node(n)        # nodes where n > len(satellites) are ground stations

    for i in range(len(connectivity_matrix)):
        for j in range(len(connectivity_matrix[i])):
            if connectivity_matrix[i][j] == 1:
                # print i,j
                mega_constellation_graph.add_edge(i, j, weight=1) #latency[i][j] - starlink, 1 - hopcount oneweb

    static_routing_list_args = []
    static_routing_list_args.append((mega_constellation_graph, p, q))

    # print mega_constellation_graph.edges.data()
    pool = Pool(20)
    static_routes = pool.map(static_routing_worker, static_routing_list_args)
    pool.close()
    pool.join()

    return static_routes

def static_routing_worker(args):
    (
        Gr,
        source,
        destination
    ) = args

    new_path = []
    path_length, path_nodes, negative_cycle = bf.bellman_ford(Gr, source=source, target=destination, weight="weight")
    new_path.append(path_nodes)

    return new_path

def static_routing(G, destinations, num_of_satellites, num_of_ground_stations, num_of_threads):
    for i in range(num_of_satellites+num_of_ground_stations):
        for dest in destinations:
            destination = -1
            if "gs" in dest[0]:
                destination = int(dest[0][2:])+num_of_satellites
            elif "sat" in dest[0]:
                destination = int(dest[0][3:])

            list_args.append((G, i, destination))

    pool = Pool(num_of_threads)
    static_routes = pool.map(static_routing_worker, list_args)
    pool.close()
    pool.join()

    return static_routes

def static_routing_update_commands(static_routes, links, list_of_Intf_IPs, satellites):
    for route in static_routes:
        current_route = route[0];
        if len(current_route) > 2:
            src_node, next_hop_node, dest_node, last_hop_node = current_route[0], current_route[1], current_route[len(current_route)-1], current_route[len(current_route)-2]

            src_node = "sat"+str(src_node) if src_node < len(satellites) else "gs"+str(src_node%len(satellites))
            next_hop_node = "sat"+str(next_hop_node) if next_hop_node < len(satellites) else "gs"+str(next_hop_node%len(satellites))
            dest_node = "sat"+str(dest_node) if dest_node < len(satellites) else "gs"+str(dest_node%len(satellites))
            last_hop_node = "sat"+str(last_hop_node) if last_hop_node < len(satellites) else "gs"+str(last_hop_node%len(satellites))

            src_node_intf = ""
            dest_node_intf= ""
            next_h_node_intf = ""
            last_h_node_intf = ""

            for link in links:
                if str(src_node)+str("-") in link and str(next_hop_node)+str("-") in link:
                    intfs = link.split(":")
                    if str(src_node) in intfs[0] and str(next_hop_node) in intfs[1]:
                        src_node_intf = intfs[0]
                        next_h_node_intf = intfs[1]
                    elif str(src_node) in intfs[1] and str(next_hop_node) in intfs[0]:
                        src_node_intf = intfs[1]
                        next_h_node_intf = intfs[0]

                if str(dest_node)+str("-") in link and str(last_hop_node)+str("-") in link:
                    intfs = link.split(":")
                    if str(dest_node) in intfs[0] and str(last_hop_node) in intfs[1]:
                        dest_node_intf = intfs[0]
                        last_h_node_intf = intfs[1]
                    elif str(dest_node) in intfs[1] and str(last_hop_node) in intfs[0]:
                        dest_node_intf = intfs[1]
                        last_h_node_intf = intfs[0]

            if dest_node_intf != "" and next_h_node_intf != "" and src_node_intf !="":
                cmd_on_src_node  = "ip route add "+get_network_address(get_node_intf_ip(dest_node_intf, list_of_Intf_IPs))+"/28 via "+get_node_intf_ip(next_h_node_intf, list_of_Intf_IPs)+" dev "+src_node_intf
                print(cmd_on_src_node)

            if src_node_intf != "" and last_h_node_intf != "" and dest_node_intf != "":
                cmd_on_dest_node = "ip route add "+get_network_address(get_node_intf_ip(src_node_intf, list_of_Intf_IPs))+"/28 via "+get_node_intf_ip(last_h_node_intf, list_of_Intf_IPs)+" dev "+dest_node_intf
                print(cmd_on_dest_node)

def get_static_route_parameter_optimised(route, links, list_of_Intf_IPs, satellites):
    parameters = []
    current_route = route[0];
    src_node        = ""
    next_hop_node   = ""
    dest_node       = ""
    last_hop_node   = ""
    link            = ""

    if len(current_route) > 2:
        src_node, next_hop_node, dest_node, last_hop_node = current_route[0], current_route[1], current_route[len(current_route)-1], current_route[len(current_route)-2]
    elif len(current_route) == 2:
        src_node, next_hop_node, dest_node, last_hop_node = current_route[0], current_route[1], current_route[1], current_route[0]

    if src_node != "":
        src_node = "sat"+str(src_node) if src_node < len(satellites) else "gs"+str(src_node%len(satellites))
        next_hop_node = "sat"+str(next_hop_node) if next_hop_node < len(satellites) else "gs"+str(next_hop_node%len(satellites))
        dest_node = "sat"+str(dest_node) if dest_node < len(satellites) else "gs"+str(dest_node%len(satellites))
        last_hop_node = "sat"+str(last_hop_node) if last_hop_node < len(satellites) else "gs"+str(last_hop_node%len(satellites))

        src_node_intf = ""
        dest_node_intf= ""
        next_h_node_intf = ""
        last_h_node_intf = ""

        key1 = str(src_node)+"_"+str(next_hop_node)
        key2 = str(next_hop_node)+"_"+str(src_node)
        if links.get(key1) is not None:
            link = links[key1][0]
        elif links.get(key2) is not None:
            link = links[key2][0]
        if link != "":
            intfs = link.split(":")
            if str(src_node) in intfs[0] and str(next_hop_node) in intfs[1]:
                src_node_intf = intfs[0]
                next_h_node_intf = intfs[1]
            elif str(src_node) in intfs[1] and str(next_hop_node) in intfs[0]:
                src_node_intf = intfs[1]
                next_h_node_intf = intfs[0]


        key1 = str(last_hop_node)+"_"+str(dest_node)
        key2 = str(dest_node)+"_"+str(last_hop_node)
        if links.get(key1) is not None:
            link = links[key1][0]
        elif links.get(key2) is not None:
            link = links[key2][0]
        if link != "":
            intfs = link.split(":")
            if str(dest_node) in intfs[0] and str(last_hop_node) in intfs[1]:
                dest_node_intf = intfs[0]
                last_h_node_intf = intfs[1]
            elif str(dest_node) in intfs[1] and str(last_hop_node) in intfs[0]:
                dest_node_intf = intfs[1]
                last_h_node_intf = intfs[0]

        if dest_node_intf != "":
            dest_ip_address = list_of_Intf_IPs[str(dest_node_intf)][0]
            next_hop_ip = list_of_Intf_IPs[str(next_h_node_intf)][0]
            out_interface = src_node_intf
            # print dest_ip_address
            dest_nw_ip = get_network_address(dest_ip_address.split("/")[0])+"/28"
        else:
            print("Error: No link between ", str(last_hop_node), " and ", str(dest_node))
            exit()

        if src_node_intf != "":
            src_ip_address = list_of_Intf_IPs[str(src_node_intf)][0]
            last_hop_ip = list_of_Intf_IPs[str(last_h_node_intf)][0]
            out_interface_2 = dest_node_intf
            # print src_ip_address
            src_nw_ip = get_network_address(src_ip_address.split("/")[0])+"/28"
        else:
            print("Error: No link between ", str(src_node), " and ", str(next_hop_node))
            exit()


        parameters.append(src_node)
        parameters.append(dest_nw_ip)
        parameters.append(next_hop_ip)
        parameters.append(out_interface)

        parameters.append(dest_node)
        parameters.append(src_nw_ip)
        parameters.append(last_hop_ip)
        parameters.append(out_interface_2)

        # parameters.append(src_node)
        # parameters.append(dest_node)
        # parameters.append(next_hop_node)
        # parameters.append(last_hop_node)
        #
        # parameters.append(src_nw_ip)
        # parameters.append(dest_nw_ip)
        # parameters.append(next_hop_ip)
        # parameters.append(last_hop_ip)
        #
        # parameters.append(out_interface)
        # parameters.append(out_interface_2)

    return parameters

def get_static_route_parameter(route, links, list_of_Intf_IPs, satellites):
    parameters = []
    current_route = route[0];
    if len(current_route) > 2:
        src_node, next_hop_node, dest_node, last_hop_node = current_route[0], current_route[1], current_route[len(current_route)-1], current_route[len(current_route)-2]

        src_node = "sat"+str(src_node) if src_node < len(satellites) else "gs"+str(src_node%len(satellites))
        next_hop_node = "sat"+str(next_hop_node) if next_hop_node < len(satellites) else "gs"+str(next_hop_node%len(satellites))
        dest_node = "sat"+str(dest_node) if dest_node < len(satellites) else "gs"+str(dest_node%len(satellites))
        last_hop_node = "sat"+str(last_hop_node) if last_hop_node < len(satellites) else "gs"+str(last_hop_node%len(satellites))

        src_node_intf = ""
        dest_node_intf= ""
        next_h_node_intf = ""
        last_h_node_intf = ""

        for link in links:
            if str(src_node)+str("-") in link and str(next_hop_node)+str("-") in link:
                intfs = link.split(":")
                if str(src_node) in intfs[0] and str(next_hop_node) in intfs[1]:
                    src_node_intf = intfs[0]
                    next_h_node_intf = intfs[1]
                elif str(src_node) in intfs[1] and str(next_hop_node) in intfs[0]:
                    src_node_intf = intfs[1]
                    next_h_node_intf = intfs[0]

            if str(dest_node)+str("-") in link and str(last_hop_node)+str("-") in link:
                intfs = link.split(":")
                if str(dest_node) in intfs[0] and str(last_hop_node) in intfs[1]:
                    dest_node_intf = intfs[0]
                    last_h_node_intf = intfs[1]
                elif str(dest_node) in intfs[1] and str(last_hop_node) in intfs[0]:
                    dest_node_intf = intfs[1]
                    last_h_node_intf = intfs[0]

        if dest_node_intf != "":
            dest_nw_ip = get_network_address(get_node_intf_ip(dest_node_intf, list_of_Intf_IPs).split("/")[0])+"/28"
            next_hop_ip = get_node_intf_ip(next_h_node_intf, list_of_Intf_IPs)
            out_interface = src_node_intf
        else:
            print("Error: No link between ", str(last_hop_node), " and ", str(dest_node))
            exit()

        if src_node_intf != "":
            src_nw_ip = get_network_address(get_node_intf_ip(src_node_intf, list_of_Intf_IPs).split("/")[0])+"/28"
            last_hop_ip = get_node_intf_ip(last_h_node_intf, list_of_Intf_IPs)
            out_interface_2 = dest_node_intf
        else:
            print("Error: No link between ", str(src_node), " and ", str(next_hop_node))
            exit()

        parameters.append(src_node)
        parameters.append(dest_node)
        parameters.append(next_hop_node)
        parameters.append(last_hop_node)

        parameters.append(src_nw_ip)
        parameters.append(dest_nw_ip)
        parameters.append(next_hop_ip)
        parameters.append(last_hop_ip)

        parameters.append(out_interface)
        parameters.append(out_interface_2)

    if len(current_route) == 2:
        src_node, next_hop_node, dest_node, last_hop_node = current_route[0], current_route[1], current_route[1], current_route[0]

        src_node = "sat"+str(src_node) if src_node < len(satellites) else "gs"+str(src_node%len(satellites))
        next_hop_node = "sat"+str(next_hop_node) if next_hop_node < len(satellites) else "gs"+str(next_hop_node%len(satellites))
        dest_node = "sat"+str(dest_node) if dest_node < len(satellites) else "gs"+str(dest_node%len(satellites))
        last_hop_node = "sat"+str(last_hop_node) if last_hop_node < len(satellites) else "gs"+str(last_hop_node%len(satellites))

        src_node_intf = ""
        dest_node_intf= ""
        next_h_node_intf = ""
        last_h_node_intf = ""

        for link in links:
            if str(src_node)+str("-") in link and str(next_hop_node)+str("-") in link:
                intfs = link.split(":")
                if str(src_node) in intfs[0] and str(next_hop_node) in intfs[1]:
                    src_node_intf = intfs[0]
                    next_h_node_intf = intfs[1]
                elif str(src_node) in intfs[1] and str(next_hop_node) in intfs[0]:
                    src_node_intf = intfs[1]
                    next_h_node_intf = intfs[0]

            if str(dest_node)+str("-") in link and str(last_hop_node)+str("-") in link:
                intfs = link.split(":")
                if str(dest_node) in intfs[0] and str(last_hop_node) in intfs[1]:
                    dest_node_intf = intfs[0]
                    last_h_node_intf = intfs[1]
                elif str(dest_node) in intfs[1] and str(last_hop_node) in intfs[0]:
                    dest_node_intf = intfs[1]
                    last_h_node_intf = intfs[0]

        if dest_node_intf != "":
            dest_nw_ip = get_network_address(get_node_intf_ip(dest_node_intf, list_of_Intf_IPs).split("/")[0])+"/28"
            next_hop_ip = get_node_intf_ip(next_h_node_intf, list_of_Intf_IPs)
            out_interface = src_node_intf
        else:
            print("Error: No link between ", str(last_hop_node), " and ", str(dest_node))
            exit()

        if src_node_intf != "":
            src_nw_ip = get_network_address(get_node_intf_ip(src_node_intf, list_of_Intf_IPs).split("/")[0])+"/28"
            last_hop_ip = get_node_intf_ip(last_h_node_intf, list_of_Intf_IPs)
            out_interface_2 = dest_node_intf
        else:
            print("Error: No link between ", str(src_node), " and ", str(next_hop_node))
            exit()

        parameters.append(src_node)
        parameters.append(dest_node)
        parameters.append(next_hop_node)
        parameters.append(last_hop_node)

        parameters.append(src_nw_ip)
        parameters.append(dest_nw_ip)
        parameters.append(next_hop_ip)
        parameters.append(last_hop_ip)

        parameters.append(out_interface)
        parameters.append(out_interface_2)

    return parameters


def find_route_between_src_dest(src_sat, dest_sat, constellation_routes):
    if src_sat < dest_sat:
        for route in constellation_routes[src_sat]:
            # print route
            current_route = route[0][:]
            if "sat"+str(src_sat) == "sat"+str(current_route[0]) and "sat"+str(dest_sat) == "sat"+str(current_route[len(current_route)-1]):
                return current_route

    # This is added because in constellation_routes and in initial_routes, we only store the route from x to y but not the route for y to x.
    # We do that to minimize the calcuations. Therefore, sometimes if src_sat > dest_sat, we need to search in the opposite direction
    if src_sat > dest_sat:
        for route in constellation_routes[dest_sat]:
            current_route = route[0][:]
            if "sat"+str(src_sat) == "sat"+str(current_route[len(current_route)-1]) and "sat"+str(dest_sat) == "sat"+str(current_route[0]):
                retr_route = route[0][:]
                retr_route.reverse()
                return retr_route

    return -1

def get_gs_ip(list_of_Intf_IPs, gs):
    for pair in list_of_Intf_IPs:
        if gs in pair["Interface"]:
            return pair["IP"]

    return -1

def gs_routing(data_path, gs_statellite_pair, links_updated, num_of_satellites, satellites_by_index, list_of_Intf_IPs, constellation_routes, main_configurations, border_gateway):
    update_gsl_routing_cmd = []
    for gs_sat in gs_statellite_pair:
        gs_number = int(gs_sat[1])%num_of_satellites

        if "gs"+str(gs_number) != border_gateway:
            key = str("gs"+str(gs_number)+"-eth0")
        else:
            key = str("gs"+str(gs_number)+"-eth1")

        # print key
        if list_of_Intf_IPs.get(key) is None:
            print("error -- no ip for this ground station", gs_number)
            return

        gs_ip = list_of_Intf_IPs[key][0].split("/")[0]
        gs_network_address = get_network_address(gs_ip)
        thread_list = []
        for i in range(num_of_satellites):
            route_to_sat_GW = find_route_between_src_dest(i, gs_sat[0], constellation_routes)
            # if key == "gs1-eth1":
            #     print route_to_sat_GW
            if route_to_sat_GW != -1:
                parameters = get_static_route_parameter_optimised([route_to_sat_GW], links_updated, list_of_Intf_IPs, satellites_by_index);
                # if key == "gs1-eth1":
                #     print parameters
                if len(parameters) > 0:
                    update_gsl_routing_cmd.append("sat"+str(i)+",ip route add "+str(gs_network_address)+"/28 via "+str(parameters[2][:-3])+" dev "+str(parameters[3]))
                    if main_configurations["constellation"]["routing"]["interDomain_routing"] == 1 and "gs"+str(gs_number) == main_configurations["constellation"]["routing"]["border_gateway"]:
                        update_gsl_routing_cmd.append("sat"+str(i)+",ip route add "+str(main_configurations["constellation"]["routing"]["other_constellation_ip_range"])+"/20 via "+str(parameters[2][:-3])+" dev "+str(parameters[3]))
                else:
                    print("-----> ", route_to_sat_GW)

    if len(update_gsl_routing_cmd) > 0:
        for update in update_gsl_routing_cmd:
            update_routes = update.split(",")       #sat1539,ip route del 10.2.2.112 via 10.2.6.130/28 dev sat1539-eth4
            file = open(data_path+"/cmd_files/"+update_routes[0]+"_routes.sh", 'a')
            file.writelines(update_routes[1].strip()+" & \n")
            file.close()

def gs_routing_parallel(data_path, gs_statellite_pair, links_updated, num_of_satellites, satellites_by_index, list_of_Intf_IPs, constellation_routes, num_of_threads):
    gs_routing_args = []
    thread_list = []

    num_thread = num_of_threads;

    for gs_sat in gs_statellite_pair:
        thread = threading.Thread(target=gs_routing_worker, args=(data_path, gs_sat, links_updated, num_of_satellites, satellites_by_index, list_of_Intf_IPs, constellation_routes))
        thread_list.append(thread)

    for thread in thread_list:
        thread.start()
    for thread in thread_list:
        thread.join()

def lightweight_routing(data_path, route_changes, links_updated, num_of_satellites, satellites_by_index, list_of_Intf_IPs, constellation_routes, t_time, border_gateway):
    update_gsl_routing_cmd = []
    isl_ch = 0
    gsl_ch = 0
    allchanges_log = open(data_path+"/allchanges_log_"+str(t_time.utc_strftime())+"_.txt", "a")
    for change in route_changes:
        start = round(time.time()*1000)
        # print "the updated route --> ", change
        allchanges_log.write(str(change[0])+","+str(change[1])+","+str(change[2])+","+str(change[3])+"\n")

        # #####
        # If there is a change the GSL links
        # #####
        if change[0] < num_of_satellites and change[1] >= num_of_satellites:
            # 1. Get the network address of the changing ground station
            gs_number = int(change[1])%num_of_satellites
            if "gs"+str(gs_number) != border_gateway:
                key = str("gs"+str(gs_number)+"-eth0")
            else:
                key = str("gs"+str(gs_number)+"-eth1")

            if list_of_Intf_IPs.get(key) is None:
                print("error -- no ip for this ground station", gs_number)
                return

            gs_ip = list_of_Intf_IPs[key][0].split("/")[0]
            gs_network_address = get_network_address(gs_ip)

            # gs_ip = get_gs_ip(list_of_Intf_IPs, "gs"+str(gs_number)+"-eth0").split("/")[0]
            # gs_network_address = get_network_address(gs_ip)

            # 2. Find the route to the current gateway of that ground station. The current gateway is at change[0].
            #    The ground station is at change[1]. constellation_routes has all the current topology routes.
            # 3. If there is a route from satellite (i) to the gateway of that ground station:
            #    3.1. Check the details of that route, specifically,
            #           (1) The IP address of the next hop to reach that gateway --> parameters[2]
            #           (2) The output interface to reach that gateway           --> parameters[3]
            #    3.2. Based on the type of the route update: Is it route addition or deletion  (change[3])
            #         We generate the IP route command.
            thread_list = []
            for i in range(num_of_satellites):

                route_to_sat_GW = find_route_between_src_dest(i, change[0], constellation_routes)

                if route_to_sat_GW != -1:

                    parameters = get_static_route_parameter_optimised([route_to_sat_GW], links_updated, list_of_Intf_IPs, satellites_by_index);

                    if len(parameters) > 0:
                        if change[2] == 0 and change[3] == 1:
                            update_gsl_routing_cmd.append("sat"+str(i)+",ip route add "+str(gs_network_address)+"/28 via "+str(parameters[2])+" dev "+str(parameters[3]))
                        elif change[2] == 1 and change[3] == 0:
                            update_gsl_routing_cmd.append("sat"+str(i)+",ip route del "+str(gs_network_address)+"/28 via "+str(parameters[2])+" dev "+str(parameters[3]))
                else:
                    if i!= int(change[0]):
                        print("Error: cannot find the route between sat", i, " and sat", change[0])
            gsl_ch += 1

        # #####
        # If there is a change the ISL links
        # #####
        elif change[0] < num_of_satellites and change[1] < num_of_satellites:
            isl_ch += 1

        end = round(time.time()*1000)
        # print "one iteration of change takes --- ", end-start, "ms "

    if len(update_gsl_routing_cmd) > 0:
        start = round(time.time()*1000)
        if os.path.isdir(data_path+"/routes_updates_"+str(t_time.utc_strftime())) == False:
            os.mkdir(data_path+"/routes_updates_"+str(t_time.utc_strftime()))

        for f in os.listdir(data_path+"/routes_updates_"+str(t_time.utc_strftime())):
            os.remove(os.path.join(data_path+"/routes_updates_"+str(t_time.utc_strftime()), f))

        updates_log = open(data_path+"/routes_updates_"+str(t_time.utc_strftime())+"/routing_updates_"+str(t_time.utc_strftime())+"_.txt", "w")
        for update in update_gsl_routing_cmd:
            updates_log.write(str(update) + "\n")
            update_routes = update.split(",")       #sat1539,ip route del 10.2.2.112 via 10.2.6.130/28 dev sat1539-eth4
            file = open(data_path+"/routes_updates_"+str(t_time.utc_strftime())+"/"+update_routes[0]+"_routes.sh", 'a')
            file.writelines(update_routes[1].strip()+"\n")
            file.close()

        cmd_path = data_path+"/routes_updates_"+str(t_time.utc_strftime())
        cmdd =  'chmod +x "'+cmd_path+'"'+'/*.sh'
        os.system(cmdd)
        end = round(time.time()*1000)
        # print "writing the routes update to file takes --- ", end-start, "ms "

        updates_log.close()
        allchanges_log.close()

    # print gsl_ch, isl_ch

def check_changes_in_topology(last, new):
    changes = []
    for i in range(len(new)):
        for j in range(len(new[i])):
            if new[i][j] != last[i][j]:
                changes.append((i, j, last[i][j], new[i][j]))
                # print i,j, last[i][j], new[i][j]

    return changes
