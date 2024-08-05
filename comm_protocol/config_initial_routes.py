import socket
import time
import subprocess
import threading
import os
import gc
import sys

sys.path.append("../")
from routing.constellation_routing import *

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

def get_links(filename):
    linksFile = open(filename, 'r')
    lines = linksFile.readlines()
    links = []

    for i in range(len(lines)):
        links.append(lines[i].strip())

    return links

def get_sats_by_index(filename):
    satsFile = open(filename, 'r')
    lines = satsFile.readlines()
    satellites = []

    for i in range(len(lines)):
        satellites.append(lines[i].strip())

    return satellites

def main():
    # links = get_links("../controller/data_gen/current_tle_data/links_log.txt")
    # list_of_Intf_IPs = get_intf("../controller/data_gen/current_tle_data/constellation_ip_assignment.txt")
    # satellites_by_index = get_sats_by_index("../controller/data_gen/current_tle_data/satellites_by_index_log.txt")

    links = get_links("../controller/data_gen/temp/links_log.txt")
    list_of_Intf_IPs = get_intf("../controller/data_gen/temp/constellation_ip_assignment.txt")
    satellites_by_index = get_sats_by_index("../controller/data_gen/temp/satellites_by_index_log.txt")


    GS_SAT_Table = get_gs_sat_table()

    # route_file = open("../controller/data_gen/current_tle_data/routes/"+str(sys.argv[1])+"_routes.txt", 'r')
    route_file = open("../controller/data_gen/temp/routes/"+str(sys.argv[1])+"_routes.txt", 'r')
    routes = route_file.readlines()

    start = round(time.time()*1000)
    for route in routes:
        route_new = []
        route_list = re.split(", | |\n", route)
        route = [int(r) for r in route_list if r.strip()]
        route_new.append(route)
        parameters = get_static_route_parameter(route_new, links, list_of_Intf_IPs, satellites_by_index)
        # print parameters
        command = ["ip", "route", "add", parameters[1], "via", parameters[2], "dev", parameters[3]]
        subprocess.call(command)

    end = round(time.time()*1000)
    timelapsed = end-start
    logg = open('logs/log-'+str(sys.argv[1])+'.txt', 'a')
    logg.write("This process from "+str(sys.argv[1])+". It takes "+str(timelapsed)+"ms to complete " + "\n")
    logg.close()

main()
exit()
