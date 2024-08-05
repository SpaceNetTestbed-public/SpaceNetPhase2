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

import socket
import time
import subprocess
import threading

import sys
sys.path.append("../")
from mobility.read_real_tles import *
from mobility.mobility_utils import *
from mobility.read_gs import *
from mininet_infra.create_mininet_topology import *
from routing.routing_utils import *
from comm_protocol.controller_main import *


def main():
    satellites = load.tle_file("https://celestrak.com/NORAD/elements/starlink.txt")
    satellites_by_name = {sat.name: sat for sat in satellites}
    planes = extract_planes("../mobility/starlink_tles_Nov.txt")

    cur_planes = planes["Planes"]
    print(len(planes["Unassigned"]))
    ts = load.timescale()
    t = ts.now()
    print(t)
    # print cur_planes
    # print satellites_by_name
    sorted_planes = sort_satellites_within_plane(cur_planes, satellites_by_name, t)

    # Get the satellites in planes only, igonore the Unassigned satellites
    available_satellites = []
    for key in list(sorted_planes.keys()):
        sats = ""
        for satellite in sorted_planes[key]:
            sats += str(satellites_by_name[str(satellite)].name).split("-")[1]+","
            available_satellites.append(satellites_by_name[str(satellite)])

    available_satellites_by_name = {sat.name: sat for sat in available_satellites}
    actual_sat_number_to_counter = label_satellites_properly(sorted_planes, len(available_satellites_by_name))

    with open('satellites_num.txt','w') as file2:
        for i in range(len(actual_sat_number_to_counter)):
            file2.write(str(actual_sat_number_to_counter[i]))
            file2.write('\n')

    ground_stations = read_gs("../mobility/ground_stations.txt")

    num_of_satellites = len(available_satellites_by_name)
    num_of_ground_stations = len(ground_stations)

    conn_mat_size = num_of_satellites + num_of_ground_stations

    connectivity_matrix = [[0 for c in range(conn_mat_size)] for r in range(conn_mat_size)]
    connectivity_matrix = mininet_add_ISLs(connectivity_matrix, available_satellites_by_name, actual_sat_number_to_counter, sorted_planes, 0, 0, "SAME_ORBIT_AND_BASED_ON_DISTANCE_FOR_INTER_ORBIT", t)

    with open('connectivity_matrix.txt','w') as file:
        for i in range(len(connectivity_matrix)):
            for j in range(len(connectivity_matrix[i])):
                file.write(str(i)+"\t"+str(j)+"\t"+str(connectivity_matrix[i][j]))
                file.write('\n')

    print("done")
    # os.system("python satellite_worker.py sat10 "+connectivity_matrix)
main()
