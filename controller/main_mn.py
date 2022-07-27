from mininet.net import Mininet
from mininet.node import Node, OVSKernelSwitch, Controller, RemoteController
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.link import *
from mininet.topo import Topo
from mininet.log import setLogLevel, info
from mininet.node import OVSController
import argparse
import re
import time
import os
import numpy as np
import datetime
from sgp4 import exporter
from pprint import pprint

import threading
import Queue
from copy import copy, deepcopy

import networkx as nx
import matplotlib.pyplot as plt
import bellmanford as bf
import itertools
from multiprocessing import Process, Manager, Pool

import socket
import time
import subprocess
import threading
import wget
import shutil
import enum

import sys
sys.path.append("../")
from mobility.read_live_tles import *
from mobility.mobility_utils import *
from mobility.read_gs import *
from mininet_infra.create_mininet_topology import *
from routing.routing_utils import *
from routing.constellation_routing import *

DEBUG = 1

class TestbedMode(enum.Enum):
   SWOnly = 1
   SWPLUSHW = 2

def ping_thread(net):
    test_node = net.getNodeByName("gs13")
    test_node.cmd("date >> iperf-intf1_s.txt")
    test_node.cmd("ping 10.1.55.66 >> iperf-intf1_s.txt")


def iperf_thread(net):
    print "started here ..."
    test_node2 = net.getNodeByName("gs0")
    test_node2.cmd("iperf -s -p 5201 >> iperf-intf1_r1_s.txt &")
    test_node2.cmd("iperf -s -p 5202 >> iperf-intf2_r2_s.txt &")
    test_node2.cmd("iperf -s -p 5203 >> iperf-intf3_r3_s.txt &")
    test_node2.cmd("iperf -s -p 5204 >> iperf-intf4_r4_s.txt &")
    test_node2.cmd("iperf -s -p 5205 >> iperf-intf5_r5_s.txt &")


    test_node = net.getNodeByName("gs1")
    # test_node.cmd("date >> iperf-intf1_c2.txt &")
    test_node.cmd("iperf -c 10.0.4.66   -p 5201 -i1 -t85 >> iperf-intf1_r1_c.txt &")
    test_node.cmd("iperf -c 10.0.9.114  -p 5202 -i1 -t85 >> iperf-intf1_r2_c.txt &")
    test_node.cmd("iperf -c 10.0.9.210  -p 5203 -i1 -t85 >> iperf-intf1_r3_c.txt &")
    test_node.cmd("iperf -c 10.0.29.66  -p 5204 -i1 -t85 >> iperf-intf1_r4_c.txt &")
    test_node.cmd("iperf -c 10.0.29.162 -p 5205 -i1 -t85 >> iperf-intf1_r5_c.txt &")

    test_node.cmd("iperf -c 10.0.9.114  -p 5202 -i1 -t85 >> iperf-intf1_r2_c.txt &")
    test_node.cmd("iperf -c 10.0.9.210  -p 5203 -i1 -t85 >> iperf-intf1_r3_c.txt &")
    test_node.cmd("iperf -c 10.0.29.66  -p 5204 -i1 -t85 >> iperf-intf1_r4_c.txt &")
    test_node.cmd("iperf -c 10.0.29.162 -p 5205 -i1 -t85 >> iperf-intf1_r5_c.txt &")
    test_node.cmd("iperf -c 10.0.9.114  -p 5202 -i1 -t85 >> iperf-intf1_r2_c.txt &")
    test_node.cmd("iperf -c 10.0.9.210  -p 5203 -i1 -t85 >> iperf-intf1_r3_c.txt &")
    test_node.cmd("iperf -c 10.0.29.66  -p 5204 -i1 -t85 >> iperf-intf1_r4_c.txt &")
    test_node.cmd("iperf -c 10.0.29.162 -p 5205 -i1 -t85 >> iperf-intf1_r5_c.txt &")

def background_loop(data_path, net, SimulationTime_secs, num_of_satellites):
    updates_files_name = []
    for fileLog in os.listdir(data_path):
        if fileLog.startswith("allchanges_log"):
            a = re.split('_| ',fileLog)
            filesd = a[2]+" "+a[3]+" "+a[4]
            updates_files_name.append(filesd)

    updates_files_name.sort()

    time_counter = 0
    for file in updates_files_name:
        if time_counter > SimulationTime_secs:
            exit()

        st = round(time.time() * 1000)
        print "[ %0.12f" % round(time.time() * 1000),"] Start --> ", file
        net = update_loop(data_path, net, file, num_of_satellites);
        print "[ %0.12f" % round(time.time() * 1000),"] End   --> ", file
        time_counter += 1

def get_gs_sat_pairs(connectivity_matrix, num_of_satellites):
    pairs = []
    for i in range(len(connectivity_matrix)):
        for j in range(len(connectivity_matrix[i])):
            if connectivity_matrix[i][j] == 1 and i < num_of_satellites and j >= num_of_satellites:
                pairs.append((i, j))

    return pairs

def update_loop(data_path, net, updates_files_name, num_of_satellites):
    filename = data_path+"/allchanges_log_"+str(updates_files_name)+"_.txt"
    updatefile = open(filename, 'r')
    updates = updatefile.readlines()

    if len(updates) < 1:
        time.sleep(1)
        return net

    for update in updates:
        update_links = update.split(",")       #330,1575,0,1
        node1 = "sat"+str(update_links[0]) if int(update_links[0]) < num_of_satellites else "gs"+str(int(update_links[0])%num_of_satellites)
        node2 = "sat"+str(update_links[1]) if int(update_links[1]) < num_of_satellites else "gs"+str(int(update_links[1])%num_of_satellites)
        if node1 == "gs13" or node1 == "gs14" or node2 == "gs13" or node2 == "gs14":
            print update_links
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
        if node1 == "gs13" or node1 == "gs14" or node2 == "gs13" or node2 == "gs14":
            print update_links
        # print node1, node2
        net_node1 = net.getNodeByName(node1)
        net_node2 = net.getNodeByName(node2)
        if update_links[2] == 0 and update_links[3].strip() == 1:
            net.addLink(net_node1, net_node2, cls=TCLink)

            # gs_node_IP = get_node_intf_ip(str(node2)+"-eth1", list_of_Intf_IPs)
            # oct1, oct2, oct3, oct4 = gs_node_IP.split(".")
            # new_sat_IP = str(oct1)+str(oct2)+str(oct3)+str(oct4-1)
            # net.addLink(net_node1, net_node2, cls=TCLink, params1 = {'ip' : new_sat_IP+"/28"}, params2 = {'ip' : gs_node_IP+"/28"})

    for i in range(0, num_of_satellites):
        sat_node = net.getNodeByName("sat"+str(i))
        sat_node.cmd("./"+data_path+"/routes_updates_"+str(updates_files_name)+"/sat"+str(i)+"_routes.sh &")

    return net

def fill_routes_parallel(routes, links, list_of_Intf_IPs, satellite_by_index, route_data, data_path):
    for route in routes:
        start = round(time.time()*1000)
        parameters = get_static_route_parameter_optimised(route, links, list_of_Intf_IPs, satellite_by_index, data_path)
        if len(parameters) > 0:
            route_data[str(parameters[0])+"_"+str(parameters[1])] = []
            for i in range(len(parameters)):
                #0 - src_node, 1 - dest_node, 2 - next_hop_node, 3 - last_hop_node, 4 - src_nw_ip, 5 - dest_nw_ip, 6 - next_hop_ip, 7 - last_hop_ip, 8 - out_interface, 9 - out_interface_2
                route_data[str(parameters[0])+"_"+str(parameters[1])].append(str(parameters[i]))
        end = round(time.time()*1000)
        print len(route_data), (start-end)
    print len(routes)

def fill_routes_database(routes, links, list_of_Intf_IPs, satellite_by_index, data_path):
    route_data = {}

    num_thread = 20;
    sublist_len = len(routes)/num_thread
    thread_list = []
    for i in range(0, len(routes), sublist_len):
        subroutes = routes[i:i+sublist_len]
        thread = threading.Thread(target=fill_routes_parallel, args=(subroutes, links, list_of_Intf_IPs, satellite_by_index, route_data, data_path))
        thread_list.append(thread)
        if i > 0:
            break

    for thread in thread_list:
        thread.start()
    for thread in thread_list:
        thread.join()

    return route_data

def read_IProute_files_thread(routes, initial_routes):
    for route in routes:
        route_new = []
        route_list = re.split(", | |\n", route)
        route = [int(r) for r in route_list if r.strip()]
        route_new.append(route)
        initial_routes.append(route_new)

def get_topology_routes(FreshRun, data_path, num_of_satellites, satellites_by_index, ground_stations, connectivity_matrix, links_charateristics):
    if FreshRun == True:
        initial_routes = initial_routing_v2(satellites_by_index, ground_stations, connectivity_matrix, links_charateristics["latency_matrix"])

        copy_initial_routes = initial_routes[:]
        constellation_routes = {k: [] for k in range(num_of_satellites)}
        for route in copy_initial_routes:
            current_route = route[0]
            i = current_route[0]
            constellation_routes[i].append(route)

    if FreshRun == False:
        start = round(time.time()*1000)
        constellation_routes = {m: [] for m in range(num_of_satellites)}
        initial_routes = []
        thread_list = []

        Rfilename = data_path+"/routes/all_routes.txt"
        route_file = open(Rfilename, 'r')
        routes = route_file.readlines()

        num_thread = 1000;
        sublist_len = len(routes)/num_thread
        for i in range(0, len(routes), sublist_len):
            subroutes = routes[i:i+sublist_len]
            thread = threading.Thread(target=read_IProute_files_thread, args=(subroutes, initial_routes))
            thread_list.append(thread)

        for thread in thread_list:
            thread.start()
        for thread in thread_list:
            thread.join()

        copy_initial_routes = initial_routes[:]
        constellation_routes = {k: [] for k in range(num_of_satellites)}
        for route in copy_initial_routes:
            current_route = route[0]
            i = current_route[0]
            constellation_routes[i].append(route)

        end = round(time.time()*1000)
        # if DEBUG == 1:
        #     print " Get Initial routes from log files took ", end-start, "ms ", "for ", len(initial_routes), " routes"

    return {
                "All_PreConfigured_routes": initial_routes,
                "Routes_per_satellites": constellation_routes
            }

def prepare_routing_config_commands(topology, data_path, initial_routes, links, list_of_Intf_IPs, satellites_by_index, num_of_threads):
    start = round(time.time()*1000)
    ipRouteCMD = topology.create_static_routes_batch_parallel(initial_routes, links, list_of_Intf_IPs, satellites_by_index, num_of_threads)
    logg = open(data_path+"/stat_r.sh", "w")
    for c in ipRouteCMD:
        logg.write(c)
    logg.close()
    end = round(time.time()*1000)
    # if DEBUG == 1:
    #     print " -------------- Generate the IP Route commands for the whole constellation took ", end-start, "ms "

    file1 = open(data_path+"/stat_r.sh", 'r')
    Lines = file1.readlines()

    if os.path.isdir(data_path+"/cmd_files") == False:
        os.mkdir(data_path+"/cmd_files")

    for f in os.listdir(data_path+"/cmd_files"):
        os.remove(os.path.join(data_path+"/cmd_files", f))

    count = 0
    for line in Lines:
        command = line.strip().split(" ")
        file = open(data_path+"/cmd_files/"+command[0]+"_routes.sh", 'a')
        string_to_write = ""
        for i in range(1,len(command)):
            string_to_write += command[i]+" "

        file.writelines(string_to_write+"\n")
        file.close()

def dump_ALL(data_path, current_time, links, m_intfs, satellites_by_index, satellites_by_name, routes):
    time_log = open(data_path+"/time_log.txt", "w")
    links_log = open(data_path+"/links_log.txt", "w")
    m_intf_log = open(data_path+"/m_intf_log.txt", "w")
    satellitesInd_log = open(data_path+"/satellites_by_index_log.txt", "w")
    satellitesName_log = open(data_path+"/satellites_by_name_log.txt", "w")

#### Log Time
    time_log.write(current_time + "\n")
#### Log links
    for link in links:
        links_log.write(link + "\n")
    links_log.close()
#### Log management interfaces -- That is not used now
    for intf in m_intfs:
        m_intf_log.write(intf["node"] + "\t" + intf["mgnt_ip"] + "\n")
    m_intf_log.close()
#### Log satellites by index
    for sat in satellites_by_index:
        satellitesInd_log.write(str(sat) + "\n")
    satellitesInd_log.close()
#### Log satellites name accourding to Starlink (STARLINKXXXX)
    for sat in satellites_by_name:
        satellitesName_log.write(str(sat) + "\n")
    satellitesName_log.close()
#### Log initial routes
    os.mkdir(data_path+"/routes")
    for route in routes:
        current_route = route[0][:]
        routes_log = open(data_path+"/routes/all_routes.txt", "a")
        routes_log.write(str(current_route)[1:-1] + "\n")
        routes_log.close()

    for route in routes:
        if len(route[0]) > 2:
            current_route = route[0][:]
            src_node, next_hop_node, dest_node, last_hop_node = current_route[0], current_route[1], current_route[len(current_route)-1], current_route[len(current_route)-2]
            src_node = "sat"+str(src_node) if src_node < len(satellites_by_index) else "gs"+str(src_node%len(satellites_by_index))
            dest_node = "sat"+str(dest_node) if dest_node < len(satellites_by_index) else "gs"+str(dest_node%len(satellites_by_index))
            routes_log = open(data_path+"/routes/"+str(src_node)+"_routes.txt", "a")
            routes_log.write(str(current_route)[1:-1] + "\n")
            routes_log.close()

            routes_log = open(data_path+"/routes/"+str(dest_node)+"_routes.txt", "a")
            current_route.reverse()
            routes_log.write(str(current_route)[1:-1] + "\n")
            routes_log.close()

        elif len(route[0]) == 2:
            current_route = route[0][:]
            src_node, next_hop_node, dest_node, last_hop_node = current_route[0], current_route[1], current_route[len(current_route)-1], current_route[len(current_route)-1]
            src_node = "sat"+str(src_node) if src_node < len(satellites_by_index) else "gs"+str(src_node%len(satellites_by_index))
            dest_node = "sat"+str(dest_node) if dest_node < len(satellites_by_index) else "gs"+str(dest_node%len(satellites_by_index))
            routes_log = open(data_path+"/routes/"+str(src_node)+"_routes.txt", "a")
            routes_log.write(str(current_route)[1:-1] + "\n")
            routes_log.close()

            routes_log = open(data_path+"/routes/"+str(dest_node)+"_routes.txt", "a")
            current_route.reverse()
            routes_log.write(str(current_route)[1:-1] + "\n")
            routes_log.close()

    print("..... ALL data is Logged!\n")

def get_time(filename):
    file = open(filename, 'r')
    lines = file.readlines()
    used_time = lines[0]

    year, month, day, hour, minute, newscs = used_time.split(",")
    ts = load.timescale()
    t = ts.utc(int(year), int(month), int(day), int(hour), int(minute), float(newscs))
    print t.tt

    return {"tt": t,
            "year": year,
            "month": month,
            "day": day,
            "hour": hour,
            "minutes": minute,
            "newscs": newscs
        }

def get_sats_by_index(filename):
    satsFile = open(filename, 'r')
    lines = satsFile.readlines()
    satellites = []

    for i in range(len(lines)):
        satellites.append(lines[i].strip())

    return satellites

def get_sats_by_name(filename):
    satsFile = open(filename, 'r')
    lines = satsFile.readlines()
    satellites = []

    for i in range(len(lines)):
        satellites.append(lines[i].strip())

    return satellites

def parse_config_file(filepath, filename):
    configurations = {"simulation_time(second)":0, "mode":0, "simulation_step(second)":0, "Fresh_run":False, "ground_stations":"./", "constellation":"starlink", "experiment":2, "constellation_ip_range":"" , "False_run_archieve_path_foldername":"" ,"Debug":1}
    configFile = open(filepath+"/"+filename, 'r')
    configs = configFile.readlines()

    for config in configs:
        config_parameters = config.split(":")
        if config_parameters[1].strip().isdigit():
            configurations[str(config_parameters[0])]=int(config_parameters[1].strip())
        elif config_parameters[1].strip() == "False" or config_parameters[1].strip() == "True":
            if config_parameters[1].strip() == "False":
                configurations[str(config_parameters[0])] = False
            elif config_parameters[1].strip() == "True":
                configurations[str(config_parameters[0])] = True
        else:
            configurations[str(config_parameters[0])]=config_parameters[1].strip()

    return configurations

def main():

    # experiment 2 => Normal run with Starlink constellation and 100 Groud station read from ground_station.txt file
    # experiment 1 => Focusing on Alan's calibration experiment
    main_configurations = parse_config_file(".","config.txt")
    number_of_orbits = 0
    print main_configurations
    if main_configurations["experiment"] == 1:
        gs_Alan = {
            "gid": 0,
            "name": "Alan-Starlink",
            "latitude_degrees_str": "51.52132683544218",
            "longitude_degrees_str": "-1.7868832746954848",
            "elevation_m_float": 0.0,
            "cartesian_x": float(3974857.483),
            "cartesian_y": float(-124004.072),
            "cartesian_z": float(4969839.203),
        }

        gw_starlink = {
            "gid": 1,
            "name": "Starlink-GW-UK",
            "latitude_degrees_str": "51.614537",
            "longitude_degrees_str": "-0.574484",
            "elevation_m_float": 0.0,
            "cartesian_x": float(3968468.136),
            "cartesian_y": float(-39791.724),
            "cartesian_z": float(4976285.352),
        }

        ground_stations = [gs_Alan, gw_starlink]
    elif main_configurations["experiment"] == 2:
        ground_stations = read_gs(main_configurations["ground_stations"])

    if main_configurations["mode"] == 2:
        number_of_hw_sats = 1
        number_of_hw_gs = 1
        number_of_hw_nodes = number_of_hw_sats + number_of_hw_gs

        ground_stations_phys_index = []
        for gs in ground_stations:
            if gs["type"] == 1:
                ground_stations_phys_index.append(gs["gid"])

    SimulationTime_secs, SimTime_s = 1000, 1000
    Step_secs = 1

    actual_time = 0
    loggedTime = ""
    # data_timestamp = "2022,07,06,12,29,42.706750" #"2022,03,16,11,29,36.124013"
    data_path = main_configurations["False_run_archieve_path_foldername"]

    N = 3

    if main_configurations["Fresh_run"] == True:
        ts = load.timescale()
        actual_time = ts.now()

        dt, leap_second = actual_time.utc_datetime_and_leap_second()
        newscs = ((str(dt).split(" ")[1]).split(":")[2]).split("+")[0]
        date, timeN, zone = actual_time.utc_strftime().split(" ")
        year, month, day = date.split("-")
        hour, minute, second = timeN.split(":")
        loggedTime = str(year)+","+str(month)+","+str(day)+","+str(hour)+","+str(minute)+","+str(newscs)
        if main_configurations["Debug"] == 1:
            print " The Actual real time for the simulation is ", loggedTime

        data_path = "../data_gen/archieved_data_"+str(loggedTime)
        os.mkdir(data_path)

        if main_configurations["constellation"]=="starlink":
            tle_url = "https://celestrak.com/NORAD/elements/supplemental/starlink.txt"
            number_of_orbits = 72

        tle_file = wget.download(tle_url, out = data_path)
        satellites = load.tle_file("https://celestrak.com/NORAD/elements/supplemental/starlink.txt")

        satellites_by_name = {sat.name.split(" ")[0]: sat for sat in satellites}
        satellites_by_index = {}

        if main_configurations["mode"] == 2:
            satellites_phys_index = []
            satellites_phys = []
            for i in range(number_of_hw_sats):
                satellites_phys.append(satellites_by_name.items()[i])
                if main_configurations["Debug"]==1:
                    print "Satellite ", satellites_by_name.items()[i], " is a physical sateellite "

        orbital_data = get_orbital_planes_classifications(data_path+"/starlink.txt",1)

    elif main_configurations["Fresh_run"] == False:
        actual_time = get_time(data_path+"/time_log.txt")
        if main_configurations["Debug"]==1:
            print " The Actual real time for the simulation is ", actual_time["tt"].utc_strftime()

        if main_configurations["constellation"]=="starlink":
            satellites = load.tle_file("https://celestrak.com/NORAD/elements/supplemental/starlink.txt")
            number_of_orbits = 72

        satellites_by_name_from_file = get_sats_by_name(data_path+"/satellites_by_name_log.txt")
        satellites_by_name = {sat.name.split(" ")[0]: sat for sat in satellites if sat.name.split(" ")[0] in satellites_by_name_from_file}
        satellites_by_index = {}

        if main_configurations["mode"] == 2:
            satellites_phys_index = []
            satellites_phys = []
            for i in range(number_of_hw_sats):
                satellites_phys.append(satellites_by_name.items()[i])
                if main_configurations["Debug"]==1:
                    print "Satellite ", satellites_by_name.items()[i], " is a physical sateellite "

        orbital_data = get_orbital_planes_classifications(data_path+"/starlink.txt",1)

############################################################################################################################################################
############################################################################################################################################################
############################################################################################################################################################

# [[Orbital Data]] Sort the satellites in the orbit. We need that in order to know the adjacent satellites
# in the same orbit.
    f = open(data_path+"/sorted_satellites_within_orbit.txt", "a")
    if main_configurations["Debug"] == 1:
        print "..... Phase-1: Constellation Orbits:"
    satellites_sorted_in_orbits = []        #carry satellites names according to STARLINK naming conversion (list of lists)
    for i in range(number_of_orbits):
        sorted = []
        satellites_in_orbit = []
        cn = 0
        for data in orbital_data:
            if i == int(orbital_data[str(data)][2]):
                satellites_in_orbit.append(satellites_by_name[str(data.split(" ")[0])])
                cn +=1
        if main_configurations["Debug"]==1:
            print ".......... Orbit no.    "+str(i)+"    ->  "+str(cn)+" satellites"

        if main_configurations["Fresh_run"] == False:
            sorted = sort_satellites_in_orbit(satellites_in_orbit, actual_time["tt"])
            satellites_sorted_in_orbits.append(sorted)
        elif main_configurations["Fresh_run"] == True:
            sorted = sort_satellites_in_orbit(satellites_in_orbit, actual_time)
            satellites_sorted_in_orbits.append(sorted)

        if main_configurations["Debug"]==1:
            for s in sorted:
                write_this = str(i)+" "+str(s.name)+" "+str(orbital_data[str(s.name)])+"\n"
                f.write(write_this)
    f.close()
# Update the satellite_by_index
    sat_index = -1
    for orbit in satellites_sorted_in_orbits:
        for i in range(len(orbit)):
            sat_index += 1
            satellites_by_index[sat_index] = orbit[i].name.split(" ")[0]

            if main_configurations["mode"] == 2:
                for phys in satellites_phys:
                    if orbit[i].name.split(" ")[0] in phys[0]:
                        satellites_phys_index.append(sat_index)
                        if main_configurations["Debug"] == 1:
                            print "Satellite ", orbit[i].name.split(" ")[0], " is a physical satellite and its index = ", sat_index
####
    num_of_satellites = len(orbital_data)
    num_of_ground_stations = len(ground_stations)
    if main_configurations["Debug"] == 1:
        print ".......... total number of satellites = ", num_of_satellites
        print ".......... total number of ground_stations = ", num_of_ground_stations

    if main_configurations["Debug"] == 1:
        print "------------------------------------------------------------------"
# [[Build Topology and Links]] Build the network topology, specifically, the Inter-Satellites-Links (mininet_add_ISLs) and GroundStation-Satellites-Links (mininet_add_GSLs)
# Compute links charateristics in terms of latency, bandwidth and snr
    if main_configurations["Debug"] == 1:
        print "..... Phase-2: Build Topology"
    conn_mat_size = num_of_satellites + num_of_ground_stations
    connectivity_matrix = [[0 for c in range(conn_mat_size)] for r in range(conn_mat_size)]

    start = round(time.time()*1000)
    if main_configurations["Fresh_run"] == False:
        connectivity_matrix = mininet_add_ISLs(connectivity_matrix, satellites_sorted_in_orbits, satellites_by_name, satellites_by_index, "SAME_ORBIT_AND_GRID_ACROSS_ORBITS", actual_time["tt"])
        connectivity_matrix = mininet_add_GSLs(connectivity_matrix, satellites_by_name, satellites_by_index, ground_stations, 12, "BASED_ON_DISTANCE_ONLY_MININET", actual_time["tt"])
    elif main_configurations["Fresh_run"] == True:
        connectivity_matrix = mininet_add_ISLs(connectivity_matrix, satellites_sorted_in_orbits, satellites_by_name, satellites_by_index, "SAME_ORBIT_AND_GRID_ACROSS_ORBITS", actual_time)
        connectivity_matrix = mininet_add_GSLs(connectivity_matrix, satellites_by_name, satellites_by_index, ground_stations, 12, "BASED_ON_DISTANCE_ONLY_MININET", actual_time)
    end = round(time.time()*1000)
    if main_configurations["Debug"] == 1:
        print ".......... Initial Connectivity Matrix for", main_configurations["constellation"], "Constellation is created in", (end-start)/1000, "secs"

    gs_statellite_pair = get_gs_sat_pairs(connectivity_matrix, num_of_satellites)

    start = round(time.time()*1000)
    if main_configurations["Fresh_run"] == False:
        links_charateristics = calculate_link_charateristics_for_gsls_isls(connectivity_matrix, satellites_by_index, satellites_by_name, ground_stations, actual_time["tt"])
    elif main_configurations["Fresh_run"] == True:
        links_charateristics = calculate_link_charateristics_for_gsls_isls(connectivity_matrix, satellites_by_index, satellites_by_name, ground_stations, actual_time)
    end = round(time.time()*1000)

    if main_configurations["Debug"] == 1:
        print ".......... GSL and ISL Links Characteristics for", main_configurations["constellation"], "Constellation is calculated in", (end-start)/1000, "secs"

    available_ips = generate_ips_for_constellation(main_configurations["constellation_ip_range"])
    available_ips_phys = generate_ips_for_physical_nodes(10)

####
# [[Routing and Mininet]] Compute the all the routes to all nodes in the topology. We need these routes before we go into mininet to do initial routing table configuration
# for all nodes in Mininet. We then pass these info to Mininet to create the topology there

    if main_configurations["Debug"] == 1:
        print "------------------------------------------------------------------"
        print "..... Phase-3: Pre-compute Routing Tables:"

    start = round(time.time()*1000)
    TopologyRoutes = get_topology_routes(main_configurations["Fresh_run"], data_path, num_of_satellites, satellites_by_index, ground_stations, connectivity_matrix, links_charateristics)
    end = round(time.time()*1000)

    if main_configurations["Debug"] == 1:
        in_sec = (end-start)/1000.0
        print ".......... Routing Pre-computation for", main_configurations["constellation"], "Constellation is completed in", (end-start)/1000, "secs"
        print ".......... Total Number of routes for", main_configurations["constellation"], "Constellation is", len(TopologyRoutes["All_PreConfigured_routes"]), "routes"

    if main_configurations["Debug"] == 1:
        print "------------------------------------------------------------------"
        print "..... Phase-4: Configure Mininet:"

    topology = sat_network(N=N)

    if main_configurations["mode"] == 1:
        ground_stations_phys_index = []
        satellites_phys_index = []

    topg = topology.create_sat_network(satellites=satellites_by_index, ground_stations=ground_stations, connectivity_matrix=connectivity_matrix, link_throughput=links_charateristics["throughput_matrix"], link_latency=links_charateristics["latency_matrix"], Tmode=main_configurations["mode"], physical_gs_index=ground_stations_phys_index, physical_sats_index=satellites_phys_index)

    net = Mininet(topo = topology, link=TCLink, autoSetMacs = True, controller=OVSController)
    net.start()
    list_of_Intf_IPs = topology.initial_ipv4_assignment_for_interfaces_optimised(data_path, net, available_ips, available_ips_phys)
    if main_configurations["Fresh_run"] == True:
        dump_ALL(data_path, loggedTime, topg["isl_gls_links"], topg["management_interface"], satellites_by_index, satellites_by_name, TopologyRoutes["All_PreConfigured_routes"])

    if main_configurations["Debug"] == 1:
        print "------------------------------------------------------------------"
        print "..... Phase-5: Generate IP Route Linux Commands:"

    links_hash = {}
    for link in topg["isl_gls_links"]:
        endpoint1, endpoint2 = link.split(":")
        endpoints = str(endpoint1.split("-")[0])+"_"+str(endpoint2.split("-")[0])
        links_hash[str(endpoints)] = []
        links_hash[str(endpoints)].append(link)

    start = round(time.time()*1000)
    prepare_routing_config_commands(topology, data_path, TopologyRoutes["All_PreConfigured_routes"], links_hash, list_of_Intf_IPs, satellites_by_index, 20);
    end = round(time.time()*1000)

    if main_configurations["Debug"] == 1:
        print ".......... Generateing the IP Route commands for", main_configurations["constellation"], "Constellation is completed in", (end-start)/1000, "secs"

    if main_configurations["Debug"] == 1:
        print "------------------------------------------------------------------"
        print "..... Phase-6: Compute Ground Stations Routing:"

    start = round(time.time()*1000)
    gs_routing(data_path, gs_statellite_pair, links_hash, num_of_satellites, satellites_by_index, list_of_Intf_IPs, TopologyRoutes["Routes_per_satellites"])
    end = round(time.time()*1000)

    if main_configurations["Debug"] == 1:
        print ".......... Ground Stations Routes for", main_configurations["constellation"], "Constellation is completed in", (end-start)/1000, "secs"

    if main_configurations["Debug"] == 1:
        print "------------------------------------------------------------------"
        print "..... Phase-7: Deploy the IP Route Commands on Mininet VMs:"

    start = round(time.time()*1000)
    topology.startRoutingConfigV2(data_path,net, satellites_by_index, ground_stations, topg["management_interface"])
    end = round(time.time()*1000)
    if main_configurations["Debug"] == 1:
        print "......... Deploy the IP Route commands for", main_configurations["constellation"], "Constellation is completed in", (end-start)/1000, "secs"
####
    # sc = data_path+"/stat_r.sh"
    # CLI(net, script=sc)
    CLI(net)
    net.stop()
    # dump_ALL(data_path, loggedTime, topg["isl_gls_links"], topg["management_interface"], satellites_by_index, satellites_by_name, TopologyRoutes["All_PreConfigured_routes"], GS_SAT_Table)
    exit()
####
#
####
# [[Iterative Simulation]] Now we compute the changes in the topology ever Step_secs and store that.
#
    addthis = 0
    links_updated = topg["isl_gls_links"][:]
    last_CMatrix = []
    updates_files_name = []
    while SimulationTime_secs > 0:
        start1 = round(time.time()*1000)
        SimulationTime_secs -= Step_secs
        addthis += Step_secs

        if FreshRun == True:
            actual_time = get_time(data_path+"/time_log.txt")

        ts = load.timescale()
        actual_time_increment = ts.utc(int(actual_time["year"]), int(actual_time["month"]), int(actual_time["day"]), int(actual_time["hour"]), int(actual_time["minutes"]), float(actual_time["newscs"])+addthis)
        print "----------------------", actual_time_increment.utc_strftime(), "----------------------"

        new_GS_SAT_Table = [[] for i in range(num_of_satellites)]
        new_CMatrix = [[0 for c in range(conn_mat_size)] for r in range(conn_mat_size)]

        start = round(time.time()*1000)
        new_CMatrix = mininet_add_ISLs(new_CMatrix, satellites_sorted_in_orbits, satellites_by_name, satellites_by_index, "SAME_ORBIT_AND_GRID_ACROSS_ORBITS", actual_time_increment)
        new_CMatrix = mininet_add_GSLs(new_CMatrix, satellites_by_name, satellites_by_index, ground_stations, 12, "BASED_ON_DISTANCE_ONLY_MININET", actual_time_increment, 1, new_GS_SAT_Table)
        end = round(time.time()*1000)

        # print " Re calculate the ISL and GSL links took ", end-start, "ms "

        if len(last_CMatrix) > 0:
            route_changes = check_changes_in_routes(last_CMatrix, new_CMatrix)

            # print " at ", actual_time_increment.utc_strftime(), "there are ", len(route_changes), " route changes"
            updates_files_name.append(str(actual_time_increment.utc_strftime())+"_.txt")
            if len(route_changes) < 400:
                lightweight_routing(data_path, route_changes, links_hash, num_of_satellites, satellites_by_index, list_of_Intf_IPs, TopologyRoutes["Routes_per_satellites"], actual_time_increment)
                # we need to update links_updated
        last_CMatrix = new_CMatrix[:]
        end1 = round(time.time()*1000)
        # print " Route update iteration took  ", (end1-start1), "ms "
    CLI(net)
    net.stop()
    exit()
# # ####
# # ####

    thread_performance = threading.Thread(target=iperf_thread, args=(net,))
    thread_performance.start()
    # thread_performance = threading.Thread(target=background_loop, args=(data_path, net, SimulationTime_secs, num_of_satellites,))
    # thread_performance.start()
    #
    # CLI(net)
    # net.stop()
    # exit()

    updates_files_name = []
    for fileLog in os.listdir(data_path):
        if fileLog.startswith("allchanges_log"):
            a = re.split('_| ',fileLog)
            filesd = a[2]+" "+a[3]+" "+a[4]
            updates_files_name.append(filesd)

    updates_files_name.sort()
    print len(updates_files_name)
    time_counter = 0
    for file in updates_files_name:
        if time_counter > SimTime_s:
            exit()

        start = round(time.time()*1000)
        # print "[ %0.12f" % round(time.time() * 1000),"] Start --> ", file
        net = update_loop(data_path, net, file, num_of_satellites);
        end = round(time.time()*1000)
        print "for file ", file, " it took ", (end-start)
        # print "[ %0.12f" % round(time.time() * 1000),"] End   --> ", file
        time_counter += 1

    exit()
####
#####

setLogLevel('info')    # 'info' is normal; 'debug' is for when there are problems
main()
