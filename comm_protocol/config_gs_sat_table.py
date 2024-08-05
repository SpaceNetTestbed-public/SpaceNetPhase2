import socket
import time
import subprocess
import threading
import os
import gc
import sys

sys.path.append("../")
from routing.constellation_routing import *
from routing.routing_utils import *

def get_gs_ip(list_of_Intf_IPs, gs):
    for pair in list_of_Intf_IPs:
        if gs in pair["Interface"]:
            return pair["IP"]

def get_intf(filename):
    Intf_file = open(filename, 'r')
    lines = Intf_file.readlines()
    list_of_Intf_IPs = []

    for i in range(len(lines)):
        intf, ip = lines[i].strip().split("\t")
        list_of_Intf_IPs.append({"Interface": intf, "IP": ip})

    return list_of_Intf_IPs

def get_gs_sat_table(filename):
    gs_sat_file = open(filename, 'r')
    lines = gs_sat_file.readlines()
    GS_SAT_Table = []

    for line in lines:
        sat_gs = line.strip().split("\t")
        gss = sat_gs[1].split(",")
        dict = {"satellite": sat_gs[0], "list_of_gs": gss}
        GS_SAT_Table.append(dict)

    return GS_SAT_Table

def find_the_route_of_this_destination_sat(sat_number, list_of_Intf_IPs):
    links = get_links("../controller/data_gen/links_log.txt")
    satellites_by_index = get_sats_by_index("../controller/data_gen/satellites_by_index_log.txt")

    route_file = open("../controller/data_gen/routes/"+str(sys.argv[1])+"_routes.txt", 'r')
    routes = route_file.readlines()

    for route in routes:
        if sat_number in route:
            parameters = get_static_route_parameter(route, links, list_of_Intf_IPs, satellites_by_index)

    return parameters

def main():
    list_of_Intf_IPs = get_intf("../controller/data_gen/constellation_ip_assignment.txt")

    GS_SAT_Table = get_gs_sat_table("../controller/data_gen/GS_SAT_Table.txt")

    for item in GS_SAT_Table:
        if len(item["list_of_gs"]) > 0:
            for i in range(len(item["list_of_gs"])):
                gs_ip = get_gs_ip(list_of_Intf_IPs, "gs"+str(item["list_of_gs"][i])+"-eth1")
                gs_network_address = get_network_address(gs_ip)
                parameters = find_the_route_of_this_destination_sat(item["satellite"], list_of_Intf_IPs)

                command = ["ip", "route", "add", gs_network_address, "via", parameters[2], "dev", parameters[3]]
                print(command)
                # subprocess.call(command)


    # end = round(time.time()*1000)
    # timelapsed = end-start
    # logg = open('logs/log-gs-sat-'+str(sys.argv[1])+'.txt', 'a')
    # logg.write("This process from "+str(sys.argv[1])+". It takes "+str(timelapsed)+"ms to complete " + "\n")
    # logg.close()

main()
exit()
