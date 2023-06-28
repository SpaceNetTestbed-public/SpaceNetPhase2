import argparse
import re
import time
import os
import numpy as np
import datetime

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

import sys
sys.path.append("../")
from mobility.read_real_tles import *
from mobility.read_live_tles import *
from mobility.mobility_utils import *
from mobility.read_gs import *
from routing.routing_utils import *
from routing.constellation_routing import *
from comm_protocol.controller_main import *

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

number_of_orbits = 72

print ground_stations

satellites = load.tle_file("https://celestrak.com/NORAD/elements/starlink.txt")
satellites_by_name = {sat.name: sat for sat in satellites}
satellites_by_index = {}


# tle_url = "https://celestrak.com/NORAD/elements/supplemental/starlink.txt"
# tle_file = wget.download(tle_url, out = "./")

orbital_data = get_orbital_planes_classifications("./starlink.txt",1)

ts = load.timescale()
t = ts.now()
print t.utc_strftime()

dt, leap_second = t.utc_datetime_and_leap_second()
newscs = ((str(dt).split(" ")[1]).split(":")[2]).split("+")[0]
date, timeN, zone = t.utc_strftime().split(" ")
year, month, day = date.split("-")
hour, minute, second = timeN.split(":")
loggedTime = str(year)+","+str(month)+","+str(day)+","+str(hour)+","+str(minute)+","+str(newscs)
t2 = ts.utc(int(year), int(month), int(day), int(hour), int(minute), float(newscs))
print t2.tt


satellites_sorted_in_orbits = []        #carry satellites names according to STARLINK naming conversion
for i in range(number_of_orbits):
    satellites_in_orbit = []
    cn = 0
    for data in orbital_data:
        if i == int(orbital_data[str(data)][2]):
            satellites_in_orbit.append(satellites_by_name[str(data)])
            print i, data, orbital_data[str(data)]
            cn +=1
    print i, cn

    satellites_sorted_in_orbits.append(sort_satellites_in_orbit(satellites_in_orbit, t))

sat_index = -1
for orbit in satellites_sorted_in_orbits:
    for i in range(len(orbit)):
        sat_index += 1
        satellites_by_index[sat_index] = orbit[i].name
        print sat_index, orbit[i].name

num_of_satellites = len(orbital_data)
num_of_ground_stations = len(ground_stations)
GS_SAT_Table = [[] for i in range(num_of_satellites)]

print num_of_satellites, num_of_ground_stations

print t
print t.utc_strftime()
dt, leap_second = t.utc_datetime_and_leap_second()
print dt
conn_mat_size = num_of_satellites + num_of_ground_stations

addthis = 0
while 1:
    ts = load.timescale()
    t = ts.now()
    addthis += 1
    t = ts.utc(int(2022), int(3), int(4), int(12), int(47), float(0)+addthis)
    print t.utc_strftime()
    # print t.utc_strftime()
    connectivity_matrix = [[0 for c in range(conn_mat_size)] for r in range(conn_mat_size)]
    connectivity_matrix = mininet_add_GSLs(connectivity_matrix, satellites_by_name, satellites_by_index, ground_stations, 12, "BASED_ON_DISTANCE_ONLY_MININET", t, 1, GS_SAT_Table)
